import webview
import pystray
from PIL import Image
import threading
import os
import sys

# গ্লোবাল উইন্ডো ভেরিয়েবল
window = None

# .exe এর ভেতর থেকে ফাইল খুঁজে বের করার জন্য ফিক্স
def get_local_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def create_tray_icon():
    # সবুজ আইকন (RasGram Style)
    image = Image.new('RGB', (64, 64), color=(0, 168, 132))
    return image

def show_window(icon, item):
    global window
    if window:
        window.show()

def quit_app(icon, item):
    icon.stop()
    os._exit(0)

def setup_tray():
    menu = pystray.Menu(
        pystray.MenuItem('Open RasGram', show_window, default=True),
        pystray.MenuItem('Exit', quit_app)
    )
    icon = pystray.Icon("RasGram", create_tray_icon(), "RasGram Desktop", menu)
    icon.run()

if __name__ == '__main__':
    # সিস্টেম ট্রে ব্যাকগ্রাউন্ডে চালু
    threading.Thread(target=setup_tray, daemon=True).start()
    
    # আপনার মেইন এন্ট্রি পয়েন্ট
    local_html = get_local_path('index.html') 
    
    window = webview.create_window(
        'RasGram | Native Messenger', 
        url=local_html,
        width=1150, 
        height=800,
        min_size=(800, 600)
    )
    
    # ক্লোজ করলে ট্রে-তে যাবে
    window.events.closing += lambda: window.hide() or False
    
    # Edge Chromium + Local Server (CORS Error ফিক্স করার জন্য)
    webview.start(gui='edgechromium', private_mode=False, http_server=True)
