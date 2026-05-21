"""
WhatsApp Business Onboarding — FastAPI Backend
----------------------------------------------
Receives the Embedded Signup result from the frontend,
exchanges the short-lived code for a Meta access token,
and saves the full account record to Supabase.

Start locally:
  uvicorn whatsapp_backend:app --reload --port 8000

Deploy to Railway / Render:
  Start command: uvicorn whatsapp_backend:app --host 0.0.0.0 --port $PORT
"""

import os
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()

SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
META_GRAPH_VERSION   = os.getenv("META_GRAPH_VERSION", "v25.0")

# ── Supabase client ───────────────────────────────────────────────────────────
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="WhatsApp Onboarding API",
    description="Handles WhatsApp Embedded Signup token exchange and Supabase storage",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Tighten to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Request / Response models ─────────────────────────────────────────────────

class OnboardRequest(BaseModel):
    """Body sent from the frontend after Embedded Signup completes."""
    code:             str            # Short-lived code from Meta (valid 30s)
    app_id:           str            # Meta App ID (entered by user in frontend)
    app_secret:       str            # Meta App Secret (entered by user in frontend)
    config_id:        Optional[str] = None
    waba_id:          str            # WhatsApp Business Account ID
    phone_number_id:  str            # WA Phone Number ID
    business_id:      Optional[str] = None


class OnboardResponse(BaseModel):
    success:          bool
    account_id:       str            # UUID of the new row in whatsapp_accounts
    waba_id:          str
    phone_number_id:  str
    access_token:     str            # The exchanged token (also stored in Supabase)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "WhatsApp Onboarding API", "version": "1.0.0"}


# ── Main onboarding endpoint ──────────────────────────────────────────────────

@app.post("/api/onboard", response_model=OnboardResponse, tags=["onboarding"])
async def onboard(req: OnboardRequest):
    """
    1. Exchange the Embedded Signup `code` for a Meta access token.
    2. Save the full account record to Supabase (whatsapp_accounts table).
    3. Return the account ID and token to the frontend.

    The `code` expires in 30 seconds — this endpoint must be called immediately
    after the user completes the Embedded Signup flow.
    """

    # ── Step 1: Exchange code → access token via Meta Graph API ───────────────
    logger.info(f"Exchanging token for waba_id={req.waba_id}, app_id={req.app_id}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_res = await client.get(
            f"https://graph.facebook.com/{META_GRAPH_VERSION}/oauth/access_token",
            params={
                "client_id":     req.app_id,
                "client_secret": req.app_secret,
                "code":          req.code,
            },
        )

    if token_res.status_code != 200:
        logger.error(f"Meta token exchange failed: {token_res.text}")
        raise HTTPException(
            status_code=400,
            detail=f"Meta token exchange failed: {token_res.text}",
        )

    token_data   = token_res.json()
    access_token = token_data.get("access_token")

    if not access_token:
        logger.error(f"No access_token in Meta response: {token_data}")
        raise HTTPException(
            status_code=400,
            detail=f"No access_token returned by Meta: {token_data}",
        )

    logger.info(f"Token exchange successful for waba_id={req.waba_id}")

    # ── Step 2: Save to Supabase ───────────────────────────────────────────────
    row = {
        "app_id":           req.app_id,
        "app_secret":       req.app_secret,
        "config_id":        req.config_id,
        "waba_id":          req.waba_id,
        "phone_number_id":  req.phone_number_id,
        "business_id":      req.business_id,
        "access_token":     access_token,
        "status":           "active",
    }

    try:
        result = supabase.table("whatsapp_accounts").insert(row).execute()
    except Exception as e:
        logger.error(f"Supabase insert failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if not result.data:
        raise HTTPException(status_code=500, detail="Supabase returned no data after insert")

    saved      = result.data[0]
    account_id = saved["id"]

    logger.info(f"Saved account {account_id} for waba_id={req.waba_id}")

    # ── Step 3: Return result ─────────────────────────────────────────────────
    return OnboardResponse(
        success=True,
        account_id=account_id,
        waba_id=req.waba_id,
        phone_number_id=req.phone_number_id,
        access_token=access_token,
    )


# ── List saved accounts (optional — useful for testing) ───────────────────────

@app.get("/api/accounts", tags=["accounts"])
def list_accounts():
    """
    Returns all saved WhatsApp accounts from Supabase.
    Omits app_secret and access_token for safety.
    Remove or protect this endpoint before going to production.
    """
    try:
        result = (
            supabase.table("whatsapp_accounts")
            .select("id, app_id, config_id, waba_id, phone_number_id, business_id, status, created_at")
            .order("created_at", desc=True)
            .execute()
        )
        return {"accounts": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
