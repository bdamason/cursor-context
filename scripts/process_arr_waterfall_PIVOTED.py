# =============================================================================
# Script: process_arr_waterfall_PIVOTED.py
# Purpose: Process ARR Summary Detail Excel into PIVOTED (long format) sheets
# Author: AI Assistant
# Date: 2025-11-25
# Dependencies: pandas, openpyxl
# Timezone: All timestamps in Central Time
# Cleanup: N/A (output files only)
# =============================================================================

import pandas as pd
import os
from datetime import datetime

# Define the source file
source_file = r"C:\Users\bdama\Downloads\_2025-10 ARR Summary & Detail by Customer.xlsx"
output_dir = r"C:\Users\bdama\Downloads"

# Define output file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"ARR_Waterfall_Import_PIVOTED_{timestamp}.xlsx")

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
    sf_num_col: 'SF_Account_Number',
    customer_name_col: 'Customer_Name',
    product_col: 'Product'
}, inplace=True)

# Rename period columns to simple period format
period_names = ['2025.01', '2025.02', '2025.03', '2025.04', '2025.05', 
                '2025.06', '2025.07', '2025.08', '2025.09', '2025.10']

for i, col in enumerate(arr_cols):
    arr_df.rename(columns={col: period_names[i]}, inplace=True)

# Pivot from wide to long format
arr_pivoted = arr_df.melt(
    id_vars=['SF_Account_Number', 'Customer_Name', 'Product'],
    value_vars=period_names,
    var_name='Period',
    value_name='ARR'
)

# Sort by account, product, period
arr_pivoted = arr_pivoted.sort_values(['SF_Account_Number', 'Product', 'Period']).reset_index(drop=True)

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
    sf_num_col: 'SF_Account_Number',
    customer_name_col: 'Customer_Name',
    product_col: 'Product'
}, inplace=True)

# Rename period columns
for i, col in enumerate(netchange_cols):
    netchange_df.rename(columns={col: period_names[i]}, inplace=True)

# Pivot from wide to long format
netchange_pivoted = netchange_df.melt(
    id_vars=['SF_Account_Number', 'Customer_Name', 'Product'],
    value_vars=period_names,
    var_name='Period',
    value_name='NetChange'
)

# Sort by account, product, period
netchange_pivoted = netchange_pivoted.sort_values(['SF_Account_Number', 'Product', 'Period']).reset_index(drop=True)

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
    sf_num_col: 'SF_Account_Number',
    customer_name_col: 'Customer_Name',
    product_col: 'Product'
}, inplace=True)

# Rename period columns
for i, col in enumerate(reason_cols):
    reason_df.rename(columns={col: period_names[i]}, inplace=True)

# Pivot from wide to long format
reason_pivoted = reason_df.melt(
    id_vars=['SF_Account_Number', 'Customer_Name', 'Product'],
    value_vars=period_names,
    var_name='Period',
    value_name='ChangeReason'
)

# Sort by account, product, period
reason_pivoted = reason_pivoted.sort_values(['SF_Account_Number', 'Product', 'Period']).reset_index(drop=True)

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
print("DATA FORMAT: PIVOTED (LONG FORMAT)")
print("="*80)
print("Each sheet now has ONE ROW per customer-product-period combination")
print("\nColumns in each sheet:")
print("  - SF_Account_Number (integer)")
print("  - Customer_Name (text)")
print("  - Product (text)")
print("  - Period (text, format: 2025.01, 2025.02, etc.)")
print("  - ARR / NetChange / ChangeReason (varies by sheet)")
print("\nAll '-' values in ChangeReason have been replaced with 'No Change'")
print("="*80)
















































