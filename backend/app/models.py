from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    tier = db.Column(db.String(20), default='free') # 'free' or 'premium'
    documents_processed = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    documents = db.relationship('Document', backref='user', lazy=True)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_path = db.Column(db.String(512), nullable=False) # Should be securely stored and deleted later
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending') # pending, processing, completed, error
    
    analysis_result = db.relationship('AnalysisResult', backref='document', uselist=False, lazy=True)

class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    
    # Storing JSON outputs
    extracted_text = db.Column(db.Text, nullable=True) # Full text
    entities_json = db.Column(db.JSON, nullable=True) # JSON of parties, dates, etc
    risks_json = db.Column(db.JSON, nullable=True) # Array of identified risks
    summary = db.Column(db.Text, nullable=True) # Plain text summary
    simplified_clauses_json = db.Column(db.JSON, nullable=True) # Mapping of complex -> simple
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
