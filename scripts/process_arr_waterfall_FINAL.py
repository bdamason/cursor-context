# =============================================================================
# Script: process_arr_waterfall_FINAL.py
# Purpose: Process ARR Summary Detail Excel into PIVOTED sheets with proper dates and join keys
# Author: AI Assistant
# Date: 2025-11-25
# Dependencies: pandas, openpyxl
# Timezone: All timestamps in Central Time
# Cleanup: N/A (output files only)
# =============================================================================

import pandas as pd
import os
from datetime import datetime
from calendar import monthrange

# Define the source file
source_file = r"C:\Users\bdama\Downloads\_2025-10 ARR Summary & Detail by Customer.xlsx"
output_dir = r"C:\Users\bdama\Downloads"

# Define output file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"ARR_Waterfall_Import_FINAL_{timestamp}.xlsx")

print(f"Reading Excel file from: {source_file}")
print(f"Output will be saved to: {output_file}")

# Read the Excel file
df = pd.read_excel(source_file, sheet_name="ARR Summary Detail", header=0)

print(f"\nLoaded {len(df)} rows and {len(df.columns)} columns")

# Get column names
all_cols = list(df.columns)

# Key columns
sf_num_col = all_cols[0]           # SF #
customer_name_col = all_cols[1]    # Customer Name
product_col = all_cols[35]         # Product

# ARR columns for 2025.01-2025.10 (indices 120-129)
arr_cols = all_cols[120:130]

# Net Change columns for 2025.01-2025.10 (indices 216-225)
netchange_cols = all_cols[216:226]

# Net Change Reason columns for 2025.01-2025.10 (indices 312-321)
reason_cols = all_cols[312:322]

print(f"\nKey Columns Identified:")
print(f"  SF #: {sf_num_col}")
print(f"  Customer Name: {customer_name_col}")
print(f"  Product: {product_col}")

# Filter to valid data rows only (numeric SF Account Number)
df_filtered = df[pd.to_numeric(df[sf_num_col], errors='coerce').notna()].copy()
df_filtered.reset_index(drop=True, inplace=True)

print(f"\nFiltered to {len(df_filtered)} data rows (from {len(df)} total rows)")

# Function to convert period to last day of month
def period_to_last_day(period_str):
    """Convert '2025.01' to '2025-01-31' (last day of month)"""
    year, month = period_str.split('.')
    year = int(year)
    month = int(month)
    last_day = monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last_day:02d}"

# Period names and their corresponding last dates
period_names = ['2025.01', '2025.02', '2025.03', '2025.04', '2025.05', 
                '2025.06', '2025.07', '2025.08', '2025.09', '2025.10']

period_dates = {p: period_to_last_day(p) for p in period_names}
print(f"\nPeriod to Date Mapping:")
for p, d in period_dates.items():
    print(f"  {p} -> {d}")

# =============================================================================
# SHEET 1: ARR Import (PIVOTED - Long Format)
# =============================================================================
print("\n" + "="*80)
print("CREATING SHEET 1: ARR by Period (PIVOTED - Long Format)")
print("="*80)

# Create ARR dataframe with key columns and ARR columns
arr_df = df_filtered[[sf_num_col, customer_name_col, product_col] + arr_cols].copy()

# Rename key columns
arr_df.rename(columns={
    sf_num_col: 'AccountNumber',
    customer_name_col: 'CustomerName',
    product_col: 'Product'
}, inplace=True)

# Create unique join key (AccountNumber_Product)
arr_df['AccountProductKey'] = arr_df['AccountNumber'].astype(str) + '_' + arr_df['Product'].astype(str)

# Rename period columns to simple period format
for i, col in enumerate(arr_cols):
    arr_df.rename(columns={col: period_names[i]}, inplace=True)

# Pivot from wide to long format
arr_pivoted = arr_df.melt(
    id_vars=['AccountProductKey', 'AccountNumber', 'CustomerName', 'Product'],
    value_vars=period_names,
    var_name='Period',
    value_name='ARR'
)

# Convert Period to last day of month date format
arr_pivoted['PeriodDate'] = arr_pivoted['Period'].map(period_dates)

# Drop the intermediate Period column and rename PeriodDate to Period
arr_pivoted.drop('Period', axis=1, inplace=True)
arr_pivoted.rename(columns={'PeriodDate': 'Period'}, inplace=True)

# Reorder columns
arr_pivoted = arr_pivoted[['AccountProductKey', 'AccountNumber', 'CustomerName', 'Product', 'Period', 'ARR']]

# Sort by account, product, period
arr_pivoted = arr_pivoted.sort_values(['AccountNumber', 'Product', 'Period']).reset_index(drop=True)

# Remove rows where ARR is NULL/NaN (product not active in that period)
arr_pivoted = arr_pivoted[arr_pivoted['ARR'].notna()].reset_index(drop=True)

print(f"ARR Import (pivoted): {len(arr_pivoted)} rows, {len(arr_pivoted.columns)} columns")
print(f"Columns: {list(arr_pivoted.columns)}")
print(f"\nFirst 10 rows:")
print(arr_pivoted.head(10))

# =============================================================================
# SHEET 2: Net Change Import (PIVOTED - Long Format)
# =============================================================================
print("\n" + "="*80)
print("CREATING SHEET 2: Net Change by Period (PIVOTED - Long Format)")
print("="*80)

# Create Net Change dataframe
netchange_df = df_filtered[[sf_num_col, customer_name_col, product_col] + netchange_cols].copy()

# Rename key columns
netchange_df.rename(columns={
    sf_num_col: 'AccountNumber',
    customer_name_col: 'CustomerName',
    product_col: 'Product'
}, inplace=True)

# Create unique join key
netchange_df['AccountProductKey'] = netchange_df['AccountNumber'].astype(str) + '_' + netchange_df['Product'].astype(str)

# Rename period columns
for i, col in enumerate(netchange_cols):
    netchange_df.rename(columns={col: period_names[i]}, inplace=True)

# Pivot from wide to long format
netchange_pivoted = netchange_df.melt(
    id_vars=['AccountProductKey', 'AccountNumber', 'CustomerName', 'Product'],
    value_vars=period_names,
    var_name='Period',
    value_name='NetChange'
)

# Convert Period to last day of month date format
netchange_pivoted['PeriodDate'] = netchange_pivoted['Period'].map(period_dates)
netchange_pivoted.drop('Period', axis=1, inplace=True)
netchange_pivoted.rename(columns={'PeriodDate': 'Period'}, inplace=True)

# Reorder columns
netchange_pivoted = netchange_pivoted[['AccountProductKey', 'AccountNumber', 'CustomerName', 'Product', 'Period', 'NetChange']]

# Sort by account, product, period
netchange_pivoted = netchange_pivoted.sort_values(['AccountNumber', 'Product', 'Period']).reset_index(drop=True)

print(f"Net Change Import (pivoted): {len(netchange_pivoted)} rows, {len(netchange_pivoted.columns)} columns")
print(f"Columns: {list(netchange_pivoted.columns)}")
print(f"\nFirst 10 rows:")
print(netchange_pivoted.head(10))

# =============================================================================
# SHEET 3: Change Reason Import (PIVOTED - Long Format)
# =============================================================================
print("\n" + "="*80)
print("CREATING SHEET 3: Change Reason by Period (PIVOTED - Long Format)")
print("="*80)

# Create Change Reason dataframe
reason_df = df_filtered[[sf_num_col, customer_name_col, product_col] + reason_cols].copy()

# Rename key columns
reason_df.rename(columns={
    sf_num_col: 'AccountNumber',
    customer_name_col: 'CustomerName',
    product_col: 'Product'
}, inplace=True)

# Create unique join key
reason_df['AccountProductKey'] = reason_df['AccountNumber'].astype(str) + '_' + reason_df['Product'].astype(str)

# Rename period columns
for i, col in enumerate(reason_cols):
    reason_df.rename(columns={col: period_names[i]}, inplace=True)

# Pivot from wide to long format
reason_pivoted = reason_df.melt(
    id_vars=['AccountProductKey', 'AccountNumber', 'CustomerName', 'Product'],
    value_vars=period_names,
    var_name='Period',
    value_name='ChangeReason'
)

# Convert Period to last day of month date format
reason_pivoted['PeriodDate'] = reason_pivoted['Period'].map(period_dates)
reason_pivoted.drop('Period', axis=1, inplace=True)
reason_pivoted.rename(columns={'PeriodDate': 'Period'}, inplace=True)

# Reorder columns
reason_pivoted = reason_pivoted[['AccountProductKey', 'AccountNumber', 'CustomerName', 'Product', 'Period', 'ChangeReason']]

# Sort by account, product, period
reason_pivoted = reason_pivoted.sort_values(['AccountNumber', 'Product', 'Period']).reset_index(drop=True)

# Replace "-" with "No Change"
reason_pivoted['ChangeReason'] = reason_pivoted['ChangeReason'].replace('-', 'No Change')

print(f"Change Reason Import (pivoted): {len(reason_pivoted)} rows, {len(reason_pivoted.columns)} columns")
print(f"Columns: {list(reason_pivoted.columns)}")
print(f"\nFirst 10 rows:")
print(reason_pivoted.head(10))
print(f"\nUnique Change Reasons: {sorted(reason_pivoted['ChangeReason'].unique())}")

# =============================================================================
# WRITE OUTPUT FILE
# =============================================================================
print("\n" + "="*80)
print("WRITING OUTPUT FILE")
print("="*80)

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    arr_pivoted.to_excel(writer, sheet_name='util_waterfall_arr_import', index=False)
    netchange_pivoted.to_excel(writer, sheet_name='util_waterfall_netChange_import', index=False)
    reason_pivoted.to_excel(writer, sheet_name='util_waterfall_changeReason_imp', index=False)

print(f"\nSUCCESS! Output file created: {output_file}")
print(f"\nSheet 1: 'util_waterfall_arr_import' - {len(arr_pivoted)} rows")
print(f"Sheet 2: 'util_waterfall_netChange_import' - {len(netchange_pivoted)} rows")
print(f"Sheet 3: 'util_waterfall_changeReason_imp' - {len(reason_pivoted)} rows")
print("\n" + "="*80)
print("DATA FORMAT: PIVOTED (LONG FORMAT) WITH JOIN KEY")
print("="*80)
print("Each sheet now has ONE ROW per customer-product-period combination")
print("\nColumns in each sheet:")
print("  - AccountProductKey (text, format: AccountNumber_Product) - JOIN KEY")
print("  - AccountNumber (integer)")
print("  - CustomerName (text)")
print("  - Product (text)")
print("  - Period (date, format: yyyy-mm-dd, LAST DAY OF MONTH)")
print("  - ARR / NetChange / ChangeReason (varies by sheet)")
print("\nAll '-' values in ChangeReason have been replaced with 'No Change'")
print("\nTo join records across tables, use: AccountProductKey + Period")
print("="*80)
















































