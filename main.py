import webview
import pystray
from PIL import Image
import threading
import os
import sys

# PyInstaller diye .exe korle local file er path ber korar jonno function
def get_local_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def create_tray_icon():
    # WhatsApp er moto green icon
    return Image.new('RGB', (64, 64), color=(0, 168, 132))

def show_window(icon, item):
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
    threading.Thread(target=setup_tray, daemon=True).start()
    
    # Ekhane URL er bodole apnar local index.html file load kora hocche
    local_html = get_local_path('index.html') 
    
    window = webview.create_window(
        'RasGram | Secure Messenger', 
        url=local_html, # Sorasori hard drive theke load hobe
        width=1100, 
        height=750,
        min_size=(800, 600)
    )
    
    window.events.closing += lambda: window.hide() or False
    webview.start(gui='edgechromium', private_mode=False)
