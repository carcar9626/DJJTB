import pyautogui
import time
from pynput import keyboard
import threading

# === CONFIGURATION ===
SCROLL_AMOUNT = -5       # Negative = scroll down, Positive = scroll up
INTERVAL = 0.7           # Seconds between scrolls
STOP_KEY = 'q'
TOGGLE_KEY = 's'         # Start/Pause toggle key

# === CONTROL FLAGS ===
scrolling = True         # Entire script running
active = False           # Whether scrolling is active
ctrl_pressed = False     # Modifier state

def scroll_loop():
    global scrolling, active
    while scrolling:
        if active:
            print("🌀 Scrolling... (Ctrl+S to pause, ESC to quit)")
            print()
            while active and scrolling:
                pyautogui.scroll(SCROLL_AMOUNT)
                time.sleep(INTERVAL)
        else:
            time.sleep(0.1)

def on_press(key):
    global scrolling, active, ctrl_pressed

    if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        ctrl_pressed = True

    if ctrl_pressed and hasattr(key, 'char') and key.char == TOGGLE_KEY:
        active = not active
        if active:
            print("\033[93m▶️  Start\033[0m")
        else:
            print("\033[93m⏸️  Paused\033[0m")

    if ctrl_pressed and hasattr(key, 'char') and key.char == STOP_KEY:
        scrolling = False
        print("🛑 Exiting...")
        return False  # Stop listener

def on_release(key):
    global ctrl_pressed
    if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        ctrl_pressed = False

if __name__ == "__main__":
    import os
    os.system('clear')
    print(" ⏬ AutoScroller is running...\n\033[93m  ⏯️  Ctrl+S \033[0m\033[91m ⏹️  Ctrl+Q\033[0m")
    print()

    scroll_thread = threading.Thread(target=scroll_loop)
    scroll_thread.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    scroll_thread.join()
    print("✅ Exiting.")