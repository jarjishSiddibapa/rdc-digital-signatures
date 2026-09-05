import fitz

def find_signing_locations(pdf_path, matching_text, clearance_height=50):
    """
    Scans the PDF for the matching text.
    Returns a list of dicts: {'page': page_num, 'rect': (x0, y0, x1, y1)}
    ONLY IF there is empty space directly above the text.
    
    clearance_height: How much space (in points) above the text must be empty.
                      Increased to 50 to fit a standard signature block.
    """
    doc = fitz.open(pdf_path)
    locations = []
    
    for page_num, page in enumerate(doc):
        # search_for returns a list of Rect objects
        text_instances = page.search_for(matching_text)
        
        for rect in text_instances:
            # rect is match rectangle: (x0, y0, x1, y1)
            # Define the clearance area straight above matches
            # We want to check the area directly above the text
            
            # Check area:
            # x0 same, x1 same (width of the text)
            # y1 = rect.y0 (top of the text)
            # y0 = rect.y0 - clearance_height
            
            check_rect = fitz.Rect(rect.x0, rect.y0 - clearance_height, rect.x1, rect.y0)
            
            # If we go off page, it's not a valid placement (too close to top)
            if check_rect.y0 < 0:
                continue
                
            # Check for any content in this area.
            # "text" extraction with clip will return string if any text is there.
            text_in_clearance = page.get_text("text", clip=check_rect).strip()
            
            # Use 'blocks' to be more thorough about layout analysis if needed, 
            # but simple text check is usually good for "empty line".
            # We can also check for vector/drawings but standard text check is primary requirement.
            
            if not text_in_clearance:
                # It is empty!
                print(f"Found valid location on page {page_num+1}: {rect} - Space above is clean.")
                
                # We want to sign in the CLEARANCE area (Above the text), not ON the text.
                # So we return the check_rect coordinates as the target for the signature.
                # We might want to expand the width slightly if the keyword is short (like "CFO"), 
                # to fit the signature text.
                
                # Let's make the signature box at least 180 units wide (standard stamp width)
                sig_width = max(check_rect.width, 180)
                sig_height = clearance_height
                
                # CENTER horizontally relative to the text
                text_center_x = (rect.x0 + rect.x1) / 2
                sig_x0 = text_center_x - (sig_width / 2)
                sig_x1 = sig_x0 + sig_width
                
                # Ensure we don't go off page left border
                if sig_x0 < 0:
                     # If centering pushes it off-screen left, shift it right
                     diff = -sig_x0
                     sig_x0 += diff
                     sig_x1 += diff
                
                sig_y0 = rect.y0 - sig_height
                sig_y1 = rect.y0 - 2 # 2 pixels buffer above the text
                
                locations.append({
                    "page": page_num,
                    "rect": [sig_x0, sig_y0, sig_x1, sig_y1], # This is NOW the space ABOVE and CENTERED
                    "search_text": matching_text
                })
            else:
                print(f"Skipping location on page {page_num+1}: {rect} - Found text above: '{text_in_clearance}'")
                
    doc.close()
    return locations

def validate_pdf_content(pdf_path):
    """
    Sanity check that PDF is readable.
    """
    try:
        doc = fitz.open(pdf_path)
        return len(doc) > 0
    except:
        return False
