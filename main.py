import webview
import os
import sys

# এই ফাংশনটি নিশ্চিত করবে যে EXE-এর ভেতর থেকে আপনার ডিজাইন ফাইলগুলো খুঁজে পাওয়া যাচ্ছে
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller যখন রান করে তখন ফাইলগুলো এই অস্থায়ী ফোল্ডারে থাকে
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    # আপনার চ্যাট ইন্টারফেসের ফাইলটি (যেমন: chat_indivisual.html)
    # যদি আপনার ফাইলের নাম chat_indivisual.html হয়, তবে সেটিই এখানে দিন
    index_file = resource_path('chat_indivisual.html') 
    
    # উইন্ডো তৈরি
    window = webview.create_window(
        'RasGram Desktop', 
        url=index_file,
        width=1200, 
        height=850,
        background_color='#0b141a', # হোয়াটসঅ্যাপ ডার্ক থিম কালার
        confirm_close=True
    )
    
    # গুরুত্বপূর্ণ: http_server=True দিলে আপনার CSS/JS ফাইলগুলো অফলাইনেও কাজ করবে
    # এবং ফায়ারবেস বা কলিং ফিচারে কোনো এরর আসবে না।
    webview.start(
        gui='edgechromium', 
        debug=False, 
        http_server=True, 
        private_mode=False
    )
