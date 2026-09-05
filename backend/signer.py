"""
RDC Digital Signer - Production Grade
======================================
Implements full cryptographic PDF signing using Windows PKCS#11 tokens.

The critical Adobe Acrobat rule this code enforces:
  - A certifying (MDP) signature LOCKS the document. Any further signature
    appended to a certified document is treated by Acrobat as a document
    modification that violates the MDP policy → marked INVALID.
  - Therefore: certify=True is ONLY safe when the document has ZERO existing
    signatures AND no more signatures will be added after this one.
  - For iterative multi-signature workflows (merged mode, N pages):
    ALL signatures must be approval (certify=False / omitted).
    They all show as valid green checkmarks — perfectly fine.

Caller contract (main.py run_process loop):
  # Merged mode — N signatures on the same PDF iteratively
  for idx, loc in enumerate(locations):
      signer.sign_pdf(..., is_first_signature=(idx == 0), total_sigs=len(locations))

  # Split mode — each call gets a fresh single-page PDF
  for loc in locations:
      signer.sign_pdf(..., is_first_signature=True, total_sigs=1)
"""

import os
import sys
import socket
import shutil
import subprocess

# PyHanko imports for cryptographic signing
from pyhanko.sign import signers, fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.fields import SigSeedSubFilter
from pyhanko.stamp import TextStampStyle
from pyhanko.pdf_utils.images import PdfImage

# PKCS#11 Support
PKCS11_AVAILABLE = False
PKCS11Signer = None
open_pkcs11_session = None
PROTECTED_AUTH = None
pkcs11_lib = None  # Raw pkcs11 library for slot detection

try:
    from pyhanko.sign.pkcs11 import PKCS11Signer as _PKCS11Signer
    from pyhanko.sign.pkcs11 import open_pkcs11_session as _open_pkcs11_session
    from pyhanko.sign.pkcs11 import PROTECTED_AUTH as _PROTECTED_AUTH
    PKCS11Signer = _PKCS11Signer
    open_pkcs11_session = _open_pkcs11_session
    PROTECTED_AUTH = _PROTECTED_AUTH
    PKCS11_AVAILABLE = True
    print("PKCS#11 support loaded successfully")
except ImportError as e:
    print(f"PKCS#11 support not available: {e}")

try:
    import pkcs11
    pkcs11_lib = pkcs11
    print("Low-level PKCS#11 slot detection available")
except ImportError:
    print("Low-level pkcs11 library not available for slot detection")

KNOWN_DLL_PATHS = [
    r"C:\Windows\System32\Watchdata\PROXKey CSP India V3.0\WDPKCS.dll",
    r"C:\Windows\System32\SignatureP11.dll",
    r"C:\Windows\SysWOW64\Watchdata\PROXKey CSP India V3.0\WDPKCS.dll",
    r"C:\Windows\SysWOW64\SignatureP11.dll",
]


def _pdf_has_existing_signatures(pdf_path: str) -> bool:
    """
    Return True if the PDF already contains any digital signature fields.
    Safety guard: we never certify a document that already has signatures.
    """
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc:
            for widget in (page.widgets() or []):
                if widget.field_type_string == "Sig":
                    doc.close()
                    return True
        doc.close()
    except Exception:
        pass
    return False


class DigitalSigner:
    """
    Production-grade Digital Signer using PKCS#11 hardware tokens.

    Public API
    ----------
    sign_pdf(pdf_path, output_path, page_num, rect,
             cert_label, user_pin, is_first_signature, total_sigs)

    is_first_signature : bool
        True  = no signatures exist in this PDF yet (first iteration).
        False = a signature was already written in a prior iteration.

    total_sigs : int
        Total signatures that will be written to this PDF.
        When > 1, certification (Blue Ribbon) is never used because
        certifying then adding more signature fields invalidates them all
        in Adobe Acrobat (MDP policy violation).
    """

    def __init__(self):
        self.dll_path = self._find_pkcs11_dll()
        self._pkcs11_signer = None
        self._sig_counter = 0
        self.log_callback = None

    def _log(self, message):
        print(message)
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception:
                pass

    def reset_session(self):
        """Discard cached PKCS#11 session. Call when switching tokens."""
        if self._pkcs11_signer is not None:
            print("Resetting PKCS#11 session cache (token change detected)")
            try:
                session = getattr(self._pkcs11_signer, 'pkcs11_session', None)
                if session:
                    session.close()
            except Exception:
                pass
            self._pkcs11_signer = None
        self._sig_counter = 0

    def _find_pkcs11_dll(self):
        for path in KNOWN_DLL_PATHS:
            if os.path.exists(path):
                print(f"Found PKCS#11 DLL: {path}")
                return path
        print("No PKCS#11 DLL found in known locations")
        return None

    def _find_token_slots(self):
        if pkcs11_lib is None or not self.dll_path:
            return [0]
        try:
            lib = pkcs11_lib.lib(self.dll_path)
            slots = lib.get_slots(token_present=True)
            if not slots:
                print("No tokens found.")
                return []
            count = len(slots)
            print(f"Found {count} token(s).")
            return list(range(count))
        except Exception as e:
            print(f"Slot detection error: {e}")
            return [0]

    def scan_certificates(self):
        """Enumerate certificates on all inserted PKCS#11 tokens."""
        certs = []

        if not self.dll_path or not pkcs11_lib:
            print("No PKCS#11 DLL or library available for scanning")
            return certs

        try:
            lib = pkcs11_lib.lib(self.dll_path)
            slots = lib.get_slots(token_present=True)

            for slot in slots:
                try:
                    token = slot.get_token()
                    if not token:
                        continue

                    token_label = (token.label or "Unknown").strip()
                    slot_id = token.slot.slot_id

                    try:
                        session = token.open(rw=False)

                        cert_objects = list(session.get_objects({
                            pkcs11_lib.Attribute.CLASS: pkcs11_lib.ObjectClass.CERTIFICATE
                        }))

                        if not cert_objects:
                            name = f"{token_label} (Slot {slot_id}) [PROXKey CSP India V3.0]"
                            if name not in certs:
                                certs.append(name)

                        for c_obj in cert_objects:
                            try:
                                cert_der = c_obj[pkcs11_lib.Attribute.VALUE]
                                try:
                                    from cryptography import x509
                                    from cryptography.hazmat.backends import default_backend
                                    cert = x509.load_der_x509_certificate(cert_der, default_backend())
                                    cn_attrs = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                                    cn = cn_attrs[0].value if cn_attrs else None
                                    display = f"{cn or token_label} (Slot {slot_id}) [PROXKey CSP India V3.0]"
                                except Exception:
                                    label = c_obj.get(pkcs11_lib.Attribute.LABEL, token_label)
                                    display = f"{label} (Slot {slot_id}) [PROXKey CSP India V3.0]"

                                if display not in certs:
                                    certs.append(display)
                            except Exception:
                                pass

                        session.close()

                    except Exception:
                        name = f"{token_label} (Slot {slot_id} - Locked) [PROXKey CSP India V3.0]"
                        if name not in certs:
                            certs.append(name)

                except Exception:
                    continue

        except Exception as e:
            print(f"Error scanning PKCS#11 tokens: {e}")
            certs = self._scan_certificates_fallback()

        if not certs:
            print("No tokens detected — ensure USB token is plugged in")

        return certs

    def _scan_certificates_fallback(self):
        certs = []
        try:
            result = subprocess.run(
                ["certutil", "-user", "-store", "My"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return certs

            for block in result.stdout.split('================'):
                if 'Subject:' not in block:
                    continue
                subject_cn = provider = None
                for line in block.splitlines():
                    line = line.strip()
                    if line.startswith('Subject:') and 'CN=' in line:
                        cn_start = line.find('CN=') + 3
                        cn_end = line.find(',', cn_start)
                        subject_cn = line[cn_start:(cn_end if cn_end != -1 else None)].strip()
                    if 'Provider =' in line:
                        provider = line.split('=', 1)[1].strip()
                if subject_cn and provider and 'Software' not in provider:
                    display = f"{subject_cn} [{provider}]"
                    if display not in certs:
                        certs.append(display)
        except Exception:
            pass
        return certs

    # ------------------------------------------------------------------
    # Public signing API
    # ------------------------------------------------------------------

    def sign_pdf(self, pdf_path, output_path, page_num, rect,
                 cert_label="Mock", user_pin=None,
                 is_first_signature=True, total_sigs=1):
        """
        Sign one page of a PDF and write the result to output_path.

        Parameters
        ----------
        pdf_path           : Input PDF (may already contain prior signatures).
        output_path        : Destination for signed output.
        page_num           : 0-based page index.
        rect               : (x0, y0, x1, y1) in top-left UI coordinates.
        cert_label         : Certificate name from scan_certificates().
                             Contains "Mock" → dry run (file just copied).
        user_pin           : PKCS#11 token PIN.
        is_first_signature : True if no signatures exist in this PDF yet.
        total_sigs         : Total signatures that will be written to this PDF.
        """
        self._log(f"📄 Signing page {page_num + 1}...")

        try:
            location = socket.gethostname()
        except Exception:
            location = "Unknown"
        reason = "I am the author of this document"

        if "Mock" in cert_label:
            self._log("  ⚠ Mock mode - no signature applied")
            shutil.copy(pdf_path, output_path)
        elif not self.dll_path or not PKCS11_AVAILABLE:
            raise RuntimeError("PKCS#11 not available. Cannot sign without hardware token.")
        else:
            self._apply_crypto_signature(
                pdf_path, output_path, page_num, rect,
                reason, location, cert_label, user_pin,
                is_first_signature=is_first_signature,
                total_sigs=total_sigs,
            )

        self._log(f"  ✓ Page {page_num + 1} signed successfully!")
        return output_path

    # ------------------------------------------------------------------
    # PKCS#11 session management
    # ------------------------------------------------------------------

    def _get_pkcs11_signer(self, user_pin=None, cert_label=None):
        """Return a cached (or newly created) PKCS11Signer."""
        if self._pkcs11_signer is not None:
            print("Reusing cached PKCS#11 session for batch signing")
            return self._pkcs11_signer

        print(f"Opening fresh PKCS#11 session: {self.dll_path}")
        available_slots = self._find_token_slots()
        print(f"Available slots: {available_slots}")

        # Resolve slot ID from cert_label → array index
        target_slot_index = None
        if cert_label and "(Slot " in cert_label:
            try:
                raw = cert_label.split("(Slot ")[1].split(")")[0]
                target_slot_id = int(raw.split(" - ")[0].strip())
                if pkcs11_lib and self.dll_path:
                    lib = pkcs11_lib.lib(self.dll_path)
                    for idx, slt in enumerate(lib.get_slots(token_present=True)):
                        if slt.slot_id == target_slot_id:
                            target_slot_index = idx
                            print(f"Mapped Slot ID {target_slot_id} -> Index {idx}")
                            break
            except Exception as e:
                print(f"Slot mapping error: {e}")

        signer_obj = None
        last_error = None

        for slot_no in available_slots:
            if target_slot_index is not None and slot_no != target_slot_index:
                continue

            try:
                print(f"Trying slot {slot_no}...")
                session = open_pkcs11_session(
                    self.dll_path, slot_no=slot_no, user_pin=user_pin
                )
                print(f"PKCS#11 session opened on slot {slot_no}")

                signing_cert_asn1 = None
                chosen_key_id = None

                if pkcs11_lib:
                    try:
                        from asn1crypto import x509 as asn1_x509
                        from cryptography import x509 as cx509
                        from cryptography.hazmat.backends import default_backend

                        cert_objects = list(session.get_objects({
                            pkcs11_lib.Attribute.CLASS: pkcs11_lib.ObjectClass.CERTIFICATE
                        }))

                        best_cert_der = None
                        best_date = None
                        for c_obj in cert_objects:
                            try:
                                c_der = c_obj[pkcs11_lib.Attribute.VALUE]
                                c_parsed = cx509.load_der_x509_certificate(c_der, default_backend())
                                expiry = (
                                    c_parsed.not_valid_after_utc
                                    if hasattr(c_parsed, 'not_valid_after_utc')
                                    else c_parsed.not_valid_after
                                )
                                if best_date is None or expiry > best_date:
                                    best_date = expiry
                                    best_cert_der = c_der
                            except Exception:
                                pass

                        if best_cert_der:
                            signing_cert_asn1 = asn1_x509.Certificate.load(best_cert_der)
                            print(f"Selected best certificate (expires {best_date})")

                        key_objects = list(session.get_objects({
                            pkcs11_lib.Attribute.CLASS: pkcs11_lib.ObjectClass.PRIVATE_KEY
                        }))
                        if key_objects:
                            chosen_key_id = key_objects[0][pkcs11_lib.Attribute.ID]

                    except Exception as e_scan:
                        print(f"Smart cert/key selection failed: {e_scan}")

                signer_obj = (
                    PKCS11Signer(
                        pkcs11_session=session,
                        signing_cert=signing_cert_asn1,
                        key_id=chosen_key_id,
                        embed_roots=True,
                    )
                    if signing_cert_asn1
                    else PKCS11Signer(pkcs11_session=session, embed_roots=True)
                )

                self._pkcs11_signer = signer_obj
                break

            except Exception as e:
                last_error = e
                err = str(e).lower()

                if 'alreadyloggedin' in err.replace(' ', '') or 'already logged in' in err:
                    try:
                        session = open_pkcs11_session(self.dll_path, slot_no=slot_no, user_pin=None)
                        signer_obj = PKCS11Signer(pkcs11_session=session, embed_roots=True)
                        self._pkcs11_signer = signer_obj
                        break
                    except Exception as e2:
                        last_error = e2
                        continue

                if 'pin' in err or 'authentication failed' in err:
                    raise RuntimeError("Incorrect PIN. Please check your token PIN and try again.")

                continue

        if signer_obj is None:
            raise RuntimeError(
                f"Could not connect to token: {last_error}"
                if last_error else "No available tokens found."
            )

        return signer_obj

    # ------------------------------------------------------------------
    # Core signing logic
    # ------------------------------------------------------------------

    def _apply_crypto_signature(self, input_path, output_path, page_num, rect,
                                reason, location, cert_label=None, user_pin=None,
                                is_first_signature=True, total_sigs=1):
        """
        Write a cryptographic signature into the PDF via pyHanko + PKCS#11.

        Certification decision (the key logic)
        ----------------------------------------
        certify=True  → Adobe Blue Ribbon (MDP / Certified Document)
        certify=False → Adobe Green Checkmark (Approval Signature)

        certify=True is ONLY used when ALL THREE conditions are satisfied:
          1. is_first_signature=True  (caller says no sigs written yet)
          2. total_sigs == 1          (no further sigs follow in this file)
          3. No existing sig fields detected in the PDF (fitz safety scan)

        Why condition 2 is critical:
          When certify=True is applied, pyHanko sets an MDP (Modification
          Detection and Prevention) policy in the PDF. Adobe then treats
          any subsequent modification — including adding more signature
          fields — as a policy violation and marks those sigs INVALID.
          This is exactly the "At least one signature is invalid" error
          seen on 285-page merged documents where page 1 was certified
          but pages 2-285 were approved afterward.

        Coordinate system:
          UI rect   (x0, y_top, x1, y_btm)  → top-left origin
          PDF box   (x0, y_btm_pdf, x1, y_top_pdf) → bottom-left origin
          pdf_y = page_height - ui_y
        """
        signer_obj = self._get_pkcs11_signer(user_pin, cert_label)

        import fitz
        with fitz.open(input_path) as fitz_doc:
            if page_num >= len(fitz_doc):
                raise IndexError(
                    f"Page {page_num} out of range (doc has {len(fitz_doc)} pages)"
                )
            page_height = fitz_doc[page_num].rect.height

        # Top-left → bottom-left coordinate conversion
        ui_x0, ui_y0, ui_x1, ui_y1 = rect
        pdf_box = (ui_x0, page_height - ui_y1, ui_x1, page_height - ui_y0)

        # ---------------------------------------------------------------
        # Certification safety check
        # ---------------------------------------------------------------
        already_signed = _pdf_has_existing_signatures(input_path)

        use_certify = (
            is_first_signature    # first sig in this iteration
            and total_sigs == 1   # ONLY sig in this file (no more follow)
            and not already_signed
        )

        if use_certify:
            self._log("  🔵 Certifying signature (Blue Ribbon)")
        elif total_sigs > 1:
            self._log(
                f"  ✅ Approval signature "
                f"({total_sigs} sigs in this file — certify disabled to keep all valid)"
            )
        elif already_signed:
            self._log("  ✅ Approval signature (document already signed)")
        else:
            self._log("  ✅ Approval signature")

        with open(input_path, 'rb') as inf:
            w = IncrementalPdfFileWriter(inf, strict=False)

            # Background image for the visible signature stamp
            bg_image = None
            try:
                base_path = (
                    sys._MEIPASS
                    if hasattr(sys, '_MEIPASS')
                    else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                bg_path = os.path.join(base_path, 'assets', 'signature_bg.png')
                if os.path.exists(bg_path):
                    bg_image = PdfImage(bg_path)
            except Exception:
                pass

            sig_style = TextStampStyle(
                background=bg_image,
                border_width=1,
                stamp_text='Digitally signed by %(signer)s\nDate: %(ts)s',
            )

            self._sig_counter += 1
            field_name = f'Signature_{self._sig_counter}'

            fields.append_signature_field(
                w,
                fields.SigFieldSpec(
                    sig_field_name=field_name,
                    box=pdf_box,
                    on_page=page_num,
                )
            )

            if use_certify:
                meta = signers.PdfSignatureMetadata(
                    field_name=field_name,
                    reason=reason,
                    location=location,
                    subfilter=SigSeedSubFilter.ADOBE_PKCS7_DETACHED,
                    certify=True,
                    md_algorithm='sha256',
                )
            else:
                meta = signers.PdfSignatureMetadata(
                    field_name=field_name,
                    reason=reason,
                    location=location,
                    subfilter=SigSeedSubFilter.ADOBE_PKCS7_DETACHED,
                    # certify intentionally omitted → defaults False
                )

            pdf_signer = signers.PdfSigner(meta, signer=signer_obj, stamp_style=sig_style)

            with open(output_path, 'wb') as outf:
                pdf_signer.sign_pdf(w, output=outf)


def test_signer():
    print("=" * 50)
    print("RDC Digital Signer - Test")
    print("=" * 50)
    s = DigitalSigner()
    print(f"\nDLL Path: {s.dll_path}")
    print(f"PKCS#11 Available: {PKCS11_AVAILABLE}")
    print("\nCertificates found:")
    for cert in s.scan_certificates():
        print(f"  - {cert}")
    print("=" * 50)


if __name__ == "__main__":
    test_signer()