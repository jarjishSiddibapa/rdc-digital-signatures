import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import time
import fitz  # PyMuPDF - for PDF page rendering
from PIL import Image, ImageTk

# Import backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from backend import pdf_processor, analyzer, signer

# --- Design System & Assets ---
# Colors (Linear / Notion inspired Dark Mode)
COLOR_BG = "#121212"        # Main Background
COLOR_SIDEBAR = "#0A0A0A"   # Darker Sidebar
COLOR_CARD = "#1E1E1E"      # Card Background
COLOR_ACCENT = "#3B82F6"    # Primary Blue
COLOR_ACCENT_HOVER = "#2563EB"
COLOR_SUCCESS = "#10B981"   # Emerald Green
COLOR_TEXT_MAIN = "#FFFFFF"
COLOR_TEXT_SUB = "#A1A1AA"  # Zinc 400

# Fonts
FONT_MAIN = ("Roboto Medium", 14)
FONT_HEADER = ("Roboto", 24, "bold")
FONT_SUBHEADER = ("Roboto", 16, "bold")
FONT_SMALL = ("Roboto", 12)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue") # We will override specific colors

class PremiumButton(ctk.CTkButton):
    """Custom button with modern styling"""
    def __init__(self, master, **kwargs):
        # Extract properties or use defaults
        height = kwargs.pop("height", 36)
        font = kwargs.pop("font", ("Roboto", 13, "bold"))
        corner_radius = kwargs.pop("corner_radius", 8)
        
        super().__init__(master, 
                         corner_radius=corner_radius, 
                         font=font,
                         height=height,
                         **kwargs)

class StatusCard(ctk.CTkFrame):
    """Card for displaying logs/status"""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color="#2A2A2A", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        # state="disabled" makes it read-only for the user
        self.text_area = ctk.CTkTextbox(self, fg_color="transparent", text_color=COLOR_TEXT_SUB, font=("Consolas", 11), wrap="word", state="disabled")
        self.text_area.pack(fill="both", expand=True, padx=15, pady=15)
        
    def log(self, text):
        # Temporarily enable to write log
        self.text_area.configure(state="normal")
        self.text_area.insert("end", f"> {text}\n")
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

# Helper function for resource paths (works for dev and PyInstaller)
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class RDCApp(ctk.CTk):
    def __init__(self, username=None):
        super().__init__()
        self.current_user = username  # Store logged-in username
        self.logout_requested = False  # Flag for logout

        # Window Setup - Responsive sizing
        self.title("RDC Digital Signatures")
        self.geometry("1100x750")
        self.minsize(900, 600)  # Minimum window size
        self.configure(fg_color=COLOR_BG)
        
        # Set Window Icon
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            self.iconbitmap(icon_path)
        except Exception:
            pass # Icon not found, ignore
        
        # Grid Layout - Responsive
        self.grid_columnconfigure(0, weight=0, minsize=220)  # Sidebar fixed width
        self.grid_columnconfigure(1, weight=1)  # Main area expands
        self.grid_rowconfigure(0, weight=1)  # Content expands vertically

        # State
        self.file_paths = []
        # Use LOCALAPPDATA so temp/output files are always writable,
        # regardless of whether the app is installed for current user or all users.
        _app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        self.output_dir = os.path.join(_app_data, "RDCSignatures", "signed_output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.signer_instance = signer.DigitalSigner()
        self._last_cert_list = []  # Track certificate changes

        # UI Components
        self.init_sidebar()
        self.init_main_verify()
        self.init_footer()
        
        # Connect signer logging to Activity Log UI
        self.signer_instance.log_callback = lambda msg: self.after(0, lambda: self.console.log(msg))
        
        # Start periodic certificate scanner for hot-plug detection
        self._start_cert_scanner()

    def init_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        # Logo / Brand
        self.brand_label = ctk.CTkLabel(self.sidebar, text="RDC Fixed\nDSC", 
                                      font=("Roboto", 28, "bold"), 
                                      text_color=COLOR_TEXT_MAIN,
                                      justify="left")
        self.brand_label.grid(row=0, column=0, padx=30, pady=(40, 20), sticky="w")

        # Removed Dashboard button as it served no purpose

        # Upload Action
        self.upload_card = ctk.CTkFrame(self.sidebar, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color="#333")
        self.upload_card.grid(row=1, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.lbl_upload = ctk.CTkLabel(self.upload_card, text="Quick Actions", font=FONT_SMALL, text_color=COLOR_TEXT_SUB)
        self.lbl_upload.pack(pady=(15, 5), padx=15, anchor="w")
        
        self.btn_select_files = PremiumButton(self.upload_card, text="Select PDF Files", 
                                            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
                                            command=self.select_files)
        self.btn_select_files.pack(pady=10, padx=15, fill="x")

        # Selected Files Display (in sidebar)
        self.files_card = ctk.CTkFrame(self.sidebar, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color="#333")
        self.files_card.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)  # Allow files card to expand
        
        ctk.CTkLabel(self.files_card, text="SELECTED FILES", font=("Roboto", 10, "bold"), text_color=COLOR_TEXT_SUB).pack(anchor="w", padx=10, pady=(10, 5))
        self.files_scroll = ctk.CTkScrollableFrame(self.files_card, fg_color="transparent")
        self.files_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        # User info and logout button
        user_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        user_frame.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        if self.current_user:
            user_label = ctk.CTkLabel(user_frame, text=f"👤 {self.current_user}", 
                                     font=("Roboto", 12), text_color="#888")
            user_label.pack(anchor="w")
        
        # Logout button
        self.btn_logout = ctk.CTkButton(
            self.sidebar,
            text="🚪 Logout",
            fg_color="#dc3545",
            hover_color="#c82333",
            font=("Roboto", 12, "bold"),
            height=35,
            corner_radius=8,
            command=self._logout
        )
        self.btn_logout.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")
        
        # Bottom Info
        self.version_label = ctk.CTkLabel(self.sidebar, text="v1.0.0", text_color="#555")
        self.version_label.grid(row=5, column=0, pady=10)

    def create_nav_button(self, text, row, selected=False):
        color = "#2A2A2A" if selected else "transparent"
        text_col = COLOR_TEXT_MAIN if selected else COLOR_TEXT_SUB
        btn = ctk.CTkButton(self.sidebar, text=text, fg_color=color, text_color=text_col, 
                            hover_color="#222", corner_radius=8, anchor="w", 
                            font=("Roboto", 14), height=40)
        btn.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        return btn

    def init_main_verify(self):
        self.main_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)
        self.main_area.grid_columnconfigure(0, weight=1)

        # Header
        self.lbl_welcome = ctk.CTkLabel(self.main_area, text="New Signing Session", font=FONT_HEADER, text_color=COLOR_TEXT_MAIN)
        self.lbl_welcome.pack(anchor="w")
        
        self.lbl_subtitle = ctk.CTkLabel(self.main_area, text="Configure your parameters and upload documents.", font=FONT_SMALL, text_color=COLOR_TEXT_SUB)
        self.lbl_subtitle.pack(anchor="w", pady=(0, 15))

        # ===== MODE SELECTOR =====
        self.signing_mode = ctk.StringVar(value="string_match")
        self.mode_selector = ctk.CTkSegmentedButton(
            self.main_area,
            values=["📝 String Match", "🖼 Visual Placement"],
            command=self._on_mode_change,
            font=("Roboto", 13, "bold"),
            fg_color="#1E1E1E",
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color="#2A2A2A",
            unselected_hover_color="#333",
            corner_radius=8,
            height=38
        )
        self.mode_selector.pack(fill="x", pady=(0, 12))
        self.mode_selector.set("📝 String Match")

        # ===== STRING MATCH MODE FRAME =====
        self.string_match_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        
        config_grid_sm = ctk.CTkFrame(self.string_match_frame, fg_color="transparent")
        config_grid_sm.pack(fill="x")
        
        # Col 1: Match Text
        self.frame_match = ctk.CTkFrame(config_grid_sm, fg_color=COLOR_CARD, corner_radius=12)
        self.frame_match.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(self.frame_match, text="MATCHING KEYWORD", font=("Roboto", 11, "bold"), text_color=COLOR_TEXT_SUB).pack(anchor="w", padx=15, pady=(15, 5))
        self.entry_match = ctk.CTkEntry(self.frame_match, placeholder_text="e.g. CFO", 
                                      height=40, corner_radius=8, border_width=1, border_color="#333", fg_color="#121212")
        self.entry_match.pack(fill="x", padx=15, pady=(0, 15))
        self.entry_match.insert(0, "CFO")

        # Col 2: Certificate (shared - placed in string match grid for now)
        self.frame_cert_sm = ctk.CTkFrame(config_grid_sm, fg_color=COLOR_CARD, corner_radius=12)
        self.frame_cert_sm.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(self.frame_cert_sm, text="DIGITAL IDENTITY", font=("Roboto", 11, "bold"), text_color=COLOR_TEXT_SUB).pack(anchor="w", padx=15, pady=(15, 5))
        self.cert_options = self.signer_instance.scan_certificates()
        self.menu_cert = ctk.CTkOptionMenu(self.frame_cert_sm, values=self.cert_options, 
                                         height=40, corner_radius=8, fg_color="#121212", button_color="#333", button_hover_color="#444",
                                         command=self.on_cert_change)
        self.menu_cert.pack(fill="x", padx=15, pady=(0, 15))
        
        self.string_match_frame.pack(fill="x", pady=(0, 5))

        # ===== VISUAL PLACEMENT MODE FRAME =====
        self.visual_mode_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        # NOT packed initially - hidden until user switches mode
        
        # Top row: Certificate selector for visual mode
        config_grid_vp = ctk.CTkFrame(self.visual_mode_frame, fg_color="transparent")
        config_grid_vp.pack(fill="x", pady=(0, 8))
        
        self.frame_cert_vp = ctk.CTkFrame(config_grid_vp, fg_color=COLOR_CARD, corner_radius=12)
        self.frame_cert_vp.pack(fill="x")
        
        ctk.CTkLabel(self.frame_cert_vp, text="DIGITAL IDENTITY", font=("Roboto", 11, "bold"), text_color=COLOR_TEXT_SUB).pack(anchor="w", padx=15, pady=(15, 5))
        self.menu_cert_vp = ctk.CTkOptionMenu(self.frame_cert_vp, values=self.cert_options,
                                              height=40, corner_radius=8, fg_color="#121212", button_color="#333", button_hover_color="#444",
                                              command=self.on_cert_change)
        self.menu_cert_vp.pack(fill="x", padx=15, pady=(0, 15))
        
        # Preview area container
        self.preview_container = ctk.CTkFrame(self.visual_mode_frame, fg_color=COLOR_CARD, corner_radius=12, border_width=1, border_color="#333", height=500)
        self.preview_container.pack(fill="both", expand=True, pady=(0, 5))
        self.preview_container.pack_propagate(False)  # Prevent shrinking
        
        # Preview header with coordinates
        preview_header = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        preview_header.pack(fill="x", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(preview_header, text="PDF PREVIEW", font=("Roboto", 11, "bold"), text_color=COLOR_TEXT_SUB).pack(side="left")
        self.lbl_coords = ctk.CTkLabel(preview_header, text="Position: -- | Size: --", font=("Consolas", 10), text_color="#666")
        self.lbl_coords.pack(side="right")
        
        # Canvas frame with scrollbar
        canvas_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Vertical scrollbar for the canvas
        self._preview_scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", bg="#333", troughcolor="#1a1a1a")
        self._preview_scrollbar.pack(side="right", fill="y")
        
        # The actual tkinter Canvas for PDF preview + signature rectangle
        self.preview_canvas = tk.Canvas(
            canvas_frame,
            bg="#0A0A0A",
            highlightthickness=0,
            cursor="crosshair",
            yscrollcommand=self._preview_scrollbar.set
        )
        self.preview_canvas.pack(side="left", fill="both", expand=True)
        self._preview_scrollbar.config(command=self.preview_canvas.yview)
        
        # Mouse wheel scrolling
        self.preview_canvas.bind("<MouseWheel>", lambda e: self.preview_canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        
        # Preview state
        self._preview_image = None     # PhotoImage reference (prevent GC)
        self._preview_scale = 1.0      # scale factor: canvas px / pdf pt
        self._pdf_page_width = 612     # PDF page width in points
        self._pdf_page_height = 792    # PDF page height in points
        self._sig_rect_id = None       # Canvas rectangle item ID
        self._sig_rect_coords = None   # (x0, y0, x1, y1) in PDF points
        self._drag_data = {"x": 0, "y": 0, "mode": None}  # drag state
        self._handle_ids = []          # corner handle item IDs
        self._HANDLE_SIZE = 6          # handle square half-size in px
        
        # Default signature size in PDF points (matches signer.py minimum)
        self._default_sig_w = 180
        self._default_sig_h = 50
        
        # Placeholder text
        self.preview_canvas.create_text(
            0, 0, text="Select a PDF file to preview",
            fill="#555", font=("Roboto", 14), anchor="center", tags="placeholder"
        )
        # Reposition placeholder on resize
        self.preview_canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mouse events for drag-and-drop
        self.preview_canvas.bind("<ButtonPress-1>", self._on_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_release)

        # White background checkbox (visual mode only)
        self.chk_white_bg = ctk.CTkCheckBox(
            self.visual_mode_frame, 
            text="Paint white background before signing (clears area under signature)",
            font=("Roboto", 12), text_color=COLOR_TEXT_MAIN, 
            fg_color="#ffffff", hover_color="#e0e0e0",
            checkmark_color="#000000"
        )
        self.chk_white_bg.pack(anchor="w", pady=(5, 0))

        # Output Mode Selection
        self.output_mode = ctk.StringVar(value="merge")
        
        self.output_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.output_frame.pack(fill="x", pady=(8, 8))
        
        ctk.CTkLabel(self.output_frame, text="OUTPUT OPTIONS", font=("Roboto", 11, "bold"), text_color=COLOR_TEXT_SUB).pack(anchor="w", pady=(0, 5))
        
        self.rb_merge = ctk.CTkRadioButton(self.output_frame, text="Merge all files into 1 signed document", 
                                        variable=self.output_mode, value="merge",
                                        font=("Roboto", 12), text_color=COLOR_TEXT_MAIN, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER)
        self.rb_merge.pack(anchor="w", pady=(0, 5))
        
        self.rb_split = ctk.CTkRadioButton(self.output_frame, text="Store stamped files page by page (one page per PDF file)", 
                                        variable=self.output_mode, value="split",
                                        font=("Roboto", 12), text_color=COLOR_TEXT_MAIN, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER)
        self.rb_split.pack(anchor="w")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_area, progress_color=COLOR_ACCENT, height=12)
        self.progress_bar.pack(fill="x", pady=(10, 15))
        self.progress_bar.set(0)

        # Activity Log (main area) — stored as attribute so we can hide/show per mode
        self.activity_log_label = ctk.CTkLabel(self.main_area, text="ACTIVITY LOG", font=("Roboto", 11, "bold"), text_color=COLOR_TEXT_SUB)
        self.activity_log_label.pack(anchor="w", pady=(0, 5))
        self.console = StatusCard(self.main_area, height=120)
        self.console.pack(fill="both", expand=True, pady=(0, 8))
        self.console.log("Ready to sign documents.")

        # Action Bar
        self.action_bar = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.action_bar.pack(fill="x", pady=(8, 0))
        
        self.btn_process = PremiumButton(self.action_bar, text="Process & Sign Documents", 
                                       fg_color=COLOR_SUCCESS, hover_color="#059669", height=45,
                                       font=("Roboto", 14, "bold"),
                                       command=self.start_processing)
        self.btn_process.pack(fill="x")

    # ===== MODE SWITCHING =====
    
    def _on_mode_change(self, selected):
        """Switch between String Match and Visual Placement modes."""
        if "String" in selected:
            self.signing_mode.set("string_match")
            self.visual_mode_frame.pack_forget()
            self.string_match_frame.pack(fill="x", pady=(0, 5), before=self.output_frame)
            # Show activity log in string match mode
            self.activity_log_label.pack(anchor="w", pady=(0, 5), before=self.action_bar)
            self.console.pack(fill="both", expand=True, pady=(0, 8), before=self.action_bar)
        else:
            self.signing_mode.set("visual_placement")
            self.string_match_frame.pack_forget()
            # Hide activity log in visual mode to give preview maximum space
            self.activity_log_label.pack_forget()
            self.console.pack_forget()
            self.visual_mode_frame.pack(fill="both", expand=True, pady=(0, 5), before=self.output_frame)
            # Auto-load preview if files are already selected
            if self.file_paths:
                self._load_preview(self.file_paths[0])

    # ===== PDF PREVIEW RENDERING =====
    
    def _on_canvas_configure(self, event):
        """Reposition placeholder text on canvas resize."""
        self.preview_canvas.coords("placeholder", event.width // 2, event.height // 2)
        # Re-render preview if we have one loaded
        if self._preview_image and self.file_paths:
            self._load_preview(self.file_paths[0])
    
    def _load_preview(self, pdf_path):
        """Render first page of PDF onto the canvas at full width."""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            self._pdf_page_width = page.rect.width
            self._pdf_page_height = page.rect.height
            
            # Calculate scale to fit canvas WIDTH (page may extend beyond height — scrollable)
            canvas_w = self.preview_canvas.winfo_width()
            
            if canvas_w < 50:
                # Canvas not ready yet, schedule retry
                self.after(100, lambda: self._load_preview(pdf_path))
                doc.close()
                return
            
            # Scale to fill canvas width
            self._preview_scale = (canvas_w - 4) / self._pdf_page_width  # -4 for small margin
            
            # Render at the computed scale via PyMuPDF
            mat = fitz.Matrix(self._preview_scale, self._preview_scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            doc.close()
            
            # Convert to PIL Image → PhotoImage
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self._preview_image = ImageTk.PhotoImage(img)
            
            # Clear canvas and draw
            self.preview_canvas.delete("all")
            
            # Position image at top-left (centered horizontally)
            img_x = max(0, (canvas_w - pix.width) // 2)
            img_y = 0
            self._img_offset_x = img_x
            self._img_offset_y = img_y
            
            self.preview_canvas.create_image(img_x, img_y, image=self._preview_image, anchor="nw", tags="pdf_image")
            
            # Set scroll region to full rendered page height
            self.preview_canvas.configure(scrollregion=(0, 0, canvas_w, pix.height + 10))
            
            # Place default signature rectangle (bottom-right area)
            default_x = self._pdf_page_width - self._default_sig_w - 30
            default_y = self._pdf_page_height - self._default_sig_h - 60
            self._sig_rect_coords = (default_x, default_y, 
                                     default_x + self._default_sig_w, 
                                     default_y + self._default_sig_h)
            self._draw_sig_rect()
            
            self.console.log(f"📄 Preview loaded: {os.path.basename(pdf_path)} ({int(self._pdf_page_width)}×{int(self._pdf_page_height)} pts)")
            
        except Exception as e:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                self.preview_canvas.winfo_width() // 2,
                self.preview_canvas.winfo_height() // 2,
                text=f"Error loading preview:\n{e}",
                fill="#ff4444", font=("Roboto", 12), anchor="center"
            )
    
    def _draw_sig_rect(self):
        """Draw the signature rectangle and corner handles on the canvas."""
        if self._sig_rect_coords is None:
            return
        
        # Delete old rect and handles
        self.preview_canvas.delete("sig_rect")
        self.preview_canvas.delete("sig_handle")
        
        x0, y0, x1, y1 = self._sig_rect_coords
        
        # Convert PDF coords to canvas coords
        cx0 = self._img_offset_x + x0 * self._preview_scale
        cy0 = self._img_offset_y + y0 * self._preview_scale
        cx1 = self._img_offset_x + x1 * self._preview_scale
        cy1 = self._img_offset_y + y1 * self._preview_scale
        
        # Draw rectangle with stipple for semi-transparency (tkinter doesn't support alpha hex)
        self._sig_rect_id = self.preview_canvas.create_rectangle(
            cx0, cy0, cx1, cy1,
            outline="#10B981", width=2, fill="#1a3a2a", stipple="gray25",
            tags="sig_rect"
        )
        
        # Draw "Digital Signature" label inside
        mid_x = (cx0 + cx1) / 2
        mid_y = (cy0 + cy1) / 2
        self.preview_canvas.create_text(
            mid_x, mid_y, text="✍ Signature",
            fill="#10B981", font=("Roboto", 10, "bold"),
            tags="sig_rect"
        )
        
        # Corner handles for resizing
        hs = self._HANDLE_SIZE
        corners = [
            (cx0, cy0, "nw"), (cx1, cy0, "ne"),
            (cx0, cy1, "sw"), (cx1, cy1, "se")
        ]
        self._handle_ids = []
        for hx, hy, corner in corners:
            hid = self.preview_canvas.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill="#10B981", outline="#fff", width=1,
                tags=("sig_handle", f"handle_{corner}")
            )
            self._handle_ids.append((hid, corner))
        
        # Update coordinate label
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        self.lbl_coords.configure(text=f"Pos: ({int(x0)}, {int(y0)}) | Size: {int(w)}×{int(h)} pts")

    # ===== DRAG AND DROP =====
    
    def _on_press(self, event):
        """Handle mouse press on canvas."""
        if self._sig_rect_coords is None:
            return
        
        # Convert viewport coords to canvas coords (accounts for scroll)
        x = self.preview_canvas.canvasx(event.x)
        y = self.preview_canvas.canvasy(event.y)
        hs = self._HANDLE_SIZE + 2
        
        # Check if press is on a corner handle (resize)
        for hid, corner in self._handle_ids:
            coords = self.preview_canvas.coords(hid)
            if coords and coords[0] - hs <= x <= coords[2] + hs and coords[1] - hs <= y <= coords[3] + hs:
                self._drag_data = {"x": x, "y": y, "mode": f"resize_{corner}"}
                return
        
        # Check if press is inside the rectangle (move)
        x0, y0, x1, y1 = self._sig_rect_coords
        cx0 = self._img_offset_x + x0 * self._preview_scale
        cy0 = self._img_offset_y + y0 * self._preview_scale
        cx1 = self._img_offset_x + x1 * self._preview_scale
        cy1 = self._img_offset_y + y1 * self._preview_scale
        
        if cx0 <= x <= cx1 and cy0 <= y <= cy1:
            self._drag_data = {"x": x, "y": y, "mode": "move"}
            self.preview_canvas.configure(cursor="fleur")
            return
        
        self._drag_data = {"x": x, "y": y, "mode": None}
    
    def _on_drag(self, event):
        """Handle mouse drag on canvas."""
        mode = self._drag_data.get("mode")
        if mode is None or self._sig_rect_coords is None:
            return
        
        # Convert viewport coords to canvas coords (accounts for scroll)
        x = self.preview_canvas.canvasx(event.x)
        y = self.preview_canvas.canvasy(event.y)
        
        dx_canvas = x - self._drag_data["x"]
        dy_canvas = y - self._drag_data["y"]
        
        # Convert canvas delta to PDF delta
        dx_pdf = dx_canvas / self._preview_scale
        dy_pdf = dy_canvas / self._preview_scale
        
        x0, y0, x1, y1 = self._sig_rect_coords
        
        if mode == "move":
            # Move the entire rectangle
            new_x0 = x0 + dx_pdf
            new_y0 = y0 + dy_pdf
            new_x1 = x1 + dx_pdf
            new_y1 = y1 + dy_pdf
            
            # Clamp to page bounds
            if new_x0 < 0:
                new_x1 -= new_x0
                new_x0 = 0
            if new_y0 < 0:
                new_y1 -= new_y0
                new_y0 = 0
            if new_x1 > self._pdf_page_width:
                new_x0 -= (new_x1 - self._pdf_page_width)
                new_x1 = self._pdf_page_width
            if new_y1 > self._pdf_page_height:
                new_y0 -= (new_y1 - self._pdf_page_height)
                new_y1 = self._pdf_page_height
            
            self._sig_rect_coords = (new_x0, new_y0, new_x1, new_y1)
        
        elif mode.startswith("resize_"):
            corner = mode.split("_")[1]
            # Resize from the appropriate corner
            min_w = 80  # minimum width in PDF pts
            min_h = 30  # minimum height in PDF pts
            
            if corner == "se":
                x1 = max(x0 + min_w, x1 + dx_pdf)
                y1 = max(y0 + min_h, y1 + dy_pdf)
            elif corner == "sw":
                x0 = min(x1 - min_w, x0 + dx_pdf)
                y1 = max(y0 + min_h, y1 + dy_pdf)
            elif corner == "ne":
                x1 = max(x0 + min_w, x1 + dx_pdf)
                y0 = min(y1 - min_h, y0 + dy_pdf)
            elif corner == "nw":
                x0 = min(x1 - min_w, x0 + dx_pdf)
                y0 = min(y1 - min_h, y0 + dy_pdf)
            
            # Clamp to page
            x0 = max(0, x0)
            y0 = max(0, y0)
            x1 = min(self._pdf_page_width, x1)
            y1 = min(self._pdf_page_height, y1)
            
            self._sig_rect_coords = (x0, y0, x1, y1)
        
        self._drag_data["x"] = x
        self._drag_data["y"] = y
        self._draw_sig_rect()
    
    def _on_release(self, event):
        """Handle mouse release."""
        self._drag_data = {"x": 0, "y": 0, "mode": None}
        self.preview_canvas.configure(cursor="crosshair")

    def init_footer(self):
        self.footer = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="#050505")
        self.footer.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        self.lbl_footer = ctk.CTkLabel(self.footer, text="Made with <3 by Jarjish", text_color="#444", font=("Roboto", 11))
        self.lbl_footer.pack(pady=10)

    def _start_cert_scanner(self):
        """Start periodic certificate scanning for hot-plug USB token detection."""
        self._scan_certificates_periodic()
    
    def _scan_certificates_periodic(self):
        """Scan for certificates and update dropdown if changed. Runs every 5 seconds."""
        try:
            new_certs = self.signer_instance.scan_certificates()
            
            # Check if certificate list has changed
            if new_certs != self._last_cert_list:
                self._last_cert_list = new_certs.copy()
                current_selection = self.menu_cert.get()
                
                # Update BOTH dropdown options (string match + visual mode)
                if new_certs:
                    self.menu_cert.configure(values=new_certs)
                    self.menu_cert_vp.configure(values=new_certs)
                    self.cert_options = new_certs
                    
                    # If current selection is no longer valid, select first available
                    if current_selection not in new_certs:
                        self.menu_cert.set(new_certs[0])
                        self.menu_cert_vp.set(new_certs[0])
                        self.signer_instance.reset_session()
                        self.console.log(f"🔌 Token changed. Now using: {new_certs[0][:35]}...")
                else:
                    self.menu_cert.configure(values=["No certificates found"])
                    self.menu_cert.set("No certificates found")
                    self.menu_cert_vp.configure(values=["No certificates found"])
                    self.menu_cert_vp.set("No certificates found")
                    self.cert_options = []
                    self.console.log("⚠ No USB tokens detected")
        except Exception as e:
            print(f"Certificate scan error: {e}")
        
        # Schedule next scan in 5 seconds
        self.after(5000, self._scan_certificates_periodic)

    # --- Logic ---

    def select_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        if files:
            self.file_paths = list(files)
            self.update_file_list()
            self.console.log(f"📁 Added {len(files)} file(s) to queue.")
            # Auto-load preview if in visual placement mode
            if self.signing_mode.get() == "visual_placement":
                self._load_preview(self.file_paths[0])

    def update_file_list(self):
        """Update the file list display with remove buttons."""
        # Clear UI
        for widget in self.files_scroll.winfo_children():
            widget.destroy()
        
        for f in self.file_paths:
            # File Row
            row = ctk.CTkFrame(self.files_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            # Remove button
            remove_btn = ctk.CTkButton(row, text="✕", width=24, height=24, 
                                       fg_color="#333", hover_color="#ff4444",
                                       font=("Arial", 12), corner_radius=4,
                                       command=lambda fp=f: self.remove_file(fp))
            remove_btn.pack(side="left", padx=(5, 5))
            
            # File icon and name
            icon = ctk.CTkLabel(row, text="📄", font=("Arial", 14))
            icon.pack(side="left", padx=(0, 5))
            name = ctk.CTkLabel(row, text=os.path.basename(f), text_color=COLOR_TEXT_MAIN, font=("Roboto", 11))
            name.pack(side="left", fill="x")

    def remove_file(self, file_path):
        """Remove a file from the selection."""
        if file_path in self.file_paths:
            self.file_paths.remove(file_path)
            self.update_file_list()
            self.console.log(f"🗑 Removed: {os.path.basename(file_path)}")

    def on_cert_change(self, choice):
        # Reset the cached PKCS#11 session when certificate selection changes
        self.signer_instance.reset_session()
        # Sync both cert dropdowns
        try:
            self.menu_cert.set(choice)
            self.menu_cert_vp.set(choice)
        except Exception:
            pass
        self.console.log(f"🔄 Switched to: {choice[:40]}..." if len(choice) > 40 else f"🔄 Switched to: {choice}")
        
        if choice == "Select PKCS#11 DLL...":
            dll_path = filedialog.askopenfilename(filetypes=[("DLL Files", "*.dll"), ("All Files", "*.*")], title="Select PKCS#11 Driver DLL")
            if dll_path:
                self.signer_instance.dll_path = dll_path
                # Update text to show selected DLL
                filename = os.path.basename(dll_path)
                self.menu_cert.set(f"Token: {filename}")
                self.console.log(f"Selected Token Driver: {filename}")
            else:
                # User cancelled, revert to default or previous
                if self.cert_options:
                    self.menu_cert.set(self.cert_options[0])

    def start_processing(self):
        if not self.file_paths:
            self.show_toast("Error", "Please select at least one PDF file.", color="red")
            return
        
        mode = self.signing_mode.get()
        
        # Mode-specific validation
        match_text = None
        visual_rect = None
        
        if mode == "string_match":
            match_text = self.entry_match.get().strip()
            if not match_text:
                self.show_toast("Error", "Matching keyword is required.", color="red")
                return
        else:  # visual_placement
            if self._sig_rect_coords is None:
                self.show_toast("Error", "Please load a preview and place the signature rectangle.", color="red")
                return
            visual_rect = list(self._sig_rect_coords)  # (x0, y0, x1, y1) in PDF pts

        # Get cert from the active mode's dropdown
        cert_label = self.menu_cert.get() if mode == "string_match" else self.menu_cert_vp.get()
        out_mode = self.output_mode.get()
        is_merge = (out_mode == "merge")
        
        # Determine Output Destination
        if is_merge:
            # Save As File
            default_name = f"Signed_{os.path.basename(self.file_paths[0])}" if len(self.file_paths) == 1 else "Signed_Document_Batch.pdf"
            target_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")],
                                                   initialfile=default_name, title="Save Signed Document As")
        else:
            # Select Folder
            target_path = filedialog.askdirectory(title="Select Output Folder")
            
        if not target_path:
            return

        # Ask for PIN if using real certificate (not Mock)
        user_pin = None
        if "Mock" not in cert_label:
            # Show PIN dialog
            pin_dialog = ctk.CTkInputDialog(
                text="Enter your Token PIN:",
                title="Token Authentication"
            )
            user_pin = pin_dialog.get_input()
            
            if not user_pin:
                self.console.log("Signing cancelled - PIN not provided.")
                return
            
            self.console.log("PIN accepted. Starting signing process...")

        # UI Lock
        self.btn_process.configure(state="disabled", text="Processing...")
        
        # Get white background flag (only relevant in visual mode)
        white_bg = False
        if mode == "visual_placement":
            white_bg = bool(self.chk_white_bg.get())
        
        # Thread - pass mode-specific data
        threading.Thread(target=self.run_process, args=(match_text, cert_label, target_path, out_mode, user_pin, mode, visual_rect, white_bg)).start()

    def run_process(self, match_text, cert_label, target_path, out_mode, user_pin=None, mode="string_match", visual_rect=None, white_bg=False):
        try:
            total_signatures_applied = 0
            files_processed = 0
            is_merge = (out_mode == "merge")
            
            import tempfile
            sys_temp = tempfile.gettempdir()
            
            # List of (input_path, output_path)
            tasks = []
            
            if out_mode == "merge":
                import tempfile
                # MERGE MODE: Consolidate all inputs into one temp file, then sign that one.
                if len(self.file_paths) > 1:
                    self.after(0, lambda: self.console.log("Merging multiple files..."))
                    merged_temp = os.path.join(tempfile.gettempdir(), "temp_merged_pending.pdf")
                    pdf_processor.merge_pdfs(self.file_paths, merged_temp)
                    input_pdf = merged_temp
                else:
                    input_pdf = self.file_paths[0]
                    
                tasks.append((input_pdf, target_path))
                
            elif out_mode == "split":
                # SPLIT MODE: Separate every page of every input file into its own single-page PDF
                import tempfile
                self.after(0, lambda: self.console.log("Splitting documents into single pages..."))
                
                for f_path in self.file_paths:
                    base_name = os.path.basename(f_path)
                    name_no_ext = os.path.splitext(base_name)[0]
                    
                    doc = fitz.open(f_path)
                    num_pages = len(doc)
                    doc.close()
                    
                    for page_idx in range(num_pages):
                        # Open the document fresh for each page to avoid corrupting the base doc
                        single_page_doc = fitz.open(f_path)
                        
                        # Use select() to retain only this specific page, discarding the rest.
                        # This perfectly preserves AcroForm annotations and background graphics
                        # better than insert_pdf() which can strip resource dictionaries.
                        single_page_doc.select([page_idx])
                        
                        # temp path for this single page
                        temp_single = os.path.join(sys_temp, f"temp_split_{name_no_ext}_pg{page_idx+1}.pdf")
                        single_page_doc.save(temp_single)
                        single_page_doc.close()
                        
                        # output path
                        out_name = f"Signed_{name_no_ext}_Page_{page_idx+1}.pdf"
                        out_path = os.path.join(target_path, out_name)
                        
                        tasks.append((temp_single, out_path))
            else:
                # BATCH MODE: Treat each input separately
                for f_path in self.file_paths:
                    base_name = os.path.basename(f_path)
                    new_name = f"signed_{base_name}"
                    out_path = os.path.join(target_path, new_name)
                    tasks.append((f_path, out_path))
            
            # ===== STEP 1: White background pre-processing (before signing) =====
            if mode == "visual_placement" and white_bg and visual_rect:
                self.after(0, lambda: self.console.log("🖌 Painting white background on signature areas..."))
                whited_tasks = []
                import tempfile
                for i, (inp, out) in enumerate(tasks):
                    try:
                        doc = fitz.open(inp)
                        rect = fitz.Rect(visual_rect[0], visual_rect[1], visual_rect[2], visual_rect[3])
                        for page in doc:
                            page.draw_rect(rect, color=None, fill=(1, 1, 1))  # White fill, no border
                        
                        # Save whited version to temp file
                        whited_path = os.path.join(tempfile.gettempdir(), f"temp_whited_{i}.pdf")
                        num_whited_pages = len(doc)
                        doc.save(whited_path)
                        doc.close()
                        whited_tasks.append((whited_path, out))
                        self.after(0, lambda m=f"  ✅ Whited: {os.path.basename(inp)} ({num_whited_pages} pages)": self.console.log(m))
                    except Exception as e_white:
                        self.after(0, lambda m=f"  ⚠ White bg failed for {os.path.basename(inp)}: {e_white}": self.console.log(m))
                        whited_tasks.append((inp, out))  # Fallback to original
                
                tasks = whited_tasks  # Use whited files for signing
            
            # ===== STEP 2: Digital signing =====
            total_tasks = len(tasks)
            self.after(0, lambda: self.progress_bar.set(0))
            
            for i, (inp, out) in enumerate(tasks):
                self.after(0, lambda m=f"Processing ({i+1}/{total_tasks}): {os.path.basename(inp)}": self.console.log(m))
                
                # CRITICAL Fix for LTV Blue Ribbon on single pages/batch:
                # The _sig_counter dictates whether the PyHanko signer sets the 'Certify' 
                # (MDP) properties. If it's not 0 at the start of a new file, the new file
                # will just get a standard approval signature, missing the Adobe blue ribbon.
                self.signer_instance._sig_counter = 0
                
                if mode == "string_match":
                    # STRING MATCH: use analyzer to find locations
                    locations = analyzer.find_signing_locations(inp, match_text)
                    
                    if not locations:
                        self.after(0, lambda m=f"SKIPPED SIGNING: No valid space found in {os.path.basename(inp)}": self.console.log(m))
                        import shutil
                        shutil.copy(inp, out)
                        files_processed += 1
                        continue
                else:
                    # VISUAL PLACEMENT: apply user's rectangle to EVERY page
                    doc = fitz.open(inp)
                    num_pages = len(doc)
                    doc.close()
                    
                    locations = []
                    for pg in range(num_pages):
                        locations.append({
                            "page": pg,
                            "rect": visual_rect  # Same position on every page
                        })
                    
                    self.after(0, lambda m=f"  Visual mode: signing {num_pages} page(s) at ({int(visual_rect[0])}, {int(visual_rect[1])}) size {int(visual_rect[2]-visual_rect[0])}×{int(visual_rect[3]-visual_rect[1])}": self.console.log(m))
                
                # Sign iteratively for this file
                current_working_file = inp
                sigs_in_file = len(locations)

                # Pass total_sigs so the signer can decide whether certifying is safe.
                # certify=True (Blue Ribbon) is ONLY used when total_sigs==1 because
                # certifying then appending more signature fields causes Acrobat to
                # flag every subsequent sig as INVALID (MDP policy violation).
                #
                #   Split mode / 1 match   : total_sigs=1 → Blue Ribbon ✅
                #   Merged mode, N matches : total_sigs=N → all approval sigs, all valid ✅

                for idx, loc in enumerate(locations):
                    is_last_sig = (idx == sigs_in_file - 1)
                    step_out = out if is_last_sig else os.path.join(sys_temp, f"temp_sig_step_{i}_{idx}.pdf")

                    try:
                        self.signer_instance.sign_pdf(
                            current_working_file, step_out,
                            loc['page'], loc['rect'],
                            cert_label, user_pin,
                            is_first_signature=(idx == 0),
                            total_sigs=sigs_in_file,
                        )
                    except IndexError:
                        # PyHanko PageTree traversal bug on complex PDFs — flatten and retry
                        self.after(0, lambda: self.console.log("  ⚠ Complex PDF structure detected. Flattening to prevent IndexError..."))
                        flat_tmp = os.path.join(sys_temp, f"temp_flat_fallback_{i}_{idx}.pdf")
                        doc_flat = fitz.open(current_working_file)
                        doc_flat.save(flat_tmp)
                        doc_flat.close()
                        self.signer_instance.sign_pdf(
                            flat_tmp, step_out,
                            loc['page'], loc['rect'],
                            cert_label, user_pin,
                            is_first_signature=(idx == 0),
                            total_sigs=sigs_in_file,
                        )

                    current_working_file = step_out
                    
                    # Update progress bar
                    progress = (i + (idx + 1) / sigs_in_file) / total_tasks
                    self.after(0, lambda p=progress: self.progress_bar.set(p))
                    
                    total_signatures_applied += 1
                
                files_processed += 1
                self.after(0, lambda m=f"Completed: {os.path.basename(out)}": self.console.log(m))

            # ===== STEP 3: Final Summary =====

            # Final Summary
            self.after(0, lambda: self.progress_bar.set(1.0))
            if files_processed > 0:
                self.after(0, lambda: self.console.log(f"Done. Processed {files_processed} files with {total_signatures_applied} signatures."))
                self.after(0, lambda: self.show_toast("Success", f"Complete! {files_processed} docs signed.", color="green"))
                
                def show_success_msg():
                    messagebox.showinfo("Complete", f"Processed: {files_processed} Files\nTotal Signatures: {total_signatures_applied}\n\nSaved to: {target_path if not is_merge else os.path.dirname(target_path)}")
                self.after(0, show_success_msg)
                
                # Open directory
                open_dir = target_path if not is_merge else os.path.dirname(target_path)
                try: os.startfile(open_dir)
                except: pass
            else:
                self.after(0, lambda: self.console.log("Process finished but no files were signed (Check matching text/spacing)."))
                def show_warning_msg():
                    messagebox.showwarning("Finished", "No documents were signed.\nPlease check your 'Matching Text' and ensure there is empty space above it.")
                self.after(0, show_warning_msg)

        except Exception as e:
            self.after(0, lambda m=f"Error: {e}": self.console.log(m))
            self.after(0, lambda m=str(e): messagebox.showerror("Error", m))
        finally:
            # ===== STEP 4: Clean up ALL temp files =====
            # Guaranteed to run even if an exception occurs mid-process
            import glob
            for pattern in ["temp_merged_pending.pdf", "temp_sig_step_*.pdf", "temp_whited_*.pdf", "temp_split_*.pdf", "temp_flat_fallback_*.pdf"]:
                for tmp in glob.glob(os.path.join(sys_temp, pattern)):
                    try:
                        os.remove(tmp)
                    except Exception as e_rm:
                        print(f"Could not remove temp file {tmp}: {e_rm}")
                        
            # Re-enable UI
            self.after(0, lambda: self.btn_process.configure(state="normal", text="Process & Sign Documents"))

    def _logout(self):
        """Logout and return to login screen."""
        if messagebox.askyesno("🚪 Logout", "Are you sure you want to logout?"):
            self.logout_requested = True
            self.destroy()

    def show_toast(self, title, message, color="green"):
        # Simple print to console fallback for now as CustomTkinter Toasts require complex Frame overlays
        # Check console log
        self.console.log(f"[{title.upper()}] {message}")

if __name__ == "__main__":
    # Secure login check before launching main app
    from backend.login_dialog import show_login
    
    while True:
        success, username = show_login()
        if success:
            app = RDCApp(username=username)
            app.mainloop()
            # Check if logout was requested
            if not app.logout_requested:
                break  # Normal exit
            # Otherwise, loop back to login screen
        else:
            break  # User cancelled or failed authentication
    
    sys.exit(0)