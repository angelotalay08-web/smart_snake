from flask import Flask, render_template, request, jsonify, make_response
from collections import deque
from threading import Lock
from pathlib import Path
import json
import time

app = Flask(__name__)

# Shared state used by the browser game and ESP32 controller.
state_lock = Lock()
game_state = "READY"
last_direction = ""
command_id = 0
start_command_id = 0
last_seen = 0
sound_events = deque(maxlen=50)

LEADERBOARD_FILE = Path(__file__).with_name("leaderboard.json")
VALID_DIRECTIONS = {"UP", "DOWN", "LEFT", "RIGHT"}
VALID_STATES = {"READY", "PLAYING", "PAUSED", "GAME_OVER"}
VALID_SOUNDS = {"button", "food", "death", "start", "coin", "powerup"}
VALID_MODES = {"SOLO", "VS_AI"}
VALID_RESULTS = {"SOLO", "WIN", "LOSS", "DRAW"}


@app.after_request
def no_cache(response):
  response.headers["Cache-Control"] = (
      "no-store, no-cache, must-revalidate, max-age=0"
  )
  response.headers["Pragma"] = "no-cache"
  return response


@app.route("/")
def home():
  return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
  # Prevent the browser's harmless missing-favicon 404 from cluttering Console.
  return "", 204


def load_scores():
  try:
    data = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
      return []
    # Ignore malformed rows and keep the fields the game needs.
    cleaned = []
    for row in data:
      if not isinstance(row, dict) or not str(row.get("name", "")).strip():
        continue
      try:
        score = max(0, int(row.get("score", 0)))
      except (TypeError, ValueError):
        score = 0

      mode = str(row.get("mode", "SOLO")).strip().upper()[:16]
      if mode not in VALID_MODES:
        mode = "SOLO"

      match_result = str(row.get("match_result", "SOLO")).strip().upper()[:16]
      if match_result not in VALID_RESULTS:
        match_result = "SOLO"

      playstyle = (
          str(row.get("playstyle", "All-Rounder")).strip()[:24] or "All-Rounder"
      )

      cleaned.append({
          "name": str(row.get("name", "")).strip()[:18],
          "score": score,
          "timestamp": row.get("timestamp", 0),
          "mode": mode,
          "match_result": match_result,
          "playstyle": playstyle,
      })
    cleaned.sort(key=lambda row: row["score"], reverse=True)
    return cleaned[:20]
  except (OSError, json.JSONDecodeError):
    return []


def save_scores(scores):
  LEADERBOARD_FILE.write_text(
      json.dumps(scores[:20], ensure_ascii=False, indent=2),
      encoding="utf-8",
  )


def add_sound(event):
  if event not in VALID_SOUNDS:
    return False
  with state_lock:
    sound_events.append(event)
  return True


@app.route("/leaderboard", methods=["GET", "POST"])
def leaderboard():
  with state_lock:
    scores = load_scores()

    if request.method == "POST":
      data = request.get_json(silent=True) or {}
      name = " ".join(str(data.get("name", "")).split())[:18]
      if not name:
        return jsonify({"error": "Please enter a player name."}), 400

      existing_names = {
          row["name"].strip().casefold()
          for row in scores
          if isinstance(row, dict)
      }
      if name.casefold() in existing_names:
        return (
            jsonify({
                "error": "Player name already exists. Please use another name."
            }),
            409,
        )

      try:
        score = max(0, int(data.get("score", 0)))
      except (TypeError, ValueError):
        score = 0

      mode = str(data.get("mode", "SOLO")).strip().upper()[:16]
      if mode not in VALID_MODES:
        mode = "SOLO"

      match_result = str(data.get("match_result", "SOLO")).strip().upper()[:16]
      if match_result not in VALID_RESULTS:
        match_result = "SOLO" if mode == "SOLO" else "WIN"

      playstyle = (
          str(data.get("playstyle", "All-Rounder")).strip()[:24] or "All-Rounder"
      )

      scores.append({
          "name": name,
          "score": score,
          "timestamp": int(time.time()),
          "mode": mode,
          "match_result": match_result,
          "playstyle": playstyle,
      })
      scores.sort(key=lambda row: row["score"], reverse=True)
      scores = scores[:20]
      try:
        save_scores(scores)
      except OSError:
        app.logger.exception("Could not save leaderboard file")
        return jsonify({"error": "Could not save leaderboard."}), 500

    # This shape matches the supplied index.html refresh() and saveScore().
    return jsonify({"leaderboard": scores})


@app.route("/check-name", methods=["POST"])
def check_name():
  data = request.get_json(silent=True) or {}
  name = " ".join(str(data.get("name", "")).split())[:18]
  if not name:
    return (
        jsonify({"available": False, "message": "Please enter a player name."}),
        400,
    )

  with state_lock:
    scores = load_scores()
    exists = any(
        row["name"].strip().casefold() == name.casefold() for row in scores
    )

  if exists:
    return (
        jsonify({
            "available": False,
            "message": "Naulit ang pangalan! Please enter another name.",
        }),
        409,
    )
  return jsonify({"available": True})


@app.route("/direction", methods=["POST"])
def direction():
  global last_direction, command_id, last_seen
  data = request.get_json(silent=True) or {}
  value = str(data.get("direction", "")).upper()
  if value not in VALID_DIRECTIONS:
    return jsonify({"error": "Invalid direction"}), 400
  with state_lock:
    last_direction = value
    command_id += 1
    last_seen = int(time.time())
    current_id = command_id
  add_sound("button")
  return jsonify({"ok": True, "direction": value, "command_id": current_id})


@app.route("/start", methods=["POST"])
def esp32_start():
  global start_command_id, last_seen
  with state_lock:
    start_command_id += 1
    last_seen = int(time.time())
    current_id = start_command_id
  add_sound("start")
  return jsonify({"ok": True, "start_command_id": current_id})


@app.route("/status", methods=["GET"])
def status():
  with state_lock:
    return jsonify({
        "last_direction": last_direction,
        "command_id": command_id,
        "start_command_id": start_command_id,
        "last_seen": last_seen,
        "game_state": game_state,
    })


@app.route("/game-state", methods=["POST"])
def set_game_state():
  global game_state
  data = request.get_json(silent=True) or {}
  value = str(data.get("state", "")).upper()
  if value not in VALID_STATES:
    return jsonify({"error": "Invalid game state"}), 400
  with state_lock:
    game_state = value
  if value == "GAME_OVER":
    add_sound("death")
  return jsonify({"ok": True, "game_state": value})


@app.route("/led-status", methods=["GET"])
def led_status():
  with state_lock:
    return jsonify({"game_state": game_state})


@app.route("/sound-event", methods=["POST"])
def sound_event():
  data = request.get_json(silent=True) or {}
  event = str(data.get("event", "")).lower()
  if not add_sound(event):
    return jsonify({"error": "Invalid sound event"}), 400
  return jsonify({"ok": True, "event": event})


@app.route("/sound-next", methods=["GET"])
def sound_next():
  with state_lock:
    event = sound_events.popleft() if sound_events else None
  if event is None:
    return "", 204
  return make_response(event, 200, {"Content-Type": "text/plain; charset=utf-8"})


if __name__ == "__main__":
  print("Smart Snake Carnival server: http://127.0.0.1:5000")
  # threaded=True lets the browser game and ESP32 requests be handled together.
  app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)