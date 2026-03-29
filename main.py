import webview
import pystray
from PIL import Image
import threading
import os
import sys

# গ্লোবাল উইন্ডো ভেরিয়েবল
window = None

# .exe এর ভেতর থেকে ফাইলগুলো খুঁজে বের করার লজিক
def get_local_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def create_tray_icon():
    # হোয়াটসঅ্যাপ স্টাইল সবুজ আইকন
    return Image.new('RGB', (64, 64), color=(0, 168, 132))

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
    # সিস্টেম ট্রে থ্রেড
    threading.Thread(target=setup_tray, daemon=True).start()
    
    # লোকাল index.html ফাইলের পাথ
    local_html = get_local_path('index.html') 
    
    # উইন্ডো তৈরি
    window = webview.create_window(
        'RasGram | Secure Messenger', 
        url=local_html,
        width=1100, 
        height=750,
        min_size=(800, 600)
    )
    
    # ব্যাকগ্রাউন্ডে লুকিয়ে রাখার কমান্ড
    window.events.closing += lambda: window.hide() or False
    
    # http_server=True অত্যন্ত জরুরি, এটি ছাড়া Firebase/CORS এরর আসবে
    webview.start(gui='edgechromium', private_mode=False, http_server=True)
