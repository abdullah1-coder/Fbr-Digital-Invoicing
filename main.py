import os
import json
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DYNAMIC DATA MODELS ---
class InvoiceItem(BaseModel):
    ItemCode: str
    ItemName: str
    Quantity: float
    TaxRate: float
    SaleValue: float
    TaxCharged: float
    TotalAmount: float

class InvoiceRequest(BaseModel):
    invoice_id: str
    usin: str
    items: List[InvoiceItem]
    total_bill: float
    # 👇 NO DEFAULTS! The Frontend MUST send these now.
    buyer_reg: str 
    buyer_name: str
    buyer_type: str
    scenario_id: str # We enforce that this must be sent

def get_client_config():
    config_str = os.getenv("CLIENT_CONFIG")
    if not config_str: return {}
    try:
        return json.loads(config_str)
    except json.JSONDecodeError:
        return {}

@app.post("/submit-invoice")
async def submit_invoice(invoice: InvoiceRequest, x_client_id: str = Header(...)):
    
    # 1. Validate Client
    client_db = get_client_config()
    if x_client_id not in client_db:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Client ID")
    
    client_settings = client_db[x_client_id]

    # 2. Build Payload DYNAMICALLY
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    
    fbr_items = []
    for item in invoice.items:
        # Dynamic Rate Conversion (Handles 18.0 -> "18%")
        rate_str = f"{int(item.TaxRate)}%" if item.TaxRate.is_integer() else f"{item.TaxRate}%"
        
        fbr_items.append({
            "hsCode": item.ItemCode,
            "productDescription": item.ItemName or "Goods", # Fallback only if empty string
            "rate": rate_str,
            "uoM": "Numbers, pieces, units",
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
            "saleType": "Goods at standard rate (default)", # Ideally this should also be dynamic if you add a dropdown
            "sroItemSerialNo": ""
        })

    fbr_payload = {
        "invoiceType": "Sale Invoice",
        "invoiceDate": invoice_date,
        # Dynamic Seller Details from Render Config
        "sellerNTNCNIC": client_settings.get("seller_ntn", "9999997"), 
        "sellerBusinessName": client_settings.get("name", "My Business"),
        "sellerProvince": client_settings.get("province", "Sindh"),
        "sellerAddress": client_settings.get("address", "Karachi"),
        
        # Dynamic Buyer Details from Frontend Request
        "buyerNTNCNIC": invoice.buyer_reg,
        "buyerBusinessName": invoice.buyer_name,
        "buyerProvince": "Sindh", # You can make this dynamic later too
        "buyerAddress": "Karachi",
        "buyerRegistrationType": invoice.buyer_type,
        "invoiceRefNo": invoice.invoice_id,
        "scenarioId": invoice.scenario_id, # 👈 KEY FIX: Uses exactly what Frontend sends
        "items": fbr_items
    }

    # 3. Send to FBR
    fbr_url = "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb"
    headers = {
        "Authorization": f"Bearer {client_settings['auth_token']}",
        "Content-Type": "application/json"
    }

    print(f"🚀 DYNAMIC PAYLOAD: {json.dumps(fbr_payload, indent=2)}") 

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(fbr_url, json=fbr_payload, headers=headers, timeout=30.0)
            
            try:
                fbr_response = response.json()
            except:
                return {"status": "failed", "message": f"FBR Error {response.status_code}: {response.text}"}
            
            if "validationResponse" in fbr_response:
                val_resp = fbr_response["validationResponse"]
                if val_resp.get("status") == "Valid":
                    return {
                        "status": "success",
                        "fbr_invoice_number": fbr_response.get("invoiceNumber", "VERIFIED"),
                        "message": "Verified by FBR"
                    }
                else:
                    return {"status": "failed", "message": val_resp.get("error", "Validation Failed")}
            
            return {"status": "failed", "message": fbr_response.get("Message", "Unknown Error")}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Connection Failed: {str(e)}")
