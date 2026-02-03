import os
import asyncio
import json
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# --- 1. DATA MODELS ---
class GameEvent(BaseModel):
    """Normalized event structure for both LoL and VALORANT"""
    game: str  # 'lol' or 'valorant'
    event_type: str
    timestamp: float
    player_id: Optional[str] = None
    team_id: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    gold_delta: Optional[int] = 0
    description: str


class MatchSnapshot(BaseModel):
    """A collection of events representing a 'high-leverage' moment"""
    moment_id: str
    events: List[GameEvent]
    game_state: Dict[str, Any]
    coach_insight: Optional[str] = None


# --- 2. API SETUP ---
app = FastAPI(title="Project C9 Echo API")

# Enable CORS for local testing and frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. CONFIGURATION (GRID & GEMINI) ---
# Replace these with your actual keys or set them as environment variables
GRID_API_KEY = os.environ.get("GRID_API_KEY", "YOUR_GRID_API_KEY_HERE")
apiKey = os.environ.get("GEMINI_API_KEY", "")  # Environment provides key at runtime

# Endpoints
GRID_QUERY_URL = "https://api.grid.gg/query"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={apiKey}"


# --- 4. GRID DATA FETCHING (AUTHENTICATION) ---
async def fetch_real_grid_data(series_id: str):
    """
    Fetches real-time series events using the 'x-api-key' header
    as specified in the GRID.gg documentation.
    """
    if not GRID_API_KEY or "YOUR_GRID" in GRID_API_KEY:
        return {"error": "GRID_API_KEY not configured."}

    # GraphQL query to extract kills and timestamps for coaching analysis
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
            return {"error": f"Failed to connect to GRID: {str(e)}"}


# --- 5. AI REASONING ENGINE (Exponential Backoff) ---
async def call_gemini_with_backoff(prompt: str):
    """
    Calls Gemini API with mandatory exponential backoff: retries up to 5 times.
    """
    system_prompt = (
        "You are Head Coach Inero from Cloud9. You provide blunt, tactical coaching. "
        "Focus on 'Moneyball' metrics: utility usage, spacing, and map pressure. "
        "Identify exactly one tactical error in the data provided."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    delays = [1, 2, 4, 8, 16]
    async with httpx.AsyncClient() as client:
        for delay in delays:
            try:
                response = await client.post(GEMINI_URL, json=payload, timeout=30.0)
                if response.status_code == 200:
                    result = response.json()
                    return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text',
                                                                                                          "No insight.")
            except Exception:
                pass
            await asyncio.sleep(delay)

    return "Coach Inero is reviewing the VOD. (API Timeout)"


# --- 6. ENDPOINTS ---
@app.get("/")
async def root():
    return {
        "status": "online",
        "coach": "Inero",
        "grid_connected": bool(GRID_API_KEY and "YOUR" not in GRID_API_KEY)
    }


@app.post("/analyze")
async def analyze_match(snapshot: MatchSnapshot):
    """
    Manual analysis endpoint: Receives normalized data and returns insight.
    """
    events_log = "\n".join([f"- {e.description}" for e in snapshot.events])
    user_query = f"Analyze this match moment:\n{events_log}\nGame State: {json.dumps(snapshot.game_state)}"

    insight = await call_gemini_with_backoff(user_query)
    snapshot.coach_insight = insight
    return snapshot


@app.get("/analyze-series/{series_id}")
async def analyze_real_match(series_id: str):
    """
    Automated Analysis: Pulls data from GRID and passes to Gemini.
    """
    grid_data = await fetch_real_grid_data(series_id)
    insight = await call_gemini_with_backoff(f"Analyze this raw GRID series data: {json.dumps(grid_data)}")

    return {
        "series_id": series_id,
        "coach_insight": insight,
        "data_source": "GRID Data Platform"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)