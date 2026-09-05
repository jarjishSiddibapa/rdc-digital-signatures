"""
RDC Digital Signatures - Login Dialog & Admin Panel
Secure login screen with admin/user detection and user management.
"""

import customtkinter as ctk
from tkinter import messagebox
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.auth import verify_credentials, add_user, delete_user, change_password, list_users, MIN_PASSWORD_LENGTH

# Color scheme - RDC Brand Color
COLOR_BG = "#121212"
COLOR_SIDEBAR = "#1e1e1e"
COLOR_ACCENT = "#00B51A"  # RDC Green
COLOR_ACCENT_HOVER = "#00991A"
COLOR_DANGER = "#dc3545"
COLOR_DANGER_HOVER = "#c82333"
COLOR_TEXT = "#ffffff"
COLOR_INPUT_BG = "#2d2d2d"
COLOR_INPUT_BORDER = "#3d3d3d"


class AdminPanel(ctk.CTkToplevel):
    """Admin Panel for user management."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        # Password visibility state
        self.new_pass_visible = False
        self.confirm_pass_visible = False
        self.change_pass_visible = False
        
        self.title("👑 RDC Admin Panel - User Management")
        self.geometry("900x700")
        self.resizable(True, True)
        self.minsize(850, 650)
        self.configure(fg_color=COLOR_BG)
        
        # Center the window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (450)
        y = (self.winfo_screenheight() // 2) - (350)
        self.geometry(f'900x700+{x}+{y}')
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
        self._refresh_user_list()
    
    def _create_ui(self):
        """Create the admin panel UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, height=60)
        header.pack(fill="x", padx=15, pady=(15, 10))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header,
            text="👑 Admin Panel - User Management",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_ACCENT
        )
        title.pack(side="left", padx=15, pady=15)
        
        # Logout button in header
        logout_btn = ctk.CTkButton(
            header,
            text="🚪 Logout",
            width=100,
            height=35,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.destroy
        )
        logout_btn.pack(side="right", padx=15, pady=12)
        
        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Left panel - Add User (scrollable)
        left_container = ctk.CTkFrame(content, fg_color=COLOR_SIDEBAR, corner_radius=12)
        left_container.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        # Make interior scrollable
        left_panel = ctk.CTkScrollableFrame(left_container, fg_color="transparent")
        left_panel.pack(fill="both", expand=True, padx=5, pady=5)
        
        add_title = ctk.CTkLabel(
            left_panel,
            text="➕ Add New User",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT
        )
        add_title.pack(pady=(10, 10))
        
        # Username input
        ctk.CTkLabel(left_panel, text="👤 Username", text_color="#aaa").pack(anchor="w", padx=15)
        self.new_username = ctk.CTkEntry(
            left_panel,
            height=38,
            placeholder_text="Enter username",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER
        )
        self.new_username.pack(fill="x", padx=15, pady=(5, 10))
        
        # Password input with eye button
        ctk.CTkLabel(left_panel, text="🔑 Password", text_color="#aaa").pack(anchor="w", padx=15)
        pw_frame1 = ctk.CTkFrame(left_panel, fg_color="transparent")
        pw_frame1.pack(fill="x", padx=15, pady=(5, 10))
        self.new_password = ctk.CTkEntry(
            pw_frame1,
            height=38,
            placeholder_text=f"Min {MIN_PASSWORD_LENGTH} characters",
            show="•",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER
        )
        self.new_password.pack(side="left", fill="x", expand=True)
        self.btn_eye1 = ctk.CTkButton(
            pw_frame1, text="👁️", width=38, height=38,
            fg_color=COLOR_INPUT_BG, hover_color="#3d3d3d",
            anchor="center",
            command=lambda: self._toggle_pass(1)
        )
        self.btn_eye1.pack(side="right", padx=(5, 0))
        
        # Confirm password with eye button
        ctk.CTkLabel(left_panel, text="🔑 Confirm Password", text_color="#aaa").pack(anchor="w", padx=15)
        pw_frame2 = ctk.CTkFrame(left_panel, fg_color="transparent")
        pw_frame2.pack(fill="x", padx=15, pady=(5, 10))
        self.confirm_password = ctk.CTkEntry(
            pw_frame2,
            height=38,
            placeholder_text="Confirm password",
            show="•",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER
        )
        self.confirm_password.pack(side="left", fill="x", expand=True)
        self.btn_eye2 = ctk.CTkButton(
            pw_frame2, text="👁️", width=38, height=38,
            fg_color=COLOR_INPUT_BG, hover_color="#3d3d3d",
            anchor="center",
            command=lambda: self._toggle_pass(2)
        )
        self.btn_eye2.pack(side="right", padx=(5, 0))
        
        # Add button
        add_btn = ctk.CTkButton(
            left_panel,
            text="➕ Create User",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._add_user
        )
        add_btn.pack(fill="x", padx=15, pady=(5, 15))
        
        # Divider
        ctk.CTkFrame(left_panel, height=2, fg_color="#444").pack(fill="x", padx=15, pady=10)
        
        # Change password section
        ctk.CTkLabel(
            left_panel,
            text="🔄 Change User Password",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(pady=(5, 10))
        
        # Username dropdown instead of text entry
        ctk.CTkLabel(left_panel, text="Select User", text_color="#aaa").pack(anchor="w", padx=15)
        user_list = [u['username'] for u in list_users()]
        if not user_list:
            user_list = ["No users yet"]
        self.change_username = ctk.CTkOptionMenu(
            left_panel,
            height=38,
            values=user_list,
            fg_color=COLOR_INPUT_BG,
            button_color="#444",
            button_hover_color="#555"
        )
        self.change_username.pack(fill="x", padx=15, pady=(5, 10))
        
        ctk.CTkLabel(left_panel, text="New Password", text_color="#aaa").pack(anchor="w", padx=15)
        pw_frame3 = ctk.CTkFrame(left_panel, fg_color="transparent")
        pw_frame3.pack(fill="x", padx=15, pady=(5, 10))
        self.change_new_password = ctk.CTkEntry(
            pw_frame3,
            height=38,
            placeholder_text=f"Min {MIN_PASSWORD_LENGTH} characters",
            show="•",
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER
        )
        self.change_new_password.pack(side="left", fill="x", expand=True)
        self.btn_eye3 = ctk.CTkButton(
            pw_frame3, text="👁️", width=38, height=38,
            fg_color=COLOR_INPUT_BG, hover_color="#3d3d3d",
            anchor="center",
            command=lambda: self._toggle_pass(3)
        )
        self.btn_eye3.pack(side="right", padx=(5, 0))
        
        change_btn = ctk.CTkButton(
            left_panel,
            text="🔄 Change Password",
            height=40,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self._change_password
        )
        change_btn.pack(fill="x", padx=15, pady=(10, 15))
        
        # Right panel - User List
        right_panel = ctk.CTkFrame(content, fg_color=COLOR_SIDEBAR, corner_radius=12)
        right_panel.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        list_title = ctk.CTkLabel(
            right_panel,
            text="👥 Existing Users",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT
        )
        list_title.pack(pady=(15, 10))
        
        # User list scrollable frame
        self.user_list_frame = ctk.CTkScrollableFrame(
            right_panel,
            fg_color=COLOR_INPUT_BG,
            corner_radius=8
        )
        self.user_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            right_panel,
            text="🔄 Refresh List",
            height=40,
            fg_color="#666",
            hover_color="#555",
            command=self._refresh_user_list
        )
        refresh_btn.pack(fill="x", padx=15, pady=(0, 15))
    
    def _toggle_pass(self, field_num):
        """Toggle password visibility for a specific field."""
        if field_num == 1:
            self.new_pass_visible = not self.new_pass_visible
            self.new_password.configure(show="" if self.new_pass_visible else "•")
            self.btn_eye1.configure(text="🙈" if self.new_pass_visible else "👁️")
        elif field_num == 2:
            self.confirm_pass_visible = not self.confirm_pass_visible
            self.confirm_password.configure(show="" if self.confirm_pass_visible else "•")
            self.btn_eye2.configure(text="🙈" if self.confirm_pass_visible else "👁️")
        elif field_num == 3:
            self.change_pass_visible = not self.change_pass_visible
            self.change_new_password.configure(show="" if self.change_pass_visible else "•")
            self.btn_eye3.configure(text="🙈" if self.change_pass_visible else "👁️")
    
    def _refresh_user_list(self):
        """Refresh the user list display."""
        # Clear existing
        for widget in self.user_list_frame.winfo_children():
            widget.destroy()
        
        users = list_users()
        
        if not users:
            no_users = ctk.CTkLabel(
                self.user_list_frame,
                text="No users created yet",
                text_color="#666"
            )
            no_users.pack(pady=20)
            return
        
        for user in users:
            user_row = ctk.CTkFrame(self.user_list_frame, fg_color="#333", corner_radius=8)
            user_row.pack(fill="x", pady=3, padx=5)
            
            # User info
            status = "✅" if user['is_active'] else "❌"
            info = ctk.CTkLabel(
                user_row,
                text=f"{status} {user['username']}",
                font=ctk.CTkFont(size=13),
                text_color=COLOR_TEXT if user['is_active'] else "#888"
            )
            info.pack(side="left", padx=10, pady=8)
            
            # Delete button (centered emoji)
            del_btn = ctk.CTkButton(
                user_row,
                text="🗑️",
                width=35,
                height=30,
                anchor="center",
                fg_color=COLOR_DANGER,
                hover_color=COLOR_DANGER_HOVER,
                command=lambda u=user['username']: self._delete_user(u)
            )
            del_btn.pack(side="right", padx=5, pady=5)
        
        # Refresh the dropdown after updating user list
        self._refresh_dropdown()
    
    def _refresh_dropdown(self):
        """Refresh the username dropdown with current users."""
        user_list = [u['username'] for u in list_users()]
        if not user_list:
            user_list = ["No users yet"]
        self.change_username.configure(values=user_list)
        if user_list and user_list[0] != "No users yet":
            self.change_username.set(user_list[0])
    
    def _add_user(self):
        """Add a new user."""
        username = self.new_username.get().strip()
        password = self.new_password.get()
        confirm = self.confirm_password.get()
        
        if not username:
            messagebox.showerror("❌ Error", "Username cannot be empty")
            return
        
        if password != confirm:
            messagebox.showerror("❌ Error", "Passwords do not match")
            return
        
        success, msg = add_user(username, password)
        
        if success:
            messagebox.showinfo("✅ Success", msg)
            self.new_username.delete(0, 'end')
            self.new_password.delete(0, 'end')
            self.confirm_password.delete(0, 'end')
            self._refresh_user_list()
        else:
            messagebox.showerror("❌ Error", msg)
    
    def _delete_user(self, username):
        """Delete a user."""
        if messagebox.askyesno("⚠️ Confirm Delete", f"Delete user '{username}'?\n\nThis cannot be undone."):
            success, msg = delete_user(username)
            if success:
                messagebox.showinfo("✅ Success", msg)
                self._refresh_user_list()
            else:
                messagebox.showerror("❌ Error", msg)
    
    def _change_password(self):
        """Change a user's password."""
        username = self.change_username.get()  # Dropdown doesn't need strip
        new_password = self.change_new_password.get()
        
        if not username or username == "No users yet":
            messagebox.showerror("❌ Error", "Select a user first")
            return
        
        success, msg = change_password(username, new_password)
        
        if success:
            messagebox.showinfo("✅ Success", msg)
            self.change_new_password.delete(0, 'end')
        else:
            messagebox.showerror("❌ Error", msg)


class LoginDialog(ctk.CTk):
    """Secure login dialog for RDC Digital Signatures."""
    
    def __init__(self):
        super().__init__()
        
        self.authenticated = False
        self.is_admin = False
        self.username = None
        self.password_visible = False
        
        # Window Setup
        self.title("🔐 RDC Digital Signatures - Login")
        self.geometry("480x520")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        
        # Center the window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # Set Window Icon
        try:
            icon_path = self._resource_path(os.path.join("assets", "icon.ico"))
            self.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Bind Enter key
        self.bind('<Return>', lambda e: self.login())
        
        # Bind Caps Lock check
        self.bind('<KeyPress>', self._check_caps_lock)
        self.bind('<KeyRelease>', self._check_caps_lock)
        
        self._create_ui()
    
    def _resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller."""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    
    def _check_caps_lock(self, event=None):
        """Check and update Caps Lock indicator."""
        try:
            import ctypes
            caps_lock_on = ctypes.windll.user32.GetKeyState(0x14) & 0xFFFF != 0
            if caps_lock_on:
                self.caps_label.configure(text="⚠️ CAPS LOCK IS ON", text_color="#FFA500")
            else:
                self.caps_label.configure(text="")
        except:
            pass
    
    def _toggle_password_visibility(self):
        """Toggle password visibility."""
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.password_entry.configure(show="")
            self.eye_btn.configure(text="🙈")
        else:
            self.password_entry.configure(show="•")
            self.eye_btn.configure(text="👁️")
    
    def _create_ui(self):
        """Create the login UI."""
        # Main container
        container = ctk.CTkFrame(self, fg_color=COLOR_SIDEBAR, corner_radius=20)
        container.pack(fill="both", expand=True, padx=25, pady=25)
        
        # Logo/Title area
        title_frame = ctk.CTkFrame(container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(25, 15))
        
        title = ctk.CTkLabel(
            title_frame,
            text="🏢 RDC",
            font=ctk.CTkFont(family="Segoe UI", size=48, weight="bold"),
            text_color=COLOR_ACCENT
        )
        title.pack()
        
        subtitle = ctk.CTkLabel(
            title_frame,
            # text="✍️ Digital Signatures",
            text="✍️ Digital Signatures Fixing Utility",
            font=ctk.CTkFont(family="Segoe UI", size=20),
            text_color=COLOR_ACCENT
        )
        subtitle.pack()
        
        # Login form
        form_frame = ctk.CTkFrame(container, fg_color="transparent")
        form_frame.pack(fill="x", padx=35, pady=15)
        
        # Username
        username_label = ctk.CTkLabel(
            form_frame,
            text="👤 Username",
            font=ctk.CTkFont(size=13),
            text_color="#aaaaaa"
        )
        username_label.pack(anchor="w", pady=(10, 5))
        
        self.username_entry = ctk.CTkEntry(
            form_frame,
            height=45,
            placeholder_text="Enter your username",
            font=ctk.CTkFont(size=14),
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            border_width=1,
            corner_radius=8
        )
        self.username_entry.pack(fill="x", pady=(0, 15))
        
        # Password
        password_label = ctk.CTkLabel(
            form_frame,
            text="🔑 Password",
            font=ctk.CTkFont(size=13),
            text_color="#aaaaaa"
        )
        password_label.pack(anchor="w", pady=(5, 5))
        
        # Password input with eye button
        password_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        password_frame.pack(fill="x", pady=(0, 5))
        
        self.password_entry = ctk.CTkEntry(
            password_frame,
            height=45,
            placeholder_text="Enter your password",
            show="•",
            font=ctk.CTkFont(size=14),
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_INPUT_BORDER,
            border_width=1,
            corner_radius=8
        )
        self.password_entry.pack(side="left", fill="x", expand=True)
        
        self.eye_btn = ctk.CTkButton(
            password_frame,
            text="👁️",
            width=45,
            height=45,
            font=ctk.CTkFont(size=18),
            fg_color=COLOR_INPUT_BG,
            hover_color="#3d3d3d",
            border_color=COLOR_INPUT_BORDER,
            border_width=1,
            corner_radius=8,
            command=self._toggle_password_visibility
        )
        self.eye_btn.pack(side="right", padx=(8, 0))
        
        # Caps Lock indicator
        self.caps_label = ctk.CTkLabel(
            form_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#FFA500"
        )
        self.caps_label.pack(anchor="w", pady=(5, 10))
        
        # Login button
        login_btn = ctk.CTkButton(
            form_frame,
            text="🚀 Login",
            height=50,
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            corner_radius=10,
            command=self.login
        )
        login_btn.pack(fill="x", pady=(15, 10))
        
        # Footer
        footer = ctk.CTkLabel(
            container,
            text="🔒 Secure Authentication Required",
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        )
        footer.pack(side="bottom", pady=15)
        
        # Focus on username
        self.username_entry.focus()
        
        # Initial caps lock check
        self._check_caps_lock()
    
    def login(self):
        """Attempt to login with provided credentials."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("❌ Error", "Please enter both username and password.")
            return
        
        # Verify credentials
        success, is_admin = verify_credentials(username, password)
        
        if success:
            self.authenticated = True
            self.is_admin = is_admin
            self.username = username
            
            if is_admin:
                # Show admin panel
                self.withdraw()  # Hide login window
                admin_panel = AdminPanel(self)
                self.wait_window(admin_panel)
                # After admin panel closes, show login again
                self.deiconify()
                self.username_entry.delete(0, 'end')
                self.password_entry.delete(0, 'end')
                self.authenticated = False
                self.is_admin = False
            else:
                # Regular user - close login and proceed to main app
                self.destroy()
        else:
            messagebox.showerror("🚫 Access Denied", "Invalid username or password.")
            self.password_entry.delete(0, 'end')
            self.password_entry.focus()


def show_login() -> tuple:
    """
    Show the login dialog.
    Returns (authenticated: bool, username: str or None).
    """
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    
    dialog = LoginDialog()
    dialog.mainloop()
    
    if dialog.authenticated and not dialog.is_admin:
        return (True, dialog.username)
    return (False, None)


if __name__ == '__main__':
    # Test the login dialog
    result = show_login()
    print(f"Login result: {result}")
