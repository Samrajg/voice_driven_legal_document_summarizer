import os
import uuid
import pandas as pd
import pickle
import re
import nltk
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from ..models import db, User, Document, AnalysisResult
from ..middlewares import check_tier_limits

from ..services.ocr_service import process_document
from ..services.nlp_service import analyze_text, get_answer, transcribe_audio_file
from ..services.translation_service import translate_analysis
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.metrics.pairwise import cosine_similarity

# ------------------ NLTK DOWNLOAD ------------------
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')

vectorizer = None
law_vectors = None
df = None

try:
    with open(os.path.join(MODELS_DIR, "tfidf_vectorizer.pkl"), "rb") as f:
        vectorizer = pickle.load(f)
    with open(os.path.join(MODELS_DIR, "law_vectors.pkl"), "rb") as f:
        law_vectors = pickle.load(f)
    df = pd.read_pickle(os.path.join(MODELS_DIR, "ipc_dataframe.pkl"))
except Exception as e:
    print("Warning: Could not load Law Bot models:", e)

def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z ]', '', text)
    tokens = text.split()
    stop_words = set(stopwords.words('english'))
    tokens = [t for t in tokens if t not in stop_words]
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(t) for t in tokens]
    return " ".join(tokens)

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

@documents_bp.route('/law-bot', methods=['POST'])
@jwt_required()
def law_bot():
    if vectorizer is None or law_vectors is None or df is None:
        return jsonify({'message': 'Law Bot models are not loaded on the server.'}), 500

    data = request.get_json()
    crime_text = data.get('crime_text', '')

    if not crime_text.strip():
        return jsonify({'message': 'Please enter a valid crime description.'}), 400

    processed = preprocess(crime_text)
    user_vector = vectorizer.transform([processed])
    similarity = cosine_similarity(user_vector, law_vectors)[0]
    top_indices = similarity.argsort()[-3:][::-1]

    results = []
    for idx in top_indices:
        results.append({
            'section': df.iloc[idx]['Section'],
            'description': df.iloc[idx]['Description'],
            'confidence': round(similarity[idx], 2)
        })

    return jsonify({'results': results}), 200
