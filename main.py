import webview
import pystray
from PIL import Image, ImageDraw
import threading
import sys
import os

# গ্লোবাল ভেরিয়েবল
window = None

def create_image():
    # একটি সিম্পল আইকন তৈরি (আপনি চাইলে নিজের .png ফাইলও ব্যবহার করতে পারেন)
    width, height = 64, 64
    image = Image.new('RGB', (width, height), color=(43, 87, 154))
    dc = ImageDraw.Draw(image)
    dc.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
    return image

def on_quit(icon, item):
    icon.stop()
    os._exit(0)

def show_window(icon, item):
    global window
    if window:
        window.show()

def setup_tray():
    icon_image = create_image()
    menu = pystray.Menu(
        pystray.MenuItem('Open RaselEduTools', show_window, default=True),
        pystray.MenuItem('Exit', on_quit)
    )
    icon = pystray.Icon("RaselEduTools", icon_image, "Rasel Edu Tools", menu)
    icon.run()

def start_app():
    global window
    url = 'https://raseledutools.github.io'
    window = webview.create_window(
        'Rasel Edu Tools', 
        url, 
        width=1200, 
        height=800,
        confirm_close=False # ক্লোজ করলে যাতে পুরোপুরি কেটে না যায়
    )
    
    # উইন্ডো ক্লোজ ইভেন্ট হ্যান্ডেল করা (মিনিমাইজ টু ট্রে)
    window.events.closing += lambda: window.hide() or False
    webview.start(gui='mshtml')

if __name__ == '__main__':
    # ট্রে আইকন আলাদা থ্রেডে চালানো
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    
    # মেইন অ্যাপ শুরু
    start_app()
