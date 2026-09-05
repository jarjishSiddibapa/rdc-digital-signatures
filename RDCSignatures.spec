# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for RDC Digital Signatures
# COMPREHENSIVE BUILD - Every import audited line by line from ALL source files
# Source files: main.py, backend/signer.py, backend/analyzer.py,
#              backend/pdf_processor.py, backend/auth.py, backend/login_dialog.py
# Last updated: 2026-02-10

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('backend', 'backend'),  # auth.py, login_dialog.py, signer.py, analyzer.py, pdf_processor.py
        ('assets', 'assets'),    # icon.ico, logo.png, signature_bg.png
        # NOTE: users.db is created at runtime by auth.py - NOT bundled
    ],
    hiddenimports=[
        # =====================================================================
        # MAIN.PY IMPORTS (line 1-11)
        # =====================================================================
        'customtkinter',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
        'tkinter.font',
        'threading',
        'os',
        'sys',
        'time',

        # =====================================================================
        # SIGNER.PY IMPORTS (line 1-42)
        # =====================================================================
        'socket',
        'shutil',
        'subprocess',

        # --- PyHanko core ---
        'pyhanko',
        'pyhanko.sign',
        'pyhanko.sign.signers',
        'pyhanko.sign.signers.pdf_signer',
        'pyhanko.sign.signers.pdf_cms',
        'pyhanko.sign.signers.cms_embedder',
        'pyhanko.sign.signers.functions',
        'pyhanko.sign.fields',
        'pyhanko.sign.pkcs11',
        'pyhanko.sign.general',
        'pyhanko.sign.timestamps',
        'pyhanko.sign.validation',
        'pyhanko.sign.diff_analysis',
        'pyhanko.pdf_utils',
        'pyhanko.pdf_utils.incremental_writer',
        'pyhanko.pdf_utils.reader',
        'pyhanko.pdf_utils.writer',
        'pyhanko.pdf_utils.misc',
        'pyhanko.pdf_utils.generic',
        'pyhanko.pdf_utils.content',
        'pyhanko.pdf_utils.images',
        'pyhanko.pdf_utils.filters',
        'pyhanko.pdf_utils.crypt',
        'pyhanko.pdf_utils.font',
        'pyhanko.pdf_utils.font.api',
        'pyhanko.pdf_utils.font.opentype',
        'pyhanko.pdf_utils.layout',
        'pyhanko.stamp',

        # --- PyHanko cert validator ---
        'pyhanko_certvalidator',
        'pyhanko_certvalidator.errors',
        'pyhanko_certvalidator.validate',
        'pyhanko_certvalidator.context',
        'pyhanko_certvalidator.path',
        'pyhanko_certvalidator.registry',
        'pyhanko_certvalidator.authority_key_identifier',

        # --- PKCS#11 (python-pkcs11) ---
        'pkcs11',
        'pkcs11._pkcs11',
        'pkcs11.types',
        'pkcs11.mechanisms',
        'pkcs11.constants',
        'pkcs11.attributes',
        'pkcs11.exceptions',
        'pkcs11.defaults',
        'pkcs11.util',
        'pkcs11.util.rsa',
        'pkcs11.util.ec',
        'pkcs11.util.dsa',
        'pkcs11.util.dh',
        'pkcs11.util.x509',

        # --- ASN.1 crypto (used directly in signer.py for cert bypass) ---
        'asn1crypto',
        'asn1crypto.core',
        'asn1crypto.cms',
        'asn1crypto.pdf',
        'asn1crypto.x509',
        'asn1crypto.keys',
        'asn1crypto.algos',
        'asn1crypto.ocsp',
        'asn1crypto.crl',
        'asn1crypto.tsp',
        'asn1crypto.pem',
        'asn1crypto.util',
        'asn1crypto.parser',

        # --- Cryptography (used in signer.py for cert DER parsing) ---
        'cryptography',
        'cryptography.x509',
        'cryptography.x509.oid',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.asymmetric',
        'cryptography.hazmat.primitives.asymmetric.rsa',
        'cryptography.hazmat.primitives.asymmetric.ec',
        'cryptography.hazmat.primitives.asymmetric.padding',
        'cryptography.hazmat.primitives.serialization',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',

        # --- oscrypto ---
        'oscrypto',
        'oscrypto._openssl',
        'oscrypto._win',
        'oscrypto.asymmetric',
        'oscrypto.keys',
        'oscrypto.trust_list',
        'oscrypto.tls',

        # =====================================================================
        # ANALYZER.PY & PDF_PROCESSOR.PY IMPORTS
        # =====================================================================
        'fitz',
        'pymupdf',

        # =====================================================================
        # AUTH.PY IMPORTS (line 7-11)
        # =====================================================================
        'sqlite3',
        'hashlib',
        'secrets',
        'base64',

        # =====================================================================
        # LOGIN_DIALOG.PY IMPORTS (line 6-9, line 16)
        # =====================================================================
        'ctypes',  # Caps lock detection

        # =====================================================================
        # PIL/PILLOW (used by customtkinter for image loading)
        # =====================================================================
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL._tkinter_finder',

        # =====================================================================
        # TRANSITIVE / SUPPORT DEPENDENCIES
        # =====================================================================
        'certifi',
        'cffi',
        '_cffi_backend',
        'lxml',
        'lxml.etree',
        'xml.etree.ElementTree',
        'yaml',
        'ruamel.yaml',
        'requests',
        'urllib3',
        'tzlocal',
        'barcode',
        'barcode.codex',
        'barcode.ean',
        'qrcode',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RDCSignatures',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI only - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RDCSignatures',
)
