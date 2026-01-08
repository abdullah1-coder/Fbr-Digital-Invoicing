import os
import json
import secrets
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

# --- 1. CONFIGURATION ---
# Enable CORS so Streamlit can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. DATA MODELS ---
# This ensures the data coming from Streamlit is correct
class InvoiceItem(BaseModel):
    ItemCode: str
    ItemName: str
    Quantity: float
    PCTCode: str
    TaxRate: float
    SaleValue: float
    TotalAmount: float
    TaxCharged: float

class InvoiceRequest(BaseModel):
    invoice_id: str
    usin: str
    items: list[InvoiceItem]
    total_bill: float

# --- 3. HELPER FUNCTION ---
# Loads client secrets securely from Render Environment
def get_client_config():
    config_str = os.getenv("CLIENT_CONFIG")
    if not config_str:
        # Fallback for local testing if needed, or return empty
        print("WARNING: No CLIENT_CONFIG found in environment variables.")
        return {}
    try:
        return json.loads(config_str)
    except json.JSONDecodeError:
        print("ERROR: CLIENT_CONFIG is not valid JSON.")
        return {}

# --- 4. THE API ENDPOINT (UPDATED FOR SANDBOX) ---
# --- 4. THE API ENDPOINT (UPDATED FOR SANDBOX FIX) ---
@app.post("/submit-invoice")
async def submit_invoice(invoice: InvoiceRequest, x_client_id: str = Header(...)):
    
    # A. Validate Client
    client_db = get_client_config()
    
    if x_client_id not in client_db:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Client ID")
    
    client_settings = client_db[x_client_id]

    # B. Get Seller NTN (Handle missing key gracefully)
    # Default to 9999997 (Sandbox Default) if not found in config
    seller_ntn = client_settings.get("seller_ntn", "9999997") 

    # C. Prepare FBR Payload
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    fbr_payload = {
        "InvoiceNumber": invoice.invoice_id,
        "POSID": int(client_settings.get("pos_id", 123456)), 
        "USIN": invoice.usin,
        "DateTime": current_time,
        "BuyerNTN": "1234567-8", # Placeholder
        "BuyerName": "Walk-in Customer",
        "TotalSaleValue": invoice.total_bill,
        "TotalQuantity": sum(item.Quantity for item in invoice.items),
        "TotalTaxCharged": sum(item.TaxCharged for item in invoice.items),
        "Items": [item.dict() for item in invoice.items], 
        "PaymentMode": 1,
        "RefUSIN": "",
        "SellerNTN": seller_ntn  # <--- NOW USING THE CORRECT 7-DIGIT VAR
    }

    # D. SEND TO REAL FBR SANDBOX
    fbr_url = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb"
    
    headers = {
        "Authorization": f"Bearer {client_settings['auth_token']}",
        "Content-Type": "application/json"
    }

    print(f"Sending to FBR with SellerNTN: {seller_ntn}") 

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(fbr_url, json=fbr_payload, headers=headers, timeout=30.0)
            
            # Print response for debugging
            print(f"FBR Status: {response.status_code}")
            print(f"FBR Response: {response.text}")
            
            try:
                fbr_response = response.json()
            except json.JSONDecodeError:
                return {
                    "status": "failed",
                    "fbr_invoice_number": None,
                    "message": f"FBR returned invalid JSON. Status: {response.status_code}"
                }
            
            if response.status_code == 200:
                 return {
                    "status": "success",
                    "fbr_invoice_number": fbr_response.get("InvoiceNumber", "No-Number-Returned"),
                    "message": "Verified by FBR Sandbox"
                }
            else:
                 # Pass the exact error message from FBR back to Streamlit
                 return {
                    "status": "failed",
                    "fbr_invoice_number": None,
                    "message": fbr_response.get("Response", fbr_response.get("Message", "Unknown Error"))
                }

        except Exception as e:
            print(f"Connection Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to connect to FBR: {str(e)}")
