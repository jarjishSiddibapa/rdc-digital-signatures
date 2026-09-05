"""
RDC Digital Signatures - User Management Script
Run this script to manage users from the command line.

Usage:
    python set_credentials.py

This uses the SQLite database for user management.
The optional master administrator is configured through environment variables.
"""

import sys
import os
import getpass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.auth import (
    add_user, 
    delete_user, 
    change_password, 
    list_users, 
    verify_credentials,
    MIN_PASSWORD_LENGTH
)


def main():
    print("=" * 50)
    print("RDC Digital Signatures - User Manager")
    print("=" * 50)
    print()
    print("Master Admin: configure RDC_SIGNATURES_ADMIN_PASSWORD when needed")
    print()
    print("Options:")
    print("  1. Add new user")
    print("  2. Delete user")
    print("  3. Change user password")
    print("  4. List all users")
    print("  5. Test login")
    print("  0. Exit")
    print()
    
    while True:
        choice = input("Enter option (0-5): ").strip()
        
        if choice == "0":
            print("Goodbye!")
            break
            
        elif choice == "1":
            # Add user
            print("\n--- Add New User ---")
            username = input("Enter username: ").strip()
            if not username:
                print("Error: Username cannot be empty.")
                continue
            
            try:
                password = getpass.getpass(f"Password (min {MIN_PASSWORD_LENGTH} chars): ")
                confirm = getpass.getpass("Confirm password: ")
            except Exception:
                password = input(f"Password (min {MIN_PASSWORD_LENGTH} chars): ").strip()
                confirm = input("Confirm password: ").strip()
            
            if password != confirm:
                print("Error: Passwords do not match.")
                continue
            
            success, msg = add_user(username, password)
            print(f"{'✓' if success else '✗'} {msg}")
            
        elif choice == "2":
            # Delete user
            print("\n--- Delete User ---")
            users = list_users()
            if not users:
                print("No users to delete.")
                continue
            print("Available users:", ", ".join(u['username'] for u in users))
            username = input("Enter username to delete: ").strip()
            
            confirm = input(f"Are you sure you want to delete '{username}'? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("Cancelled.")
                continue
            
            success, msg = delete_user(username)
            print(f"{'✓' if success else '✗'} {msg}")
            
        elif choice == "3":
            # Change password
            print("\n--- Change Password ---")
            users = list_users()
            if not users:
                print("No users to modify.")
                continue
            print("Available users:", ", ".join(u['username'] for u in users))
            username = input("Enter username: ").strip()
            
            try:
                new_password = getpass.getpass(f"New password (min {MIN_PASSWORD_LENGTH} chars): ")
            except Exception:
                new_password = input(f"New password (min {MIN_PASSWORD_LENGTH} chars): ").strip()
            
            success, msg = change_password(username, new_password)
            print(f"{'✓' if success else '✗'} {msg}")
            
        elif choice == "4":
            # List users
            print("\n--- User List ---")
            users = list_users()
            if not users:
                print("No users in database.")
            else:
                for u in users:
                    status = "Active" if u['is_active'] else "Inactive"
                    print(f"  • {u['username']} ({status}) - Created: {u['created_at']}")
                    
        elif choice == "5":
            # Test login
            print("\n--- Test Login ---")
            username = input("Username: ").strip()
            try:
                password = getpass.getpass("Password: ")
            except Exception:
                password = input("Password: ").strip()
            
            success, is_admin = verify_credentials(username, password)
            if success:
                role = "Admin" if is_admin else "User"
                print(f"✓ Login successful! Role: {role}")
            else:
                print("✗ Invalid credentials.")
        
        else:
            print("Invalid option. Please enter 0-5.")
        
        print()


if __name__ == '__main__':
    main()

