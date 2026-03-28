import customtkinter as ctk
import screen_brightness_control as sbc
import ctypes
from threading import Timer

# ২. উইন্ডোজের জন্য ওভারলে ম্যানেজার (Screen Filter for Warmth/Nightlight)
class ScreenFilterOverlay:
    def __init__(self):
        self.overlay = None
        self.current_warmth = 0 # ০ থেকে ১০০
        self.max_alpha = 0.4 # সর্বোচ্চ ৪০% ফিল্টার স্বচ্ছতা

    def create_overlay(self):
        if not self.overlay:
            self.overlay = ctk.CTkToplevel()
            self.overlay.title("Screen Filter")
            # ফুল স্ক্রিন করা
            screen_width = self.overlay.winfo_screenwidth()
            screen_height = self.overlay.winfo_screenheight()
            self.overlay.geometry(f"{screen_width}x{screen_height}+0+0")
            
            # উইন্ডোর বর্ডার এবং টাইটেল বার মুছে ফেলা
            self.overlay.overrideredirect(True)
            # উইন্ডোটিকে সবকিছুর ওপরে রাখা
            self.overlay.attributes("-topmost", True)
            # উইন্ডোটিকে স্বচ্ছ করা
            self.overlay.attributes("-transparentcolor", "white")
            # ফিল্টার কালার (হালকা হলুদ/অ্যাম্বার)
            self.overlay.configure(fg_color="#ffcc33") 
            
            # মাউস ক্লিক যাতে নিচ দিয়ে পাস হয় (উইন্ডোজ এপিআই)
            hwnd = ctypes.windll.user32.GetParent(self.overlay.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
            
            self.update_alpha(self.current_warmth)

    def update_alpha(self, warmth_val):
        self.current_warmth = warmth_val
        if warmth_val > 0:
            if not self.overlay:
                self.create_overlay()
            
            # স্লাইডারের মান অনুযায়ী ফিল্টারের ঘনত্ব (Alpha) সেট করা
            calculated_alpha = (warmth_val / 100) * self.max_alpha
            self.overlay.attributes("-alpha", calculated_alpha)
        else:
            if self.overlay:
                self.overlay.destroy()
                self.overlay = None

    def destroy(self):
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

# ২. মেইন অ্যাপ্লিকেশন ক্লাস
class RasPcCareApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Ras PC Care - Eye Protection")
        self.geometry("700x480")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # বাম পাশের মেনু বার (Sidebar)
        self.sidebar = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="RasCare 1.0", font=("Arial", 22, "bold"))
        self.logo.pack(pady=25)
        
        menu_items = [("Display", "#3a3a3a"), ("Break", "transparent"), ("Focus", "transparent"), ("Options", "transparent"), ("About", "transparent")]
        for item, color in menu_items:
            ctk.CTkButton(self.sidebar, text=item, fg_color=color, anchor="w", corner_radius=10, height=35).pack(pady=6, padx=12, fill="x")
        
        self.activate_btn = ctk.CTkButton(self.sidebar, text="Activate 🎉", fg_color="#10ac84", corner_radius=20, font=("Arial", 14, "bold"))
        self.activate_btn.pack(side="bottom", pady=25)

        # ডান পাশের মেইন কন্টেন্ট
        self.main_view = ctk.CTkFrame(self, corner_radius=18, fg_color="#212121")
        self.main_view.pack(side="right", fill="both", expand=True, padx=25, pady=25)

        # ১. নাইট মোড / Warmth সেকশন
        self.warm_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        self.warm_frame.pack(fill="x", padx=40, pady=(35, 10))
        
        self.warm_lbl_text = ctk.CTkLabel(self.warm_frame, text="Warm (Color Temp)", font=("Arial", 15, "bold"))
        self.warm_lbl_text.pack(side="left")
        
        self.warm_val_lbl = ctk.CTkLabel(self.warm_frame, text="40%", font=("Arial", 14, "bold"), text_color="#aaaaaa")
        self.warm_val_lbl.pack(side="right")
        
        self.warm_slider = ctk.CTkSlider(self.main_view, from_=0, to=100, command=self.change_warmth, button_color="#e67e22", progress_color="#e67e22")
        self.warm_slider.set(40) # ডিফল্ট মান ৪০%
        self.warm_slider.pack(fill="x", padx=40)

        # ২. ব্রাইটনেস / Dimmer সেকশন
        self.bright_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        self.bright_frame.pack(fill="x", padx=40, pady=(40, 10))
        
        self.bright_lbl_text = ctk.CTkLabel(self.bright_frame, text="Dimmer (Brightness)", font=("Arial", 15, "bold"))
        self.bright_lbl_text.pack(side="left")
        
        self.bright_val_lbl = ctk.CTkLabel(self.bright_frame, text="80%", font=("Arial", 14, "bold"), text_color="#aaaaaa")
        self.bright_val_lbl.pack(side="right")
        
        self.bright_slider = ctk.CTkSlider(self.main_view, from_=0, to=100, command=self.change_brightness, button_color="#3498db", progress_color="#3498db")
        try:
            current_b = sbc.get_brightness(display=0)[0]
        except:
            current_b = 80
        self.bright_slider.set(current_b)
        self.bright_slider.pack(fill="x", padx=40)
        self.bright_val_lbl.configure(text=f"{current_b}%")

        # ৩. স্মার্ট মোড (Preset Modes)
        self.modes_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        self.modes_frame.pack(fill="x", padx=40, pady=(50, 10))
        
        self.modes_title = ctk.CTkLabel(self.modes_frame, text="Smart Modes", font=("Arial", 15, "bold"))
        self.modes_title.pack(anchor="w")
        
        # মোড বাটনগুলোর জন্য গ্রিড
        self.grid_frame = ctk.CTkFrame(self.main_view, fg_color="transparent")
        self.grid_frame.pack(fill="x", padx=40)
        
        self.grid_frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        # মোড ডেটা: (নাম, Warmth, Brightness)
        modes = [("Health", 35, 75), ("Game", 10, 95), ("Movie", 50, 60), ("Custom", 40, 80)]
        self.mode_buttons = []
        
        for i, (name, w, b) in enumerate(modes):
            # ডিফল্টভাবে Custom মোড সিলেক্টেড (i == 3)
            bg_c = "#3a3a3a" if i == 3 else "transparent"
            text_c = "#ffffff" if i == 3 else "#aaaaaa"
            btn = ctk.CTkButton(self.grid_frame, text=name, 
                                command=lambda w=w, b=b, idx=i: self.set_preset(w, b, idx), 
                                fg_color=bg_c, text_color=text_c, corner_radius=12, height=40)
            btn.grid(row=0, column=i, padx=8, pady=10, sticky="ew")
            self.mode_buttons.append(btn)

        # স্ক্রিন ফিল্টার ম্যানেজার
        self.filter_manager = ScreenFilterOverlay()
        self.filter_manager.create_overlay() # শুরুতেই ফিল্টার চালু রাখা

    def change_brightness(self, val):
        sbc.set_brightness(int(val))
        self.bright_val_lbl.configure(text=f"{int(val)}%")
        self.reset_mode_buttons()

    def change_warmth(self, val):
        self.filter_manager.update_alpha(int(val))
        self.warm_val_lbl.configure(text=f"{int(val)}%")
        self.reset_mode_buttons()

    def set_preset(self, w_val, b_val, btn_idx):
        # স্লাইডার আপডেট
        self.warm_slider.set(w_val)
        self.bright_slider.set(b_val)
        
        # ফাংশন কল
        self.filter_manager.update_alpha(w_val)
        sbc.set_brightness(b_val)
        
        # লেবেল আপডেট
        self.warm_val_lbl.configure(text=f"{w_val}%")
        self.bright_val_lbl.configure(text=f"{b_val}%")
        
        # বাটন হাইলাইট
        self.reset_mode_buttons()
        self.mode_buttons[btn_idx].configure(fg_color="#3a3a3a", text_color="#ffffff")

    def reset_mode_buttons(self):
        for btn in self.mode_buttons:
            btn.configure(fg_color="transparent", text_color="#aaaaaa")

if __name__ == "__main__":
    app = RasPcCareApp()
    app.mainloop()
