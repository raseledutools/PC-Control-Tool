"""
PDF Editor Pro - Advanced Edition
Full PDF editing with text boxes, rich text, annotations, Word-like editing
Libraries: pypdf, reportlab, pillow, tkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, font as tkfont
import os, io, json, math, copy
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib import colors as rl_colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class TextBox:
    """Represents an editable text box on a PDF page."""
    def __init__(self, x, y, width=300, height=80, page=0):
        self.x = x          # position on page (pts)
        self.y = y
        self.width = width
        self.height = height
        self.page = page
        self.text = ""
        self.font_name = "Helvetica"
        self.font_size = 12
        self.font_bold = False
        self.font_italic = False
        self.font_underline = False
        self.color = "#000000"
        self.bg_color = None        # None = transparent
        self.border_color = "#cccccc"
        self.border_width = 1
        self.align = "left"         # left / center / right
        self.id = id(self)          # unique id

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        tb = cls(d["x"], d["y"])
        tb.__dict__.update(d)
        return tb


class Annotation:
    """Highlight / underline / strikethrough / freehand annotation."""
    def __init__(self, kind, points, color="#FFFF00", page=0, width=2):
        self.kind = kind        # highlight / underline / strikethrough / freehand / arrow / rect / oval
        self.points = points    # list of (x,y)
        self.color = color
        self.page = page
        self.width = width
        self.id = id(self)

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        a = cls(d["kind"], d["points"])
        a.__dict__.update(d)
        return a


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class PDFEditorPro:
    APP_NAME = "PDF Editor Pro — Advanced"
    VERSION  = "2.0"

    # Toolbar modes
    MODE_SELECT    = "select"
    MODE_TEXT      = "textbox"
    MODE_HIGHLIGHT = "highlight"
    MODE_DRAW      = "freehand"
    MODE_ARROW     = "arrow"
    MODE_RECT      = "rect"
    MODE_OVAL      = "oval"
    MODE_ERASE     = "erase"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(self.APP_NAME)
        self.root.geometry("1280x820")
        self.root.configure(bg="#0f0f17")
        self.root.minsize(900, 600)

        # ── State ──────────────────────────────────────────────────────────────
        self.current_file   = None
        self.pdf_reader     = None
        self.total_pages    = 0
        self.current_page   = 0
        self.zoom           = 1.0
        self.mode           = self.MODE_SELECT

        # Per-page data
        self.textboxes: dict[int, list[TextBox]]   = {}   # page -> [TextBox]
        self.annotations: dict[int, list[Annotation]] = {}

        # Interaction state
        self.selected_tb    = None      # selected TextBox
        self.drag_start     = None
        self.draw_points    = []
        self.temp_shape_id  = None
        self.canvas_items   = {}        # canvas_id -> TextBox/Annotation

        # Undo stack
        self.undo_stack     = []
        self.redo_stack     = []

        # Current tool settings
        self.tool_color     = "#000000"
        self.tool_bg        = ""
        self.tool_font      = "Helvetica"
        self.tool_size      = 12
        self.tool_bold      = tk.BooleanVar(value=False)
        self.tool_italic    = tk.BooleanVar(value=False)
        self.tool_underline = tk.BooleanVar(value=False)
        self.tool_align     = tk.StringVar(value="left")
        self.annot_color    = "#FFFF00"
        self.annot_width    = 2

        self._build_ui()
        self._bind_shortcuts()

    # ══════════════════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_menu()

        # Top: title bar
        hdr = tk.Frame(self.root, bg="#0a0a12", height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="✦ PDF Editor Pro", font=("Georgia", 13, "bold"),
                 bg="#0a0a12", fg="#e8d5b7").pack(side="left", padx=14, pady=10)
        self.file_label = tk.Label(hdr, text="No file open",
                                   font=("Consolas", 8), bg="#0a0a12", fg="#555577")
        self.file_label.pack(side="left", padx=8)
        tk.Label(hdr, text=f"v{self.VERSION}  •  Python + pypdf + reportlab",
                 font=("Consolas", 7), bg="#0a0a12", fg="#333355"
                 ).pack(side="right", padx=12)

        # Mode toolbar
        self._build_mode_bar()

        # Formatting bar (Word-like ribbon)
        self._build_format_bar()

        # Main workspace
        workspace = tk.Frame(self.root, bg="#0f0f17")
        workspace.pack(fill="both", expand=True)

        self._build_sidebar(workspace)
        self._build_canvas_area(workspace)
        self._build_properties_panel(workspace)

        # Status bar
        self._build_statusbar()

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        M = {"bg": "#0a0a12", "fg": "#c8c8e8", "activebackground": "#2a2a3e",
             "activeforeground": "#ffffff", "relief": "flat"}
        mb = tk.Menu(self.root, **M)
        self.root.config(menu=mb)

        def _menu(label, items):
            m = tk.Menu(mb, tearoff=0, **M)
            mb.add_cascade(label=label, menu=m)
            for it in items:
                if it == "-":
                    m.add_separator()
                else:
                    m.add_command(label=it[0], command=it[1])
            return m

        _menu("File", [
            ("📂  Open PDF                Ctrl+O", self.open_pdf),
            ("💾  Save                    Ctrl+S", self.save_pdf),
            ("💾  Save As…               Ctrl+Shift+S", self.save_pdf_as),
            ("📤  Export Edited PDF", self.export_edited_pdf),
            "-",
            ("🆕  Create New PDF", self.create_new_pdf),
            "-",
            ("❌  Exit", self.root.quit),
        ])
        _menu("Edit", [
            ("↩  Undo                    Ctrl+Z", self.undo),
            ("↪  Redo                    Ctrl+Y", self.redo),
            "-",
            ("🗑  Delete Selected", self.delete_selected),
            ("📋  Duplicate Text Box", self.duplicate_textbox),
        ])
        _menu("Insert", [
            ("🔤  Text Box", lambda: self._set_mode(self.MODE_TEXT)),
            ("➡  Arrow", lambda: self._set_mode(self.MODE_ARROW)),
            ("▭  Rectangle", lambda: self._set_mode(self.MODE_RECT)),
            ("○  Oval", lambda: self._set_mode(self.MODE_OVAL)),
            ("✏  Freehand Draw", lambda: self._set_mode(self.MODE_DRAW)),
            "-",
            ("🖼  Insert Image on Page", self.insert_image_on_page),
        ])
        _menu("Pages", [
            ("➕  Insert Blank Page", self.insert_blank_page),
            ("🗑  Delete Current Page", self.delete_page),
            ("🔄  Rotate Page 90°", lambda: self.rotate_page(90)),
            ("🔄  Rotate Page −90°", lambda: self.rotate_page(-90)),
            "-",
            ("🔀  Merge PDFs", self.merge_pdfs),
            ("✂  Split PDF", self.split_pdf),
            ("🔢  Go To Page…", self.goto_page_dialog),
        ])
        _menu("Tools", [
            ("📝  Extract All Text", self.extract_text),
            ("ℹ  PDF Metadata", self.show_metadata),
            "-",
            ("🔒  Encrypt PDF", self.encrypt_pdf),
            ("🔓  Decrypt PDF", self.decrypt_pdf),
            ("💧  Add Watermark", self.add_watermark),
        ])

    # ── Mode toolbar ──────────────────────────────────────────────────────────

    def _build_mode_bar(self):
        bar = tk.Frame(self.root, bg="#15152a", height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        self.mode_btns = {}
        modes = [
            ("↖ Select",    self.MODE_SELECT,    "#334"),
            ("T Text Box",  self.MODE_TEXT,      "#334"),
            ("|", None, None),
            ("🖍 Highlight", self.MODE_HIGHLIGHT, "#334"),
            ("✏ Draw",      self.MODE_DRAW,      "#334"),
            ("➡ Arrow",    self.MODE_ARROW,     "#334"),
            ("▭ Rect",      self.MODE_RECT,      "#334"),
            ("○ Oval",      self.MODE_OVAL,      "#334"),
            ("⌫ Erase",    self.MODE_ERASE,     "#334"),
            ("|", None, None),
        ]
        for label, mode, _ in modes:
            if label == "|":
                tk.Frame(bar, bg="#2a2a3e", width=1).pack(side="left", fill="y", pady=8, padx=4)
                continue
            btn = tk.Button(
                bar, text=label, font=("Segoe UI", 9),
                bg="#1e1e32", fg="#9999cc", relief="flat",
                padx=10, pady=4, cursor="hand2", bd=0,
                command=lambda m=mode: self._set_mode(m)
            )
            btn.pack(side="left", padx=2, pady=8)
            self.mode_btns[mode] = btn
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#2a2a45") if b.cget("bg") != "#5533aa" else None)
            btn.bind("<Leave>", lambda e, b=btn, m=mode: b.config(bg="#5533aa" if self.mode == m else "#1e1e32"))

        # Annotation colour picker
        tk.Label(bar, text="  Ink:", font=("Segoe UI", 8), bg="#15152a", fg="#666688").pack(side="left")
        self.ink_swatch = tk.Label(bar, bg=self.annot_color, width=3, cursor="hand2", relief="flat")
        self.ink_swatch.pack(side="left", padx=4, pady=14)
        self.ink_swatch.bind("<Button-1>", self._pick_ink_color)

        tk.Label(bar, text="  Width:", font=("Segoe UI", 8), bg="#15152a", fg="#666688").pack(side="left")
        self.width_spin = tk.Spinbox(bar, from_=1, to=20, width=3,
                                     bg="#1e1e32", fg="#9999cc", relief="flat",
                                     font=("Segoe UI", 8),
                                     command=lambda: setattr(self, 'annot_width', int(self.width_spin.get())))
        self.width_spin.pack(side="left", padx=4, pady=10)

        self._set_mode(self.MODE_SELECT)

    # ── Format bar (Word ribbon) ──────────────────────────────────────────────

    def _build_format_bar(self):
        bar = tk.Frame(self.root, bg="#12122a", height=38)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Font family
        tk.Label(bar, text="Font:", font=("Segoe UI", 8), bg="#12122a", fg="#666688").pack(side="left", padx=(8, 2))
        self.font_var = tk.StringVar(value="Helvetica")
        fonts = ["Helvetica", "Times-Roman", "Courier", "Helvetica-Oblique",
                 "Times-Bold", "Courier-Bold"]
        font_cb = ttk.Combobox(bar, textvariable=self.font_var, values=fonts,
                               width=14, font=("Segoe UI", 8))
        font_cb.pack(side="left", pady=6, padx=2)
        font_cb.bind("<<ComboboxSelected>>", self._apply_format)

        # Font size
        tk.Label(bar, text="Size:", font=("Segoe UI", 8), bg="#12122a", fg="#666688").pack(side="left", padx=(6, 2))
        self.size_var = tk.StringVar(value="12")
        size_cb = ttk.Combobox(bar, textvariable=self.size_var,
                               values=["8","9","10","11","12","14","16","18","20","24","28","32","36","48","72"],
                               width=5, font=("Segoe UI", 8))
        size_cb.pack(side="left", pady=6, padx=2)
        size_cb.bind("<<ComboboxSelected>>", self._apply_format)
        size_cb.bind("<Return>", self._apply_format)

        sep = lambda: tk.Frame(bar, bg="#2a2a3e", width=1).pack(side="left", fill="y", pady=6, padx=4)
        sep()

        # B I U
        def fmt_btn(text, var):
            b = tk.Checkbutton(bar, text=text, variable=var, indicatoron=False,
                               font=("Georgia", 10, "bold"), bg="#1e1e32", fg="#9999cc",
                               selectcolor="#5533aa", activebackground="#5533aa",
                               relief="flat", padx=8, pady=3, cursor="hand2",
                               command=self._apply_format)
            b.pack(side="left", padx=2, pady=6)
            return b

        fmt_btn("B", self.tool_bold)
        fmt_btn("I", self.tool_italic)
        fmt_btn("U", self.tool_underline)
        sep()

        # Align
        for sym, val in [("≡L","left"),("≡C","center"),("≡R","right")]:
            tk.Radiobutton(bar, text=sym, variable=self.tool_align, value=val,
                           indicatoron=False, font=("Segoe UI", 8),
                           bg="#1e1e32", fg="#9999cc", selectcolor="#5533aa",
                           activebackground="#5533aa", relief="flat",
                           padx=6, pady=3, cursor="hand2",
                           command=self._apply_format).pack(side="left", padx=2, pady=6)
        sep()

        # Text colour
        tk.Label(bar, text="Color:", font=("Segoe UI", 8), bg="#12122a", fg="#666688").pack(side="left", padx=(4,2))
        self.color_swatch = tk.Label(bar, bg=self.tool_color, width=3, cursor="hand2",
                                     relief="flat", bd=1)
        self.color_swatch.pack(side="left", padx=4, pady=12)
        self.color_swatch.bind("<Button-1>", self._pick_text_color)

        # BG colour
        tk.Label(bar, text="BG:", font=("Segoe UI", 8), bg="#12122a", fg="#666688").pack(side="left", padx=(4,2))
        self.bg_swatch = tk.Label(bar, bg="white", width=3, cursor="hand2",
                                  relief="flat", bd=1, text="∅", fg="#888888")
        self.bg_swatch.pack(side="left", padx=4, pady=12)
        self.bg_swatch.bind("<Button-1>", self._pick_bg_color)

        sep()

        # Quick action buttons
        for lbl, cmd in [("Export PDF", self.export_edited_pdf),
                         ("Extract Text", self.extract_text)]:
            tk.Button(bar, text=lbl, command=cmd, font=("Segoe UI", 8),
                      bg="#2a1a55", fg="#ccaaff", relief="flat",
                      padx=8, pady=3, cursor="hand2"
                      ).pack(side="left", padx=3, pady=6)

    # ── Left sidebar ──────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg="#0d0d1e", width=160)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="PAGES", font=("Consolas", 8, "bold"),
                 bg="#0d0d1e", fg="#444466", pady=6).pack()

        frame = tk.Frame(sb, bg="#0d0d1e")
        frame.pack(fill="both", expand=True, padx=4)

        ys = tk.Scrollbar(frame, bg="#1e1e32", troughcolor="#0d0d1e", width=8)
        ys.pack(side="right", fill="y")

        self.page_list = tk.Listbox(
            frame, bg="#0a0a18", fg="#8888aa", selectbackground="#5533aa",
            selectforeground="#ffffff", relief="flat", bd=0,
            font=("Consolas", 8), yscrollcommand=ys.set, activestyle="none"
        )
        self.page_list.pack(fill="both", expand=True)
        ys.config(command=self.page_list.yview)
        self.page_list.bind("<<ListboxSelect>>", self._on_page_select)

        # Page controls
        ctrl = tk.Frame(sb, bg="#0d0d1e")
        ctrl.pack(fill="x", pady=4)
        for sym, cmd in [("◀", self.prev_page), ("▶", self.next_page)]:
            tk.Button(ctrl, text=sym, command=cmd, bg="#1e1e32", fg="#8888aa",
                      relief="flat", font=("Segoe UI", 9), padx=10, pady=3,
                      cursor="hand2").pack(side="left", padx=2, expand=True, fill="x")

    # ── Canvas area ───────────────────────────────────────────────────────────

    def _build_canvas_area(self, parent):
        center = tk.Frame(parent, bg="#0f0f17")
        center.pack(side="left", fill="both", expand=True)

        # Nav bar
        nav = tk.Frame(center, bg="#0a0a18", height=32)
        nav.pack(fill="x")
        nav.pack_propagate(False)
        self.page_lbl = tk.Label(nav, text="–", font=("Consolas", 8),
                                 bg="#0a0a18", fg="#555577")
        self.page_lbl.pack(side="left", padx=10, pady=8)

        for sym, cmd in [("−", self.zoom_out), ("+", self.zoom_in),
                          ("100%", self.zoom_reset)]:
            tk.Button(nav, text=sym, command=cmd, bg="#1e1e32", fg="#8888aa",
                      relief="flat", font=("Segoe UI", 8), padx=6, pady=2,
                      cursor="hand2").pack(side="right", padx=2, pady=4)
        tk.Label(nav, text="Zoom:", font=("Segoe UI", 7), bg="#0a0a18", fg="#333355"
                 ).pack(side="right", padx=4)

        # Scrollable canvas
        cf = tk.Frame(center, bg="#0f0f17")
        cf.pack(fill="both", expand=True, padx=6, pady=6)

        vsc = tk.Scrollbar(cf, orient="vertical", bg="#1e1e32", troughcolor="#0f0f17", width=8)
        vsc.pack(side="right", fill="y")
        hsc = tk.Scrollbar(cf, orient="horizontal", bg="#1e1e32", troughcolor="#0f0f17", width=8)
        hsc.pack(side="bottom", fill="x")

        self.canvas = tk.Canvas(cf, bg="#1a1a2e", relief="flat", bd=0,
                                xscrollcommand=hsc.set, yscrollcommand=vsc.set,
                                cursor="arrow")
        self.canvas.pack(fill="both", expand=True)
        vsc.config(command=self.canvas.yview)
        hsc.config(command=self.canvas.xview)

        # Canvas events
        self.canvas.bind("<ButtonPress-1>",   self._on_canvas_press)
        self.canvas.bind("<B1-Motion>",        self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>",  self._on_canvas_release)
        self.canvas.bind("<Double-Button-1>",  self._on_canvas_double)
        self.canvas.bind("<Button-3>",         self._on_right_click)
        self.canvas.bind("<Delete>",           lambda e: self.delete_selected())

        self._show_welcome()

    # ── Right properties panel ────────────────────────────────────────────────

    def _build_properties_panel(self, parent):
        rp = tk.Frame(parent, bg="#0d0d1e", width=210)
        rp.pack(side="right", fill="y")
        rp.pack_propagate(False)

        tk.Label(rp, text="PROPERTIES", font=("Consolas", 8, "bold"),
                 bg="#0d0d1e", fg="#444466", pady=8).pack()

        # Text box properties
        self.prop_frame = tk.LabelFrame(rp, text=" Selected Text Box ",
                                        font=("Segoe UI", 8), bg="#0d0d1e", fg="#666688",
                                        relief="flat", bd=1, labelanchor="n")
        self.prop_frame.pack(fill="x", padx=8, pady=4)

        self.prop_text_lbl = tk.Label(self.prop_frame, text="Select a text box\nor click T to add one",
                                      font=("Segoe UI", 8), bg="#0d0d1e", fg="#555577",
                                      justify="center", pady=10)
        self.prop_text_lbl.pack()

        # Quick add section
        qa = tk.LabelFrame(rp, text=" Quick Insert ", font=("Segoe UI", 8),
                           bg="#0d0d1e", fg="#666688", relief="flat", bd=1, labelanchor="n")
        qa.pack(fill="x", padx=8, pady=8)

        for lbl, cmd in [
            ("➕ Add Text Box", lambda: self._set_mode(self.MODE_TEXT)),
            ("✏ Freehand",     lambda: self._set_mode(self.MODE_DRAW)),
            ("🖍 Highlight",   lambda: self._set_mode(self.MODE_HIGHLIGHT)),
            ("➡ Arrow",       lambda: self._set_mode(self.MODE_ARROW)),
            ("▭ Rectangle",   lambda: self._set_mode(self.MODE_RECT)),
            ("○ Oval",         lambda: self._set_mode(self.MODE_OVAL)),
        ]:
            b = tk.Button(qa, text=lbl, command=cmd, bg="#1e1e32", fg="#9999cc",
                          relief="flat", font=("Segoe UI", 8), padx=6, pady=4,
                          cursor="hand2", anchor="w")
            b.pack(fill="x", padx=6, pady=2)
            b.bind("<Enter>", lambda e, w=b: w.config(bg="#5533aa"))
            b.bind("<Leave>", lambda e, w=b: w.config(bg="#1e1e32"))

        # PDF operations
        op = tk.LabelFrame(rp, text=" PDF Operations ", font=("Segoe UI", 8),
                           bg="#0d0d1e", fg="#666688", relief="flat", bd=1, labelanchor="n")
        op.pack(fill="x", padx=8, pady=4)

        for lbl, cmd, col in [
            ("📤 Export Edited PDF", self.export_edited_pdf, "#3a1a66"),
            ("🔀 Merge PDFs",        self.merge_pdfs,         "#1a3366"),
            ("✂ Split PDF",          self.split_pdf,          "#1a4433"),
            ("🔒 Encrypt",           self.encrypt_pdf,        "#4a1a33"),
            ("💧 Watermark",         self.add_watermark,      "#2a3a1a"),
        ]:
            b = tk.Button(op, text=lbl, command=cmd, bg=col, fg="#ccbbff",
                          relief="flat", font=("Segoe UI", 8), padx=6, pady=4,
                          cursor="hand2", anchor="w")
            b.pack(fill="x", padx=6, pady=2)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg="#07070f", height=24)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self.status_var = tk.StringVar(value="Ready  •  Open a PDF or create a new one")
        tk.Label(sb, textvariable=self.status_var, font=("Consolas", 7),
                 bg="#07070f", fg="#444466", anchor="w").pack(side="left", padx=10, pady=4)
        self.mode_lbl = tk.Label(sb, text="Mode: SELECT", font=("Consolas", 7),
                                 bg="#07070f", fg="#5533aa")
        self.mode_lbl.pack(side="right", padx=10)

    # ══════════════════════════════════════════════════════════════════════════
    #  MODE & TOOL MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def _set_mode(self, mode):
        self.mode = mode
        for m, btn in self.mode_btns.items():
            btn.config(bg="#5533aa" if m == mode else "#1e1e32",
                       fg="#ffffff" if m == mode else "#9999cc")

        cursors = {
            self.MODE_SELECT:    "arrow",
            self.MODE_TEXT:      "crosshair",
            self.MODE_HIGHLIGHT: "crosshair",
            self.MODE_DRAW:      "pencil",
            self.MODE_ARROW:     "crosshair",
            self.MODE_RECT:      "crosshair",
            self.MODE_OVAL:      "crosshair",
            self.MODE_ERASE:     "X_cursor",
        }
        self.canvas.config(cursor=cursors.get(mode, "arrow"))
        self.mode_lbl.config(text=f"Mode: {mode.upper()}")
        self.status_var.set(f"Tool: {mode}  •  Click on the page to use")

    # ══════════════════════════════════════════════════════════════════════════
    #  CANVAS EVENT HANDLERS
    # ══════════════════════════════════════════════════════════════════════════

    def _canvas_coords(self, event):
        """Convert screen coords to canvas coords."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        return x, y

    def _canvas_to_page(self, cx, cy):
        """Convert canvas coords to page-space coords (pts)."""
        px = (cx - self.page_offset_x) / self.zoom
        py = (cy - self.page_offset_y) / self.zoom
        return px, py

    def _page_to_canvas(self, px, py):
        cx = px * self.zoom + self.page_offset_x
        cy = py * self.zoom + self.page_offset_y
        return cx, cy

    def _on_canvas_press(self, event):
        cx, cy = self._canvas_coords(event)
        self.draw_start = (cx, cy)
        self.draw_points = [(cx, cy)]

        if self.mode == self.MODE_SELECT:
            self._try_select(cx, cy)

        elif self.mode == self.MODE_TEXT:
            pass  # handled on release

        elif self.mode in (self.MODE_HIGHLIGHT, self.MODE_DRAW,
                           self.MODE_ARROW, self.MODE_RECT, self.MODE_OVAL):
            self.temp_shape_id = None

        elif self.mode == self.MODE_ERASE:
            self._erase_at(cx, cy)

    def _on_canvas_drag(self, event):
        cx, cy = self._canvas_coords(event)

        if self.mode == self.MODE_SELECT and self.selected_tb:
            if self.drag_start:
                dx = cx - self.drag_start[0]
                dy = cy - self.drag_start[1]
                self.selected_tb.x += dx / self.zoom
                self.selected_tb.y += dy / self.zoom
                self.drag_start = (cx, cy)
                self._redraw_page()

        elif self.mode == self.MODE_DRAW:
            self.draw_points.append((cx, cy))
            if len(self.draw_points) >= 2:
                p1 = self.draw_points[-2]
                p2 = self.draw_points[-1]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1],
                                        fill=self.annot_color,
                                        width=self.annot_width, smooth=True)

        elif self.mode in (self.MODE_HIGHLIGHT, self.MODE_ARROW,
                           self.MODE_RECT, self.MODE_OVAL):
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            x0, y0 = self.draw_start
            if self.mode == self.MODE_RECT:
                self.temp_shape_id = self.canvas.create_rectangle(
                    x0, y0, cx, cy, outline=self.annot_color,
                    width=self.annot_width, dash=(4, 2))
            elif self.mode == self.MODE_OVAL:
                self.temp_shape_id = self.canvas.create_oval(
                    x0, y0, cx, cy, outline=self.annot_color,
                    width=self.annot_width, dash=(4, 2))
            elif self.mode == self.MODE_ARROW:
                self.temp_shape_id = self.canvas.create_line(
                    x0, y0, cx, cy, fill=self.annot_color,
                    width=self.annot_width, arrow="last")
            elif self.mode == self.MODE_HIGHLIGHT:
                self.temp_shape_id = self.canvas.create_rectangle(
                    x0, y0, cx, cy,
                    fill=self.annot_color, stipple="gray50",
                    outline="", width=0)

    def _on_canvas_release(self, event):
        cx, cy = self._canvas_coords(event)
        x0, y0 = self.draw_start if hasattr(self, 'draw_start') else (cx, cy)

        if self.mode == self.MODE_TEXT:
            px, py = self._canvas_to_page(cx, cy)
            self._create_textbox_at(px, py)

        elif self.mode == self.MODE_SELECT:
            self.drag_start = None

        elif self.mode == self.MODE_DRAW and len(self.draw_points) > 1:
            pts = [self._canvas_to_page(p[0], p[1]) for p in self.draw_points]
            self._add_annotation("freehand", pts)
            self.draw_points = []
            self._redraw_page()

        elif self.mode in (self.MODE_HIGHLIGHT, self.MODE_ARROW,
                           self.MODE_RECT, self.MODE_OVAL):
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
                self.temp_shape_id = None
            if abs(cx - x0) > 5 or abs(cy - y0) > 5:
                p0 = self._canvas_to_page(x0, y0)
                p1 = self._canvas_to_page(cx, cy)
                self._add_annotation(self.mode, [p0, p1])
                self._redraw_page()

    def _on_canvas_double(self, event):
        cx, cy = self._canvas_coords(event)
        # Find textbox under cursor and open editor
        for tb in self._page_textboxes():
            tx, ty = self._page_to_canvas(tb.x, tb.y)
            tw = tb.width * self.zoom
            th = tb.height * self.zoom
            if tx <= cx <= tx + tw and ty <= cy <= ty + th:
                self._open_text_editor(tb)
                return

    def _on_right_click(self, event):
        cx, cy = self._canvas_coords(event)
        for tb in self._page_textboxes():
            tx, ty = self._page_to_canvas(tb.x, tb.y)
            tw = tb.width * self.zoom
            th = tb.height * self.zoom
            if tx <= cx <= tx + tw and ty <= cy <= ty + th:
                self.selected_tb = tb
                self._show_context_menu(event, tb)
                return

    def _try_select(self, cx, cy):
        self.selected_tb = None
        for tb in self._page_textboxes():
            tx, ty = self._page_to_canvas(tb.x, tb.y)
            tw = tb.width * self.zoom
            th = tb.height * self.zoom
            if tx <= cx <= tx + tw and ty <= cy <= ty + th:
                self.selected_tb = tb
                self.drag_start = (cx, cy)
                self._update_format_bar_from(tb)
                break
        self._redraw_page()

    def _erase_at(self, cx, cy):
        # Erase annotations near click
        annots = self.annotations.get(self.current_page, [])
        to_remove = []
        for a in annots:
            for px, py in a.points:
                acx, acy = self._page_to_canvas(px, py)
                if math.hypot(cx - acx, cy - acy) < 20:
                    to_remove.append(a)
                    break
        for a in to_remove:
            annots.remove(a)
        self._redraw_page()

    # ══════════════════════════════════════════════════════════════════════════
    #  TEXT BOX OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _create_textbox_at(self, px, py):
        page = self.current_page
        tb = TextBox(px, py, width=250, height=60, page=page)
        tb.font_name  = self.font_var.get()
        tb.font_size  = self._safe_int(self.size_var.get(), 12)
        tb.font_bold  = self.tool_bold.get()
        tb.font_italic = self.tool_italic.get()
        tb.font_underline = self.tool_underline.get()
        tb.color      = self.tool_color
        tb.align      = self.tool_align.get()

        if page not in self.textboxes:
            self.textboxes[page] = []
        self.textboxes[page].append(tb)

        self.selected_tb = tb
        self._push_undo()
        self._redraw_page()
        self._open_text_editor(tb)

    def _open_text_editor(self, tb: TextBox):
        """Open a rich text editor window for a text box."""
        win = tk.Toplevel(self.root)
        win.title("Edit Text Box")
        win.geometry("560x480")
        win.configure(bg="#0f0f1e")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="✦ Text Box Editor", font=("Georgia", 11, "bold"),
                 bg="#0f0f1e", fg="#e8d5b7").pack(pady=(12, 4))

        # Mini format bar inside editor
        fmt = tk.Frame(win, bg="#0a0a18")
        fmt.pack(fill="x", padx=10)

        fv = tk.StringVar(value=tb.font_name)
        sv = tk.StringVar(value=str(tb.font_size))
        bv = tk.BooleanVar(value=tb.font_bold)
        iv = tk.BooleanVar(value=tb.font_italic)
        uv = tk.BooleanVar(value=tb.font_underline)
        av = tk.StringVar(value=tb.align)

        fonts = ["Helvetica","Times-Roman","Courier","Helvetica-Oblique","Times-Bold","Courier-Bold"]
        ttk.Combobox(fmt, textvariable=fv, values=fonts, width=14,
                     font=("Segoe UI", 8)).pack(side="left", padx=2, pady=4)
        ttk.Combobox(fmt, textvariable=sv,
                     values=["8","9","10","11","12","14","16","18","20","24","28","32","36","48","72"],
                     width=4, font=("Segoe UI", 8)).pack(side="left", padx=2, pady=4)

        for txt, var in [("B", bv), ("I", iv), ("U", uv)]:
            tk.Checkbutton(fmt, text=txt, variable=var, indicatoron=False,
                           font=("Georgia", 9, "bold"), bg="#1e1e32", fg="#9999cc",
                           selectcolor="#5533aa", relief="flat", padx=6, pady=2
                           ).pack(side="left", padx=1, pady=4)

        for sym, val in [("L","left"),("C","center"),("R","right")]:
            tk.Radiobutton(fmt, text=sym, variable=av, value=val, indicatoron=False,
                           font=("Segoe UI", 7), bg="#1e1e32", fg="#9999cc",
                           selectcolor="#5533aa", relief="flat", padx=4, pady=2
                           ).pack(side="left", padx=1, pady=4)

        # Text area
        text_frame = tk.Frame(win, bg="#0f0f1e")
        text_frame.pack(fill="both", expand=True, padx=10, pady=6)

        yscr = tk.Scrollbar(text_frame, bg="#1e1e32", troughcolor="#0f0f1e", width=8)
        yscr.pack(side="right", fill="y")

        text_area = tk.Text(
            text_frame, bg="#0d0d1c", fg="#e0e0f0", insertbackground="#aa88ff",
            font=("Consolas", 11), relief="flat", bd=8, wrap="word",
            yscrollcommand=yscr.set, undo=True
        )
        text_area.pack(fill="both", expand=True)
        yscr.config(command=text_area.yview)

        if tb.text:
            text_area.insert("1.0", tb.text)
        text_area.focus_set()

        # Size fields
        dim_frame = tk.Frame(win, bg="#0f0f1e")
        dim_frame.pack(fill="x", padx=10, pady=4)
        tk.Label(dim_frame, text="Width:", font=("Segoe UI", 8), bg="#0f0f1e", fg="#666688").pack(side="left")
        wv = tk.StringVar(value=str(int(tb.width)))
        tk.Entry(dim_frame, textvariable=wv, width=6, bg="#1e1e32", fg="#9999cc",
                 relief="flat", font=("Segoe UI", 8)).pack(side="left", padx=4)
        tk.Label(dim_frame, text="Height:", font=("Segoe UI", 8), bg="#0f0f1e", fg="#666688").pack(side="left", padx=(8,0))
        hv = tk.StringVar(value=str(int(tb.height)))
        tk.Entry(dim_frame, textvariable=hv, width=6, bg="#1e1e32", fg="#9999cc",
                 relief="flat", font=("Segoe UI", 8)).pack(side="left", padx=4)

        # Buttons
        btns = tk.Frame(win, bg="#0f0f1e")
        btns.pack(fill="x", padx=10, pady=8)

        def apply():
            tb.text         = text_area.get("1.0", "end-1c")
            tb.font_name    = fv.get()
            tb.font_size    = self._safe_int(sv.get(), 12)
            tb.font_bold    = bv.get()
            tb.font_italic  = iv.get()
            tb.font_underline = uv.get()
            tb.align        = av.get()
            tb.width        = self._safe_int(wv.get(), 250)
            tb.height       = self._safe_int(hv.get(), 60)
            self._push_undo()
            self._redraw_page()
            self._update_prop_panel(tb)
            win.destroy()

        def delete_tb():
            self._page_textboxes().remove(tb)
            self.selected_tb = None
            self._redraw_page()
            win.destroy()

        tk.Button(btns, text="✓ Apply", command=apply, bg="#5533aa", fg="white",
                  relief="flat", font=("Segoe UI", 9, "bold"), padx=14, pady=5,
                  cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="✕ Cancel", command=win.destroy, bg="#2a2a3e", fg="#9999cc",
                  relief="flat", font=("Segoe UI", 9), padx=10, pady=5,
                  cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="🗑 Delete Box", command=delete_tb, bg="#5a1a1a", fg="#ffaaaa",
                  relief="flat", font=("Segoe UI", 9), padx=10, pady=5,
                  cursor="hand2").pack(side="right", padx=4)

        win.bind("<Control-Return>", lambda e: apply())
        win.bind("<Escape>",         lambda e: win.destroy())

    def _show_context_menu(self, event, tb):
        menu = tk.Menu(self.root, tearoff=0, bg="#0a0a18", fg="#c8c8e8",
                       activebackground="#5533aa")
        menu.add_command(label="✏ Edit Text",          command=lambda: self._open_text_editor(tb))
        menu.add_command(label="📋 Duplicate",          command=self.duplicate_textbox)
        menu.add_command(label="🗑 Delete",             command=self.delete_selected)
        menu.add_separator()
        menu.add_command(label="Move to Front",         command=lambda: self._reorder_tb(tb, "front"))
        menu.add_command(label="Move to Back",          command=lambda: self._reorder_tb(tb, "back"))
        menu.post(event.x_root, event.y_root)

    def _reorder_tb(self, tb, direction):
        lst = self._page_textboxes()
        if tb in lst:
            lst.remove(tb)
            if direction == "front":
                lst.append(tb)
            else:
                lst.insert(0, tb)
            self._redraw_page()

    def duplicate_textbox(self):
        if not self.selected_tb:
            return
        tb = copy.deepcopy(self.selected_tb)
        tb.x += 10
        tb.y += 10
        tb.id = id(tb)
        self._page_textboxes().append(tb)
        self.selected_tb = tb
        self._push_undo()
        self._redraw_page()

    def delete_selected(self):
        if self.selected_tb and self.selected_tb in self._page_textboxes():
            self._page_textboxes().remove(self.selected_tb)
            self.selected_tb = None
            self._push_undo()
            self._redraw_page()

    # ══════════════════════════════════════════════════════════════════════════
    #  ANNOTATION OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _add_annotation(self, kind, points):
        page = self.current_page
        if page not in self.annotations:
            self.annotations[page] = []
        a = Annotation(kind, points, color=self.annot_color,
                       page=page, width=self.annot_width)
        self.annotations[page].append(a)
        self._push_undo()

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE RENDERING
    # ══════════════════════════════════════════════════════════════════════════

    PAGE_PADDING = 40

    def _redraw_page(self):
        self.canvas.delete("all")
        if not self.pdf_reader:
            return

        page = self.pdf_reader.pages[self.current_page]
        pw = float(page.mediabox.width)
        ph = float(page.mediabox.height)

        cw = int(pw * self.zoom)
        ch = int(ph * self.zoom)

        pad = self.PAGE_PADDING
        total_w = cw + pad * 2
        total_h = ch + pad * 2
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))

        ox = pad
        oy = pad
        self.page_offset_x = ox
        self.page_offset_y = oy

        # Shadow
        self.canvas.create_rectangle(ox+5, oy+5, ox+cw+5, oy+ch+5, fill="#050510", outline="")
        # Page white
        self.canvas.create_rectangle(ox, oy, ox+cw, oy+ch, fill="white", outline="#222244", width=1)

        # Page number
        self.canvas.create_text(ox + cw - 8, oy + 8,
                                text=f"Page {self.current_page+1}", font=("Consolas", 7),
                                fill="#aaaaaa", anchor="ne")

        # Extract & draw existing page text content (preview)
        try:
            raw = page.extract_text() or ""
            if raw:
                preview = raw[:600]
                lines = preview.split("\n")
                y_pos = oy + 20
                for ln in lines:
                    if y_pos > oy + ch - 10:
                        break
                    self.canvas.create_text(ox + 10, y_pos, text=ln[:80],
                                            font=("Courier", max(6, int(7 * self.zoom))),
                                            fill="#333333", anchor="nw")
                    y_pos += max(8, int(10 * self.zoom))
        except Exception:
            pass

        # Draw annotations
        for a in self.annotations.get(self.current_page, []):
            pts_c = [self._page_to_canvas(px, py) for px, py in a.points]
            if a.kind == "freehand" and len(pts_c) >= 2:
                flat = [coord for p in pts_c for coord in p]
                self.canvas.create_line(*flat, fill=a.color, width=a.width, smooth=True)
            elif a.kind == "arrow" and len(pts_c) == 2:
                self.canvas.create_line(*pts_c[0], *pts_c[1], fill=a.color,
                                        width=a.width, arrow="last",
                                        arrowshape=(12,15,4))
            elif a.kind == "rect" and len(pts_c) == 2:
                self.canvas.create_rectangle(*pts_c[0], *pts_c[1],
                                             outline=a.color, width=a.width)
            elif a.kind == "oval" and len(pts_c) == 2:
                self.canvas.create_oval(*pts_c[0], *pts_c[1],
                                        outline=a.color, width=a.width)
            elif a.kind == "highlight" and len(pts_c) == 2:
                self.canvas.create_rectangle(*pts_c[0], *pts_c[1],
                                             fill=a.color, stipple="gray50", outline="")

        # Draw text boxes
        for tb in self._page_textboxes():
            tx, ty = self._page_to_canvas(tb.x, tb.y)
            tw = tb.width  * self.zoom
            th = tb.height * self.zoom

            is_selected = (tb is self.selected_tb)

            # Background
            if tb.bg_color:
                self.canvas.create_rectangle(tx, ty, tx+tw, ty+th,
                                             fill=tb.bg_color, outline="")

            # Border
            outline_col = "#5533aa" if is_selected else tb.border_color
            outline_w   = 2         if is_selected else tb.border_width
            self.canvas.create_rectangle(tx, ty, tx+tw, ty+th,
                                         outline=outline_col, width=outline_w,
                                         dash=(4,3) if not is_selected else ())

            # Render text
            if tb.text:
                fs = max(6, int(tb.font_size * self.zoom))
                weight = "bold"   if tb.font_bold   else "normal"
                slant  = "italic" if tb.font_italic  else "roman"
                try:
                    fnt = tkfont.Font(family=self._map_font(tb.font_name),
                                      size=fs, weight=weight, slant=slant)
                except Exception:
                    fnt = tkfont.Font(size=fs)

                anchor_map = {"left": "nw", "center": "n", "right": "ne"}
                if tb.align == "center":
                    text_x = tx + tw / 2
                elif tb.align == "right":
                    text_x = tx + tw - 4
                else:
                    text_x = tx + 4

                self.canvas.create_text(
                    text_x, ty + 4,
                    text=tb.text, font=fnt, fill=tb.color,
                    anchor=anchor_map.get(tb.align, "nw"),
                    width=tw - 8,
                )

                # Underline simulation
                if tb.font_underline:
                    line_y = ty + fs + 6
                    self.canvas.create_line(tx+4, line_y, tx+tw-4, line_y,
                                            fill=tb.color, width=1)

            # Selection handles
            if is_selected:
                for hx, hy in [(tx, ty), (tx+tw/2, ty), (tx+tw, ty),
                                (tx, ty+th/2), (tx+tw, ty+th/2),
                                (tx, ty+th), (tx+tw/2, ty+th), (tx+tw, ty+th)]:
                    self.canvas.create_rectangle(hx-4, hy-4, hx+4, hy+4,
                                                 fill="#5533aa", outline="white", width=1)

        # Update nav
        self.page_lbl.config(
            text=f"Page {self.current_page+1}/{self.total_pages}  •  "
                 f"Zoom {int(self.zoom*100)}%  •  "
                 f"{len(self._page_textboxes())} text boxes  •  "
                 f"{len(self.annotations.get(self.current_page,[]))} annotations"
        )

    def _show_welcome(self):
        self.canvas.delete("all")
        w, h = 900, 560
        self.canvas.config(scrollregion=(0, 0, w, h))
        self.canvas.create_rectangle(60, 60, w-60, h-60, fill="#0a0a18",
                                     outline="#2a2a3e", width=2)
        self.canvas.create_text(w/2, 160, text="✦", font=("Georgia", 56), fill="#5533aa")
        self.canvas.create_text(w/2, 230, text="PDF Editor Pro — Advanced",
                                font=("Georgia", 18, "bold"), fill="#e8d5b7")
        self.canvas.create_text(w/2, 265,
                                text="Open a PDF and add text boxes, annotations, highlights, drawings",
                                font=("Segoe UI", 10), fill="#555577")
        tips = ["📂  File → Open PDF  (Ctrl+O)",
                "T   Click 'T Text Box' then click the page to add editable text",
                "✏   Use Draw / Highlight / Arrow tools to annotate",
                "📤  Export Edited PDF to save all your changes"]
        y = 310
        for t in tips:
            self.canvas.create_text(w/2, y, text=t, font=("Consolas", 9), fill="#444466")
            y += 26

    # ══════════════════════════════════════════════════════════════════════════
    #  FORMAT BAR SYNC
    # ══════════════════════════════════════════════════════════════════════════

    def _apply_format(self, *_):
        if self.selected_tb:
            self.selected_tb.font_name = self.font_var.get()
            self.selected_tb.font_size = self._safe_int(self.size_var.get(), 12)
            self.selected_tb.font_bold = self.tool_bold.get()
            self.selected_tb.font_italic = self.tool_italic.get()
            self.selected_tb.font_underline = self.tool_underline.get()
            self.selected_tb.align = self.tool_align.get()
            self.selected_tb.color = self.tool_color
            self._redraw_page()

    def _update_format_bar_from(self, tb):
        self.font_var.set(tb.font_name)
        self.size_var.set(str(tb.font_size))
        self.tool_bold.set(tb.font_bold)
        self.tool_italic.set(tb.font_italic)
        self.tool_underline.set(tb.font_underline)
        self.tool_align.set(tb.align)
        self.tool_color = tb.color
        self.color_swatch.config(bg=self.tool_color)
        self._update_prop_panel(tb)

    def _update_prop_panel(self, tb):
        info = (f"Text: {tb.text[:30]+'…' if len(tb.text)>30 else tb.text or '(empty)'}\n"
                f"Font: {tb.font_name} {tb.font_size}pt\n"
                f"Bold: {tb.font_bold}  Italic: {tb.font_italic}\n"
                f"Align: {tb.align}\n"
                f"Size: {int(tb.width)}×{int(tb.height)} pts")
        self.prop_text_lbl.config(text=info, justify="left")

    # ══════════════════════════════════════════════════════════════════════════
    #  COLOR PICKERS
    # ══════════════════════════════════════════════════════════════════════════

    def _pick_text_color(self, *_):
        from tkinter.colorchooser import askcolor
        c = askcolor(color=self.tool_color, title="Text Color")[1]
        if c:
            self.tool_color = c
            self.color_swatch.config(bg=c)
            if self.selected_tb:
                self.selected_tb.color = c
                self._redraw_page()

    def _pick_bg_color(self, *_):
        from tkinter.colorchooser import askcolor
        c = askcolor(title="Background Color (cancel = transparent)")[1]
        self.tool_bg = c or ""
        self.bg_swatch.config(bg=c if c else "white", text="" if c else "∅")
        if self.selected_tb:
            self.selected_tb.bg_color = c
            self._redraw_page()

    def _pick_ink_color(self, *_):
        from tkinter.colorchooser import askcolor
        c = askcolor(color=self.annot_color, title="Ink Color")[1]
        if c:
            self.annot_color = c
            self.ink_swatch.config(bg=c)

    # ══════════════════════════════════════════════════════════════════════════
    #  FILE OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def open_pdf(self):
        path = filedialog.askopenfilename(title="Open PDF",
                                          filetypes=[("PDF","*.pdf"),("All","*.*")])
        if not path:
            return
        try:
            self.current_file = path
            self.pdf_reader   = PdfReader(path)
            self.total_pages  = len(self.pdf_reader.pages)
            self.current_page = 0
            self.textboxes    = {}
            self.annotations  = {}
            self.selected_tb  = None
            self._refresh_page_list()
            self._redraw_page()
            self.file_label.config(text=os.path.basename(path))
            self._set_status(f"Opened: {os.path.basename(path)}  •  {self.total_pages} pages")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open PDF:\n{e}")

    def save_pdf(self):
        if not self.current_file:
            self.save_pdf_as(); return
        self._write_base_pdf(self.current_file)

    def save_pdf_as(self):
        if not self.pdf_reader:
            messagebox.showwarning("No File", "Open a PDF first."); return
        path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                            filetypes=[("PDF","*.pdf")])
        if path:
            self._write_base_pdf(path)
            self.current_file = path

    def _write_base_pdf(self, path):
        try:
            writer = PdfWriter()
            for p in self.pdf_reader.pages:
                writer.add_page(p)
            with open(path, "wb") as f:
                writer.write(f)
            self._set_status(f"Saved: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def export_edited_pdf(self):
        """Flatten text boxes and annotations into the PDF and save."""
        if not self.pdf_reader:
            messagebox.showwarning("No File", "Open a PDF first."); return
        path = filedialog.asksaveasfilename(
            title="Export Edited PDF",
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")],
            initialfile="edited_output.pdf"
        )
        if not path:
            return
        try:
            writer = PdfWriter()
            for page_idx, page in enumerate(self.pdf_reader.pages):
                pw = float(page.mediabox.width)
                ph = float(page.mediabox.height)

                tbs   = self.textboxes.get(page_idx, [])
                annots = self.annotations.get(page_idx, [])

                if tbs or annots:
                    # Create overlay with reportlab
                    buf = io.BytesIO()
                    c = rl_canvas.Canvas(buf, pagesize=(pw, ph))

                    # Draw annotations
                    for a in annots:
                        c.setStrokeColor(rl_colors.HexColor(a.color))
                        c.setLineWidth(a.width)
                        pts = [(px, ph - py) for px, py in a.points]  # flip Y

                        if a.kind == "freehand" and len(pts) >= 2:
                            path = c.beginPath()
                            path.moveTo(*pts[0])
                            for pt in pts[1:]:
                                path.lineTo(*pt)
                            c.drawPath(path)

                        elif a.kind == "arrow" and len(pts) == 2:
                            x1,y1 = pts[0]; x2,y2 = pts[1]
                            c.line(x1,y1,x2,y2)
                            # arrowhead
                            angle = math.atan2(y2-y1, x2-x1)
                            for da in [2.5, -2.5]:
                                c.line(x2, y2,
                                       x2 - 12*math.cos(angle+da),
                                       y2 - 12*math.sin(angle+da))

                        elif a.kind in ("rect","highlight") and len(pts) == 2:
                            x0,y0 = pts[0]; x1,y1 = pts[1]
                            if a.kind == "highlight":
                                c.setFillColor(rl_colors.HexColor(a.color), alpha=0.35)
                                c.rect(min(x0,x1), min(y0,y1),
                                       abs(x1-x0), abs(y1-y0), stroke=0, fill=1)
                            else:
                                c.rect(min(x0,x1), min(y0,y1),
                                       abs(x1-x0), abs(y1-y0), stroke=1, fill=0)

                        elif a.kind == "oval" and len(pts) == 2:
                            x0,y0 = pts[0]; x1,y1 = pts[1]
                            cx2 = (x0+x1)/2; cy2 = (y0+y1)/2
                            rx = abs(x1-x0)/2; ry = abs(y1-y0)/2
                            c.ellipse(cx2-rx, cy2-ry, cx2+rx, cy2+ry, stroke=1, fill=0)

                    # Draw text boxes
                    for tb in tbs:
                        if not tb.text:
                            continue
                        x  = tb.x
                        y  = ph - tb.y - tb.height   # flip Y

                        # Background
                        if tb.bg_color:
                            c.setFillColor(rl_colors.HexColor(tb.bg_color))
                            c.rect(x, y, tb.width, tb.height, stroke=0, fill=1)

                        # Border
                        c.setStrokeColor(rl_colors.HexColor(tb.border_color))
                        c.setLineWidth(tb.border_width)
                        c.rect(x, y, tb.width, tb.height, stroke=1, fill=0)

                        # Text
                        c.setFillColor(rl_colors.HexColor(tb.color))
                        font_name = self._rl_font(tb)
                        c.setFont(font_name, tb.font_size)

                        lines = tb.text.split("\n")
                        ty = y + tb.height - tb.font_size - 2
                        for line in lines:
                            if ty < y:
                                break
                            if tb.align == "center":
                                c.drawCentredString(x + tb.width/2, ty, line)
                            elif tb.align == "right":
                                c.drawRightString(x + tb.width - 4, ty, line)
                            else:
                                c.drawString(x + 4, ty, line)

                            if tb.font_underline:
                                tw = c.stringWidth(line, font_name, tb.font_size)
                                c.line(x+4, ty-1, x+4+tw, ty-1)
                            ty -= tb.font_size * 1.2

                    c.save()
                    buf.seek(0)

                    overlay_reader = PdfReader(buf)
                    overlay_page   = overlay_reader.pages[0]
                    page.merge_page(overlay_page)

                writer.add_page(page)

            with open(path, "wb") as f:
                writer.write(f)

            self._set_status(f"Exported: {os.path.basename(path)}")
            if messagebox.askyesno("Exported!", f"Edited PDF saved to:\n{path}\n\nOpen it now?"):
                os.startfile(path) if os.name == "nt" else os.system(f"xdg-open '{path}'")

        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def create_new_pdf(self):
        title = simpledialog.askstring("New PDF", "Document title:", initialvalue="My Document")
        if not title:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF","*.pdf")],
            initialfile=f"{title}.pdf"
        )
        if not path:
            return
        try:
            c = rl_canvas.Canvas(path, pagesize=A4)
            w, h = A4
            c.setFillColor(rl_colors.HexColor("#5533aa"))
            c.rect(0, h-80, w, 80, fill=True, stroke=False)
            c.setFillColor(rl_colors.white)
            c.setFont("Helvetica-Bold", 22)
            c.drawCentredString(w/2, h-52, title)
            c.setFillColor(rl_colors.HexColor("#555555"))
            c.setFont("Helvetica", 11)
            c.drawCentredString(w/2, h-110, "Created with PDF Editor Pro")
            c.save()

            self.current_file = path
            self.pdf_reader   = PdfReader(path)
            self.total_pages  = len(self.pdf_reader.pages)
            self.current_page = 0
            self.textboxes    = {}
            self.annotations  = {}
            self._refresh_page_list()
            self._redraw_page()
            self.file_label.config(text=os.path.basename(path))
            self._set_status(f"Created: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    #  PAGE OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def rotate_page(self, deg):
        if not self.pdf_reader: return
        self.pdf_reader.pages[self.current_page].rotate(deg)
        self._redraw_page()

    def delete_page(self):
        if not self.pdf_reader: return
        if self.total_pages == 1:
            messagebox.showwarning("Cannot Delete", "Cannot delete the only page."); return
        if not messagebox.askyesno("Delete", f"Delete page {self.current_page+1}?"): return
        writer = PdfWriter()
        for i, p in enumerate(self.pdf_reader.pages):
            if i != self.current_page:
                writer.add_page(p)
        tmp = self.current_file + "._tmp.pdf"
        with open(tmp, "wb") as f: writer.write(f)
        self.pdf_reader   = PdfReader(tmp)
        self.total_pages  = len(self.pdf_reader.pages)
        self.current_page = min(self.current_page, self.total_pages-1)
        os.remove(tmp)
        self._refresh_page_list(); self._redraw_page()

    def insert_blank_page(self):
        if not self.pdf_reader: return
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        c.setFillColor(rl_colors.white); c.rect(0,0,*A4,fill=True,stroke=False); c.save()
        buf.seek(0)
        blank = PdfReader(buf).pages[0]
        writer = PdfWriter()
        for i, p in enumerate(self.pdf_reader.pages):
            writer.add_page(p)
            if i == self.current_page: writer.add_page(blank)
        tmp = self.current_file + "._tmp.pdf"
        with open(tmp, "wb") as f: writer.write(f)
        self.pdf_reader  = PdfReader(tmp)
        self.total_pages = len(self.pdf_reader.pages)
        os.remove(tmp)
        self._refresh_page_list(); self._redraw_page()

    def merge_pdfs(self):
        paths = filedialog.askopenfilenames(title="Select PDFs to Merge",
                                            filetypes=[("PDF","*.pdf")])
        if not paths: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                          filetypes=[("PDF","*.pdf")],
                                          initialfile="merged.pdf")
        if not out: return
        writer = PdfWriter()
        for p in paths:
            for page in PdfReader(p).pages: writer.add_page(page)
        with open(out, "wb") as f: writer.write(f)
        messagebox.showinfo("Done", f"Merged {len(paths)} PDFs → {os.path.basename(out)}")

    def split_pdf(self):
        if not self.pdf_reader:
            messagebox.showwarning("No File","Open a PDF first."); return
        folder = filedialog.askdirectory(title="Save Split Pages To")
        if not folder: return
        base = os.path.splitext(os.path.basename(self.current_file))[0]
        for i, page in enumerate(self.pdf_reader.pages):
            w = PdfWriter(); w.add_page(page)
            with open(os.path.join(folder, f"{base}_page_{i+1}.pdf"), "wb") as f: w.write(f)
        messagebox.showinfo("Done", f"Split into {self.total_pages} files → {folder}")

    def goto_page_dialog(self):
        if not self.pdf_reader: return
        p = simpledialog.askinteger("Go To", f"Page (1–{self.total_pages}):",
                                    minvalue=1, maxvalue=self.total_pages)
        if p:
            self.current_page = p-1
            self._redraw_page()

    def encrypt_pdf(self):
        if not self.pdf_reader:
            messagebox.showwarning("No File","Open a PDF first."); return
        pw = simpledialog.askstring("Encrypt","Password:", show="*")
        if not pw: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                          filetypes=[("PDF","*.pdf")],
                                          initialfile="encrypted.pdf")
        if not out: return
        writer = PdfWriter()
        for p in self.pdf_reader.pages: writer.add_page(p)
        writer.encrypt(pw)
        with open(out,"wb") as f: writer.write(f)
        messagebox.showinfo("Done","PDF encrypted!")

    def decrypt_pdf(self):
        path = filedialog.askopenfilename(title="Open Encrypted PDF",
                                          filetypes=[("PDF","*.pdf")])
        if not path: return
        pw = simpledialog.askstring("Decrypt","Password:", show="*")
        if not pw: return
        r = PdfReader(path)
        if r.decrypt(pw):
            out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                              filetypes=[("PDF","*.pdf")],
                                              initialfile="decrypted.pdf")
            if out:
                writer = PdfWriter()
                for p in r.pages: writer.add_page(p)
                with open(out,"wb") as f: writer.write(f)
                messagebox.showinfo("Done","PDF decrypted!")
        else:
            messagebox.showerror("Wrong Password","Incorrect password.")

    def add_watermark(self):
        if not self.pdf_reader:
            messagebox.showwarning("No File","Open a PDF first."); return
        text = simpledialog.askstring("Watermark","Watermark text:", initialvalue="CONFIDENTIAL")
        if not text: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                          filetypes=[("PDF","*.pdf")],
                                          initialfile="watermarked.pdf")
        if not out: return
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        c.setFillColor(rl_colors.Color(0.6,0.6,0.6,alpha=0.25))
        c.setFont("Helvetica-Bold", 52)
        c.saveState(); c.translate(A4[0]/2,A4[1]/2); c.rotate(45)
        c.drawCentredString(0,0,text); c.restoreState(); c.save(); buf.seek(0)
        wm = PdfReader(buf).pages[0]
        writer = PdfWriter()
        for p in self.pdf_reader.pages:
            p.merge_page(wm); writer.add_page(p)
        with open(out,"wb") as f: writer.write(f)
        messagebox.showinfo("Done",f"Watermark added → {os.path.basename(out)}")

    def insert_image_on_page(self):
        if not self.pdf_reader:
            messagebox.showwarning("No File","Open a PDF first."); return
        img_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Images","*.png *.jpg *.jpeg *.bmp *.gif"),("All","*.*")]
        )
        if not img_path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
                                          filetypes=[("PDF","*.pdf")],
                                          initialfile="with_image.pdf")
        if not out: return
        try:
            page = self.pdf_reader.pages[self.current_page]
            pw = float(page.mediabox.width)
            ph = float(page.mediabox.height)
            buf = io.BytesIO()
            c = rl_canvas.Canvas(buf, pagesize=(pw,ph))
            c.drawImage(img_path, 50, ph-250, width=200, height=180,
                        preserveAspectRatio=True, mask="auto")
            c.save(); buf.seek(0)
            overlay = PdfReader(buf).pages[0]
            page.merge_page(overlay)
            writer = PdfWriter()
            for p in self.pdf_reader.pages: writer.add_page(p)
            with open(out,"wb") as f: writer.write(f)
            self.current_file = out
            self.pdf_reader   = PdfReader(out)
            self._redraw_page()
            messagebox.showinfo("Done","Image inserted!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def extract_text(self):
        if not self.pdf_reader:
            messagebox.showwarning("No File","Open a PDF first."); return
        win = tk.Toplevel(self.root)
        win.title("Extracted Text"); win.geometry("720x520")
        win.configure(bg="#0f0f1e")
        tk.Label(win, text="Extracted Text", font=("Georgia",11,"bold"),
                 bg="#0f0f1e", fg="#e8d5b7").pack(pady=10)
        f = tk.Frame(win, bg="#0f0f1e"); f.pack(fill="both",expand=True,padx=10,pady=(0,6))
        ys = tk.Scrollbar(f); ys.pack(side="right",fill="y")
        tb = tk.Text(f, bg="#0a0a18", fg="#c0c0e0", font=("Consolas",9),
                     relief="flat", bd=6, yscrollcommand=ys.set, wrap="word")
        tb.pack(fill="both",expand=True); ys.config(command=tb.yview)
        all_text = ""
        for i, pg in enumerate(self.pdf_reader.pages):
            t = pg.extract_text() or "(no text)"
            all_text += f"\n{'─'*55}\n  PAGE {i+1}\n{'─'*55}\n{t}\n"
        tb.insert("1.0", all_text.strip()); tb.config(state="disabled")
        def save():
            sp = filedialog.asksaveasfilename(defaultextension=".txt",
                                              filetypes=[("Text","*.txt")])
            if sp:
                with open(sp,"w",encoding="utf-8") as f: f.write(all_text)
                messagebox.showinfo("Saved",f"Text saved → {sp}")
        tk.Button(win, text="💾 Save .txt", command=save, bg="#5533aa", fg="white",
                  relief="flat", font=("Segoe UI",9), padx=12, pady=6,
                  cursor="hand2").pack(pady=6)

    def show_metadata(self):
        if not self.pdf_reader:
            messagebox.showwarning("No File","Open a PDF first."); return
        meta = self.pdf_reader.metadata or {}
        info = "\n".join([
            f"File:      {os.path.basename(self.current_file)}",
            f"Pages:     {self.total_pages}",
            f"Title:     {meta.get('/Title','N/A')}",
            f"Author:    {meta.get('/Author','N/A')}",
            f"Creator:   {meta.get('/Creator','N/A')}",
            f"Producer:  {meta.get('/Producer','N/A')}",
            f"Created:   {meta.get('/CreationDate','N/A')}",
            f"Encrypted: {'Yes' if self.pdf_reader.is_encrypted else 'No'}",
        ])
        messagebox.showinfo("PDF Metadata", info)

    # ══════════════════════════════════════════════════════════════════════════
    #  UNDO / REDO
    # ══════════════════════════════════════════════════════════════════════════

    def _push_undo(self):
        state = {
            "textboxes":   copy.deepcopy(self.textboxes),
            "annotations": copy.deepcopy(self.annotations),
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack: return
        self.redo_stack.append({
            "textboxes":   copy.deepcopy(self.textboxes),
            "annotations": copy.deepcopy(self.annotations),
        })
        state = self.undo_stack.pop()
        self.textboxes   = state["textboxes"]
        self.annotations = state["annotations"]
        self.selected_tb = None
        self._redraw_page()

    def redo(self):
        if not self.redo_stack: return
        self._push_undo()
        state = self.redo_stack.pop()
        self.textboxes   = state["textboxes"]
        self.annotations = state["annotations"]
        self.selected_tb = None
        self._redraw_page()

    # ══════════════════════════════════════════════════════════════════════════
    #  NAVIGATION & ZOOM
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_page_list(self):
        self.page_list.delete(0,"end")
        for i in range(self.total_pages):
            self.page_list.insert("end", f"  pg {i+1}")

    def _on_page_select(self, event):
        sel = self.page_list.curselection()
        if sel:
            self.current_page = sel[0]
            self.selected_tb  = None
            self._redraw_page()

    def prev_page(self):
        if self.pdf_reader and self.current_page > 0:
            self.current_page -= 1; self.selected_tb = None; self._redraw_page()

    def next_page(self):
        if self.pdf_reader and self.current_page < self.total_pages-1:
            self.current_page += 1; self.selected_tb = None; self._redraw_page()

    def zoom_in(self):
        self.zoom = min(4.0, self.zoom + 0.15); self._redraw_page()

    def zoom_out(self):
        self.zoom = max(0.2, self.zoom - 0.15); self._redraw_page()

    def zoom_reset(self):
        self.zoom = 1.0; self._redraw_page()

    # ══════════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _page_textboxes(self) -> list:
        if self.current_page not in self.textboxes:
            self.textboxes[self.current_page] = []
        return self.textboxes[self.current_page]

    def _map_font(self, rl_name):
        mapping = {
            "Helvetica":        "Arial",
            "Helvetica-Bold":   "Arial",
            "Helvetica-Oblique":"Arial",
            "Times-Roman":      "Times New Roman",
            "Times-Bold":       "Times New Roman",
            "Courier":          "Courier New",
            "Courier-Bold":     "Courier New",
        }
        return mapping.get(rl_name, "Arial")

    def _rl_font(self, tb: TextBox) -> str:
        base = tb.font_name.replace("-Bold","").replace("-Oblique","")
        if base not in ["Helvetica","Times-Roman","Courier"]:
            base = "Helvetica"
        if tb.font_bold and tb.font_italic:
            suffixes = {"Helvetica":"BoldOblique","Times-Roman":"BoldItalic","Courier":"BoldOblique"}
            return base + "-" + suffixes.get(base, "Bold")
        elif tb.font_bold:
            return base + "-Bold"
        elif tb.font_italic:
            suffixes = {"Helvetica":"Oblique","Times-Roman":"Italic","Courier":"Oblique"}
            return base + "-" + suffixes.get(base, "Oblique")
        return base

    @staticmethod
    def _safe_int(val, default=12):
        try: return max(1, int(val))
        except: return default

    def _set_status(self, msg):
        self.status_var.set(f"✓  {msg}")

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.open_pdf())
        self.root.bind("<Control-s>", lambda e: self.save_pdf())
        self.root.bind("<Control-S>", lambda e: self.save_pdf_as())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Left>",      lambda e: self.prev_page())
        self.root.bind("<Right>",     lambda e: self.next_page())
        self.root.bind("<Delete>",    lambda e: self.delete_selected())
        self.root.bind("<Escape>",    lambda e: self._set_mode(self.MODE_SELECT))


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(True, True)
    app = PDFEditorPro(root)
    root.mainloop()
