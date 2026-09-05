
import os
import sys
import pkcs11
from pkcs11 import Attribute, ObjectClass

# Auto-detect DLL (Using same logic as signer.py)
SYSTEM_DRIVE = os.environ.get('SystemDrive', 'C:')
POSSIBLE_DLLS = [
    r"Windows\System32\WDPKCS.dll",
    r"Windows\SysWOW64\WDPKCS.dll",
    r"Windows\System32\SignatureP11.dll", 
    r"Windows\SysWOW64\SignatureP11.dll",
    r"Program Files\WatchData\ProxKey\WDPKCS.dll",
]

def find_dll():
    for dll in POSSIBLE_DLLS:
        full_path = os.path.join(SYSTEM_DRIVE + '\\', dll)
        if os.path.exists(full_path):
            return full_path
    
    # Try searching
    try:
        import glob
        search_paths = [
            f"{SYSTEM_DRIVE}\\Windows\\System32\\*pkcs*.dll",
            f"{SYSTEM_DRIVE}\\Windows\\SysWOW64\\*pkcs*.dll"
        ]
        for pattern in search_paths:
            found = glob.glob(pattern)
            if found: return found[0]
    except: pass
    return None

def main():
    dll_path = find_dll()
    if not dll_path:
        print("Error: PKCS#11 DLL not found.")
        return

    print(f"Using DLL: {dll_path}")
    lib = pkcs11.lib(dll_path)
    
    slots = lib.get_slots(token_present=True)
    if not slots:
        print("No token slots found.")
        return

    slot = slots[0]
    print(f"Using Slot: {slot}")

    pin = input("Enter Token PIN: ")
    
    try:
        with slot.open(user_pin=pin, rw=True) as session:
            print("\n=== Certificates ===")
            for obj in session.get_objects({Attribute.CLASS: ObjectClass.CERTIFICATE}):
                label = obj.get(Attribute.LABEL, b'<No Label>').decode('utf-8', 'ignore')
                print(f"Label: {label}")
                # ID?
                id_val = obj.get(Attribute.ID, b'')
                print(f"  ID: {id_val.hex()}")
            
            print("\n=== Private Keys ===")
            for obj in session.get_objects({Attribute.CLASS: ObjectClass.PRIVATE_KEY}):
                label = obj.get(Attribute.LABEL, b'<No Label>').decode('utf-8', 'ignore')
                print(f"Label: {label}")
                id_val = obj.get(Attribute.ID, b'')
                print(f"  ID: {id_val.hex()}")
                
    except Exception as e:
        print(f"Error accessing token: {e}")

if __name__ == "__main__":
    main()
