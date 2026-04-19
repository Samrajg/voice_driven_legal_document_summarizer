from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from .models import User

def check_tier_limits(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        if user.tier == 'free' and user.documents_processed >= 5:
            return jsonify({
                'message': 'Free tier limit reached. Please upgrade to premium to process more documents.'
            }), 403
            
        return f(*args, **kwargs)
    return decorated_function
