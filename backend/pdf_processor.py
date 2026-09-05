import fitz  # PyMuPDF
import os

def merge_pdfs(pdf_list, output_path):
    """
    Merge a list of PDF file paths into a single PDF.

    FIX: save() is called with garbage=3 and deflate=True.

    Why this matters for digital signatures:
    - fitz.insert_pdf() copies pages but can leave duplicate/orphaned
      objects in the cross-reference (xref) table — dead entries that
      still occupy object IDs.
    - Without garbage=3, the saved PDF has an xref table with gaps and
      inconsistent offsets. pyHanko's IncrementalPdfFileWriter parses
      this xref to know where every object lives so it can compute the
      /ByteRange for the signature hash. If pyHanko and Adobe Reader
      parse the xref differently (Adobe is stricter), the byte ranges
      don't match → Adobe flags the signature as INVALID.
    - garbage=3: removes all unreachable/duplicate objects AND compacts
      the xref so every object offset is correct and unambiguous.
    - deflate=True: compresses streams, which is standard and ensures
      Adobe doesn't trip over uncompressed stream lengths during validation.
    - Together these produce a clean, self-consistent PDF that both
      pyHanko and Adobe agree on — making all incremental signature
      revisions validate correctly.
    """
    result = fitz.open()
    for pdf_path in pdf_list:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")
        
        with fitz.open(pdf_path) as mfile:
            result.insert_pdf(mfile)
            
    result.save(output_path, garbage=3, deflate=True)
    result.close()
    return output_path

def get_pdf_info(pdf_path):
    """
    Returns basic info about the PDF (page count).
    """
    doc = fitz.open(pdf_path)
    info = {"pages": len(doc)}
    doc.close()
    return info