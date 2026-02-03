import os
import json
import httpx
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any

# Initialize FastAPI with custom paths for Vercel
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
# Keys are pulled from Vercel Environment Variables for security
GRID_API_KEY = os.environ.get("GRID_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# GRID API Endpoint (Standard GraphQL Query)
GRID_QUERY_URL = "https://api.grid.gg/query"

# Gemini 2.5 Flash Endpoint
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={GEMINI_API_KEY}"


# --- GRID AUTHENTICATION LOGIC ---

async def fetch_real_grid_data(series_id: str):
    """
    Fetches real-time series events using the 'x-api-key' header
    as specified in the GRID.gg documentation.
    """
    if not GRID_API_KEY:
        return {"error": "GRID_API_KEY missing in environment variables"}

    # This GraphQL query targets high-leverage kill events and timestamps
    query = """
    query GetMatchDetails($id: ID!) {
      series(id: $id) {
        id
        games {
          id
          events {
            type
            timestamp
            ... on KillEvent {
              killer { name }
              victim { name }
            }
          }
        }
      }
    }
    """

    headers = {
        "x-api-key": GRID_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                GRID_QUERY_URL,
                json={"query": query, "variables": {"id": series_id}},
                headers=headers,
                timeout=15.0
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}


# --- ENDPOINTS ---

@app.get("/api/python")
def hello_world():
    return {
        "status": "online",
        "message": "Echo Engine Operational",
        "grid_auth": "x-api-key ready" if GRID_API_KEY else "Missing GRID Key"
    }


@app.post("/api/analyze")
async def analyze(request: Request):
    """
    Unified endpoint: Fetches from GRID (if ID provided) or analyzes the snapshot.
    """
    data = await request.json()
    series_id = data.get("series_id")

    # 1. Gather Context (Real data from GRID or the provided manual snapshot)
    if series_id:
        grid_result = await fetch_real_grid_data(series_id)
        match_context = json.dumps(grid_result)
    else:
        match_context = str(data)

    # 2. Check for Gemini Key
    if not GEMINI_API_KEY:
        return {
            "coach_insight": "[DEMO MODE] Coach Inero: I'm seeing a lack of tactical discipline. You committed to that site entry without clearing the corners or waiting for utility backup. It's a fundamental error that costs us rounds. Fix it."
        }

    # 3. Call Gemini Reasoning Layer (Exponential Backoff included)
    system_prompt = (
        "You are Head Coach Inero from Cloud9. Analyze this GRID match data and identify "
        "one specific tactical error. Be blunt, professional, and explain the 'Why' behind "
        "the tactical failure using terms like 'spacing', 'utility usage', or 'map pressure'."
    )

    payload = {
        "contents": [{"parts": [{"text": f"Analyze this match sequence: {match_context}"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    async with httpx.AsyncClient() as client:
        for delay in [1, 2, 4]:  # Retry delays
            try:
                response = await client.post(GEMINI_URL, json=payload, timeout=25.0)
                if response.status_code == 200:
                    result = response.json()
                    insight = result['candidates'][0]['content']['parts'][0]['text']
                    return {"coach_insight": insight}
            except Exception:
                await asyncio.sleep(delay)

    return {"coach_insight": "Coach is busy reviewing the tape. Connection to reasoning engine timed out."}


@app.get("/api/leaderboard")
async def get_leaderboard():
    """
    Returns the Tactical IQ rankings.
    """
    return [
        {"rank": 1, "player": "C9_Berserker", "iq": 98, "status": "ELITE"},
        {"rank": 2, "player": "C9_Blaber", "iq": 94, "status": "PRO"},
        {"rank": 3, "player": "You (User)", "iq": 85, "status": "IMPROVING"},
        {"rank": 4, "player": "VOD_Reviewer_42", "iq": 62, "status": "LEARNING"}
    ]