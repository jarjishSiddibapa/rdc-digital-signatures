"""
RDC Digital Signatures - Secure Authentication Module
Supports master admin account and SQLite-based user management.
Uses PBKDF2-SHA256 for secure password hashing.
"""

import os
import sqlite3
import hashlib
import secrets
import base64
from datetime import datetime

# Database file path - stored in per-user AppData so it's always writable,
# even when the app is installed for all users under Program Files.
_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
_db_dir = os.path.join(_app_data, "RDCSignatures")
os.makedirs(_db_dir, exist_ok=True)
DB_PATH = os.path.join(_db_dir, "users.db")

# Master admin identity. The optional password is supplied at runtime and is
# never embedded in source code or the packaged executable.
ADMIN_USERNAME = os.getenv("RDC_SIGNATURES_ADMIN_USERNAME", "admin").strip().lower()

# Minimum password length
MIN_PASSWORD_LENGTH = 8


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a secure key from password using PBKDF2."""
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)


def _hash_password(password: str) -> str:
    """Hash a password with a random salt using PBKDF2-SHA256."""
    salt = secrets.token_bytes(32)
    key = _derive_key(password, salt)
    # Store salt + hash together, base64 encoded
    combined = salt + key
    return base64.b64encode(combined).decode('utf-8')


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        combined = base64.b64decode(stored_hash.encode('utf-8'))
        salt = combined[:32]
        stored_key = combined[32:]
        key = _derive_key(password, salt)
        return secrets.compare_digest(key, stored_key)
    except Exception:
        return False


def _init_database():
    """Initialize the SQLite database with users table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()


def is_admin(username: str, password: str) -> bool:
    """Check the optional environment-configured administrator account."""
    configured_password = os.getenv("RDC_SIGNATURES_ADMIN_PASSWORD", "")
    return (
        bool(configured_password)
        and username.strip().lower() == ADMIN_USERNAME
        and secrets.compare_digest(password, configured_password)
    )

def verify_user(username: str, password: str) -> bool:
    """Verify user credentials against SQLite database."""
    _init_database()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT password_hash FROM users WHERE username = ? AND is_active = 1',
            (username,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result is None:
            return False
        
        return _verify_password(password, result[0])
    except Exception as e:
        print(f"Error verifying user: {e}")
        return False


def verify_credentials(username: str, password: str) -> tuple:
    """
    Verify credentials and return (success, is_admin).
    Returns (True, True) for admin, (True, False) for regular user, (False, False) for failure.
    """
    # Check admin first
    if is_admin(username, password):
        return (True, True)
    
    # Check regular users
    if verify_user(username, password):
        return (True, False)
    
    return (False, False)


def add_user(username: str, password: str) -> tuple:
    """
    Add a new user to the database.
    Returns (success: bool, message: str).
    """
    # Validation
    if not username or len(username.strip()) < 1:
        return (False, "Username cannot be empty")
    
    username = username.strip().lower()
    
    if username == ADMIN_USERNAME:
        return (False, "Cannot create user with admin username")
    
    if len(password) < MIN_PASSWORD_LENGTH:
        return (False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    
    _init_database()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return (False, f"User '{username}' already exists")
        
        # Hash password and insert
        password_hash = _hash_password(password)
        cursor.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        conn.commit()
        conn.close()
        return (True, f"User '{username}' created successfully")
    except Exception as e:
        return (False, f"Error creating user: {e}")


def delete_user(username: str) -> tuple:
    """
    Delete a user from the database.
    Returns (success: bool, message: str).
    """
    username = username.strip().lower()
    
    if username == ADMIN_USERNAME:
        return (False, "Cannot delete admin account")
    
    _init_database()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        if cursor.rowcount == 0:
            conn.close()
            return (False, f"User '{username}' not found")
        
        conn.commit()
        conn.close()
        return (True, f"User '{username}' deleted successfully")
    except Exception as e:
        return (False, f"Error deleting user: {e}")


def change_password(username: str, new_password: str) -> tuple:
    """
    Change a user's password.
    Returns (success: bool, message: str).
    """
    username = username.strip().lower()
    
    if username == ADMIN_USERNAME:
        return (False, "Cannot change admin password")
    
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return (False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    
    _init_database()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = _hash_password(new_password)
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE username = ?',
            (password_hash, username)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return (False, f"User '{username}' not found")
        
        conn.commit()
        conn.close()
        return (True, f"Password changed for '{username}'")
    except Exception as e:
        return (False, f"Error changing password: {e}")


def list_users() -> list:
    """
    List all users in the database.
    Returns list of dicts: [{'id': int, 'username': str, 'created_at': str, 'is_active': bool}]
    """
    _init_database()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at, is_active FROM users ORDER BY username')
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'username': row[1],
                'created_at': row[2],
                'is_active': bool(row[3])
            }
            for row in rows
        ]
    except Exception as e:
        print(f"Error listing users: {e}")
        return []


def toggle_user_active(username: str) -> tuple:
    """
    Toggle user active status.
    Returns (success: bool, message: str).
    """
    username = username.strip().lower()
    
    _init_database()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE users SET is_active = NOT is_active WHERE username = ?',
            (username,)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return (False, f"User '{username}' not found")
        
        conn.commit()
        conn.close()
        return (True, f"User '{username}' status toggled")
    except Exception as e:
        return (False, f"Error toggling user status: {e}")


# Initialize database on module load
_init_database()

