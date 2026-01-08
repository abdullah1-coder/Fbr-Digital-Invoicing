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

# --- 4. THE API ENDPOINT ---
@app.post("/submit-invoice")
async def submit_invoice(invoice: InvoiceRequest, x_client_id: str = Header(...)):
    
    # A. Validate Client
    client_db = get_client_config()
    
    if x_client_id not in client_db:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Client ID")
    
    client_settings = client_db[x_client_id]

    # B. Prepare FBR Payload (The exact JSON FBR expects)
    # We calculate the current time dynamically
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    fbr_payload = {
        "InvoiceNumber": invoice.invoice_id,
        "POSID": client_settings["pos_id"],
        "USIN": invoice.usin,
        "DateTime": current_time,
        "BuyerNTN": "1234567-8", # Optional: Add to model if you need real buyer NTNs
        "BuyerName": "Walk-in Customer",
        "TotalSaleValue": invoice.total_bill,
        "TotalQuantity": sum(item.Quantity for item in invoice.items),
        "TotalTaxCharged": sum(item.TaxCharged for item in invoice.items),
        "Items": [item.dict() for item in invoice.items], # Converts Pydantic items to dict
        "PaymentMode": 1,
        "RefUSIN": ""
    }

    # C. Send to FBR (Real Logic vs Simulation)
    
    # --- REAL FBR CALL (Uncomment this when you have real credentials) ---
    # headers = {
    #     "Authorization": f"Bearer {client_settings['auth_token']}",
    #     "Content-Type": "application/json"
    # }
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         "https://esp.fbr.gov.pk:8243/FBR/v1/api/Live/PostData", 
    #         json=fbr_payload, 
    #         headers=headers
    #     )
    #     fbr_response = response.json()
    
    # --- SIMULATED FBR RESPONSE (So you can test immediately) ---
    # We simulate what FBR *would* return if it was successful
    fake_fbr_invoice_number = f"FBR-{secrets.token_hex(4).upper()}"
    fbr_response = {
        "Response": "Success", 
        "Code": 100, 
        "InvoiceNumber": fake_fbr_invoice_number,
        "Message": "Invoice posted successfully"
    }
    
    # D. Return Data to Frontend
    # This is exactly what Streamlit will see
    if fbr_response.get("Response") == "Success":
        return {
            "status": "success",
            "fbr_invoice_number": fbr_response.get("InvoiceNumber"),
            "message": "Verified by FBR"
        }
    else:
        return {
            "status": "failed",
            "fbr_invoice_number": None,
            "message": fbr_response.get("Message", "Unknown Error")
        }
