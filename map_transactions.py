# map_transactions.py
# UPDATED to use the OpenAI API for transaction categorization

import openai
import json
import pandas as pd
import re

def get_ai_categorization(description): # client parameter is no longer used but we keep it for compatibility with main.py
    if not description or pd.isna(description):
        return {"category": "Uncategorized", "subcategory": ""}

    # The prompt is now structured for OpenAI's Chat model with strict category enforcement
    system_prompt = """You are a Georgian bank transaction categorization expert. You must categorize transactions using ONLY the predefined categories below. NEVER create new categories or use variations.

ALLOWED CATEGORIES (choose EXACTLY one):
შემოწირულობა, ბთ, საპარლამენტო დაფინანსება, მერჩი, რეკლამიდან, ტელევიზია, კომუნალური, სამეურნეო, მერჩი ყიდვა, გატანილი თანხა, ხელფასი, ხელფასი TV, დაზღვევა, მივლინება, იჯარა, Facebook, ჯედების, სხვა, სკოლა

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
{"category": "შემოწირულობა", "subcategory": "donation"}
{"category": "სხვა", "subcategory": "unclassified"}

Analyze this transaction description and return the appropriate category:"""

    user_prompt = f"Please categorize this transaction: '{description}'"

    # Call OpenAI with v1 client if available; fallback to legacy style.
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
    except Exception:
        # Legacy SDK fallback
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response["choices"][0]["message"]["content"]

    # Parse JSON content; guard against invalid JSON
    try:
        return json.loads(content)
    except Exception:
        return {"category": "Uncategorized", "subcategory": ""}



def apply_bt_specific_rules(df):
    """
    Apply BT-specific business rules for categorization.
    If income from BT BOG or BT TBC GEL is exactly 175, 176, or 200 GEL,
    it should be categorized as "ბთ".
    For BT BOG: checks column E (Paid In) for income of 175 GEL specifically.
    For BT TBC GEL: checks all target amounts (175, 176, 200).
    IMPORTANT: Only applies to income transactions (Paid In > 0), not expenses.
    """
    bt_bog_files = ['BT BOG.xlsx']
    bt_tbc_files = ['BT TBC GEL.xlsx']

    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # BT BOG specific rule: only 175 GEL income (must be positive income, not expense)
    bt_bog_mask = (
        uncategorized_mask &
        df['Source File'].isin(bt_bog_files) &
        (df['Paid In'] == 175.0) &
        (df['Paid In'] > 0) &  # Only income transactions
        (df['Paid Out'].fillna(0) == 0)  # Not expense transactions
    )

    # BT TBC GEL rule: 175, 176, or 200 GEL income (must be positive income, not expense)
    bt_tbc_mask = (
        uncategorized_mask &
        df['Source File'].isin(bt_tbc_files) &
        df['Paid In'].isin([175.0, 176.0, 200.0]) &
        (df['Paid In'] > 0) &  # Only income transactions
        (df['Paid Out'].fillna(0) == 0)  # Not expense transactions
    )

    # Apply the rules
    df.loc[bt_bog_mask, 'D) Mapped Description'] = 'ბთ'
    df.loc[bt_bog_mask, 'E) Sub-description'] = 'BT BOG 175 GEL income rule'

    df.loc[bt_tbc_mask, 'D) Mapped Description'] = 'ბთ'
    df.loc[bt_tbc_mask, 'E) Sub-description'] = 'BT TBC specific amount income rule'

    return df


def apply_beta_girchi_rule(df):
    """
    Apply beta.girchi detection rule.
    If "beta.girchi" appears in the transaction description,
    it should be categorized as "შემოწირულობა".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "beta.girchi"
    beta_girchi_mask = uncategorized_mask & df['Original Description'].str.contains('beta.girchi', case=False, na=False)

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
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "რეზერვის თანხა"
    rezervis_mask = uncategorized_mask & df['Original Description'].str.contains('რეზერვის თანხა', case=False, na=False)

    # Apply the rule
    df.loc[rezervis_mask, 'D) Mapped Description'] = 'შემოწირულობა'
    df.loc[rezervis_mask, 'E) Sub-description'] = 'რეზერვის თანხა donation rule'

    return df


def apply_kkk_salary_rule(df):
    """
    Apply კკკ salary detection rule.
    If "კკკ" appears in the transaction description,
    it should be categorized as "ხელფასი".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "კკკ"
    kkk_mask = uncategorized_mask & df['Original Description'].str.contains('კკკ', case=False, na=False)

    # Apply the rule
    df.loc[kkk_mask, 'D) Mapped Description'] = 'ხელფასი'
    df.loc[kkk_mask, 'E) Sub-description'] = 'კკკ salary rule'

    return df


def apply_sakomis_commission_rule(df):
    """
    Apply საკომის commission detection rule.
    If "საკომის" appears in the transaction description,
    it should be categorized as "საკომისიო".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "საკომის"
    sakomis_mask = uncategorized_mask & df['Original Description'].str.contains('საკომის', case=False, na=False)

    # Apply the rule
    df.loc[sakomis_mask, 'D) Mapped Description'] = 'საკომისიო'
    df.loc[sakomis_mask, 'E) Sub-description'] = 'საკომის commission rule'

    return df


def apply_facebook_ads_rule(df):
    """
    Apply Facebook ads detection rule.
    If "FACEBK" appears in the transaction description,
    it should be categorized as "რეკლამა".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "FACEBK"
    facebook_mask = uncategorized_mask & df['Original Description'].str.contains('FACEBK', case=False, na=False)

    # Apply the rule
    df.loc[facebook_mask, 'D) Mapped Description'] = 'რეკლამა'
    df.loc[facebook_mask, 'E) Sub-description'] = 'FACEBK ads rule'

    return df


def apply_konvertacia_rule(df):
    """
    Apply კონვერტაცია detection rule.
    If "კონვერტაცია" appears in the transaction description,
    it should be categorized as "კონვერტაცია".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "კონვერტაცია"
    konvertacia_mask = uncategorized_mask & df['Original Description'].str.contains('კონვერტაცია', case=False, na=False)

    # Apply the rule
    df.loc[konvertacia_mask, 'D) Mapped Description'] = 'კონვერტაცია'
    df.loc[konvertacia_mask, 'E) Sub-description'] = 'კონვერტაცია keyword rule'

    return df


def apply_server_services_rule(df):
    """
    Apply server/digital services detection rule.
    If any of the specified service providers appear in the transaction description,
    it should be categorized as "სერვერები".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Service providers that should be categorized as "სერვერები"
    service_keywords = [
        'BUZZSPROUT',
        'Mailchimp',
        'DIGITALOCEAN.COM',
        'Google',
        'CLOUDFLARE',
        'VEED',
        '2CO.COM',
        'WWW.VMIX.COM',
        'TALLY.SO',
        'ZOOM.COM'
    ]

    # Build regex pattern for all service keywords
    pattern = '|'.join(re.escape(keyword) for keyword in service_keywords)

    # Create mask for transactions containing any of the service keywords
    server_mask = uncategorized_mask & df['Original Description'].str.contains(pattern, case=False, na=False)

    # Apply the rule
    df.loc[server_mask, 'D) Mapped Description'] = 'სერვერები'
    df.loc[server_mask, 'E) Sub-description'] = 'Server/digital services rule'

    return df


def apply_sapensio_salary_rule(df):
    """
    Apply საპენსიო detection rule.
    If "საპენსიო" appears in the transaction description,
    it should be categorized as "ხელფასი".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "საპენსიო"
    sapensio_mask = uncategorized_mask & df['Original Description'].str.contains('საპენსიო', case=False, na=False)

    # Apply the rule
    df.loc[sapensio_mask, 'D) Mapped Description'] = 'ხელფასი'
    df.loc[sapensio_mask, 'E) Sub-description'] = 'საპენსიო salary rule'

    return df


def apply_montajis_safasuri_rule(df):
    """
    Apply მონტაჟის საფასური detection rule.
    If "მონტაჟის საფასური" appears in the transaction description,
    it should be categorized as "ხელფასი".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "მონტაჟის საფასური"
    montajis_mask = uncategorized_mask & df['Original Description'].str.contains('მონტაჟის საფასური', case=False, na=False)

    # Apply the rule
    df.loc[montajis_mask, 'D) Mapped Description'] = 'ხელფასი'
    df.loc[montajis_mask, 'E) Sub-description'] = 'მონტაჟის საფასური salary rule'

    return df


def apply_merchi_keyword_rule(df):
    """
    Apply მერჩი keyword detection rule.
    If "მერჩი" appears in the transaction description,
    it should be categorized as "მერჩი".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "მერჩი"
    merchi_mask = uncategorized_mask & df['Original Description'].str.contains('მერჩი', case=False, na=False)

    # Apply the rule
    df.loc[merchi_mask, 'D) Mapped Description'] = 'მერჩი'
    df.loc[merchi_mask, 'E) Sub-description'] = 'მერჩი keyword rule'

    return df


def apply_dazgveva_rule(df):
    """
    Apply insurance detection rule.
    If "დაზღვ" appears in the transaction description,
    it should be categorized as "დაზღვევა".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "დაზღვ"
    dazgveva_mask = uncategorized_mask & df['Original Description'].str.contains('დაზღვ', case=False, na=False)

    # Apply the rule
    df.loc[dazgveva_mask, 'D) Mapped Description'] = 'დაზღვევა'
    df.loc[dazgveva_mask, 'E) Sub-description'] = 'დაზღვ insurance rule'

    return df


def apply_mevafinansebbts_rule(df):
    """
    Apply mevafinansebbts detection rule.
    If "mevafinansebbts" appears in the transaction description,
    it should be categorized as "შემოწირულობა".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    # Create mask for transactions containing "mevafinansebbts"
    mevafinansebbts_mask = uncategorized_mask & df['Original Description'].str.contains('mevafinansebbts', case=False, na=False)

    # Apply the rule
    df.loc[mevafinansebbts_mask, 'D) Mapped Description'] = 'შემოწირულობა'
    df.loc[mevafinansebbts_mask, 'E) Sub-description'] = 'mevafinansebbts donation rule'

    return df


def apply_utility_companies_rule(df):
    """
    Apply utility companies detection rule.
    If Partner Name contains "მაგთი" or "სილქ",
    it should be categorized as "კომუნალური".
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    utility_companies = ['მაგთი', 'სილქ']
    pattern = '|'.join(re.escape(company) for company in utility_companies)

    # Check Partner Name for utility companies
    partner_name = df.get('Partner Name', pd.Series('', index=df.index)).astype(str)
    utility_mask = uncategorized_mask & partner_name.str.contains(pattern, case=False, na=False)

    # Apply the rule
    df.loc[utility_mask, 'D) Mapped Description'] = 'კომუნალური'
    df.loc[utility_mask, 'E) Sub-description'] = 'Utility company rule'

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
    """
    Maps internal transfers and automatically categorizes them as კონვერტაცია.
    This function now detects when both source and destination accounts are internal
    and sets the category to კონვერტაცია without requiring AI categorization.
    """
    # Ensure Partner Account and Source Account are strings
    df['Partner Account'] = df['Partner Account'].astype(str)
    df['Source Account'] = df['Source Account'].astype(str) if 'Source Account' in df.columns else ''

    # Mark Partner Account as Internal or External
    df['AD) Partner Account Internal Map'] = df['Partner Account'].apply(
        lambda x: 'Internal Transfer' if x in internal_accounts_list else 'External'
    )

    # Detect internal-to-internal transfers and categorize as კონვერტაცია
    internal_transfer_mask = (
        df['Source Account'].isin(internal_accounts_list) &
        df['Partner Account'].isin(internal_accounts_list) &
        (df['Partner Account'] != 'nan') &  # Exclude NaN values converted to string
        (df['Partner Account'] != '') &     # Exclude empty strings
        (df['Source Account'] != df['Partner Account'])  # Exclude same account transfers
    )

    # Apply კონვერტაცია categorization for internal transfers
    df.loc[internal_transfer_mask, 'D) Mapped Description'] = 'კონვერტაცია'
    df.loc[internal_transfer_mask, 'E) Sub-description'] = 'Internal account transfer'

    return df


def apply_specific_people_gatanili_rule(df):
    """
    If either the original description or partner name contains any of
    the specified Georgian names, force-map the category to "გატანილი თანხა".

    Names checked:
    - რაქვიაშვილი
    - მეგრელიშვილი
    - ჰერმან
    - იაგო ხვიჩია
    - ნარტყოშვილი
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    target_names = ['რაქვიაშვილი', 'მეგრელიშვილი', 'ჰერმან', 'იაგო ხვიჩია', 'ნარტყოშვილი']
    # Build a regex pattern that matches any of the names
    pattern = '|'.join(re.escape(name) for name in target_names)

    # Prepare safe series for checks
    orig_desc = df.get('Original Description', pd.Series('', index=df.index)).astype(str)
    partner_name = df.get('Partner Name', pd.Series('', index=df.index)).astype(str)

    mask = uncategorized_mask & (
        orig_desc.str.contains(pattern, case=False, na=False) |
        partner_name.str.contains(pattern, case=False, na=False)
    )

    df.loc[mask, 'D) Mapped Description'] = 'გატანილი თანხა'
    df.loc[mask, 'E) Sub-description'] = 'Name-based mapping rule'

    return df


def apply_salary_name_mapping_rule(df):
    """
    If Original Description OR Partner Name contains any of the specified names,
    force-map the category to "ხელფასი".

    Names checked:
    ლევან ჯგერენაია,
    ნუგზარ ტაბატაძე,
    რევაზი სუთიძე,
    მაყვალა გიორგაძე,
    იზა ნადარეიშვილი,
    მარიკა ვერულიძე,
    ლიზი შეწირული,
    გიორგი პაჭიკაშვილი,
    ვაკო თენეიშვილი,
    თედო ჯაბუა,
    ანა ნოდია,
    გიორგი სოლოღაშვილი,
    რუსუდანი აბუაშვილი,
    სიმონ ღარიბაშვილი,
    ავთანდილ ლაბაძე,
    ეკა ონიანი,
    ბორის სოლომონია,
    ვახტანგ თენეიშვილი
    """
    # Only apply to uncategorized transactions
    uncategorized_mask = ~df.get('D) Mapped Description', pd.Series(dtype=bool)).notna()

    names = [
        'ლევან ჯგერენაია',
        'ნუგზარ ტაბატაძე',
        'რევაზი სუთიძე',
        'მაყვალა გიორგაძე',
        'იზა ნადარეიშვილი',
        'მარიკა ვერულიძე',
        'ლიზი შეწირული',
        'გიორგი პაჭიკაშვილი',
        'ვაკო თენეიშვილი',
        'თედო ჯაბუა',
        'ანა ნოდია',
        'გიორგი სოლოღაშვილი',
        'რუსუდანი აბუაშვილი',
        'სიმონ ღარიბაშვილი',
        'ავთანდილ ლაბაძე',
        'ეკა ონიანი',
        'ბორის სოლომონია',
        'ვახტანგ თენეიშვილი',
    ]

    pattern = '|'.join(re.escape(n) for n in names)
    desc = df.get('Original Description', pd.Series('', index=df.index)).astype(str)
    partner_name = df.get('Partner Name', pd.Series('', index=df.index)).astype(str)

    # Check both Original Description AND Partner Name
    mask = uncategorized_mask & (
        desc.str.contains(pattern, case=False, na=False) |
        partner_name.str.contains(pattern, case=False, na=False)
    )

    df.loc[mask, 'D) Mapped Description'] = 'ხელფასი'
    df.loc[mask, 'E) Sub-description'] = 'Salary name mapping rule'

    return df
