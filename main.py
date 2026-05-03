import webview
import threading
import time
import ctypes
import json
import os
import sys

# ডেটা সেভ করার লোকেশন
DATA_DIR = r"C:\ProgramData\RasFocus"
DATA_PATH = os.path.join(DATA_DIR, "rf_sys_data.json")

# ব্লকলিস্ট
HARDCORE_KEYWORDS = ["porn", "xxx", "sex", "nude", "nsfw", "sexy", "hentai", "xvideos", "pornhub", "xnxx", "xhamster", "চটি", "পর্ণ", "সেক্স", "magi", "khanki"]
ROMANTIC_KEYWORDS = ["hot dance", "seductive", "item song", "kissing scene", "bikini", "cleavage", "hot scene"]

# গ্লোবাল স্টেট
state = {
    "is_focus_active": False,
    "is_24h_lock": False,
    "lock_24h_end": 0,
    "focus_end_time": 0,
    "settings": {}
}

# --- HTML এর সাথে যোগাযোগের জন্য API ---
class Api:
    def update_settings(self, settings):
        state["settings"] = settings
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DATA_PATH, "w") as f:
            json.dump(settings, f)

    def start_focus(self, data):
        state["is_focus_active"] = True
        if data.get("is24h"):
            state["is_24h_lock"] = True
            state["lock_24h_end"] = time.time() + (24 * 3600)
        else:
            state["is_24h_lock"] = False
            state["focus_end_time"] = time.time() + (data.get("durationMs", 0) / 1000)

    def stop_focus(self):
        if not state["is_24h_lock"]:
            state["is_focus_active"] = False

# --- ট্যাব ক্লোজ করার ফাংশন (Ctrl + W) ---
def close_active_tab():
    VK_CONTROL = 0x11
    VK_W = 0x57
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_W, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_W, 0, 2, 0) # KEY UP
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 2, 0) # KEY UP

# --- ব্যাকগ্রাউন্ড থ্রেড (উইন্ডোজ টাইটেল চেকার) ---
def background_task(window):
    user32 = ctypes.windll.user32
    while True:
        time.sleep(1)
        if not state["is_focus_active"]:
            continue

        # টাইমার শেষ হয়েছে কিনা চেক
        now = time.time()
        if state["is_24h_lock"] and now >= state["lock_24h_end"]:
            state["is_24h_lock"] = False
            state["is_focus_active"] = False
            window.evaluate_js("stopFocusUI();")
            
        elif not state["is_24h_lock"] and now >= state["focus_end_time"]:
            state["is_focus_active"] = False
            window.evaluate_js("stopFocusUI();")

        # অ্যাকটিভ উইন্ডোর টাইটেল পড়া
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value.lower()

        if not title:
            continue

        should_block = False
        settings = state.get("settings", {})

        # Security Check
        if any(x in title for x in ["task manager", "taskmgr", "uninstall", "control panel"]):
            close_active_tab()
            window.evaluate_js("alert('Security Alert: System settings are blocked during Focus!');")
            continue
        
        # Keywords Check
        if settings.get("cbHardcore") and any(kw in title for kw in HARDCORE_KEYWORDS): should_block = True
        if settings.get("cbRomantic") and any(kw in title for kw in ROMANTIC_KEYWORDS): should_block = True
        if settings.get("cbSocial") and any(kw in title for kw in ["reels", "shorts"]): should_block = True
        
        custom_kws = settings.get("customKeywords", [])
        if any(kw.lower() in title for kw in custom_kws): should_block = True

        if should_block:
            close_active_tab()
            # উইন্ডোতে অ্যালার্ট পাঠানো
            window.evaluate_js("alert('দৃষ্টি নত রাখুন। খারাপ কিছু ব্লক করা হয়েছে।');")

# --- HTML ফাইল লোড করার পাথ ---
def get_html_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'index.html')
    return 'index.html'

if __name__ == '__main__':
    api = Api()
    # উইন্ডো তৈরি
    window = webview.create_window('RasFocus - Adult Filter', get_html_path(), js_api=api, width=900, height=700)
    
    # ব্যাকগ্রাউন্ড লজিক চালু
    t = threading.Thread(target=background_task, args=(window,), daemon=True)
    t.start()
    
    # অ্যাপ চালু
    webview.start()
