# map_transactions.py
# UPDATED to use the OpenAI API for transaction categorization

import openai
import json
import pandas as pd

def get_ai_categorization(description): # client parameter is no longer used but we keep it for compatibility with main.py
    if not description or pd.isna(description):
        return {"category": "Uncategorized", "subcategory": ""}

    # The prompt is now structured for OpenAI's Chat model with strict category enforcement
    system_prompt = """You are a Georgian bank transaction categorization expert. You must categorize transactions using ONLY the predefined categories below. NEVER create new categories or use variations.

ALLOWED CATEGORIES (choose EXACTLY one):
Facebook, QR იდან, ბთ, გამოქეშება, გატანილი თანხა, დაზღვევა, იჯარა, კომუნალური, კონვერტაცია, მერჩი, მერჩი ყიდვა, მივლინება, რეკლამიდან, სამეურნეო, საპარლამენტო დაფინანსება, სკოლა, სხვა, ტელევიზია, უკუგატარება, შემოწირულობა, წასაშლელი, ხელფასი, ხელფასი TV, ჯედების

STRICT RULES:
1. Use EXACTLY one category from the list above - character-for-character match
2. NO variations, abbreviations, or new categories allowed
3. If you cannot determine the category with confidence, use "სხვა"
4. Return ONLY valid JSON in this exact format: {"category": "exact_category_name", "subcategory": "brief_description"}
5. The category field must match the list above EXACTLY
6. Subcategory is optional but helpful for detailed classification

Examples of good responses:
{"category": "სამეურნეო", "subcategory": "office supplies"}
{"category": "Facebook", "subcategory": "advertising"}
{"category": "საკომისიო", "subcategory": "bank fee"}
{"category": "სხვა", "subcategory": "unclassified"}

Analyze this transaction description and return the appropriate category:"""

    user_prompt = f"Please categorize this transaction: '{description}'"

    # This will fail loudly if there's an API key issue or other error.
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",  # A powerful and cost-effective model
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"} # This forces the model to return valid JSON!
    )
    
    # The response content is already a JSON string, so we parse it.
    return json.loads(response.choices[0].message.content)



def apply_bt_specific_rules(df):
    """
    Apply BT-specific business rules for categorization.
    If income from BT BOG or BT TBC GEL is exactly 175, 176, or 200 GEL,
    it should be categorized as "ბთ".
    """
    bt_files = ['BT BOG.xlsx', 'BT TBC GEL.xlsx']
    target_amounts = [175.0, 176.0, 200.0]
    
    # Create mask for BT files and target amounts
    mask = (
        df['Source File'].isin(bt_files) &
        df['Paid In'].isin(target_amounts)
    )
    
    # Apply the rule
    df.loc[mask, 'D) Mapped Description'] = 'ბთ'
    df.loc[mask, 'E) Sub-description'] = 'BT specific amount rule'
    
    return df


def apply_beta_girchi_rule(df):
    """
    Apply beta.girchi detection rule.
    If "beta.girchi" appears in the transaction description,
    it should be categorized as "შემოწირულობა".
    """
    # Create mask for transactions containing "beta.girchi"
    beta_girchi_mask = df['Original Description'].str.contains('beta.girchi', case=False, na=False)
    
    # Apply the rule
    df.loc[beta_girchi_mask, 'D) Mapped Description'] = 'შემოწირულობა'
    df.loc[beta_girchi_mask, 'E) Sub-description'] = 'beta.girchi donation rule'
    
    return df


def apply_rezervis_tanxa_rule(df):
    """
    Apply რეზერვის თანხა detection rule.
    If "რეზერვის თანხა" appears in the transaction description,
    it should be categorized as "შემოწირულობა".
    """
    # Create mask for transactions containing "რეზერვის თანხა"
    rezervis_mask = df['Original Description'].str.contains('რეზერვის თანხა', case=False, na=False)
    
    # Apply the rule
    df.loc[rezervis_mask, 'D) Mapped Description'] = 'შემოწირულობა'
    df.loc[rezervis_mask, 'E) Sub-description'] = 'რეზერვის თანხა donation rule'
    
    return df


def apply_gatanili_tanxa_restrictions(df):
    """
    Apply restrictions for "გატანილი თანხა" categorization.
    This category can only be used for transactions to specific approved people:
    - ვახტანგი მეგრელიშვილი
    - ალექსანდრე რაქვიაშვილი  
    - იაგო ხვიჩია
    - ჰერმან საბო
    """
    approved_names = [
        'ვახტანგი მეგრელიშვილი',
        'ალექსანდრე რაქვიაშვილი', 
        'იაგო ხვიჩია',
        'ჰერმან საბო'
    ]
    
    # Find transactions currently categorized as "გატანილი თანხა"
    gatanili_mask = df['D) Mapped Description'] == 'გატანილი თანხა'
    
    # For each transaction with "გატანილი თანხა", check if it's to an approved person
    for idx in df[gatanili_mask].index:
        description = str(df.loc[idx, 'Original Description']).lower()
        
        # Check if any approved name appears in the transaction description
        name_found = any(name.lower() in description for name in approved_names)
        
        # If no approved name found, change category to "სხვა"
        if not name_found:
            df.loc[idx, 'D) Mapped Description'] = 'სხვა'
            df.loc[idx, 'E) Sub-description'] = 'გატანილი თანხა restriction applied'
    
    return df


def map_internal_transfers(df, internal_accounts_list):
    """ This function remains unchanged. """
    df['Partner Account'] = df['Partner Account'].astype(str)
    df['AD) Partner Account Internal Map'] = df['Partner Account'].apply(
        lambda x: 'Internal Transfer' if x in internal_accounts_list else 'External'
    )
    return df