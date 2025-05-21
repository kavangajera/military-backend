import logging
import jwt
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from zoneinfo import ZoneInfo
from middlewares.auth import token_required

login_bp = Blueprint('login', __name__)

# Initialize OAuth
oauth = OAuth()

# Maintain a blacklist of invalidated tokens (you might want to use Redis in production)
token_blacklist = set()

# Your personal email - ONLY this email will be allowed to log in
AUTHORIZED_EMAIL = os.getenv('AUTHORIZED_EMAIL')  # Set this in your .env file

def setup_google_oauth(app):
    """
    Configure Google OAuth with the Flask app
    Call this function from app.py after creating the app
    """
    oauth.init_app(app)
    
    # Google OAuth config
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

@login_bp.route('/login/google')
def login_google():
    """
    Initiate Google OAuth2 authentication flow
    """
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI') 
    return oauth.google.authorize_redirect(redirect_uri)

@login_bp.route('/login/google/callback')
def google_auth_callback():
    """
    Handle Google OAuth2 callback
    Only allow login for the authorized email
    """
    try:
        # Complete the OAuth flow
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token, nonce=session.get("nonce"))
        
        # Get user info
        email = user_info.get('email')
        name = user_info.get('name')
        
        # Check if this is the authorized user
        if email != AUTHORIZED_EMAIL:
            return jsonify({
                'message': 'Access denied. You are not authorized to access this application.'
            }), 403
        
        # Create payload for JWT
        secret_key = current_app.config['SECRET_KEY']
        payload = {
            'name': name,
            'email': email,
            'role': 'admin',  # Since you're the only user, you're the admin
            'exp': datetime.now(tz=ZoneInfo('UTC')) + timedelta(days=1)  # Token expires in 1 day
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        # User data to return
        user_data = {
            'name': name,
            'email': email,
            'role': 'admin'
        }
        
        # Redirect to your frontend with the token
        redirect_url = f"https://mtm-store.com/auth-callback?token={token}&user={json.dumps(user_data)}"
        return redirect(redirect_url)
        
    except Exception as e:
        logging.error(f"Google authentication error: {str(e)}")
        return jsonify({
            'message': 'Google authentication failed',
            'error_details': str(e)
        }), 500



# Optional: Add a logout route
@login_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Invalidate the current token by adding it to the blacklist
    """
    token = request.headers['Authorization'].split(' ')[1]
    token_blacklist.add(token)
    return jsonify({'message': 'Successfully logged out'}), 200