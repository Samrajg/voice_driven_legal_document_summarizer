import os
import io
from flask import Blueprint, request, jsonify, current_app, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

generator_bp = Blueprint('generator', __name__)

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates_docs')

def load_template(doc_type):
    file_path = os.path.join(TEMPLATES_DIR, f"{doc_type}.txt")
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def generate_document_text(doc_type, data):
    template = load_template(doc_type)
    if not template:
        return None
    
    # Use python string formatting. We fill missing keys with empty strings to avoid KeyError
    from collections import defaultdict
    safe_data = defaultdict(str, data)
    try:
        filled_text = template.format_map(safe_data)
        return filled_text
    except Exception as e:
        print("Error formatting document:", e)
        return None

def create_pdf(text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER)
    body_style = styles['Normal']
    
    Story = []
    
    lines = text.split('\n')
    # Treat the very first non-empty line as title if we want, or just let text dictate it
    first_line = True
    for line in lines:
        if line.strip() == '':
            Story.append(Spacer(1, 12))
        else:
            # Let's make all uppercase lines bold titles for simplicity
            if line.isupper() and len(line) > 3:
                Story.append(Paragraph(line, title_style))
                Story.append(Spacer(1, 12))
            else:
                Story.append(Paragraph(line, body_style))
                
    doc.build(Story)
    buffer.seek(0)
    return buffer

@generator_bp.route('/generate-document', methods=['POST'])
def generate_document_api():
    data = request.get_json()
    doc_type = data.get('type')
    if not doc_type:
        return jsonify({'message': 'Document type is required'}), 400
        
    doc_text = generate_document_text(doc_type, data)
    if not doc_text:
        return jsonify({'message': 'Template not found or error in generation'}), 404
        
    return jsonify({'document': doc_text}), 200

@generator_bp.route('/download-pdf', methods=['POST'])
def download_pdf_api():
    data = request.get_json()
    doc_type = data.get('type')
    if not doc_type:
        return jsonify({'message': 'Document type is required'}), 400
        
    doc_text = generate_document_text(doc_type, data)
    if not doc_text:
        return jsonify({'message': 'Template not found or error in generation'}), 404
        
    pdf_buffer = create_pdf(doc_text)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{doc_type}_document.pdf",
        mimetype='application/pdf'
    )
