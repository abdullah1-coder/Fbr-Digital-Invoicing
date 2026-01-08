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

CSV_FILE_NAME = "REFERENCES - REFERENCES.csv" 

# --- PAGE SETUP ---
st.set_page_config(page_title="FBR Digital Invoicing", page_icon="FBR-Logo-Small.png", layout="wide")

# --- YOUR CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #F5F7F9; }
    
    /* STYLE FOR THE CARDS */
    .css-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* STYLE FOR THE HEADERS inside cards */
    .header-bar {
        background-color: #004B87;
        color: white;
        padding: 10px;
        border-radius: 8px 8px 0 0;
        font-weight: bold;
        font-size: 16px;
    }
    
    .stButton>button {
        width: 100%;
        background-color: #004B87;
        color: white;
        border-radius: 8px;
        height: 50px;
        font-weight: bold;
        font-size: 18px;
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
