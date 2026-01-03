"""
DW2Salesforce Sync Monitor
Compares SQL view data with Salesforce Account data to detect sync issues.
"""

import os
import pyodbc
from datetime import datetime
import json

# ============================================================================
# Configuration
# ============================================================================

# SQL Server Configuration (from your mcp.json)
MSSQL_CONFIG = {
    'driver': os.getenv('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server'),
    'server': os.getenv('MSSQL_HOST', 'ea-sqlserver-enterpriseanalytics-shared.database.windows.net'),
    'database': os.getenv('MSSQL_DATABASE', 'ea-prod-sqldb-semanticdb'),
    'tenant_id': os.getenv('AZURE_TENANT_ID'),
    'client_id': os.getenv('AZURE_CLIENT_ID'),
    'client_secret': os.getenv('AZURE_CLIENT_SECRET')
}

# Sample ESO Internal IDs to monitor
SAMPLE_IDS = ['1', '10', '100', '1000', '10000']

# Fields to compare
COMPARE_FIELDS = [
    'CAPDB_Score_Num__c',
    'CAPDB_Grade_syncari__c',
    'Greenspace_SAM__c',
    'Whitespace_SAM__c',
    'EDW_Account_Status__c',
    'FH_Product_Status__c',
    'Emergency_Reporting_Product_Status__c'
]

# ============================================================================
# Functions
# ============================================================================

def get_sql_connection():
    """Connect to SQL Server using Azure AD authentication."""
    from azure.identity import ClientSecretCredential
    
    credential = ClientSecretCredential(
        tenant_id=MSSQL_CONFIG['tenant_id'],
        client_id=MSSQL_CONFIG['client_id'],
        client_secret=MSSQL_CONFIG['client_secret']
    )
    
    token = credential.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    
    conn_str = (
        f"DRIVER={{{MSSQL_CONFIG['driver']}}};"
        f"SERVER={MSSQL_CONFIG['server']};"
        f"DATABASE={MSSQL_CONFIG['database']};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
    )
    
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
    return conn


def get_sql_data(eso_ids):
    """Fetch data from SQL view."""
    print(f"📊 Fetching SQL view data for {len(eso_ids)} accounts...")
    
    conn = get_sql_connection()
    cursor = conn.cursor()
    
    ids_str = "', '".join(eso_ids)
    query = f"""
    SELECT 
        ESO_Internal_ID__c,
        CAPDB_Score_Num__c,
        CAPDB_Grade_syncari__c,
        Greenspace_SAM__c,
        Whitespace_SAM__c,
        EDW_Account_Status__c,
        FH_Product_Status__c,
        Emergency_Reporting_Product_Status__c
    FROM [bi].[vw_salesforce_dw2SF_account]
    WHERE ESO_Internal_ID__c IN ('{ids_str}')
    ORDER BY ESO_Internal_ID__c
    """
    
    cursor.execute(query)
    columns = [column[0] for column in cursor.description]
    results = {}
    
    for row in cursor.fetchall():
        eso_id = row[0]
        results[eso_id] = dict(zip(columns, row))
    
    cursor.close()
    conn.close()
    
    print(f"✅ Retrieved {len(results)} records from SQL")
    return results


def get_salesforce_data(eso_ids):
    """
    Fetch data from Salesforce using sf CLI.
    Note: Requires Salesforce CLI and authenticated org.
    """
    print(f"☁️  Fetching Salesforce data for {len(eso_ids)} accounts...")
    
    import subprocess
    
    fields = ', '.join(COMPARE_FIELDS)
    ids_str = "', '".join(eso_ids)
    
    query = (
        f"SELECT Id, ESO_Internal_ID__c, {fields} "
        f"FROM Account "
        f"WHERE ESO_Internal_ID__c IN ('{ids_str}') "
        f"ORDER BY ESO_Internal_ID__c"
    )
    
    cmd = [
        'sf', 'data', 'query',
        '--query', query,
        '--target-org', 'benjamin.mason@eso.com',
        '--json'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error querying Salesforce: {result.stderr}")
        return {}
    
    data = json.loads(result.stdout)
    results = {}
    
    for record in data.get('result', {}).get('records', []):
        eso_id = record.get('ESO_Internal_ID__c')
        if eso_id:
            results[eso_id] = record
    
    print(f"✅ Retrieved {len(results)} records from Salesforce")
    return results


def compare_records(sql_data, sf_data):
    """Compare SQL and Salesforce data and report differences."""
    print("\n" + "="*80)
    print("🔍 COMPARISON RESULTS")
    print("="*80 + "\n")
    
    all_ids = sorted(set(list(sql_data.keys()) + list(sf_data.keys())))
    mismatches = []
    
    for eso_id in all_ids:
        sql_record = sql_data.get(eso_id, {})
        sf_record = sf_data.get(eso_id, {})
        
        print(f"\n📋 ESO_Internal_ID__c = {eso_id}")
        print("-" * 80)
        
        if not sql_record:
            print("  ⚠️  NOT FOUND in SQL view")
            continue
        
        if not sf_record:
            print("  ⚠️  NOT FOUND in Salesforce")
            continue
        
        has_mismatch = False
        record_mismatches = []
        
        for field in COMPARE_FIELDS:
            sql_value = sql_record.get(field)
            sf_value = sf_record.get(field)
            
            # Handle float comparison with tolerance
            if isinstance(sql_value, (int, float)) and isinstance(sf_value, (int, float)):
                if abs(float(sql_value) - float(sf_value)) > 0.01:
                    match = False
                else:
                    match = True
            else:
                match = str(sql_value) == str(sf_value)
            
            status = "✅" if match else "❌"
            
            if not match:
                has_mismatch = True
                record_mismatches.append({
                    'field': field,
                    'sql_value': sql_value,
                    'sf_value': sf_value
                })
                print(f"  {status} {field}:")
                print(f"       SQL: {sql_value}")
                print(f"       SF:  {sf_value}")
        
        if not has_mismatch:
            print("  ✅ All fields match!")
        else:
            mismatches.append({
                'eso_id': eso_id,
                'sf_id': sf_record.get('Id'),
                'fields': record_mismatches
            })
    
    return mismatches


def generate_report(mismatches):
    """Generate a summary report."""
    print("\n" + "="*80)
    print("📊 SUMMARY REPORT")
    print("="*80 + "\n")
    
    if not mismatches:
        print("🎉 ALL RECORDS MATCH! Pipeline is working correctly.")
        return
    
    print(f"❌ Found {len(mismatches)} accounts with mismatches\n")
    
    field_mismatch_counts = {}
    for mismatch in mismatches:
        for field_info in mismatch['fields']:
            field = field_info['field']
            field_mismatch_counts[field] = field_mismatch_counts.get(field, 0) + 1
    
    print("📈 Most Common Field Mismatches:")
    for field, count in sorted(field_mismatch_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {field}: {count} records")
    
    print("\n💡 Recommendations:")
    print("  1. Check if DW2SF pipeline is running on schedule")
    print("  2. Verify SQL view has current data (run investigate_dw2sf_source.sql)")
    print("  3. Check Bulk API job logs for the time period")
    print("  4. Review pipeline code for data transformation issues")
    
    # Save detailed report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"dw2sf_mismatch_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total_mismatches': len(mismatches),
            'mismatches': mismatches,
            'field_counts': field_mismatch_counts
        }, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("🔍 DW2SALESFORCE SYNC MONITOR")
    print("="*80 + "\n")
    print(f"Monitoring {len(SAMPLE_IDS)} sample accounts...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Fetch data from both sources
        sql_data = get_sql_data(SAMPLE_IDS)
        sf_data = get_salesforce_data(SAMPLE_IDS)
        
        # Compare and report
        mismatches = compare_records(sql_data, sf_data)
        generate_report(mismatches)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import struct
        import pyodbc
        from azure.identity import ClientSecretCredential
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\nPlease install required packages:")
        print("  pip install pyodbc azure-identity")
        exit(1)
    
    main()




