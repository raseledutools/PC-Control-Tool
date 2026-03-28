import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import PyPDF2
import qrcode
import cv2
import fitz  # PyMuPDF (PDF to Image এর জন্য)
from datetime import datetime
import calendar

class RaselToolsetFull(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rasel Web Tools - Offline PRO")
        self.geometry("800x650")
        ctk.set_appearance_mode("dark")

        self.title_lbl = ctk.CTkLabel(self, text="My Local Toolset", font=("Arial", 26, "bold"))
        self.title_lbl.pack(pady=10)

        # Tab View
        self.tabview = ctk.CTkTabview(self, width=750, height=550)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tabview.add("Image Tools")
        self.tabview.add("PDF Tools")
        self.tabview.add("Utilities")

        self.setup_image_tools()
        self.setup_pdf_tools()
        self.setup_utilities()

    # ================== 1. IMAGE TOOLS ==================
    def setup_image_tools(self):
        tab = self.tabview.tab("Image Tools")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # Job Photo & Signature
        ctk.CTkLabel(scroll, text="BD Job Photo & Signature", font=("Arial", 16, "bold"), text_color="#3498db").pack(pady=(10,5))
        f1 = ctk.CTkFrame(scroll, fg_color="transparent")
        f1.pack(pady=5)
        ctk.CTkButton(f1, text="Job Photo (300x300)", command=lambda: self.process_image(300, 300, "Job_Photo.jpg")).pack(side="left", padx=10)
        ctk.CTkButton(f1, text="Signature (300x80)", command=lambda: self.process_image(300, 80, "Signature.jpg")).pack(side="left", padx=10)

        # Custom Photo Resizer
        ctk.CTkLabel(scroll, text="Custom Photo Resizer", font=("Arial", 16, "bold"), text_color="#e74c3c").pack(pady=(20,5))
        f2 = ctk.CTkFrame(scroll, fg_color="transparent")
        f2.pack(pady=5)
        self.res_w = ctk.CTkEntry(f2, placeholder_text="Width (px)", width=100)
        self.res_w.pack(side="left", padx=5)
        self.res_h = ctk.CTkEntry(f2, placeholder_text="Height (px)", width=100)
        self.res_h.pack(side="left", padx=5)
        ctk.CTkButton(f2, text="Resize Now", fg_color="#e74c3c", command=self.custom_resize).pack(side="left", padx=10)

        # Photo to PDF
        ctk.CTkLabel(scroll, text="Photo to PDF", font=("Arial", 16, "bold"), text_color="#2ecc71").pack(pady=(20,5))
        ctk.CTkButton(scroll, text="Select Images -> Create PDF", fg_color="#2ecc71", command=self.images_to_pdf).pack()

    def process_image(self, w, h, out_name):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.png *.jpeg")])
        if file_path:
            try:
                img = Image.open(file_path)
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                save_path = filedialog.asksaveasfilename(defaultextension=".jpg", initialfile=out_name)
                if save_path:
                    if img.mode != 'RGB': img = img.convert('RGB')
                    img.save(save_path, "JPEG", quality=90)
                    messagebox.showinfo("Success", f"Saved successfully as {w}x{h}!")
            except Exception as e: messagebox.showerror("Error", str(e))

    def custom_resize(self):
        try:
            w = int(self.res_w.get())
            h = int(self.res_h.get())
            self.process_image(w, h, f"Resized_{w}x{h}.jpg")
        except: messagebox.showerror("Error", "Enter valid width and height!")

    def images_to_pdf(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image Files", "*.jpg *.png *.jpeg")])
        if file_paths:
            try:
                images = [Image.open(p).convert('RGB') for p in file_paths]
                save_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="Images_to_PDF.pdf")
                if save_path:
                    images[0].save(save_path, save_all=True, append_images=images[1:])
                    messagebox.showinfo("Success", "PDF created successfully!")
            except Exception as e: messagebox.showerror("Error", str(e))


    # ================== 2. PDF TOOLS ==================
    def setup_pdf_tools(self):
        tab = self.tabview.tab("PDF Tools")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Merge PDF
        ctk.CTkLabel(scroll, text="Advanced PDF Merger", font=("Arial", 16, "bold")).pack(pady=(10,5))
        ctk.CTkButton(scroll, text="Merge Multiple PDFs", command=self.merge_pdfs).pack()

        # Split PDF
        ctk.CTkLabel(scroll, text="Split / Extract PDF", font=("Arial", 16, "bold"), text_color="#e67e22").pack(pady=(20,5))
        f_split = ctk.CTkFrame(scroll, fg_color="transparent")
        f_split.pack(pady=5)
        self.split_start = ctk.CTkEntry(f_split, placeholder_text="Start Page", width=100)
        self.split_start.pack(side="left", padx=5)
        self.split_end = ctk.CTkEntry(f_split, placeholder_text="End Page", width=100)
        self.split_end.pack(side="left", padx=5)
        ctk.CTkButton(f_split, text="Extract Pages", fg_color="#e67e22", command=self.split_pdf).pack(side="left", padx=10)

        # Compress PDF
        ctk.CTkLabel(scroll, text="Compress PDF", font=("Arial", 16, "bold"), text_color="#9b59b6").pack(pady=(20,5))
        ctk.CTkButton(scroll, text="Compress PDF File", fg_color="#9b59b6", command=self.compress_pdf).pack()

        # PDF to Image
        ctk.CTkLabel(scroll, text="PDF to Image (High Quality)", font=("Arial", 16, "bold"), text_color="#f1c40f").pack(pady=(20,5))
        ctk.CTkButton(scroll, text="Convert PDF to PNG", text_color="black", fg_color="#f1c40f", command=self.pdf_to_image).pack()

    def merge_pdfs(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        if len(files) > 1:
            try:
                merger = PyPDF2.PdfMerger()
                for pdf in files: merger.append(pdf)
                save_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="Merged.pdf")
                if save_path:
                    merger.write(save_path)
                    merger.close()
                    messagebox.showinfo("Success", "Merged successfully!")
            except Exception as e: messagebox.showerror("Error", str(e))
        else: messagebox.showwarning("Warning", "Select at least 2 PDFs!")

    def split_pdf(self):
        file = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file:
            try:
                start = int(self.split_start.get())
                end = int(self.split_end.get())
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                for i in range(start - 1, end):
                    writer.add_page(reader.pages[i])
                save_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"Split_{start}_to_{end}.pdf")
                if save_path:
                    with open(save_path, "wb") as f:
                        writer.write(f)
                    messagebox.showinfo("Success", "Pages extracted successfully!")
            except Exception as e: messagebox.showerror("Error", "Invalid page numbers or file error!")

    def compress_pdf(self):
        file = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file:
            try:
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                for page in reader.pages:
                    page.compress_content_streams() # PDF structure compress
                    writer.add_page(page)
                save_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="Compressed.pdf")
                if save_path:
                    with open(save_path, "wb") as f:
                        writer.write(f)
                    messagebox.showinfo("Success", "PDF Compressed successfully!")
            except Exception as e: messagebox.showerror("Error", str(e))

    def pdf_to_image(self):
        file = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file:
            try:
                doc = fitz.open(file)
                save_dir = filedialog.askdirectory(title="Select Folder to Save Images")
                if save_dir:
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # High Quality (Scale 2x)
                        pix.save(f"{save_dir}/Page_{page_num + 1}.png")
                    messagebox.showinfo("Success", "All pages converted to PNG successfully!")
            except Exception as e: messagebox.showerror("Error", str(e))


    # ================== 3. UTILITIES ==================
    def setup_utilities(self):
        tab = self.tabview.tab("Utilities")
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Age Calculator
        ctk.CTkLabel(scroll, text="Age Calculator", font=("Arial", 16, "bold"), text_color="#1abc9c").pack(pady=(10,5))
        self.dob_entry = ctk.CTkEntry(scroll, placeholder_text="DOB: YYYY-MM-DD", width=200)
        self.dob_entry.pack(pady=2)
        self.target_entry = ctk.CTkEntry(scroll, placeholder_text="Target Date (Optional): YYYY-MM-DD", width=200)
        self.target_entry.pack(pady=2)
        ctk.CTkButton(scroll, text="Calculate Exact Age", fg_color="#1abc9c", command=self.calc_age).pack(pady=5)
        self.age_res = ctk.CTkLabel(scroll, text="", font=("Arial", 14, "bold"))
        self.age_res.pack()

        # QR Generator
        ctk.CTkLabel(scroll, text="QR Generator", font=("Arial", 16, "bold")).pack(pady=(20,5))
        self.qr_gen_entry = ctk.CTkEntry(scroll, placeholder_text="Enter text/link to generate", width=250)
        self.qr_gen_entry.pack(pady=2)
        ctk.CTkButton(scroll, text="Generate & Save", command=self.generate_qr).pack(pady=5)

        # QR Reader
        ctk.CTkLabel(scroll, text="QR Reader", font=("Arial", 16, "bold"), text_color="#e67e22").pack(pady=(20,5))
        ctk.CTkButton(scroll, text="Scan Image for QR", fg_color="#e67e22", command=self.read_qr).pack(pady=5)
        self.qr_res = ctk.CTkEntry(scroll, width=300, justify="center")
        self.qr_res.pack(pady=5)

    def calc_age(self):
        try:
            dob = datetime.strptime(self.dob_entry.get(), "%Y-%m-%d")
            t_str = self.target_entry.get()
            target = datetime.strptime(t_str, "%Y-%m-%d") if t_str else datetime.today()
            
            years = target.year - dob.year
            months = target.month - dob.month
            days = target.day - dob.day

            if days < 0:
                months -= 1
                prev_month = (target.month - 2) % 12 + 1
                prev_year = target.year if target.month > 1 else target.year - 1
                days += calendar.monthrange(prev_year, prev_month)[1]
            if months < 0:
                years -= 1
                months += 12

            self.age_res.configure(text=f"{years} Years, {months} Months, {days} Days", text_color="#1abc9c")
        except: self.age_res.configure(text="Invalid Format! Use YYYY-MM-DD", text_color="red")

    def generate_qr(self):
        data = self.qr_gen_entry.get()
        if data:
            try:
                qr = qrcode.QRCode(box_size=10, border=4)
                qr.add_data(data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                save_path = filedialog.asksaveasfilename(defaultextension=".png", initialfile="QRCode.png")
                if save_path:
                    img.save(save_path)
                    messagebox.showinfo("Success", "QR Code saved!")
            except Exception as e: messagebox.showerror("Error", str(e))

    def read_qr(self):
        file = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file:
            try:
                img = cv2.imread(file)
                detector = cv2.QRCodeDetector()
                data, bbox, _ = detector.detectAndDecode(img)
                if data:
                    self.qr_res.delete(0, "end")
                    self.qr_res.insert(0, data)
                    messagebox.showinfo("QR Result", "QR Code Scanned Successfully!")
                else:
                    messagebox.showerror("Error", "No valid QR code found in the image!")
            except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = RaselToolsetFull()
    app.mainloop()
