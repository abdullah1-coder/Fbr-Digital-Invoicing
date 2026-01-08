import streamlit as st
import pandas as pd
import datetime
import requests
import json
import re
# In your app.py


# ==========================================
# ⚙️ MULTI-CLIENT CONFIGURATION
# ==========================================
# Add as many clients as you want here.
# Format: "username": {"password": "...", "webhook": "...", "name": "..."}
CLIENT_CONFIG = {
    "client_a": {
        "password": "password123",
        "webhook": "https://your-n8n.com/webhook/client-a-token",
        "company_name": "Alpha Traders Ltd"
    },
    "client_b": {
        "password": "secure456",
        "webhook": "https://your-n8n.com/webhook/client-b-token",
        "company_name": "Beta Industries"
    },
    "admin": {
        "password": "admin",
        "webhook": "https://your-n8n.com/webhook/test-token",
        "company_name": "M.A Auto (Admin)"
    }
}
# ==========================================
# ==========================================
# 🧪 FBR TESTING SCENARIOS (SOURCE: DI SANDBOX PDF)
# ==========================================
TEST_SCENARIOS = {
    "Select a Scenario...": {},

    "SN001: Standard Rate (Reg Buyer)": {
        "doc_type": "Sale Invoice", "buyer_reg": "2046004", "buyer_name": "FERTILIZER MANUFAC IRS NEW",
        "buyer_type": "Registered", "sale_type": "Goods at standard rate (default)", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 400.0, "val_excl": 1000.0, "uom": "Numbers, pieces, units"
    },
    "SN002: Standard Rate (Unreg Buyer)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1234567", "buyer_name": "Unregistered Buyer",
        "buyer_type": "Unregistered", "sale_type": "Goods at standard rate (default)", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 400.0, "val_excl": 1000.0, "uom": "Numbers, pieces, units"
    },
    "SN003: Steel / Re-Rolling": {
        "doc_type": "Sale Invoice", "buyer_reg": "3710505701479", "buyer_name": "Steel Buyer Ltd",
        "buyer_type": "Unregistered", "sale_type": "Steel melting and re-rolling", "rate_idx": "18%",
        "hs_code_idx": "7214.1010", "qty": 1.0, "val_excl": 205000.0, "uom": "MT"
    },
    "SN004: Ship Breaking (Scrap)": {
        "doc_type": "Sale Invoice", "buyer_reg": "3710505701479", "buyer_name": "Ship Scrapper Co",
        "buyer_type": "Unregistered", "sale_type": "Ship breaking", "rate_idx": "18%",
        "hs_code_idx": "7204.1010", "qty": 1.0, "val_excl": 175000.0, "uom": "MT"
    },
    "SN005: Reduced Rate (8th Sch)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Reduced Rate Buyer",
        "buyer_type": "Unregistered", "sale_type": "Goods at Reduced Rate", "rate_idx": "1%",
        "hs_code_idx": "0102.2930", "qty": 1.0, "val_excl": 1000.0, "sro": "EIGHTH SCHEDULE Table 1", "item_no": "82"
    },
    "SN006: Exempt Goods (6th Sch)": {
        "doc_type": "Sale Invoice", "buyer_reg": "2046004", "buyer_name": "Exempt Buyer Reg",
        "buyer_type": "Registered", "sale_type": "Exempt goods", "rate_idx": "Exempt", # Check your CSV for exact spelling
        "hs_code_idx": "0102.2930", "qty": 1.0, "val_excl": 10.0, "sro": "6th Schd Table I", "item_no": "100"
    },
    "SN007: Zero-Rated (5th Sch)": {
        "doc_type": "Sale Invoice", "buyer_reg": "3710505701479", "buyer_name": "Exporter Co",
        "buyer_type": "Unregistered", "sale_type": "Goods at zero-rate", "rate_idx": "0%",
        "hs_code_idx": "0101.2100", "qty": 100.0, "val_excl": 100.0, "sro": "327(1)/2008"
    },
    "SN008: 3rd Schedule Goods": {
        "doc_type": "Sale Invoice", "buyer_reg": "3710505701479", "buyer_name": "Retail Item Buyer",
        "buyer_type": "Unregistered", "sale_type": "3rd Schedule Goods", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 100.0, "val_excl": 0.0, "fixed_val": 1000.0 # Retail Price
    },
    "SN009: Cotton Ginners": {
        "doc_type": "Sale Invoice", "buyer_reg": "2046004", "buyer_name": "Cotton Buyer Reg",
        "buyer_type": "Registered", "sale_type": "Cotton ginners", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 0.0, "val_excl": 2500.0
    },
    "SN010: Telecom Services": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Telecom Consumer",
        "buyer_type": "Unregistered", "sale_type": "Telecommunication services", "rate_idx": "17%", # Check if 17% exists in your CSV
        "hs_code_idx": "0101.2100", "qty": 1000.0, "val_excl": 100.0
    },
    "SN011: Toll Manufacturing": {
        "doc_type": "Sale Invoice", "buyer_reg": "3710505701479", "buyer_name": "Principal Co",
        "buyer_type": "Unregistered", "sale_type": "Toll Manufacturing", "rate_idx": "18%",
        "hs_code_idx": "7214.9990", "qty": 1.0, "val_excl": 205000.0, "uom": "MT"
    },
    "SN012: Petroleum Products": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Petrol Pump",
        "buyer_type": "Unregistered", "sale_type": "Petroleum Products", "rate_idx": "1.43%", # Special Rate
        "hs_code_idx": "0101.2100", "qty": 123.0, "val_excl": 100.0, "sro": "1450(I)/2021"
    },
    "SN013: Electricity to Retailers": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Retail Shop Elec",
        "buyer_type": "Unregistered", "sale_type": "Electricity Supply to Retailers", "rate_idx": "5%",
        "hs_code_idx": "0101.2100", "qty": 123.0, "val_excl": 1000.0
    },
    "SN014: Gas to CNG Stations": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "CNG Station",
        "buyer_type": "Unregistered", "sale_type": "Gas to CNG stations", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 123.0, "val_excl": 1000.0
    },
    "SN015: Mobile Phones (9th Sch)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Mobile Buyer",
        "buyer_type": "Unregistered", "sale_type": "Mobile Phones", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 123.0, "val_excl": 1234.0, "sro": "NINTH SCHEDULE"
    },
    "SN016: Processing/Conversion": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000078", "buyer_name": "Processing Client",
        "buyer_type": "Unregistered", "sale_type": "Processing/Conversion of Goods", "rate_idx": "5%",
        "hs_code_idx": "0101.2100", "qty": 1.0, "val_excl": 100.0
    },
    "SN017: Goods (FED in ST Mode)": {
        "doc_type": "Sale Invoice", "buyer_reg": "7000009", "buyer_name": "FED Payer",
        "buyer_type": "Unregistered", "sale_type": "Goods (FED in ST Mode)", "rate_idx": "8%",
        "hs_code_idx": "0101.2100", "qty": 1.0, "val_excl": 100.0
    },
    "SN018: Services (FED in ST Mode)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000056", "buyer_name": "Service Receiver",
        "buyer_type": "Unregistered", "sale_type": "Services (FED in ST Mode)", "rate_idx": "8%",
        "hs_code_idx": "0101.2100", "qty": 20.0, "val_excl": 1000.0
    },
    "SN019: Services (ICT Ordinance)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "ICT Service Buyer",
        "buyer_type": "Unregistered", "sale_type": "Services", "rate_idx": "5%",
        "hs_code_idx": "0101.2900", "qty": 1.0, "val_excl": 100.0, "sro": "ICTO TABLE I"
    },
    "SN020: Electric Vehicles": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "EV Buyer",
        "buyer_type": "Unregistered", "sale_type": "Electric Vehicle", "rate_idx": "1%",
        "hs_code_idx": "0101.2900", "qty": 122.0, "val_excl": 1000.0, "sro": "6th Schd Table III"
    },
    "SN021: Cement/Concrete Block": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Builder Co",
        "buyer_type": "Unregistered", "sale_type": "Cement/Concrete Block", "rate_idx": "Rs.3", # Check CSV
        "hs_code_idx": "0101.2100", "qty": 12.0, "val_excl": 123.0
    },
    "SN022: Potassium Chlorate": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Chemical Buyer",
        "buyer_type": "Unregistered", "sale_type": "Potassium Chlorate", "rate_idx": "18% + Rs 60", # CSV check needed
        "hs_code_idx": "3104.2000", "qty": 1.0, "val_excl": 100.0, "uom": "KG", "sro": "EIGHTH SCHEDULE Table 1"
    },
    "SN023: Sale of CNG": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "CNG Car Owner",
        "buyer_type": "Unregistered", "sale_type": "CNG Sales", "rate_idx": "Rs.200", # CSV check needed
        "hs_code_idx": "0101.2100", "qty": 123.0, "val_excl": 234.0, "sro": "581(1)/2024"
    },
    "SN024: SRO 297(1)/2023": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "SRO Buyer",
        "buyer_type": "Unregistered", "sale_type": "Goods as per SRO.297( )/2023", "rate_idx": "25%",
        "hs_code_idx": "0101.2100", "qty": 123.0, "val_excl": 1000.0, "sro": "297(I)/2023-Table-"
    },
    "SN025: Fixed ST (Drugs)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000078", "buyer_name": "Pharma Buyer",
        "buyer_type": "Unregistered", "sale_type": "Non-Adjustable Supplies", "rate_idx": "0%",
        "hs_code_idx": "0101.2100", "qty": 1.0, "val_excl": 100.0, "sro": "EIGHTH SCHEDULE Table 1"
    },
    "SN026: Retailer (Standard)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000078", "buyer_name": "Consumer (POS)",
        "buyer_type": "Registered", "sale_type": "Goods at standard rate (default)", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 123.0, "val_excl": 1000.0
    },
    "SN027: Retailer (3rd Schedule)": {
        "doc_type": "Sale Invoice", "buyer_reg": "7000006", "buyer_name": "Consumer (POS)",
        "buyer_type": "Registered", "sale_type": "3rd Schedule Goods", "rate_idx": "18%",
        "hs_code_idx": "0101.2100", "qty": 1.0, "val_excl": 0.0, "fixed_val": 100.0
    },
    "SN028: Retailer (Reduced Rate)": {
        "doc_type": "Sale Invoice", "buyer_reg": "1000000000000", "buyer_name": "Consumer (POS)",
        "buyer_type": "Registered", "sale_type": "Goods at Reduced Rate", "rate_idx": "1%",
        "hs_code_idx": "0101.2100", "qty": 0.0, "val_excl": 0.0, "fixed_val": 100.0
    },
}
CSV_FILE_NAME = "REFERENCES - REFERENCES.csv" 

# --- PAGE SETUP ---
st.set_page_config(page_title="FBR Digital Invoicing", page_icon="FBR-Logo-Small.png", layout="wide")

# --- YOUR CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #F5F7F9; }
    .stButton>button {
        width: 100%;
        background-color: #004B87;
        color: white;
        border-radius: 8px;
        height: 50px;
        font-weight: bold;
    }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)



# --- SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_details = {} # Stores the current logged-in user's config

# --- LOGIN LOGIC ---
def check_login():
    user = st.session_state['username'].strip()
    pwd = st.session_state['password']
    
    # Check if user exists in config and password matches
    if user in CLIENT_CONFIG and CLIENT_CONFIG[user]["password"] == pwd:
        st.session_state.authenticated = True
        # Save specific user details to session (Webhook, Company Name)
        st.session_state.user_details = CLIENT_CONFIG[user]
        st.session_state.user_details['username_key'] = user
    else:
        st.error("❌ Incorrect Username or Password")

def logout():
    st.session_state.authenticated = False
    st.session_state.user_details = {}
    st.rerun()

# --- IF NOT LOGGED IN, SHOW LOGIN PAGE ---
if not st.session_state.authenticated:
    # 1. Get Username from URL if present (e.g. ?user=client_a) for easier login
    query_params = st.query_params
    prefill_user = query_params.get("user", "")

    # Centered Login Box
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image("FBR-Logo-Small.png", width=150)
        st.markdown("## FBR Portal Login")
        st.markdown("Please sign in to access the Invoicing System.")
        
        with st.form("login_form"):
            st.text_input("Username", value=prefill_user, key="username", placeholder="Enter username")
            st.text_input("Password", type="password", key="password", placeholder="Enter password")
            st.form_submit_button("Login", on_click=check_login)
    
    st.stop() # Stop here

# =========================================================
# === MAIN APP (Only runs if Logged In) ===
# =========================================================

# --- HELPER: RATE PARSER ---
def parse_rate(rate_str):
    if not isinstance(rate_str, str): return 0.0
    if "%" in rate_str:
        try: return float(rate_str.replace("%", "").strip())
        except: return 0.0
    if "Rs." in rate_str or "/" in rate_str: return 0.0
    try: return float(rate_str)
    except: return 0.0

# --- DATA LOADER ---
@st.cache_data
def load_reference_data():
    try:
        df = pd.read_csv(CSV_FILE_NAME)
        data = {}
        target_cols = ["Item Sr. No.", "SRO", "Document Type", "UOM", "Province", "Buyer Type", "Sale Types", "Rate", "Description", "Reason"]
        for col in target_cols:
            if col in df.columns:
                items = df[col].dropna().astype(str).unique().tolist()
                items.sort()
                data[col] = items
            else:
                data[col] = []
        return data
    except FileNotFoundError:
        st.error(f"⚠️ Critical Error: '{CSV_FILE_NAME}' not found.")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Error reading CSV: {e}")
        st.stop()

ref_data = load_reference_data()
def get_options(key): return ref_data.get(key, [])

# --- STATE & CLEAR ---
def init_state():
    # Use the logged-in company name as default
    default_seller = st.session_state.user_details.get("company_name", "M.A Auto")
    
    defaults = {
        "doc_type": ref_data["Document Type"][0] if ref_data["Document Type"] else "",
        "inv_date": datetime.date.today(),
        "buyer_reg": "", "buyer_name": "",
        "buyer_type": ref_data["Buyer Type"][0] if ref_data["Buyer Type"] else "",
        "dest_supply": "PUNJAB", "buyer_addr": "",
        "hs_code_idx": ref_data["Description"][0] if ref_data["Description"] else "",
        "sale_type": ref_data["Sale Types"][0] if ref_data["Sale Types"] else "",
        "rate_idx": ref_data["Rate"][0] if ref_data["Rate"] else "0.00%",
        "uom": ref_data["UOM"][0] if ref_data["UOM"] else "",
        "qty": 1.0, "val_excl": 0.0,
        "sro": ref_data["SRO"][0] if ref_data["SRO"] else "",
        "item_no": ref_data["Item Sr. No."][0] if ref_data["Item Sr. No."] else "",
        "reason": ref_data["Reason"][0] if ref_data["Reason"] else "",
        "prod_desc": "", "ref_no": "",
        "seller_name": default_seller
    }
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

init_state()

def clear_form():
    auth = st.session_state.authenticated
    user_det = st.session_state.user_details
    st.session_state.clear()
    st.session_state.authenticated = auth
    st.session_state.user_details = user_det
    init_state()

# --- APP LAYOUT (HEADER) ---
# ==========================================
# 🧪 SIDEBAR: TEST DATA LOADER
# ==========================================
st.sidebar.markdown("---")
st.sidebar.header("🧪 Test Data Loader")
selected_scenario = st.sidebar.selectbox("Load FBR Scenario", list(TEST_SCENARIOS.keys()))

if selected_scenario != "Select a Scenario...":
    data = TEST_SCENARIOS[selected_scenario]
    
    # Helper to check if option exists in dropdown before setting
    # (Prevents crashing if your CSV doesn't have the exact same text)
    def set_safe(key, value, options_list=None):
        if options_list:
            # For Dropdowns: Check if value exists in list
            # We check partially because PDF might say "18%" but CSV has "18.00%"
            match = next((x for x in options_list if str(value) in str(x)), None)
            if match:
                st.session_state[key] = match
            else:
                st.sidebar.warning(f"⚠️ '{value}' not found in {key} options.")
        else:
            # For Text Inputs: Just set it
            st.session_state[key] = value

    if st.sidebar.button(f"Apply {selected_scenario}"):
        # Load Text Fields
        set_safe('buyer_reg', data.get('buyer_reg', ''))
        set_safe('buyer_name', data.get('buyer_name', ''))
        set_safe('buyer_addr', "Karachi") # Default for all tests
        set_safe('qty', data.get('qty', 1.0))
        set_safe('val_excl', data.get('val_excl', 0.0))
        set_safe('fixed_val', data.get('fixed_val', 0.0))
        
        # Load Dropdowns (Matches against your ref_data)
        set_safe('doc_type', data.get('doc_type'), get_options("Document Type"))
        set_safe('buyer_type', data.get('buyer_type'), get_options("Buyer Type"))
        set_safe('sale_type', data.get('sale_type'), get_options("Sale Types"))
        set_safe('rate_idx', data.get('rate_idx'), get_options("Rate"))
        set_safe('uom', data.get('uom', 'Numbers'), get_options("UOM"))
        set_safe('sro', data.get('sro'), get_options("SRO"))
        set_safe('item_no', data.get('item_no'), get_options("Item Sr. No."))
        
        # HS Code is Tricky (Partial Match)
        hs_val = data.get('hs_code_idx')
        if hs_val:
            # Finds the option that starts with the code (e.g. "0101.2100")
            hs_match = next((x for x in get_options("Description") if x.startswith(hs_val)), None)
            if hs_match: st.session_state['hs_code_idx'] = hs_match

        st.success("✅ Data Loaded!")
        st.rerun()
c1, c2, c3 = st.columns([1, 5, 1])
with c1: st.image("FBR-Logo-Small.png", width=100)
with c2: 
    # Show Company Name in Header
    company = st.session_state.user_details.get("company_name", "FBR Portal")
    st.markdown(f"# FBR Digital Invoicing\n#### **{company}**")
with c3:
    st.write("")
    if st.button("Logout"): logout()

# --- CLEAR BUTTON ---
if st.button("🔄 Reset / Clear Form"): 
    clear_form()
    st.rerun()

# --- MAIN FORM ---
with st.form("invoice_form"):

    # 1. DOCUMENT
    st.markdown('<div class="header-bar">📄 1. Document Details</div><div class="css-card">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: doc_type = st.selectbox("Document Type *", get_options("Document Type"), key="doc_type")
    with c2: inv_date = st.date_input("Invoice Date *", key="inv_date")
    with c3: reason = st.selectbox("Reason (Credit/Debit Notes)", get_options("Reason"), key="reason")
    with c4: ref_no = st.text_input("Reference No", key="ref_no")
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. BUYER & SELLER
    st.markdown('<div class="header-bar">🏢 2. Buyer & Seller</div><div class="css-card">', unsafe_allow_html=True)
    
    with st.expander("Seller Information (Click to Edit)", expanded=True):
        sc1, sc2 = st.columns(2)
        with sc1: seller_name_input = st.text_input("Seller Name", key="seller_name") 
        with sc2: seller_prov = st.selectbox("Seller Province", get_options("Province"), index=5)

    st.markdown("---")
    st.markdown("### Buyer Details")
    bc1, bc2, bc3 = st.columns(3)
    with bc1: buyer_reg = st.text_input("Buyer NTN/CNIC *", key="buyer_reg")
    with bc2: buyer_name = st.text_input("Buyer Name *", key="buyer_name")
    with bc3: buyer_type = st.selectbox("Buyer Type *", get_options("Buyer Type"), key="buyer_type")
    bc4, bc5 = st.columns([1, 2])
    with bc4: dest_supply = st.selectbox("Destination Supply *", get_options("Province"), key="dest_supply")
    with bc5: buyer_addr = st.text_input("Buyer Address *", key="buyer_addr")
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. PRODUCT
    st.markdown('<div class="header-bar">📦 3. Product Details</div><div class="css-card">', unsafe_allow_html=True)
    ic1, ic2, ic3, ic4 = st.columns(4)
    with ic1: 
        hs_raw = st.selectbox("HS Code / Description *", get_options("Description"), key="hs_code_idx")
        hs_code = hs_raw.split(":-")[0] if hs_raw else ""
    with ic2: prod_desc = st.text_input("Product Description", key="prod_desc")
    with ic3: uom = st.selectbox("UoM *", get_options("UOM"), key="uom")
    with ic4: qty = st.number_input("Quantity *", min_value=0.01, step=1.0, key="qty")
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. FINANCIALS
    st.markdown('<div class="header-bar">💰 4. Financials</div><div class="css-card">', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1: 
        rate_str = st.selectbox("GST Rate *", get_options("Rate"), key="rate_idx")
        rate_val = parse_rate(rate_str)
    with fc2: sale_type = st.selectbox("Sale Type *", get_options("Sale Types"), key="sale_type")
    with fc3: val_excl = st.number_input("Value (Excl. Tax) *", min_value=0.0, step=100.0, key="val_excl")
    with fc4:
        tax_amt = (val_excl * rate_val / 100) if val_excl else 0.0
        st.metric("Est. Sales Tax", f"{tax_amt:,.2f}")

    # ADVANCED FIELDS
    st.markdown("---")
    st.markdown("### Advanced Tax Fields")
    at1, at2, at3, at4 = st.columns(4)
    with at1: st_fed = st.number_input("Sales Tax / FED", value=tax_amt)
    with at2: extra_tax = st.number_input("Extra Tax", 0.0)
    with at3: further_tax = st.number_input("Further Tax", 0.0)
    with at4: wht = st.number_input("WHT Source", 0.0)
    
    at5, at6, at7 = st.columns(3)
    with at5: discount = st.number_input("Discount", 0.0)
    with at6: fixed_val = st.number_input("Fixed/Retail Value", 0.0)
    with at7: st_app = st.number_input("Sales Tax Applicable", 0.0)

    at8, at9 = st.columns(2)
    with at8: sro = st.selectbox("SRO / Schedule No", get_options("SRO"), key="sro")
    with at9: item_no = st.selectbox("Item Sr. No.", get_options("Item Sr. No."), key="item_no")
    st.markdown('</div>', unsafe_allow_html=True)

    # SUBMIT
    # ... inside your 'with st.form(...):' block ...

    # THIS IS THE ONLY BUTTON YOU NEED
    # THIS IS THE ONLY BUTTON YOU NEED
    if st.form_submit_button("SUBMIT INVOICE TO FBR"):
        
        # 1. Validation
        missing = []
        if not buyer_reg: missing.append("Buyer NTN")
        if not buyer_name: missing.append("Buyer Name")
        if not buyer_addr: missing.append("Buyer Address")
        if qty <= 0: missing.append("Quantity")
        if val_excl <= 0: missing.append("Value")
        
        if missing:
            st.error(f"❌ Missing: {', '.join(missing)}")
            st.stop()
            
        # 2. Prepare Data (Payload for Render)
        # Note: We send the raw values, Python Backend will calculate tax/totals
        payload = {
            "invoice_id": ref_no if ref_no else "INV-AUTO-001", 
            "usin": "USIN001",
            "total_bill": val_excl,
            "items": [
                {
                    "ItemCode": str(hs_code),
                    "ItemName": prod_desc,
                    "Quantity": qty,
                    "PCTCode": str(hs_code),
                    "TaxRate": rate_val,
                    "SaleValue": val_excl,
                    "TotalAmount": val_excl + tax_amt,
                    "TaxCharged": tax_amt
                }
            ]
        }
        
        # 3. Prepare Headers (Dynamic)
        current_user = st.session_state.user_details.get('username_key', 'client_a')
        headers = {
            "x-client-id": current_user,
            "Content-Type": "application/json"
        }

        # 4. SEND TO RENDER
        api_url = "https://fbr-digital-invoicing.onrender.com/submit-invoice"
        
        with st.spinner("Talking to FBR..."):
            try:
                response = requests.post(api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Success! FBR Number: {data.get('fbr_invoice_number')}")
                    
                    with st.expander("View FBR Receipt Details"):
                        st.json(data)
                else:
                    st.error(f"FBR Error: {response.text}")
                    
            except Exception as e:
                st.error(f"Connection Failed: {e}")
