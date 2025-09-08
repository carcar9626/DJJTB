import pyautogui
import time
from pynput import keyboard
import threading

# === CONFIGURATION ===
SCROLL_AMOUNT = -5      # Negative = scroll down, Positive = scroll up
INTERVAL = 0.1          # Seconds between scrolls
DELAY_BEFORE_SCROLL = 5 # Countdown before scrolling starts
STOP_KEY = keyboard.Key.esc
PAUSE_KEY = keyboard.KeyCode(char='p')
RESTART_KEY = keyboard.KeyCode(char='r')

# === CONTROL FLAGS ===
scrolling = True   # True if script is running
active = True      # True if scrolling is active, False = paused

def scroll_loop():
    global scrolling, active
    while scrolling:
        if active:
            print(f"⌛ Countdown {DELAY_BEFORE_SCROLL}s before scrolling...")
            time.sleep(DELAY_BEFORE_SCROLL)
            print("🌀 Scrolling active. Press P to pause, R to restart, ESC to exit.")
            while active and scrolling:
                pyautogui.scroll(SCROLL_AMOUNT)
                time.sleep(INTERVAL)
        else:
            time.sleep(0.1)  # Small delay while paused

def on_key(key):
    global scrolling, active
    if key == STOP_KEY:
        scrolling = False
        print("🛑 Script exited by ESC.")
        return False  # Stop listener
    elif key == PAUSE_KEY:
        if active:
            active = False
            print("⏸️ Paused scrolling. Press R to restart.")
    elif key == RESTART_KEY:
        if not active:
            active = True
            print("🔄 Restarting scroll... countdown applies.")

if __name__ == "__main__":
    scroll_thread = threading.Thread(target=scroll_loop)
    scroll_thread.start()

    with keyboard.Listener(on_press=on_key) as listener:
        listener.join()

    scroll_thread.join()
    print("✅ Exiting.")