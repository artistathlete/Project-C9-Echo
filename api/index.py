import os
import json
import httpx
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any

# Initialize FastAPI with custom docs paths for Vercel
app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keys from Vercel Environment Variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


@app.get("/api/python")
def hello_world():
    return {"status": "online", "message": "Echo Logic Operational on Vercel"}


@app.post("/api/analyze")
async def analyze(request: Request):
    snapshot = await request.json()

    # Check if key is available, else return a high-quality mock for the demo
    if not GEMINI_API_KEY:
        return {
            "coach_insight": "[DEMO MODE] Coach Inero: I noticed a major coordination lapse here. You committed to the B-site push without waiting for the Sova drone to clear back-site. In a professional environment, we don't gamble on 50/50s like that. Fix your utility timing."
        }

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={GEMINI_API_KEY}"

    system_prompt = "You are Head Coach Inero from Cloud9. Analyze this game data and identify one specific tactical error. Be blunt and professional."

    payload = {
        "contents": [{"parts": [{"text": str(snapshot)}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(gemini_url, json=payload, timeout=25.0)
            result = response.json()
            insight = result['candidates'][0]['content']['parts'][0]['text']
            return {"coach_insight": insight}
        except Exception as e:
            return {"coach_insight": f"Coach is reviewing the tape. (Error: {str(e)})"}


@app.get("/api/leaderboard")
async def get_leaderboard():
    # Persistent Leaderboard Fallback
    return [
        {"rank": 1, "player": "C9_Berserker", "iq": 98, "status": "ELITE"},
        {"rank": 2, "player": "C9_Blaber", "iq": 94, "status": "PRO"},
        {"rank": 3, "player": "You (User)", "iq": 85, "status": "IMPROVING"},
        {"rank": 4, "player": "VOD_Reviewer_42", "iq": 62, "status": "LEARNING"}
    ]