# main.py
import os
import sys
import pandas as pd
from dotenv import load_dotenv
import openai # CORRECT: Import the openai library
# REMOVED: import google.generativeai as genai

import config
from process_files import process_statement
from map_transactions import (
    get_ai_categorization,
    map_internal_transfers,
    apply_bt_specific_rules,
    apply_gatanili_tanxa_restrictions,
    apply_beta_girchi_rule,
    apply_rezervis_tanxa_rule,
    apply_kkk_salary_rule,
    apply_sakomis_commission_rule,
    apply_facebook_ads_rule,
    apply_konvertacia_rule,
    apply_server_services_rule,
    apply_sapensio_salary_rule,
    apply_montajis_safasuri_rule,
    apply_merchi_keyword_rule,
    apply_dazgveva_rule,
    apply_mevafinansebbts_rule,
    apply_utility_companies_rule,
    apply_specific_people_gatanili_rule,
    apply_salary_name_mapping_rule,
)

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

    print("Mapping internal transfers and categorizing as კონვერტაცია...")
    master_df = map_internal_transfers(master_df, config.INTERNAL_ACCOUNTS)

    print("Applying regex-based categorization rules first...")

    print("Applying BT-specific categorization rules...")
    master_df = apply_bt_specific_rules(master_df)

    print("Applying beta.girchi donation rules...")
    master_df = apply_beta_girchi_rule(master_df)

    print("Applying specific-person name mapping to გატანილი თანხა...")
    master_df = apply_specific_people_gatanili_rule(master_df)

    print("Applying salary name mapping to ხელფასი...")
    master_df = apply_salary_name_mapping_rule(master_df)

    print("Applying რეზერვის თანხა donation rules...")
    master_df = apply_rezervis_tanxa_rule(master_df)

    print("Applying კკკ salary rules...")
    master_df = apply_kkk_salary_rule(master_df)

    print("Applying საკომის commission rules...")
    master_df = apply_sakomis_commission_rule(master_df)

    print("Applying FACEBK ads rules...")
    master_df = apply_facebook_ads_rule(master_df)

    print("Applying კონვერტაცია keyword rules...")
    master_df = apply_konvertacia_rule(master_df)

    print("Applying server/digital services rules...")
    master_df = apply_server_services_rule(master_df)

    print("Applying საპენსიო salary rules...")
    master_df = apply_sapensio_salary_rule(master_df)

    print("Applying მონტაჟის საფასური salary rules...")
    master_df = apply_montajis_safasuri_rule(master_df)

    print("Applying მერჩი keyword rules...")
    master_df = apply_merchi_keyword_rule(master_df)

    print("Applying დაზღვ insurance rules...")
    master_df = apply_dazgveva_rule(master_df)

    print("Applying mevafinansebbts donation rules...")
    master_df = apply_mevafinansebbts_rule(master_df)

    print("Applying utility companies rules...")
    master_df = apply_utility_companies_rule(master_df)

    print("Starting AI categorization for remaining transactions... this may take a while.")
    # Only categorize transactions that haven't been categorized yet (after all regex rules)
    uncategorized_mask = (
        master_df['D) Mapped Description'].isna()
        if 'D) Mapped Description' in master_df.columns
        else pd.Series(True, index=master_df.index)
    )
    unique_descriptions = master_df[uncategorized_mask]['Original Description'].dropna().unique()
    ai_mappings = {desc: get_ai_categorization(desc) for desc in unique_descriptions}

    master_df['ai_map'] = master_df['Original Description'].map(ai_mappings)
    # Only apply AI categorization to uncategorized transactions
    master_df.loc[uncategorized_mask, 'D) Mapped Description'] = master_df.loc[uncategorized_mask, 'ai_map'].apply(lambda x: x.get('category') if isinstance(x, dict) else 'Uncategorized')
    master_df.loc[uncategorized_mask, 'E) Sub-description'] = master_df.loc[uncategorized_mask, 'ai_map'].apply(lambda x: x.get('subcategory') if isinstance(x, dict) else '')

    print("Applying გატანილი თანხა restriction rules...")
    master_df = apply_gatanili_tanxa_restrictions(master_df)
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
