import webview # pip install pywebview
import tkinter as tk

def on_closed():
    print("Rasel Edu Tools Closed")

def on_loaded(window):
    # ওয়েবসাইট লোড হওয়ার পর কোনো মেসেজ দিতে চাইলে এখানে যোগ করা যায়
    pass

if __name__ == '__main__':
    # আপনার ওয়েবসাইটের ইউআরএল
    url = 'https://raseledutools.github.io'
    
    # উইন্ডো তৈরি করা
    window = webview.create_window(
        'Rasel Edu Tools - Desktop App', 
        url, 
        width=1200, 
        height=800,
        resizable=True,
        confirm_close=True
    )
    
    # অ্যাপ শুরু করা
    webview.start(on_loaded, window, gui='mshtml')
