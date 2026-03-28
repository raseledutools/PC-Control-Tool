import customtkinter as ctk
import screen_brightness_control as sbc
import ctypes
import threading
import pystray
from PIL import Image, ImageDraw
import sys

# নাইট মোড ওভারলে (Screen Filter)
class ScreenFilterOverlay:
    def __init__(self):
        # ওভারলের জন্য আলাদা একটি রুট তৈরি করা হলো যাতে মেইন উইন্ডো হাইড হলেও এটি থাকে
        self.hidden_root = ctk.CTk()
        self.hidden_root.withdraw() 
        self.overlay = None
        self.max_alpha = 0.4 

    def update_alpha(self, warmth_val):
        if warmth_val > 0:
            if not self.overlay:
                self.overlay = ctk.CTkToplevel(self.hidden_root)
                self.overlay.title("Screen Filter")
                self.overlay.geometry(f"{self.overlay.winfo_screenwidth()}x{self.overlay.winfo_screenheight()}+0+0")
                self.overlay.overrideredirect(True)
                self.overlay.attributes("-topmost", True)
                self.overlay.attributes("-transparentcolor", "white")
                self.overlay.configure(fg_color="#ffcc33") 
                
                # মাউস ক্লিক বাইপাস করা
                hwnd = ctypes.windll.user32.GetParent(self.overlay.winfo_id())
                style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
                
            calculated_alpha = (warmth_val / 100) * self.max_alpha
            self.overlay.attributes("-alpha", calculated_alpha)
            self.hidden_root.update()
        else:
            if self.overlay:
                self.overlay.destroy()
                self.overlay = None

# মেইন উইন্ডো ক্লাস
class RasPcCareApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Ras PC Care 2.0")
        self.geometry("600x400")
        ctk.set_appearance_mode("dark")
        
        # উইন্ডো ক্লোজ (X) বাটনে ক্লিক করলে কী হবে তার কমান্ড
        self.protocol('WM_DELETE_WINDOW', self.hide_to_tray)

        self.filter_manager = ScreenFilterOverlay()

        # UI ডিজাইন (সংক্ষিপ্ত এবং প্রফেশনাল)
        self.title_lbl = ctk.CTkLabel(self, text="Display Settings", font=("Arial", 20, "bold"))
        self.title_lbl.pack(pady=20)

        # Warmth Slider
        self.warm_lbl = ctk.CTkLabel(self, text="Night Mode (Warmth)", font=("Arial", 14))
        self.warm_lbl.pack(pady=(10, 0))
        self.warm_slider = ctk.CTkSlider(self, from_=0, to=100, command=self.change_warmth, button_color="#e67e22")
        self.warm_slider.set(0)
        self.warm_slider.pack(fill="x", padx=50, pady=10)

        # Brightness Slider
        self.bright_lbl = ctk.CTkLabel(self, text="Brightness", font=("Arial", 14))
        self.bright_lbl.pack(pady=(20, 0))
        self.bright_slider = ctk.CTkSlider(self, from_=0, to=100, command=self.change_brightness, button_color="#3498db")
        try:
            current_b = sbc.get_brightness(display=0)[0]
        except:
            current_b = 80
        self.bright_slider.set(current_b)
        self.bright_slider.pack(fill="x", padx=50, pady=10)
        
        self.info_lbl = ctk.CTkLabel(self, text="টিপস: সফটওয়্যারটি কাটলে এটি System Tray তে চলে যাবে।", text_color="#888888")
        self.info_lbl.pack(side="bottom", pady=20)

        self.tray_icon = None

    def change_brightness(self, val):
        sbc.set_brightness(int(val))

    def change_warmth(self, val):
        self.filter_manager.update_alpha(int(val))

    # --- System Tray (সিস্টেম ট্রে) লজিক ---
    def create_tray_image(self):
        # সিস্টেম ট্রের জন্য একটি গোল হলুদ আইকন তৈরি করা হচ্ছে
        image = Image.new('RGB', (64, 64), color=(43, 43, 43))
        dc = ImageDraw.Draw(image)
        dc.ellipse((10, 10, 54, 54), fill=(255, 204, 51))
        return image

    def hide_to_tray(self):
        self.withdraw() # মেইন উইন্ডো হাইড করা
        
        # ট্রে মেনু সেটআপ
        menu = pystray.Menu(
            pystray.MenuItem('Open Ras PC Care', self.show_window),
            pystray.MenuItem('Exit', self.quit_app)
        )
        self.tray_icon = pystray.Icon("RasCare", self.create_tray_image(), "Ras PC Care", menu)
        
        # ট্রে আইকন আলাদা থ্রেডে রান করানো যাতে সফটওয়্যার ক্র্যাশ না করে
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item):
        icon.stop() # ট্রে আইকন বন্ধ করা
        self.after(0, self.deiconify) # আবার উইন্ডো সামনে আনা

    def quit_app(self, icon, item):
        icon.stop()
        self.quit()
        sys.exit()

if __name__ == "__main__":
    app = RasPcCareApp()
    app.mainloop()
