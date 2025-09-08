# process_files.py
import pandas as pd
import os

def excel_col_to_int(col_str):
    """Converts Excel column letters (A, B, AA, etc.) to a zero-based integer index."""
    num = 0
    for c in col_str:
        num = num * 26 + (ord(c.upper()) - ord('A')) + 1
    return num - 1

def process_statement(filepath, config):
    """
    Reads a specific sheet and start row from an Excel file,
    and maps columns by their letter position (A, B, H, etc.).
    """
    sheet_name = config['sheet_name']
    start_row = config['start_row']
    column_map = config['column_map']
    
    # Read the specific sheet, skip the top rows, and treat the first row of data as having no header.
    # The 'skiprows' parameter is zero-indexed, so we subtract 1.
    df = pd.read_excel(
        filepath,
        sheet_name=sheet_name,
        skiprows=start_row - 1,
        header=None
    )

    # Create a new, clean DataFrame to hold our processed data
    processed_df = pd.DataFrame()

    # Map the data using column letters
    for col_letter, target_name in column_map.items():
        col_index = excel_col_to_int(col_letter)
        if col_index < len(df.columns):
            processed_df[target_name] = df.iloc[:, col_index]
        else:
            # If a column doesn't exist (e.g., no 'Balance' column), create an empty one
            processed_df[target_name] = None
    
    # Handle conditional partner account logic for BOG files
    if 'conditional_partner_account' in config:
        conditional_config = config['conditional_partner_account']
        condition_col = conditional_config['condition_column']
        col_if_content = conditional_config['if_has_content']
        col_if_empty = conditional_config['if_empty']
        
        # Get the condition column data
        condition_col_index = excel_col_to_int(condition_col)
        if condition_col_index < len(df.columns):
            condition_data = df.iloc[:, condition_col_index]
        else:
            condition_data = pd.Series([None] * len(df))
        
        # Get data from both potential partner account columns
        col_content_index = excel_col_to_int(col_if_content)
        col_empty_index = excel_col_to_int(col_if_empty)
        
        partner_data_content = df.iloc[:, col_content_index] if col_content_index < len(df.columns) else pd.Series([None] * len(df))
        partner_data_empty = df.iloc[:, col_empty_index] if col_empty_index < len(df.columns) else pd.Series([None] * len(df))
        
        # Create Partner Account column based on condition
        partner_account = []
        for i, condition_value in enumerate(condition_data):
            # Check if condition column has content (not null, not empty string, not 0)
            has_content = (
                pd.notna(condition_value) and 
                str(condition_value).strip() != '' and 
                condition_value != 0
            )
            
            if has_content:
                # Use column L if E has content
                partner_account.append(partner_data_content.iloc[i] if i < len(partner_data_content) else None)
            else:
                # Use column Q if E is empty
                partner_account.append(partner_data_empty.iloc[i] if i < len(partner_data_empty) else None)
        
        processed_df['Partner Account'] = partner_account
    
    # Extract partner names based on file type and rules
    source_filename = os.path.basename(filepath)
    file_key = os.path.splitext(source_filename)[0]
    
    # For TBC files (BT TBC GEL, GIRCHI TBC GEL, GIRCHI TBC USD), extract from column K
    if file_key in ['BT TBC GEL', 'GIRCHI TBC GEL', 'GIRCHI TBC USD']:
        partner_name_col_index = excel_col_to_int('K')
        if partner_name_col_index < len(df.columns):
            processed_df['Partner Name'] = df.iloc[:, partner_name_col_index]
        else:
            processed_df['Partner Name'] = None
    
    # For BOG files (TV36 BOG, BT BOG), use conditional logic for partner names
    elif file_key in ['TV36 BOG', 'BT BOG']:
        # Get column data for conditions and partner names
        col_e_index = excel_col_to_int('E')
        col_d_index = excel_col_to_int('D')
        col_j_index = excel_col_to_int('J')
        col_o_index = excel_col_to_int('O')
        
        col_e_data = df.iloc[:, col_e_index] if col_e_index < len(df.columns) else pd.Series([0] * len(df))
        col_d_data = df.iloc[:, col_d_index] if col_d_index < len(df.columns) else pd.Series([0] * len(df))
        col_j_data = df.iloc[:, col_j_index] if col_j_index < len(df.columns) else pd.Series([None] * len(df))
        col_o_data = df.iloc[:, col_o_index] if col_o_index < len(df.columns) else pd.Series([None] * len(df))
        
        # Create Partner Name column based on conditional logic
        partner_names = []
        for i in range(len(df)):
            col_e_val = pd.to_numeric(col_e_data.iloc[i], errors='coerce') if i < len(col_e_data) else 0
            col_d_val = pd.to_numeric(col_d_data.iloc[i], errors='coerce') if i < len(col_d_data) else 0
            
            # Default to None
            partner_name = None
            
            # If column E > 0, use column J for partner name
            if pd.notna(col_e_val) and col_e_val > 0:
                partner_name = col_j_data.iloc[i] if i < len(col_j_data) else None
            # If column D > 0, use column O for partner name
            elif pd.notna(col_d_val) and col_d_val > 0:
                partner_name = col_o_data.iloc[i] if i < len(col_o_data) else None
            
            partner_names.append(partner_name)
        
        processed_df['Partner Name'] = partner_names
    
    else:
        # For other files, no partner name extraction
        processed_df['Partner Name'] = None
    
    # Drop rows where the 'Date' is empty, as these are often summary or empty rows at the end.
    processed_df.dropna(subset=['Date'], inplace=True)
    if processed_df.empty:
        return pd.DataFrame() # Return empty if no valid data rows are found

    # Add source file name
    processed_df['Source File'] = os.path.basename(filepath)

    # Standardize Date format
    processed_df['Date'] = pd.to_datetime(processed_df['Date'], errors='coerce').dt.date

    # Ensure numeric columns are numeric, filling errors with 0
    for col in ['Paid Out', 'Paid In', 'Balance']:
        if col in processed_df.columns:
            processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce').fillna(0)

    return processed_df