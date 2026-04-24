import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .models import db
from .config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    CORS(app)
    db.init_app(app)
    jwt = JWTManager(app)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.documents import documents_bp
    from .routes.generator import generator_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(generator_bp, url_prefix='/api/generator')

    # Create tables
    with app.app_context():
        db.create_all()

    return app
