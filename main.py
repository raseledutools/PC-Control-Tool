import customtkinter as ctk
import screen_brightness_control as sbc

class NightModeOverlay:
    def __init__(self):
        self.overlay = None

    def toggle(self, is_on):
        if is_on:
            self.overlay = ctk.CTkToplevel()
            self.overlay.geometry(f"{self.overlay.winfo_screenwidth()}x{self.overlay.winfo_screenheight()}+0+0")
            self.overlay.overrideredirect(True)
            self.overlay.attributes("-topmost", True)
            self.overlay.attributes("-alpha", 0.2) # স্বচ্ছতা ২০%
            self.overlay.configure(fg_color="#ffcc33") # হালকা হলুদ রঙ
            self.overlay.attributes("-transparentcolor", "#ffffff")
            # মাউস ক্লিক যাতে নিচ দিয়ে পাস হয়
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.overlay.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
        else:
            if self.overlay:
                self.overlay.destroy()

def set_brightness(val):
    sbc.set_brightness(int(val))
    bright_lbl.configure(text=f"ব্রাইটনেস: {int(val)}%")

app = ctk.CTk()
app.title("Ras PC Tool")
app.geometry("400x300")
overlay_manager = NightModeOverlay()

title = ctk.CTkLabel(app, text="ব্রাইটনেস ও নাইট মোড", font=("Arial", 20, "bold"))
title.pack(pady=20)

bright_lbl = ctk.CTkLabel(app, text="ব্রাইটনেস সেট করুন")
bright_lbl.pack()
slider = ctk.CTkSlider(app, from_=0, to=100, command=set_brightness)
slider.set(sbc.get_brightness(display=0)[0])
slider.pack(pady=10, padx=30, fill="x")

night_switch = ctk.CTkSwitch(app, text="নাইট মোড (Blue Light Filter)", 
                             command=lambda: overlay_manager.toggle(night_switch.get()))
night_switch.pack(pady=30)

app.mainloop()
