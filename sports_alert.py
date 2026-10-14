import os
import datetime
import time
import requests
from nhlpy import NHLClient  # Fixed correct import for the nhl-api-py package

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_USER_KEY = "u4qyk2eg37arj219w7typkcm8arwuj"
PUSHOVER_APP_TOKEN = "ar3yir78t4k5hxxym7e9dhkxsetvqe"

PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN")

# --- CONFIGURATION ---
# Dictionary of teams to track and their custom notification settings
TEAMS = {
    "DET": {
        "image_path": "wings.jpg", # Save a file named octopus.jpg in the same folder
        "cheer": "LGRW! 🐙"
    },
    "CHI": {
        "image_path": "chicago.jpg", 
        "cheer": "Go Hawks Go!"
    }
}
# Pulling credentials securely from Render's Environment Variables
PUSHOVER_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_USER_KEY = os.environ.get("PUSHOVER_USER_KEY")
PUSHOVER_APP_TOKEN = os.environ.get("PUSHOVER_APP_TOKEN")

# Initialize the NHL API Client
nhl_client = NHLClient()

def send_push_notification(message, team_abbrev):
    """Sends a Pushover notification with custom team details."""
    team_data = TEAMS.get(team_abbrev, {})
    cheer = team_data.get("cheer", "")
    image_path = team_data.get("image_path")

    payload = {
        "token": PUSHOVER_APP_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": f"{message}\n\n{cheer}",
        "title": f"{team_abbrev} Score Update 🚨"
    }

    try:
        # Check if local image attachment exists in the folder
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                files = {"attachment": ("image.jpg", image_file, "image/jpeg")}
                requests.post(PUSHOVER_URL, data=payload, files=files)
        else:
            requests.post(PUSHOVER_URL, data=payload)

        print(f"Notification sent for {team_abbrev}")

    except Exception as e:
        print(f"Failed to send notification for {team_abbrev}: {e}")

def track_game_for_team(team_abbrev):
    """Checks and updates live score status for a specific team."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Fetch today's games using the updated nhlpy syntax
        schedule = nhl_client.schedule.daily_schedule(date=today)
    except Exception as e:
        print(f"Failed to fetch schedule: {e}")
        return

    target_game = None
    for game in schedule:
        if game['awayTeam']['abbrev'] == team_abbrev or game['homeTeam']['abbrev'] == team_abbrev:
            target_game = game
            break

    if not target_game:
        print(f"No game today for {team_abbrev}.")
        return

    # Calculate wait time until puck drop
    start_time_str = target_game['startTimeUTC']
    game_start_utc = datetime.datetime.strptime(
        start_time_str, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.timezone.utc)
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    wait_seconds = (game_start_utc - now_utc).total_seconds()

    if wait_seconds > 0:
        print(f"Game for {team_abbrev} starts in {wait_seconds / 3600:.1f} hours.")
        time.sleep(wait_seconds)

    print(f"Game starting for {team_abbrev}! Monitoring score...")
    last_score = ""

    # Live polling loop
    while True:
        try:
            live_data = nhl_client.schedule.daily_schedule(date=today)
        except Exception:
            time.sleep(60)
            continue
            
        current_game = None
        for g in live_data:
            if g['awayTeam']['abbrev'] == team_abbrev or g['homeTeam']['abbrev'] == team_abbrev:
                current_game = g
                break

        if not current_game:
            break

        away_team = current_game['awayTeam']['abbrev']
        home_team = current_game['homeTeam']['abbrev']
        away_score = current_game.get('awayTeam', {}).get('score', 0)
        home_score = current_game.get('homeTeam', {}).get('score', 0)
        game_state = current_game.get('gameState')  # "FUT", "PRE", "LIVE", "CRIT", "OFF", "FINAL"

        current_score_str = f"{away_team} {away_score} - {home_score} {home_team}"

        # Send alert if game is active or final, and the score changed
        if game_state not in ["FUT", "PRE"] and current_score_str != last_score:
            if game_state in ["OFF", "FINAL"]:
                send_push_notification(f"🏁 FINAL SCORE: {current_score_str}", team_abbrev)
            else:
                send_push_notification(f"🚨 SCORE ALERT: {current_score_str}", team_abbrev)

            last_score = current_score_str

        # Stop polling if the game is over
        if game_state in ["OFF", "FINAL"]:
            print(f"Game complete for {team_abbrev}.")
            break

        time.sleep(300)  # Wait 5 minutes between updates

def main():
    print("Starting NHL Score Tracker...")
    for team in TEAMS.keys():
        track_game_for_team(team)

if __name__ == "__main__":
    main()