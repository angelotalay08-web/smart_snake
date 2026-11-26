SMART SNAKE — CARNIVAL EDITION

Included:
- templates/index.html: carnival colors, power-ups (food +10, coin +50, speed boost, temporary shield, extra life), game-over celebration/confetti, top 20 leaderboard, local personal best/games played, keyboard + on-screen controls, fullscreen button.
- app.py: Flask endpoints for ESP32, sound events, and persistent Top 20 leaderboard in leaderboard.json.
- esp32_snake.ino: physical button controller, LED status, buzzer sounds for start/food/coin/death/power-up.

SETUP
1. Back up your existing project first.
2. Copy this package's app.py and templates/index.html into your project, preserving the templates folder.
3. Install dependencies in the project terminal: pip install -r requirements.txt
4. Open esp32_snake.ino and set WIFI_SSID, WIFI_PASSWORD, and SERVER_BASE to your actual Wi-Fi/hotspot and laptop IPv4 address. Do not share your Wi-Fi password publicly.
5. Wiring: each directional button between its GPIO and GND; START button GPIO23 to GND. Buzzer on GPIO26, red LED GPIO32, green LED GPIO33 (use suitable resistors for LEDs).
6. Upload esp32_snake.ino to ESP32.
7. Run app.py and open http://127.0.0.1:5000 on the laptop. Other devices on same network use laptop IPv4 address and port 5000.

NOTE
- The Top 20 server leaderboard is stored in leaderboard.json next to app.py. Existing older scores in a different file will not automatically migrate; back up and merge manually if needed.
- Player best score and games played are stored in that browser's localStorage, so they are local to that browser/device.
- The shield lasts 6 seconds. The extra-life token starts available once per round; if used, a later heart pickup can restore it.
- Verify your ESP32 pins match your actual wiring before powering the board.
