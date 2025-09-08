# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a financial aggregator application that processes bank statements from multiple Georgian banks (BOG, TBC) and accounts, consolidates transactions, and categorizes them using AI. The application reads Excel files containing bank statements, processes them according to bank-specific configurations, and outputs a consolidated Excel file with categorized transactions.

## Development Commands

### Running the Application
```bash
python main.py
```

### Virtual Environment Setup
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies (create requirements.txt if needed)
pip install pandas openpyxl python-dotenv openai
```

### Environment Setup
- Create a `.env` file with `OPENAI_API_KEY=your_key_here`
- The application requires OpenAI API access for transaction categorization

## Architecture

### Core Components

1. **main.py** - Entry point and orchestration
   - Loads environment variables and OpenAI API key
   - Processes all Excel files in `input_statements/` directory
   - Consolidates data, runs AI categorization, and maps internal transfers
   - Outputs final consolidated file to `output/Main_File.xlsx`

2. **config.py** - Configuration management
   - `INTERNAL_ACCOUNTS`: List of internal Georgian bank IBANs for transfer detection
   - `FILE_CONFIGS`: Bank-specific configurations mapping file names to sheet names, start rows, and column mappings
   - `FINAL_COLUMNS`: Output file column structure

3. **process_files.py** - Excel processing utilities
   - `process_statement()`: Reads specific sheets from Excel files based on configuration
   - Handles different bank statement formats (BOG vs TBC)
   - Maps Excel column letters (A, B, etc.) to semantic names
   - Standardizes date formats and numeric columns

4. **map_transactions.py** - AI categorization and transfer mapping
   - `get_ai_categorization()`: Uses OpenAI GPT-3.5-turbo to categorize transactions into predefined Georgian categories
   - `map_internal_transfers()`: Identifies transfers between internal accounts
   - Categories: შემოწირულობა, ბთ, საპარლამენტო დაფინანსება, მერჩი, ტელევიზია, etc.

### Data Flow
1. Read Excel files from `input_statements/` using bank-specific configurations
2. Extract and standardize transaction data (date, description, amounts, accounts)
3. Consolidate all transactions into single DataFrame
4. Apply AI categorization to unique transaction descriptions
5. Map internal vs external transfers
6. Output consolidated and categorized data to Excel

### Bank-Specific Handling
- **TBC Bank**: Uses specific sheet names with IBAN-currency format, starts from row 3, Partner Account always in column J
- **BOG Bank**: Uses "Statement of Account" or "ტრანზაქციები" sheets, different start rows and column mappings
- Each bank has different column layouts requiring specific mapping configurations

#### Partner Account Column Mapping
- **BORIS TBC**: Column J
- **BT TBC GEL**: Column J  
- **GIRCHI TBC GEL**: Column J
- **GIRCHI TBC USD**: Column J
- **TV36 BOG**: Conditional - Column L if column E has content, Column Q if column E is empty
- **BT BOG**: Conditional - Column L if column E has content, Column Q if column E is empty
- **BORIS BOG**: Column J (direct mapping)

#### Conditional Partner Account Logic (BOG Files)
For TV36 BOG and BT BOG files, the partner account column is determined dynamically:
- Check if column E contains data (not null, not empty string, not zero)
- If column E has content: use column L for partner account
- If column E is empty: use column Q for partner account
- This logic is implemented in `process_files.py` using the `conditional_partner_account` configuration

### AI Categorization System
The application uses OpenAI's GPT-3.5-turbo for intelligent transaction categorization with strict category enforcement:

#### Strict Category Framework
- AI must choose from exactly 23 predefined Georgian categories
- No variations, abbreviations, or new categories allowed
- Uses "სხვა" as fallback for unclear transactions
- JSON response format ensures consistent categorization
- System prompt enforces character-exact matching to category list

#### Supported Categories
შემოწირულობა, ბთ, საპარლამენტო დაფინანსება, მერჩი, ტელევიზია, კომუნალური, სამეურნეო, მერჩი ყიდვა, გატანილი თანხა, ხელფასი, დაზღვევა, მივლინება, იჯარა, Facebook, ჯედების, სხვა, სკოლა, გამოქეშება, კონვერტაცია, საკომისიო, სერვერები, სესსხის ფული შემოსავალი

### Key Dependencies
- pandas: Excel file processing and data manipulation
- openai: AI-powered transaction categorization
- openpyxl: Excel file reading/writing
- python-dotenv: Environment variable management

### Error Handling
- Application terminates on any file processing error to prevent data corruption
- Missing configuration for files results in warnings but continues processing
- AI categorization failures default to "Uncategorized"
- Strict JSON format validation ensures proper categorization responses