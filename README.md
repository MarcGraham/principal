# EduOS Professional — Principal's Workstation

> [!IMPORTANT]
> **OPERATIONAL SUMMARY (READ FIRST)**
> * **Display Mode:** This application runs in **Immersive Fullscreen Mode** by default on all platforms. Keyboard focus is held so players cannot escape or access the underlying operating system.
> * **Game Master Escape Backdoor:** To exit the application at any time, hold **`Control + Option`** (or **`Control + Alt`**) and tap the **`Escape`** key **3 times quickly (in under 1.5 seconds)**. Active at all times, including on win/lose screens.
> * **Game Master Reset Backdoor:** To restart/reset the game at any time for another play, hold **`Control + Option`** (or **`Control + Alt`**) and tap the **`R`** key **3 times quickly (in under 1.5 seconds)**. This relocks the physical maglock, clears any lockout counters, and restarts the game cleanly.
> * **System Passwords:**
>   * **Computer Lock Screen Login:** `admin`
>   * **District Grades Portal gateway Key:** `override`

---

## 🎮 Game Flow Overview

The game simulates the "EduOS Professional" desktop on a high school principal's workstation. Players must navigate the desktop to hack into the District Grade Database and override a student's grades to trigger the physical door release.

```mermaid
graph TD
    Start[Computer Lock Screen] -->|Password: admin| Desktop[EduOS Desktop]
    Desktop -->|Explore files| FakeFiles[Excel/Notepad/PDF - Lore & Clues]
    Desktop -->|🌐 Grade Portal icon| Gateway[Encrypted Portal gateway]
    Gateway -->|Key: override| Modifier[Grade Modifier Panel]
    Gateway -->|4 Consecutive Fails| Lose[SECURITY LOCKOUT SCREEN]
    Modifier -->|Change all grades to A| Win[SYSTEM OVERRIDE SUCCESS]
    Win -->|Triggers Relay Pin 18| Door[🚪 EXIT DOOR UNLOCKED]
```

---

## 🔒 Escape & Lockout Mechanics

### 1. Win Condition (System Override)
* **Objective:** Open the **Grade Portal**, authenticate, and change all subjects for student *Alex Mercer* (Math, History, Chemistry) to **"A"**.
* **Commit Changes:** Click "Commit Changes to Server". 
* **The Victory Sequence:**
  1. Shows a simulated green database sync progress bar in real-time.
  2. Synthesizes and plays a custom retro 8-bit winning arpeggio sound chime asynchronously.
  3. Releases the **physical door maglock** by activating **BCM GPIO Pin 18** (sending a High 3.3V signal to your relay).
  4. Runs a beautiful, animated **Green Matrix digital rain screensaver** on the fullscreen display.

### 2. Lockout Penalty (Lose Screen)
* **Trigger:** Players are allowed **3 incorrect login attempts** on the Grades Portal. 
* **The Lockout Sequence:** On the **4th consecutive failure**, the system permanently locks out:
  1. Closes the gateway, turns the screen a deep dark red, and runs an animated **Red Matrix digital rain screensaver**.
  2. Displays bold HUD warnings: `SECURITY BREACH DETECTED - SYSTEM PERMANENTLY LOCKED`.
  3. Synthesizes and plays a retro 8-bit dual-tone hazard alarm klaxon siren asynchronously.
  4. The only way to exit the lockout screen is using the **Game Master Backdoor** shortcut.

---

## 🛠️ Installation & Hardware Setup

### 1. System Packages (Linux/Raspberry Pi)
Run the following commands in the terminal to set up the system-level Python libraries (Tkinter GUI, GPIO Zero, Pillow images, and the Pi 5 GPIO backend):

```bash
sudo apt update
sudo apt install -y python3-tk python3-gpiozero python3-lgpio python3-pil python3-pil.imagetk
```

### 2. Python Dependencies (Pip)
Navigate to the directory and install requirements:
```bash
pip install -r requirements.txt
```

### 3. Hardware Wiring (Maglock Relay)
Connect your physical relay board to the Raspberry Pi:
* **Relay Signal (IN):** **GPIO 18** (BCM Pin 12 on standard Pi header).
* **VCC:** 3.3V or 5V (as required by your relay board).
* **GND:** Ground.
* **Relay Output (COM/NO):** Wired to break or complete the circuit powering your 12V/24V magnetic lock.

---

## 🛠️ Diagnostics & Files

* **`main.py`:** Main application source code.
* **`requirements.txt`:** Package dependencies.
* **`win.wav` / `lose.wav`:** Dynamically synthesized audio files (generated on runtime and automatically excluded from Git tracking).
