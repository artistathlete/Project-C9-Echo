import httpx
import asyncio
import json


async def test_coach_inero():
    """
    Simulates sending a high-leverage match moment to the Echo API.
    """
    # The URL where your main.py server is running
    url = "http://127.0.0.1:8000/analyze"

    # Mock data: A typical 'Moneyball' failure scenario in VALORANT
    # Scenario: A duelist dies early without utility support, leading to a site loss.
    payload = {
        "moment_id": "val-match-001-round-10",
        "events": [
            {
                "game": "valorant",
                "event_type": "death",
                "timestamp": 142.5,
                "player_id": "C9_Perkz",
                "description": "Jett died at B-Main. She dashed in alone with no flash support from the team.",
                "gold_delta": -2900
            },
            {
                "game": "valorant",
                "event_type": "spike_plant",
                "timestamp": 148.2,
                "description": "Opponents planted the spike for B-Long. Defenders are tucked in site with no utility to retake.",
                "gold_delta": -500
            }
        ],
        "game_state": {
            "round_score": "4-5",
            "attacking_team": "Opponent",
            "economy": "Half-buy"
        }
    }

    print("--- PROJECT C9 ECHO: CONSULTATION START ---")
    print(f"Connecting to server at {url}...")

    async with httpx.AsyncClient() as client:
        try:
            # We use a long timeout (60s) because the AI reasoning might take a moment
            response = await client.post(url, json=payload, timeout=60.0)

            if response.status_code == 200:
                result = response.json()
                print("\n✅ CONNECTION SUCCESSFUL")
                print("\n[COACH INERO'S ANALYSIS]:")
                print("--------------------------------------------------")
                print(result.get('coach_insight'))
                print("--------------------------------------------------")
                print("\nStrategy Tip: Use this text for your 'Echo Insight' demo examples.")
            else:
                print(f"\n❌ SERVER ERROR: {response.status_code}")
                print(f"Detail: {response.text}")

        except httpx.ConnectError:
            print("\n❌ CONNECTION ERROR: Is your 'main.py' server running?")
            print("Run 'python main.py' in a separate terminal tab first.")
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_coach_inero())