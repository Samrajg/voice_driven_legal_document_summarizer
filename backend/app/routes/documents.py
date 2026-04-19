import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from ..models import db, User, Document, AnalysisResult
from ..middlewares import check_tier_limits

from ..services.ocr_service import process_document
from ..services.nlp_service import analyze_text, get_answer, transcribe_audio_file
from ..services.translation_service import translate_analysis

documents_bp = Blueprint('documents', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@documents_bp.route('/upload', methods=['POST'])
@jwt_required()
@check_tier_limits
def upload_document():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Save file securely
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Create database entry
        new_doc = Document(
            filename=filename,
            original_path=file_path,
            user_id=current_user_id,
            status='processing'
        )
        db.session.add(new_doc)
        
        # Increment user usage
        user.documents_processed += 1
        db.session.commit()
        
        # Process document
        extracted_text = process_document(file_path)
        
        command = request.form.get('command', '')
        audio_file = request.files.get('audio_cmd')
        
        if audio_file:
            audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename('audio_' + str(new_doc.id) + '.wav'))
            audio_file.save(audio_path)
            transcribed = transcribe_audio_file(audio_path)
            if transcribed:
                command = transcribed
        
        # Analyze text
        analysis_data = analyze_text(extracted_text, command)
        
        # Create result
        result = AnalysisResult(
            document_id=new_doc.id,
            extracted_text=extracted_text,
            summary=analysis_data.get('summary')
        )
        new_doc.status = 'completed'
        db.session.add(result)
        db.session.commit()
        
        return jsonify({
            'message': 'File processed successfully',
            'document_id': new_doc.id
        }), 201

    return jsonify({'message': 'File type not allowed'}), 400

@documents_bp.route('/<int:doc_id>', methods=['GET'])
@jwt_required()
def get_document(doc_id):
    current_user_id = get_jwt_identity()
    doc = Document.query.filter_by(id=doc_id, user_id=current_user_id).first()
    
    if not doc:
        return jsonify({'message': 'Document not found'}), 404
        
    result = doc.analysis_result
    
    # Check for translation request
    target_lang = request.args.get('lang', 'en')
    if target_lang != 'en' and result:
         result = translate_analysis(result, target_lang)
        
    return jsonify({
        'id': doc.id,
        'filename': doc.filename,
        'status': doc.status,
        'created_at': doc.created_at.isoformat(),
        'analysis': {
            'extracted_text': result.extracted_text if result else None,
            'summary': result.summary if result else None,
            'entities': result.entities_json if result else None,
            'risks': result.risks_json if result else None,
            'simplified': result.simplified_clauses_json if result else None
        }
    }), 200

@documents_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    current_user_id = get_jwt_identity()
    docs = Document.query.filter_by(user_id=current_user_id).order_by(Document.created_at.desc()).all()
    
    return jsonify([{
        'id': d.id,
        'filename': d.filename,
        'status': d.status,
        'created_at': d.created_at.isoformat()
    } for d in docs]), 200

@documents_bp.route('/<int:doc_id>/qa', methods=['POST'])
@jwt_required()
def document_qa(doc_id):
    current_user_id = get_jwt_identity()
    doc = Document.query.filter_by(id=doc_id, user_id=current_user_id).first()
    
    if not doc or not doc.analysis_result:
        return jsonify({'message': 'Document not ready or not found'}), 404
        
    data = request.get_json()
    question = data.get('question', '')
    if not question:
        return jsonify({'message': 'No question provided'}), 400
        
    answer = get_answer(question, doc.analysis_result.extracted_text)
    
    return jsonify({'answer': answer}), 200
