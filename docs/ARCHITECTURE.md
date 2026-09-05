# Architecture

## Components

- `main.py` owns the desktop lifecycle, file queue, PDF preview, placement controls, progress reporting, and orchestration.
- `backend/analyzer.py` locates matching text and accepts a placement only when the required area above it is clear.
- `backend/pdf_processor.py` merges documents and rewrites cross-reference structures before signing.
- `backend/signer.py` discovers PKCS#11 libraries and tokens, selects certificates, and delegates incremental signing to pyHanko.
- `backend/auth.py` stores regular users in a per-user SQLite database with salted PBKDF2 hashes. The optional administrator secret comes from the process environment.

## Data flow

The interface receives local file paths and placement instructions. PDF pages are previewed and analyzed locally. At signing time, the application opens a PKCS#11 session, asks the hardware token to perform the private-key operation, and writes a new signed PDF. The private key remains on the token.

## PDF integrity

Multiple source PDFs are merged with PyMuPDF using garbage collection and stream compression. This removes unreachable or duplicate objects and produces a consistent cross-reference table before pyHanko appends signature revisions. Each signature is added incrementally so earlier signed bytes remain covered by their original digest.

## Local state

The installed application is read-only under Program Files. Per-user state is placed under `%LOCALAPPDATA%\RDCSignatures`, including the user database and signed-output directory. No document, database, PIN, key, or certificate is part of the repository.

## Security boundaries

- Token PINs are requested at signing time and are not persisted.
- The administrator password must be supplied through `RDC_SIGNATURES_ADMIN_PASSWORD`; an unset value disables master-administrator login.
- Regular-user passwords are salted and hashed before SQLite storage.
- Document content never needs a network service for the signing workflow.
- Public tests create synthetic PDFs at runtime and delete them afterward.
