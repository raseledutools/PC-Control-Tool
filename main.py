import webview
import pystray
from PIL import Image, ImageDraw
import threading
import os
import sys

# গ্লোবাল ভেরিয়েবল
window = None

def create_image():
    # অ্যাপের জন্য একটি ডিফল্ট আইকন (৬৪x৬৪)
    image = Image.new('RGB', (64, 64), color=(43, 87, 154))
    return image

def on_quit(icon, item):
    icon.stop()
    os._exit(0)

def show_window(icon, item):
    global window
    if window:
        window.show()

def setup_tray():
    icon = pystray.Icon("RaselEduTools", create_image(), "Rasel Edu Tools", 
                        menu=pystray.Menu(
                            pystray.MenuItem('Open App', show_window, default=True),
                            pystray.MenuItem('Exit', on_quit)
                        ))
    icon.run()

if __name__ == '__main__':
    # সিস্টেম ট্রে থ্রেড শুরু
    threading.Thread(target=setup_tray, daemon=True).start()
    
    # মেইন উইন্ডো তৈরি
    # 'https://raseledutools.github.io' লোড হবে
    window = webview.create_window(
        'Rasel Edu Tools', 
        'https://raseledutools.github.io', 
        width=1200, 
        height=800,
        background_color='#FFFFFF'
    )
    
    # ক্লোজ করলে যাতে ব্যাকগ্রাউন্ডে (ট্রে-তে) থাকে
    window.events.closing += lambda: window.hide() or False
    
    # সবচেয়ে গুরুত্বপূর্ণ অংশ: এখানে gui='edgechromium' ফোর্স করা হয়েছে
    # এটি আপনার পিসির Microsoft Edge ইঞ্জিন ব্যবহার করবে, ফলে CSS এরর হবে না
    webview.start(gui='edgechromium')
