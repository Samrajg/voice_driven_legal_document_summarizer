import os
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

def process_document(file_path):
    """
    Extracts text from a given file (PDF or Image).
    For MVP, uses PyMuPDF for PDFs (fast text extraction) and pytesseract for images.
    """
    ext = file_path.rsplit('.', 1)[1].lower()
    text = ""
    
    try:
        if ext == 'pdf':
            if fitz:
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text()
                doc.close()
            else:
                text = "PyMuPDF not installed."
        elif ext in ['png', 'jpg', 'jpeg']:
            if Image and pytesseract:
                text = pytesseract.image_to_string(Image.open(file_path))
            else:
                text = "Pillow or pytesseract not installed/configured properly."
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        text = f"Error processing document: {str(e)}"
        
    return text.strip()
