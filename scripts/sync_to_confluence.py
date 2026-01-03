"""
Sync Git repository markdown files to Confluence
Target: enterpriseanalytics space > semantic folder
"""

import os
import sys
from pathlib import Path
from atlassian import Confluence
from md2cf.confluence_renderer import ConfluenceRenderer
import mistune

# ========================================
# CONFIGURATION
# ========================================

CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://esosolutions.atlassian.net/wiki")
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME")  # Load from environment/Bitwarden
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN")  # Load from environment/Bitwarden
CONFLUENCE_SPACE_KEY = "IA"  # Infrastructure & Analytics space
PARENT_PAGE_TITLE = "semantic"  # Your folder name
ENTERPRISE_ANALYTICS_PAGE_ID = "5887492434"  # Enterprise Analytics parent page

# Check for required credentials
if not CONFLUENCE_USERNAME or not CONFLUENCE_API_TOKEN:
    print("[ERROR] Missing required environment variables!")
    print("Please set CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN")
    print("Run: .\\load-secrets-from-bitwarden.ps1")
    print("Or set manually: $env:CONFLUENCE_USERNAME='your-email'; $env:CONFLUENCE_API_TOKEN='your-token'")
    sys.exit(1)

# ========================================
# FILE MAPPING
# ========================================

# Map Git files to Confluence page titles
FILE_MAPPINGS = {
    "README.md": {
        "title": "Home",
        "parent": PARENT_PAGE_TITLE
    },
    "GETTING_STARTED.md": {
        "title": "Getting Started: AI-Enhanced Data Engineering Framework",
        "parent": "Onboarding"
    },
    "QUICK_START_GUIDE.md": {
        "title": "Quick Start Guide: Your First Hour with Cursor",
        "parent": "Onboarding"
    },
    "TEAM_README.md": {
        "title": "ESO BI Semantic Repository",
        "parent": "Onboarding"
    },
    "GIT_SETUP_GUIDE.md": {
        "title": "Git Repository Setup Guide",
        "parent": "Onboarding"
    },
    "CONFLUENCE_INTEGRATION_GUIDE.md": {
        "title": "Confluence Integration Guide",
        "parent": "Onboarding"
    },
    "_diagrams/SYSTEM_ARCHITECTURE_CONFLUENCE.md": {
        "title": "System Architecture",
        "parent": PARENT_PAGE_TITLE
    },
    "RECOMMENDATIONS.md": {
        "title": "Recommendations",
        "parent": PARENT_PAGE_TITLE
    },
    "CONTRIBUTING.md": {
        "title": "Contributing",
        "parent": PARENT_PAGE_TITLE
    },
    "DOCUMENTATION_INDEX.md": {
        "title": "Documentation Index",
        "parent": PARENT_PAGE_TITLE
    },
    "salesforce/README.md": {
        "title": "Salesforce Overview",
        "parent": "Salesforce"
    },
    "salesforce/ARCHITECTURE_DIAGRAM.md": {
        "title": "Salesforce Architecture",
        "parent": "Salesforce"
    },
    "salesforce/kb/cursor/SALESFORCE_COMPLETE_LINEAGE.md": {
        "title": "Salesforce Complete Lineage",
        "parent": "Salesforce"
    },
    "salesforce/LINEAGE_GRAPH_RESULTS.md": {
        "title": "Lineage Graph Results",
        "parent": "Salesforce"
    },
    "jira/README.md": {
        "title": "Jira Overview",
        "parent": "Jira"
    },
    "jira/kb/cursor/flows/JIRA_DATA_FLOW.md": {
        "title": "Jira Data Flow",
        "parent": "Jira"
    },
    "jira/kb/cursor/JIRA_DATA_DICTIONARY.md": {
        "title": "Jira Data Dictionary",
        "parent": "Jira"
    },
    "jira/kb/cursor/JIRA_BUSINESS_RULES.md": {
        "title": "Jira Business Rules",
        "parent": "Jira"
    },
    "_templates/DATA_FLOW_TEMPLATE.md": {
        "title": "Data Flow Template",
        "parent": "Templates"
    },
    "_templates/CONTEXT_TEMPLATE.md": {
        "title": "Context Template",
        "parent": "Templates"
    },
    "_templates/POWER_BI_BEST_PRACTICES.md": {
        "title": "Power BI Best Practices",
        "parent": "Templates"
    },
    "core/kb/cursor/TAM_SAM_BUSINESS_OVERVIEW.md": {
        "title": "TAM/SAM Business Overview",
        "parent": "TAM SAM"
    },
    "core/kb/cursor/TAM_SAM_DATA_DICTIONARY_SUMMARY.md": {
        "title": "TAM/SAM Data Dictionary (Summary)",
        "parent": "TAM SAM"
    },
    "salesforce/ARR_CALCULATION_DISCREPANCIES.md": {
        "title": "ARR Calculation Discrepancies",
        "parent": "Known Issues"
    },
    "core/kb/cursor/KNOWN_ISSUES_LOGIS_ARR_GRANULARITY.md": {
        "title": "Logis Acquisition ARR Granularity",
        "parent": "Known Issues"
    },
    "salesforce/CPQ_LINEAGE_GRAPHS.md": {
        "title": "CPQ Data Lineage",
        "parent": "Salesforce"
    },
    # Sales Domain - Bookings & Pipeline
    "sales/kb/cursor/BOOKINGS_PIPELINE_OVERVIEW.md": {
        "title": "Bookings & Pipeline Data Model",
        "parent": "Sales"
    },
    "sales/kb/cursor/BOOKINGS_PIPELINE_TECHNICAL.md": {
        "title": "Bookings & Pipeline Technical Reference",
        "parent": "Sales"
    },
    # Onboarding Documentation - Cursor Setup subfolder
    "CURSOR_ONBOARDING_CHECKLIST.md": {
        "title": "Complete Setup Guide",
        "parent": "Cursor Setup"
    },
    "BITWARDEN_SETUP_GUIDE.md": {
        "title": "Bitwarden Integration",
        "parent": "Cursor Setup"
    },
    "MCP_SECURITY_GUIDE.md": {
        "title": "MCP Security Configuration",
        "parent": "Cursor Setup"
    },
    "QUICK_START_MCP.md": {
        "title": "MCP Quick Reference",
        "parent": "Cursor Setup"
    },
    # dbt Project Guide
    "dbt_local/GENERIC_DBT_PARQUET_GUIDE.md": {
        "title": "Building a dbt Project with Medallion Architecture",
        "parent": "Onboarding"
    }
}

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_or_create_page(confluence, space_key: str, parent_title: str, page_title: str) -> str:
    """
    Get existing page ID or create new page under parent
    Returns page_id
    """
    # Try to find existing page
    try:
        page = confluence.get_page_by_title(space=space_key, title=page_title)
        if page:
            print(f"[OK] Found existing page: {page_title}")
            return page['id']
    except Exception:
        print(f"[INFO] Page not found, will create: {page_title}")
    
    # Get parent page ID
    try:
        parent_page = confluence.get_page_by_title(space=space_key, title=parent_title)
        if not parent_page:
            print(f"[ERROR] Parent page '{parent_title}' not found!")
            return None
        parent_id = parent_page['id']
    except Exception as e:
        print(f"[ERROR] Error getting parent page '{parent_title}': {e}")
        return None
    
    # Create new page
    try:
        new_page = confluence.create_page(
            space=space_key,
            title=page_title,
            body="<p>Content will be updated...</p>",
            parent_id=parent_id
        )
        print(f"[OK] Created new page: {page_title}")
        return new_page['id']
    except Exception as e:
        print(f"[ERROR] Error creating page '{page_title}': {e}")
        return None


def update_page_content(confluence, page_id: str, page_title: str, content: str):
    """
    Update page content
    """
    try:
        # Get current page to get version number
        page = confluence.get_page_by_id(page_id, expand='version')
        
        # Update page
        confluence.update_page(
            page_id=page_id,
            title=page_title,
            body=content,
            parent_id=None,
            type='page',
            representation='storage',
            minor_edit=False
        )
        print(f"[OK] Updated page: {page_title}")
        return True
    except Exception as e:
        print(f"[ERROR] Error updating page '{page_title}': {e}")
        return False


def convert_markdown_to_confluence(markdown_content: str) -> str:
    """
    Convert markdown to Confluence storage format (XHTML)
    Uses md2cf library for proper conversion
    """
    renderer = ConfluenceRenderer(use_xhtml=True)
    confluence_mistune = mistune.Markdown(renderer=renderer)
    return confluence_mistune(markdown_content)


def sync_file_to_confluence(confluence, space_key: str, file_path: str, mapping: dict, repo_root: Path):
    """
    Sync a single file to Confluence
    """
    full_path = repo_root / file_path
    
    if not full_path.exists():
        print(f"[WARN] File not found: {file_path}")
        return False
    
    # Read file content
    with open(full_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Convert markdown to Confluence format
    import datetime
    converted_content = convert_markdown_to_confluence(markdown_content)
    
    # Add metadata footer (moved from top to bottom)
    metadata_footer = f"""
    <hr/>
    <p><em>Source: <a href="https://bitbucket.org/eso-bi-semantic/semantic/src/main/{file_path}">{file_path}</a> | Last updated: {datetime.datetime.now().strftime('%Y-%m-%d')}</em></p>
    """
    
    # Add professional footer
    footer = """
    <hr/>
    <p style="text-align: center; color: #6B778C; font-size: 0.9em;">
      <strong>Maintained By:</strong> Enterprise Business Intelligence<br/>
      <strong>Questions?</strong> <a href="mailto:bi@eso.com">bi@eso.com</a>
    </p>
    """
    
    # Combine content with metadata and footer at bottom
    confluence_content = converted_content + metadata_footer + footer
    
    # Get or create page
    page_id = get_or_create_page(
        confluence=confluence,
        space_key=space_key,
        parent_title=mapping['parent'],
        page_title=mapping['title']
    )
    
    if not page_id:
        return False
    
    # Update page content
    return update_page_content(
        confluence=confluence,
        page_id=page_id,
        page_title=mapping['title'],
        content=confluence_content
    )


def ensure_semantic_page(confluence, space_key: str, parent_page_id: str, semantic_title: str) -> bool:
    """
    Ensure the 'semantic' page exists under Enterprise Analytics
    Creates it if it doesn't exist
    Returns True if successful
    """
    try:
        # Check if semantic page exists
        page = confluence.get_page_by_title(space=space_key, title=semantic_title)
        if page:
            print(f"[OK] Found existing '{semantic_title}' page")
            return True
    except Exception:
        print(f"[INFO] '{semantic_title}' page not found, creating it...")
    
    # Create semantic page under Enterprise Analytics
    try:
        semantic_content = """
        <h1>ESO BI Semantic Repository</h1>
        <p>This is the central documentation hub for the ESO Business Intelligence team's semantic repository.</p>
        <p>All data engineering, analytics, and Power BI documentation is organized here.</p>
        <ac:structured-macro ac:name="info">
          <ac:rich-text-body>
            <p><strong>Source:</strong> <a href="https://bitbucket.org/eso-bi-semantic/semantic">Git Repository</a></p>
            <p><strong>Auto-synced from Git</strong> - All documentation is automatically synchronized from the Bitbucket repository.</p>
          </ac:rich-text-body>
        </ac:structured-macro>
        """
        
        new_page = confluence.create_page(
            space=space_key,
            title=semantic_title,
            body=semantic_content,
            parent_id=parent_page_id
        )
        print(f"[OK] Created '{semantic_title}' page")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create '{semantic_title}' page: {e}")
        return False


def create_folder_structure(confluence, space_key: str, parent_title: str):
    """
    Create folder pages (Domains, Templates, etc.)
    """
    folders = [
        ("Onboarding", """
            <ac:structured-macro ac:name="info">
              <ac:rich-text-body>
                <p><strong>Welcome to ESO Solutions Business Intelligence & Analytics!</strong></p>
                <p>This is your complete onboarding guide for joining the Enterprise BI team as a Business Intelligence Analyst.</p>
              </ac:rich-text-body>
            </ac:structured-macro>
            
            <h1>ESO BI Analyst Onboarding</h1>
            
            <h2>👋 About the Role</h2>
            <p>As a <strong>Business Intelligence Analyst</strong> at ESO Solutions, you'll be working with:</p>
            <ul>
              <li><strong>Azure Synapse Analytics</strong> - Our enterprise data warehouse platform</li>
              <li><strong>Power BI</strong> - Building semantic models and reports for stakeholders</li>
              <li><strong>SQL Server</strong> - T-SQL for data transformations and stored procedures</li>
              <li><strong>Python</strong> - Data engineering and automation scripts</li>
              <li><strong>Cursor IDE</strong> - Enhanced development environment</li>
              <li><strong>Git/Bitbucket</strong> - Version control and collaboration</li>
            </ul>
            
            <h2>🎯 Your First Week</h2>
            <p><strong>Day 1-2: Environment Setup & Access</strong></p>
            <ol>
              <li><strong>Getting Started: Enhanced Data Engineering Framework</strong> - Understand our development approach and philosophy</li>
              <li><strong>ESO BI Semantic Repository</strong> - How we work together, standards, and processes</li>
              <li><strong>Git Repository Setup Guide</strong> - Set up version control and understand our branching strategy</li>
            </ol>
            
            <p><strong>Day 3-4: Cursor Setup</strong></p>
            <ol>
              <li>Complete the <strong>Cursor Setup</strong> section (see below)</li>
              <li>Configure your development environment securely</li>
              <li>Run your first queries</li>
            </ol>
            
            <p><strong>Day 5: First Contributions</strong></p>
            <ol>
              <li><strong>Quick Start Guide: Your First Hour with Cursor</strong> - Hands-on walkthrough</li>
              <li>Review domain documentation (Salesforce, Jira, Finance, etc.)</li>
              <li>Complete a small task to get familiar with the workflow</li>
            </ol>
            
            <h2>💻 Cursor Setup</h2>
            <p>We use <strong>Cursor</strong> as our enhanced IDE to boost productivity and code quality. Complete these guides in order:</p>
            <ol>
              <li><strong>Complete Setup Guide</strong> - 90-minute comprehensive Cursor installation and configuration</li>
              <li><strong>Bitwarden Integration</strong> - Secure credential management</li>
              <li><strong>MCP Security Configuration</strong> - Model Context Protocol server setup</li>
              <li><strong>MCP Quick Reference</strong> - Quick reference for MCP commands</li>
            </ol>
            
            <h2>📊 Data Platform Overview</h2>
            <p><strong>Our Data Stack:</strong></p>
            <ul>
              <li><strong>Source Systems:</strong> Salesforce, Jira, NetSuite, ServiceNow</li>
              <li><strong>Ingestion:</strong> Azure Synapse Pipelines (daily ETL)</li>
              <li><strong>Storage:</strong> Azure Data Lake Gen2</li>
              <li><strong>Warehouse:</strong> Azure Synapse Analytics (SQL pools)</li>
              <li><strong>Schemas:</strong> 
                <ul>
                  <li><code>[bi]</code> - Current production schema (all business data)</li>
                  <li>Future: <code>[sales]</code>, <code>[jira]</code>, <code>[support]</code>, <code>[finance]</code>, etc.</li>
                  <li><strong>Never use <code>[stage]</code></strong> - temporary staging only</li>
                </ul>
              </li>
              <li><strong>Consumption:</strong> Power BI semantic models and reports</li>
            </ul>
            
            <h2>📚 Key Documentation</h2>
            <p><strong>Domain Documentation:</strong></p>
            <ul>
              <li><strong>Salesforce</strong> - CRM data, opportunities, accounts, subscriptions</li>
              <li><strong>Jira</strong> - Project tracking, sprint analytics, bug resolution</li>
              <li><strong>Templates</strong> - SQL templates, Power BI best practices, documentation templates</li>
              <li><strong>TAM/SAM</strong> - Total Addressable Market and market sizing analysis</li>
            </ul>
            
            <p><strong>Additional Resources:</strong></p>
            <ul>
              <li><strong>Confluence Integration Guide</strong> - How to update and sync documentation</li>
              <li><strong>System Architecture</strong> - High-level system design and data flows</li>
              <li><strong>Known Issues</strong> - Current data quality concerns and technical debt</li>
            </ul>
            
            <h2>✅ Onboarding Checklist</h2>
            <ac:structured-macro ac:name="status">
              <ac:parameter ac:name="colour">Grey</ac:parameter>
              <ac:parameter ac:name="title">TO DO</ac:parameter>
            </ac:structured-macro>
            <p><strong>Week 1: Setup & Learning</strong></p>
            <ul>
              <li>☐ Read "Getting Started" guide</li>
              <li>☐ Read "Team Collaboration Guidelines"</li>
              <li>☐ Complete Git setup</li>
              <li>☐ Complete Cursor AI Setup (all 4 guides)</li>
              <li>☐ Complete "Quick Start Guide"</li>
              <li>☐ Meet with team lead for role overview</li>
              <li>☐ Get access to Azure Synapse, Power BI, Confluence</li>
            </ul>
            
            <ac:structured-macro ac:name="tip">
              <ac:rich-text-body>
                <p><strong>Estimated Time:</strong> Plan for your first week to complete all setup and onboarding. You'll be productive and contributing by day 5!</p>
                <p><strong>Questions?</strong> Reach out to your team lead or post in the BI team channel.</p>
              </ac:rich-text-body>
            </ac:structured-macro>
        """),
        ("Cursor Setup", """
            <h1>Cursor Development Environment</h1>
            <p><strong>Cursor</strong> is an enhanced IDE that improves productivity through intelligent code completion, refactoring, and documentation generation.</p>
            
            <h2>Why We Use Cursor</h2>
            <ul>
              <li>✅ <strong>Faster Development:</strong> Assisted SQL writing and debugging</li>
              <li>✅ <strong>Better Code Quality:</strong> Follows our repository standards automatically</li>
              <li>✅ <strong>Learning Tool:</strong> Great for understanding complex queries and business logic</li>
              <li>✅ <strong>Documentation:</strong> Auto-generates comments and documentation</li>
              <li>✅ <strong>Cost Effective:</strong> Properly configured, costs $100-300/month per developer</li>
            </ul>
            
            <h2>🚀 Setup Guides (Complete in Order)</h2>
            <ol>
              <li><strong>Complete Setup Guide</strong> - Start here! 90-minute comprehensive setup
                <ul>
                  <li>Install Cursor IDE</li>
                  <li>Configure security with Bitwarden</li>
                  <li>Set up MS SQL MCP server for database access</li>
                  <li>Configure cost optimization settings</li>
                  <li>Learn repository standards and AI collaboration</li>
                </ul>
              </li>
              <li><strong>Bitwarden Integration</strong> - Secure credential management (referenced in setup guide)</li>
              <li><strong>MCP Security Configuration</strong> - Model Context Protocol security patterns (referenced in setup guide)</li>
              <li><strong>MCP Quick Reference</strong> - Quick commands and tips for daily use</li>
            </ol>
            
            <h2>💡 Cost Management</h2>
            <ac:structured-macro ac:name="warning">
              <ac:rich-text-body>
                <p><strong>IMPORTANT:</strong> Always use <code>claude-4.5-sonnet</code> (regular mode), NOT <code>claude-4.5-sonnet-thinking</code></p>
                <p>Thinking mode costs 5x more and is rarely needed. See the Complete Setup Guide for details.</p>
              </ac:rich-text-body>
            </ac:structured-macro>
            
            <h2>📚 What You'll Learn</h2>
            <ul>
              <li>How to write production-ready SQL queries with Cursor</li>
              <li>How to verify table and column names before writing code</li>
              <li>How to follow ESO BI repository standards automatically</li>
              <li>How to use MCP servers to interact with databases directly</li>
              <li>How to manage secrets securely with Bitwarden</li>
              <li>How to use Cursor for documentation and code review</li>
            </ul>
            
            <h2>⏱️ Time Estimate</h2>
            <ul>
              <li><strong>Complete Setup Guide:</strong> 90 minutes</li>
              <li><strong>Security Guides:</strong> 30 minutes (reference materials)</li>
              <li><strong>Total:</strong> ~2 hours for full Cursor environment setup</li>
            </ul>
            
            <ac:structured-macro ac:name="tip">
              <ac:rich-text-body>
                <p><strong>Pro Tip:</strong> Bookmark the <strong>MCP Quick Reference</strong> for daily use. It contains all the common commands and patterns you'll need.</p>
              </ac:rich-text-body>
            </ac:structured-macro>
        """),
        ("Salesforce", "<p>Salesforce data domain documentation - CRM, accounts, contacts, and CPQ lineage.</p>"),
        ("Sales", """
            <h1>Sales Domain</h1>
            <p>Sales analytics and reporting - Bookings, Pipeline, Revenue tracking, and Win Rate analysis.</p>
            
            <h2>Key Data Models</h2>
            <ul>
              <li><strong>fact_bookings</strong> - Closed deals (Won + Lost) at product line level</li>
              <li><strong>fact_pipeline</strong> - Open opportunities at product line level</li>
              <li><strong>dim_opportunity</strong> - Opportunity attributes and dimensions</li>
            </ul>
            
            <h2>Business Metrics</h2>
            <ul>
              <li>Total Bookings (Recurring vs One-time)</li>
              <li>Win Rate %</li>
              <li>Pipeline Value</li>
              <li>Weighted Pipeline</li>
              <li>Conversion Netting</li>
            </ul>
            
            <ac:structured-macro ac:name="info">
              <ac:rich-text-body>
                <p><strong>Schema:</strong> <code>[sales]</code></p>
                <p><strong>Data Cutoff:</strong> 2023-01-01 onwards</p>
              </ac:rich-text-body>
            </ac:structured-macro>
        """),
        ("Jira", "<p>Jira analytics domain documentation - Sprint tracking, issue resolution, and project metrics.</p>"),
        ("Templates", "<p>Reusable templates for documentation</p>"),
        ("TAM SAM", "<p>Market sizing (Total Addressable / Serviceable Available Market) documentation and data dictionary.</p>"),
        ("Known Issues", """
            <ac:structured-macro ac:name="warning">
              <ac:rich-text-body>
                <p><strong>Known Issues & Data Quality Concerns</strong></p>
                <p>This section documents identified data quality issues, field discrepancies, and technical debt requiring attention.</p>
              </ac:rich-text-body>
            </ac:structured-macro>
            <p>This folder contains documentation of known data quality issues, field standardization needs, and system discrepancies that have been identified and are being tracked for resolution.</p>
        """)
    ]
    
    for folder_title, folder_description in folders:
        page_id = get_or_create_page(
            confluence=confluence,
            space_key=space_key,
            parent_title=parent_title,
            page_title=folder_title
        )
        if page_id:
            # Update folder description
            update_page_content(
                confluence=confluence,
                page_id=page_id,
                page_title=folder_title,
                content=folder_description
            )
            print(f"[OK] Folder ready: {folder_title}")


# ========================================
# MAIN SCRIPT
# ========================================

def main():
    """
    Main sync function
    """
    print("=" * 60)
    print("Confluence Sync Script")
    print("=" * 60)
    
    # Initialize Confluence connection
    print("\nConnecting to Confluence...")
    try:
        confluence = Confluence(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            password=CONFLUENCE_API_TOKEN,
            cloud=True
        )
        # Test connection
        confluence.get_space(CONFLUENCE_SPACE_KEY)
        print("Connected successfully!")
    except Exception as e:
        print(f"Failed to connect to Confluence: {e}")
        print("\nMake sure you've set the correct:")
        print("   - CONFLUENCE_URL (e.g., https://your-domain.atlassian.net/wiki)")
        print("   - CONFLUENCE_USERNAME (your email)")
        print("   - CONFLUENCE_API_TOKEN (create at: https://id.atlassian.com/manage-profile/security/api-tokens)")
        sys.exit(1)
    
    # Get repository root
    repo_root = Path(__file__).parent
    print(f"\nRepository root: {repo_root}")
    
    # Ensure semantic page exists under Enterprise Analytics
    print(f"\nEnsuring '{PARENT_PAGE_TITLE}' page exists...")
    if not ensure_semantic_page(confluence, CONFLUENCE_SPACE_KEY, ENTERPRISE_ANALYTICS_PAGE_ID, PARENT_PAGE_TITLE):
        print(f"[ERROR] Failed to create/find '{PARENT_PAGE_TITLE}' page. Cannot continue.")
        sys.exit(1)
    
    # Create folder structure
    print("\nCreating folder structure...")
    create_folder_structure(confluence, CONFLUENCE_SPACE_KEY, PARENT_PAGE_TITLE)
    
    # Sync all files
    print("\nSyncing files to Confluence...")
    success_count = 0
    fail_count = 0
    
    for file_path, mapping in FILE_MAPPINGS.items():
        print(f"\n{'='*60}")
        print(f"Processing: {file_path}")
        print(f"{'='*60}")
        
        if sync_file_to_confluence(confluence, CONFLUENCE_SPACE_KEY, file_path, mapping, repo_root):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    print(f"Successfully synced: {success_count} files")
    print(f"Failed: {fail_count} files")
    print(f"\nView in Confluence: {CONFLUENCE_URL}/spaces/{CONFLUENCE_SPACE_KEY}/pages")
    print("=" * 60)


if __name__ == "__main__":
    main()


