# =============================================================================
# Script: process_arr_waterfall.py
# Purpose: Process ARR Summary Detail Excel file into three import-ready sheets
#          Extracts trailing 12 months of ARR, Net Change, and Change Reason data
# Author: AI Assistant
# Date: 2025-12-13
# Dependencies: pandas, openpyxl
# Timezone: All timestamps in Central Time
# Cleanup: N/A (output files only)
# =============================================================================

import pandas as pd
import os
from datetime import datetime

# =============================================================================
# CONFIGURATION - Update these paths as needed
# =============================================================================
source_file = r"C:\cursor_repo\finance\kb\ESO\_2025-11 ARR Summary & Detail by Customer (ARR detail only).xlsx"
output_dir = r"C:\cursor_repo\finance\kb\ESO"

# Minimum number of non-null data rows required to consider a period as "having data"
MIN_DATA_ROWS = 1000

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def find_section_indices(columns):
    """
    Find the starting indices of each major section in the spreadsheet.
    Returns dict with section names and their starting column indices.
    """
    sections = {
        'arr_start': None,
        'netchange_start': None,
        'reason_start': None,
        'filters_start': None
    }
    
    for idx, col in enumerate(columns):
        col_str = str(col)
        if col_str == 'ARR by Period by Product':
            sections['arr_start'] = idx
        elif col_str == 'Net Change by Period':
            sections['netchange_start'] = idx
        elif col_str == 'Net Change Reason by Period':
            sections['reason_start'] = idx
        elif col_str == 'Net Change Filters':
            sections['filters_start'] = idx
    
    return sections


def get_all_period_indices(df, section_start, next_section_start, header_row_idx=0):
    """
    Get all valid period column indices in a section.
    Returns list of column indices in order.
    """
    all_cols = list(df.columns)
    header_row = df.iloc[header_row_idx]
    
    period_indices = []
    
    for idx in range(section_start, next_section_start):
        col_name = all_cols[idx]
        header_val = header_row[col_name]
        
        # Check if header value looks like a period (year.month format)
        is_valid_period = False
        try:
            if isinstance(header_val, (int, float)) and 2017 <= header_val <= 2030:
                is_valid_period = True
            elif isinstance(header_val, str):
                if '.' in header_val:
                    year_part = float(header_val.split('.')[0])
                    if 2017 <= year_part <= 2030:
                        is_valid_period = True
        except (ValueError, TypeError):
            continue
        
        if is_valid_period:
            period_indices.append(idx)
    
    return period_indices


def get_trailing_12_indices_with_data(df, section_start, next_section_start, header_row_idx=0, min_data_rows=MIN_DATA_ROWS):
    """
    Get the indices for trailing 12 months from a section.
    Only considers columns that have significant data.
    Returns list of column indices.
    """
    all_cols = list(df.columns)
    
    # Get all period indices
    all_period_indices = get_all_period_indices(df, section_start, next_section_start, header_row_idx)
    
    # Filter to only periods with significant data
    valid_period_indices = []
    for idx in all_period_indices:
        col_name = all_cols[idx]
        col_data = df.iloc[1:][col_name]
        non_null_count = col_data.notna().sum()
        
        if non_null_count >= min_data_rows:
            valid_period_indices.append(idx)
    
    # Return the last 12
    if len(valid_period_indices) >= 12:
        return valid_period_indices[-12:]
    else:
        print(f"  WARNING: Only found {len(valid_period_indices)} periods with data")
        return valid_period_indices


def get_period_value(df, col_idx, header_row_idx=0):
    """
    Get the period value from the header row for a given column index.
    """
    col_name = df.columns[col_idx]
    header_val = df.iloc[header_row_idx][col_name]
    return header_val


def calculate_period_names(start_year, start_month, count):
    """
    Generate a list of period names in YYYY_MM format.
    Given a starting year/month, generate 'count' consecutive months.
    """
    periods = []
    for i in range(count):
        total_months = start_year * 12 + start_month - 1 + i
        year = total_months // 12
        month = (total_months % 12) + 1
        periods.append(f"{year}_{month:02d}")
    return periods


def detect_start_period_from_first_value(period_val):
    """
    Detect the starting year and month from a period value.
    This is trickier because floats lose precision (2025.01 vs 2025.1 vs 2025.10).
    
    Strategy: Look at the raw string representation.
    """
    if isinstance(period_val, str):
        parts = period_val.split('.')
        return int(parts[0]), int(parts[1])
    elif isinstance(period_val, (int, float)):
        val_str = str(period_val)
        if '.' in val_str:
            parts = val_str.split('.')
            year = int(parts[0])
            month_str = parts[1]
            # Handle: "12" = December, "01" = January, "1" = ambiguous (could be Jan or Oct)
            # Since we're looking at the FIRST period in trailing 12, and the file is
            # November 2025, trailing 12 starts at December 2024.
            # So if we see "12" that's December. If we see "1" or "01" that's January.
            month = int(month_str)
            return year, month
        else:
            return int(period_val), 1
    return 2024, 12  # Default fallback


# =============================================================================
# MAIN PROCESSING
# =============================================================================

print("=" * 80)
print("ARR WATERFALL PROCESSOR - Trailing 12 Months")
print("=" * 80)

# Generate output filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"ARR_Waterfall_Import_{timestamp}.xlsx")

print(f"\nSource: {source_file}")
print(f"Output: {output_file}")

# Read the Excel file
print("\nReading Excel file...")
df = pd.read_excel(source_file, sheet_name="ARR Summary Detail", header=0)

print(f"Loaded {len(df):,} rows and {len(df.columns)} columns")

# Get column list
all_cols = list(df.columns)

# Find section boundaries
sections = find_section_indices(all_cols)
print(f"\nSection boundaries detected:")
print(f"  ARR starts at column index: {sections['arr_start']}")
print(f"  Net Change starts at column index: {sections['netchange_start']}")
print(f"  Change Reason starts at column index: {sections['reason_start']}")
print(f"  Filters starts at column index: {sections['filters_start']}")

# Key identifier columns
sf_num_col = all_cols[0]           # SF #
customer_name_col = all_cols[1]    # Customer Name
product_col = all_cols[35]         # Product

# Get trailing 12 indices from ARR section (this is the source of truth)
print(f"\nFinding trailing 12 periods with significant data (min {MIN_DATA_ROWS:,} rows)...")
arr_indices = get_trailing_12_indices_with_data(df, sections['arr_start'], sections['netchange_start'])

# Calculate relative positions within each section
# The sections all have the same structure, just different starting column indices
# So if ARR trailing 12 starts at position X within the ARR section,
# Net Change trailing 12 starts at position X within the Net Change section

# Get all period indices for each section
arr_all_periods = get_all_period_indices(df, sections['arr_start'], sections['netchange_start'])
netchange_all_periods = get_all_period_indices(df, sections['netchange_start'], sections['reason_start'])
reason_all_periods = get_all_period_indices(df, sections['reason_start'], sections['filters_start'])

# Find the relative position of the first trailing 12 period within ARR section
first_trailing_idx = arr_indices[0]
relative_start_pos = arr_all_periods.index(first_trailing_idx)

print(f"\nARR trailing 12 indices: {arr_indices[0]} to {arr_indices[-1]}")
print(f"Relative start position within section: {relative_start_pos}")

# Map to other sections using the same relative positions
netchange_indices = netchange_all_periods[relative_start_pos:relative_start_pos + 12]
reason_indices = reason_all_periods[relative_start_pos:relative_start_pos + 12]

print(f"\nMapped indices:")
print(f"  ARR: {arr_indices[0]} to {arr_indices[-1]} ({len(arr_indices)} periods)")
print(f"  Net Change: {netchange_indices[0]} to {netchange_indices[-1]} ({len(netchange_indices)} periods)")
print(f"  Change Reason: {reason_indices[0]} to {reason_indices[-1]} ({len(reason_indices)} periods)")

# Get the actual column names
arr_cols = [all_cols[i] for i in arr_indices]
netchange_cols = [all_cols[i] for i in netchange_indices]
reason_cols = [all_cols[i] for i in reason_indices]

# Detect starting period from the first ARR value
first_period_val = get_period_value(df, arr_indices[0])
start_year, start_month = detect_start_period_from_first_value(first_period_val)

# Generate period names for trailing 12
period_names = calculate_period_names(start_year, start_month, 12)

print(f"\nDetected starting period: {start_year}.{start_month:02d}")
print(f"Period names: {period_names}")

# Remove header row from dataframe
df_data = df[df[sf_num_col] != 'SF #'].copy()
print(f"\nData rows (after removing header row): {len(df_data):,}")

# =============================================================================
# CREATE SHEET 1: ARR by Period
# =============================================================================
print("\n" + "=" * 80)
print("CREATING SHEET 1: ARR by Period (util_waterfall_arr_import)")
print("=" * 80)

arr_df = df_data[[sf_num_col, customer_name_col, product_col] + arr_cols].copy()
arr_df.reset_index(drop=True, inplace=True)

# Build rename mapping
arr_rename = {
    sf_num_col: 'SF_Account_Number',
    customer_name_col: 'Customer_Name',
    product_col: 'Product'
}
for pos, old_col in enumerate(arr_cols):
    arr_rename[old_col] = f"{period_names[pos]}_ARR"

arr_df.rename(columns=arr_rename, inplace=True)

print(f"Rows: {len(arr_df):,}")
print(f"Columns: {list(arr_df.columns)}")

# =============================================================================
# CREATE SHEET 2: Net Change by Period
# =============================================================================
print("\n" + "=" * 80)
print("CREATING SHEET 2: Net Change by Period (util_waterfall_netChange_import)")
print("=" * 80)

netchange_df = df_data[[sf_num_col, customer_name_col, product_col] + netchange_cols].copy()
netchange_df.reset_index(drop=True, inplace=True)

# Build rename mapping
netchange_rename = {
    sf_num_col: 'SF_Account_Number',
    customer_name_col: 'Customer_Name',
    product_col: 'Product'
}
for pos, old_col in enumerate(netchange_cols):
    netchange_rename[old_col] = f"{period_names[pos]}_NetChange"

netchange_df.rename(columns=netchange_rename, inplace=True)

print(f"Rows: {len(netchange_df):,}")
print(f"Columns: {list(netchange_df.columns)}")

# =============================================================================
# CREATE SHEET 3: Change Reason by Period
# =============================================================================
print("\n" + "=" * 80)
print("CREATING SHEET 3: Change Reason by Period (util_waterfall_changeReason_import)")
print("=" * 80)

reason_df = df_data[[sf_num_col, customer_name_col, product_col] + reason_cols].copy()
reason_df.reset_index(drop=True, inplace=True)

# Build rename mapping
reason_rename = {
    sf_num_col: 'SF_Account_Number',
    customer_name_col: 'Customer_Name',
    product_col: 'Product'
}
for pos, old_col in enumerate(reason_cols):
    reason_rename[old_col] = f"{period_names[pos]}_ChangeReason"

reason_df.rename(columns=reason_rename, inplace=True)

print(f"Rows: {len(reason_df):,}")
print(f"Columns: {list(reason_df.columns)}")

# =============================================================================
# WRITE OUTPUT FILE
# =============================================================================
print("\n" + "=" * 80)
print("WRITING OUTPUT FILE")
print("=" * 80)

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    arr_df.to_excel(writer, sheet_name='util_waterfall_arr_import', index=False)
    netchange_df.to_excel(writer, sheet_name='util_waterfall_netChange_import', index=False)
    reason_df.to_excel(writer, sheet_name='util_waterfall_changeReason_imp', index=False)

print(f"\nSUCCESS! Output file created: {output_file}")
print(f"\nSheet 1: 'util_waterfall_arr_import' - {len(arr_df):,} rows")
print(f"Sheet 2: 'util_waterfall_netChange_import' - {len(netchange_df):,} rows")
print(f"Sheet 3: 'util_waterfall_changeReason_imp' - {len(reason_df):,} rows")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("1. Open the output file to verify the data looks correct")
print("2. Import each sheet into its corresponding SQL table:")
print("   - Sheet 1 -> [bi].[util_waterfall_arr_import]")
print("   - Sheet 2 -> [bi].[util_waterfall_netChange_import]")
print("   - Sheet 3 -> [bi].[util_waterfall_changeReason_import]")
print("=" * 80)
