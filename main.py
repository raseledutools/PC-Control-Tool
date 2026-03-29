import webview
import os
import sys

# এই ফাংশনটি EXE-এর ভেতর থেকে আপনার ডিজাইন ফাইলগুলো খুঁজে বের করবে
def resource_path(relative_path):
    try:
        # PyInstaller যখন ফাইলগুলো এক্সট্রাক্ট করে তখন এই পাথ ব্যবহার করে
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    # আপনার চ্যাট ইন্টারফেসটি লোড করা হচ্ছে (যা এখন EXE এর ভেতরেই থাকবে)
    # যদি আপনার মেইন ফাইল 'chat_indivisual.html' হয়, তবে সেটিই এখানে দিন
    index_file = resource_path('chat_indivisual.html') 
    
    # উইন্ডো তৈরি
    window = webview.create_window(
        'RasGram Desktop', 
        url=index_file, # কোনো অনলাইন লিঙ্ক নয়, সরাসরি ফাইল লোড
        width=1200, 
        height=800,
        background_color='#FFFFFF'
    )
    
    # ব্রাউজার ছাড়াই নেটিভলি রান করা
    webview.start(gui='edgechromium', http_server=True)
