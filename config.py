# config.py

# List of your internal account numbers (IBANs)
INTERNAL_ACCOUNTS = [
    'GE59BG0000000533997843', # BORIS BOG
    'GE21TB7772545167800001', # GIRCHI TBC USD
    'GE78BG0000000604676551', # TV36 BOG
    'GE60TB7791136080100005', # BT TBC GEL
    'GE04TB7772536080100003', # GIRCHI TBC GEL
    'GE74BG0000000101146034', # BT BOG
    'GE83TB7398736010100052', # BORIS TBC
]

# UPDATED Configuration with sheet name, start row, and column letter mappings
FILE_CONFIGS = {
    'GIRCHI TBC GEL': {
        'sheet_name': 'GE04TB7772536080100003-GEL', # Corrected from your list
        'start_row': 3,
        'column_map': { 'A': 'Date', 'B': 'Original Description', 'D': 'Paid Out', 'E': 'Paid In', 'F': 'Balance', 'J': 'Partner Account' }
    },
    'GIRCHI TBC USD': { # Assumed sheet name based on your description
        'sheet_name': 'GE21TB7772545167800001-USD',
        'start_row': 3,
        'column_map': { 'A': 'Date', 'B': 'Original Description', 'D': 'Paid Out', 'E': 'Paid In', 'F': 'Balance', 'J': 'Partner Account' }
    },
    'BT TBC GEL': {
        'sheet_name': 'GE60TB7791136080100005-GEL',
        'start_row': 3,
        'column_map': { 'A': 'Date', 'B': 'Original Description', 'D': 'Paid Out', 'E': 'Paid In', 'F': 'Balance', 'J': 'Partner Account' }
    },
    'BT BOG': {
        'sheet_name': 'Statement of Account',
        'start_row': 14,
        'column_map': { 'A': 'Date', 'F': 'Original Description', 'D': 'Paid Out', 'E': 'Paid In', 'Z': 'Balance' },
        'conditional_partner_account': {
            'condition_column': 'E',  # Check if column E has content
            'if_has_content': 'L',    # Use column L if E has content
            'if_empty': 'Q'           # Use column Q if E is empty
        }
    },
    'TV36 BOG': {
        'sheet_name': 'Statement of Account',
        'start_row': 14,
        'column_map': { 'A': 'Date', 'F': 'Original Description', 'D': 'Paid Out', 'E': 'Paid In', 'Z': 'Balance' },
        'conditional_partner_account': {
            'condition_column': 'E',  # Check if column E has content
            'if_has_content': 'L',    # Use column L if E has content
            'if_empty': 'Q'           # Use column Q if E is empty
        }
    },
    'BORIS TBC': {
        'sheet_name': 'GE83TB7398736010100052-GEL',
        'start_row': 3,
        'column_map': { 'A': 'Date', 'B': 'Original Description', 'D': 'Paid Out', 'E': 'Paid In', 'F': 'Balance', 'J': 'Partner Account' }
    },
    'BORIS BOG': {
        'sheet_name': 'ტრანზაქციები',
        'start_row': 2,
        'column_map': { 'H': 'Date', 'B': 'Original Description', 'D': 'Paid Out', 'E': 'Paid In', 'J': 'Partner Account' }
    },
}

# The final column order for the output Excel file
FINAL_COLUMNS = [
    'A) Source File', 'B) Date', 'C) Currency', 'D) Mapped Description', 'E) Sub-description',
    'F) Original Description', 'G) Transaction ID', 'H) Paid Out', 'I) Paid In', 'J) Balance',
    'K) Partner Name', 'L)', 'M)', 'N) Partner Account', 'AD) Partner Account Internal Map'
]