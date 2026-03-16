# Assassin's Creed Syndicate - Auto-Combat AI 🗡️🤖

A fully automated, multi-threaded combat assistant for *Assassin's Creed Syndicate* built in Python. This script uses high-speed screen capture and OpenCV template matching to play the game's combat loop for you. It automatically spams attacks and reacts to enemy visual cues to parry, dodge, and break guards flawlessly.

## ✨ Features
* **Computer Vision "Brain":** Uses `OpenCV` and `mss` to capture and analyze the screen at high FPS, identifying enemy health bars, attack indicators (yellow highlights), and UI prompts.
* **Auto-Attacking:** A dedicated background thread constantly spams light attacks (Left Click) whenever the AI detects you are in combat.
* **Flawless Defense:** Instantly pauses auto-attacking to execute a rapid 3-key defensive sequence when it detects:
  * **Parry (`E`):** Detects incoming yellow attacks or the 'E' prompt.
  * **Dodge (`F`):** Detects incoming gunshot/dodge prompts.
  * **Guard Break (`Space`):** Detects defending enemies to break their stance.
* **Custom UI Overlay:** Features a transparent, click-through Tkinter overlay running at 60 FPS that draws bounding boxes around detected threats and displays the bot's current state (IDLE / SPAMMING ATTACK / DEFENDING).
* **Fail-Safe:** Pressing the `END` key immediately releases all mouse inputs and safely kills the script.

## ⚙️ How it Works
The AI is divided into three parallel threads to ensure zero input lag:
1. **The Vision Thread:** Captures the screen, applies HSV color masking (to isolate yellow attack indicators), and uses `cv2.matchTemplate` to find exact matches from the `.png` image banks.
2. **The Action Thread:** Uses `pydirectinput` to simulate human-like mouse clicks and keyboard presses based on what the vision thread sees. 
3. **The Rendering Thread:** Draws real-time visual feedback (magenta, blue, and orange boxes) directly over the game window using a borderless `tkinter` window.

## 🛑 Controls
* **Start:** Run the script (ensure your game is in Borderless/Windowed mode).
* **Kill Switch:** Press `END` on your keyboard to completely shut down the AI and release all inputs.

## ⚠️ Requirements
To run this AI, you need the following Python libraries:
`pip install opencv-python numpy mss pydirectinput keyboard`
*(Note: You must provide your own image template `.png` banks in the root directory for the AI to recognize the game's UI).*
