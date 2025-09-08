# main.py
import os
import sys
import pandas as pd
from dotenv import load_dotenv
import openai # CORRECT: Import the openai library
# REMOVED: import google.generativeai as genai

import config
from process_files import process_statement
from map_transactions import get_ai_categorization, map_internal_transfers, apply_bt_specific_rules, apply_gatanili_tanxa_restrictions, apply_beta_girchi_rule, apply_rezervis_tanxa_rule

def main():
    # 1. Setup
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY not found in .env file.")
        sys.exit(1)
    openai.api_key = openai_key

    input_dir = 'input_statements'
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. Process all statement files
    all_dfs = []
    statement_files = [f for f in os.listdir(input_dir) if f.endswith('.xlsx') or f.endswith('.xls')]

    for filename in statement_files:
        filepath = os.path.join(input_dir, filename)

        # Identify file type based on consistent naming
        file_key = os.path.splitext(filename)[0] # e.g., "GIRCHI TBC GEL"

        if file_key in config.FILE_CONFIGS:
            print(f"Processing {filename}...")
            try:
                # This is the critical block for error handling
                df = process_statement(filepath, config.FILE_CONFIGS[file_key])
                if not df.empty:
                    all_dfs.append(df)
            except Exception as e:
                print("\n" + "="*50)
                print(f"FATAL ERROR: Failed to process file: {filename}")
                print(f"Reason: {e}")
                print("The script will now terminate. Please fix the source file or the configuration in config.py.")
                print("="*50 + "\n")
                sys.exit(1) # Stop execution
        else:
            print(f"Warning: No config found for file '{filename}'. Skipping.")

    if not all_dfs:
        print("No files were successfully processed. Exiting.")
        return

    # 3. Consolidate, Categorize, and Map
    master_df = pd.concat(all_dfs, ignore_index=True)

    print("Starting AI categorization... this may take a while.")
    unique_descriptions = master_df['Original Description'].dropna().unique()
    ai_mappings = {desc: get_ai_categorization(desc) for desc in unique_descriptions}

    master_df['ai_map'] = master_df['Original Description'].map(ai_mappings)
    master_df['D) Mapped Description'] = master_df['ai_map'].apply(lambda x: x.get('category') if isinstance(x, dict) else 'Uncategorized')
    master_df['E) Sub-description'] = master_df['ai_map'].apply(lambda x: x.get('subcategory') if isinstance(x, dict) else '')

    print("Applying BT-specific categorization rules...")
    master_df = apply_bt_specific_rules(master_df)
    
    print("Applying beta.girchi donation rules...")
    master_df = apply_beta_girchi_rule(master_df)
    
    print("Applying რეზერვის თანხა donation rules...")
    master_df = apply_rezervis_tanxa_rule(master_df)
    
    print("Applying გატანილი თანხა restriction rules...")
    master_df = apply_gatanili_tanxa_restrictions(master_df)

    print("Mapping internal transfers...")
    master_df = map_internal_transfers(master_df, config.INTERNAL_ACCOUNTS)
    # The rest of the file remains the same...
    master_df.rename(columns={'Source File': 'A) Source File', 'Date': 'B) Date', 'Original Description': 'F) Original Description', 'Paid Out': 'H) Paid Out', 'Paid In': 'I) Paid In', 'Balance': 'J) Balance', 'Partner Name': 'K) Partner Name', 'Partner Account': 'N) Partner Account'}, inplace=True)

    # 4. Finalize and Save
    final_df = pd.DataFrame() # Initialize empty dataframe
    for col in config.FINAL_COLUMNS:
        if col in master_df.columns:
            final_df[col] = master_df[col]
        else:
            final_df[col] = None # Ensure all columns from config are present

    output_path = os.path.join(output_dir, 'Main_File.xlsx')
    final_df.to_excel(output_path, index=False)

    print(f"\nSuccess! Processed {len(all_dfs)} files.")
    print(f"Final consolidated file saved to: {output_path}")

if __name__ == "__main__":
    main()