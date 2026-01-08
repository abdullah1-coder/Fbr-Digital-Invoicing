import os
import json
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# --- 1. CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. DATA MODELS (Matches what Streamlit Sends) ---
class InvoiceItem(BaseModel):
    ItemCode: str          # Maps to hsCode
    ItemName: str          # Maps to productDescription
    Quantity: float        # Maps to quantity
    TaxRate: float         # Maps to rate (need to convert to string "18%")
    SaleValue: float       # Maps to valueSalesExcludingST
    TaxCharged: float      # Maps to salesTaxApplicable
    TotalAmount: float     # Maps to totalValues

class InvoiceRequest(BaseModel):
    invoice_id: str
    usin: str
    items: List[InvoiceItem]
    total_bill: float
    buyer_reg: Optional[str] = "1000000000000" # Default dummy
    buyer_name: Optional[str] = "Walk-in Customer"
    buyer_type: Optional[str] = "Unregistered"

# --- 3. HELPER FUNCTION ---
def get_client_config():
    config_str = os.getenv("CLIENT_CONFIG")
    if not config_str: return {}
    try:
        return json.loads(config_str)
    except json.JSONDecodeError:
        print("ERROR: CLIENT_CONFIG is not valid JSON.")
        return {}

# --- 4. THE API ENDPOINT (REWRITTEN FOR DI FORMAT) ---
@app.post("/submit-invoice")
async def submit_invoice(invoice: InvoiceRequest, x_client_id: str = Header(...)):
    
    # A. Validate Client
    client_db = get_client_config()
    if x_client_id not in client_db:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Client ID")
    
    client_settings = client_db[x_client_id]

    # B. Prepare DI Format Payload
    # ---------------------------------------------------------
    # We map the data from Streamlit to the FBR DI JSON format
    # ---------------------------------------------------------
    
    # 1. Format the Date (YYYY-MM-DD)
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    
    # 2. Convert Items
    fbr_items = []
    for item in invoice.items:
        # Convert Rate 18.0 -> "18%"
        rate_str = f"{int(item.TaxRate)}%" if item.TaxRate.is_integer() else f"{item.TaxRate}%"
        
        fbr_item = {
            "hsCode": item.ItemCode,
            "productDescription": item.ItemName if item.ItemName else "Goods",
            "rate": rate_str,
            "uoM": "Numbers, pieces, units", # Default UoM
            "quantity": item.Quantity,
            "totalValues": item.TotalAmount,
            "valueSalesExcludingST": item.SaleValue,
            "fixedNotifiedValueOrRetailPrice": 0,
            "salesTaxApplicable": item.TaxCharged,
            "salesTaxWithheldAtSource": 0,
            "extraTax": 0,
            "furtherTax": 0,
            "sroScheduleNo": "",
            "fedPayable": 0,
            "discount": 0,
            "saleType": "Goods at standard rate (default)", # Default Scenario
            "sroItemSerialNo": ""
        }
        fbr_items.append(fbr_item)

    # 3. Build Final Payload
    fbr_payload = {
        "invoiceType": "Sale Invoice",
        "invoiceDate": invoice_date,
        "sellerNTNCNIC": client_settings.get("seller_ntn", "9999997"),
        "sellerBusinessName": client_settings.get("name", "My Business"),
        "sellerProvince": client_settings.get("province", "Sindh"), # Default if missing
        "sellerAddress": client_settings.get("address", "Karachi"), # Default if missing
        "buyerNTNCNIC": invoice.buyer_reg,
        "buyerBusinessName": invoice.buyer_name,
        "buyerProvince": "Sindh",
        "buyerAddress": "Karachi",
        "buyerRegistrationType": invoice.buyer_type,
        "invoiceRefNo": invoice.invoice_id,
        "scenarioId": "SN001", # Default to Standard Scenario
        "items": fbr_items
    }

    # C. SEND TO FBR
    fbr_url = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb"
    headers = {
        "Authorization": f"Bearer {client_settings['auth_token']}",
        "Content-Type": "application/json"
    }

    # Log what we are sending (Crucial for debugging)
    print(f"🚀 SENDING DI PAYLOAD: {json.dumps(fbr_payload, indent=2)}") 

    async with httpx.AsyncClient() as client:
        try:
            # verify=False is needed for FBR Sandbox SSL
            response = await client.post(fbr_url, json=fbr_payload, headers=headers, timeout=30.0)
            
            print(f"FBR Status: {response.status_code}")
            print(f"FBR Response: {response.text}")
            
            try:
                fbr_response = response.json()
            except json.JSONDecodeError:
                return {
                    "status": "failed", 
                    "message": f"Invalid JSON from FBR: {response.status_code}"
                }
            
            # D. Handle Response
            # FBR DI API returns "validationResponse" with "status": "Valid"
            if "validationResponse" in fbr_response:
                val_resp = fbr_response["validationResponse"]
                
                if val_resp.get("status") == "Valid":
                    # Success! Grab the top-level invoiceNumber if available
                    return {
                        "status": "success",
                        "fbr_invoice_number": fbr_response.get("invoiceNumber", "VERIFIED"),
                        "message": "Verified by FBR"
                    }
                else:
                    # Logic Error (e.g., Invalid HS Code)
                    return {
                        "status": "failed",
                        "message": val_resp.get("error", "Validation Failed")
                    }
            
            # Fallback for 401 or other errors
            return {
                "status": "failed",
                "message": fbr_response.get("Message", f"Error {response.status_code}")
            }

        except Exception as e:
            print(f"Connection Error: {e}")
            raise HTTPException(status_code=500, detail=f"FBR Connection Failed: {str(e)}")
