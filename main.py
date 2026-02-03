import os
import asyncio
import json
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# --- 1. DATA MODELS ---
# These models normalize GRID data so the AI can process LoL and VALORANT consistently.
class GameEvent(BaseModel):
    game: str  # 'lol' or 'valorant'
    event_type: str
    timestamp: float
    player_id: Optional[str] = None
    team_id: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    gold_delta: Optional[int] = 0
    description: str


class MatchSnapshot(BaseModel):
    moment_id: str
    events: List[GameEvent]
    game_state: Dict[str, Any]
    coach_insight: Optional[str] = None


# --- 2. API SETUP ---
app = FastAPI(title="Project C9 Echo API")

# Enable CORS for frontend or local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key and URL Configuration
# Note: apiKey is set to an empty string as required by the environment.
apiKey = ""
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"


# --- 3. AI REASONING ENGINE (Exponential Backoff) ---
async def call_gemini_with_backoff(prompt: str):
    """
    Calls the Gemini API to generate coaching insights.
    Implements mandatory exponential backoff: retries up to 5 times.
    """
    system_prompt = (
        "You are Head Coach Inero from Cloud9. You are a legendary coach in VALORANT and League of Legends. "
        "Your goal is to provide 'Moneyball' style tactical analysis. "
        "Do not just list stats. Explain WHY a play failed or succeeded based on tactical positioning and utility usage. "
        "Be concise, professional, and slightly blunt. Use terms like 'defaulting', 'spacing', 'utility usage', and 'rotations'."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    # Delays for backoff: 1s, 2s, 4s, 8s, 16s
    delays = [1, 2, 4, 8, 16]

    async with httpx.AsyncClient() as client:
        for delay in delays:
            try:
                response = await client.post(GEMINI_URL, json=payload, timeout=30.0)
                if response.status_code == 200:
                    result = response.json()
                    # Parse the content from the Gemini response structure
                    return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text',
                                                                                                          "Insight unavailable.")
            except Exception:
                # Silently fail and wait for next retry
                pass
            await asyncio.sleep(delay)

    return "The coach is currently reviewing the VOD. Please try again later. (API Timeout)"


# --- 4. ENDPOINTS ---
@app.get("/")
async def root():
    return {"status": "online", "coach": "Inero"}


@app.post("/analyze")
async def analyze_match(snapshot: MatchSnapshot):
    """
    Primary endpoint for 'Echo'. Receives match data and returns coaching insights.
    """
    if not snapshot.events:
        raise HTTPException(status_code=400, detail="No events provided in the snapshot.")

    # Format the events into a log for the AI
    events_log = "\n".join([f"- {e.timestamp}s: {e.description} (Type: {e.event_type})" for e in snapshot.events])

    user_query = f"""
    Analyze this high-leverage moment in a {snapshot.events[0].game} match:
    Moment ID: {snapshot.moment_id}
    Current Game State: {json.dumps(snapshot.game_state)}

    Events Log:
    {events_log}

    As Coach Inero, identify the most critical mistake or winning play in this sequence. 
    Explain what should have been done differently.
    """

    # Generate the insight using the reasoning engine
    insight = await call_gemini_with_backoff(user_query)
    snapshot.coach_insight = insight
    return snapshot


if __name__ == "__main__":
    import uvicorn

    # Start the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)