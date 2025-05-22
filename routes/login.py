# import logging
# import jwt
# import os
# import json
# from datetime import datetime, timedelta
# from flask import Blueprint, request, jsonify, current_app, redirect, url_for, session
# from authlib.integrations.flask_client import OAuth
# from zoneinfo import ZoneInfo
# from middlewares.auth import token_required
# from google.oauth2 import id_token
# from google.auth.transport import requests as google_requests

# login_bp = Blueprint('login', __name__)

# # Initialize OAuth
# oauth = OAuth()

# # Maintain a blacklist of invalidated tokens (you might want to use Redis in production)
# token_blacklist = set()

# # Your personal email - ONLY this email will be allowed to log in
# AUTHORIZED_EMAIL = os.getenv('AUTHORIZED_EMAIL')  # Set this in your .env file

# def setup_google_oauth(app):
#     """
#     Configure Google OAuth with the Flask app
#     Call this function from app.py after creating the app
#     """
#     oauth.init_app(app)
    
#     # Google OAuth config
#     oauth.register(
#         name='google',
#         client_id=app.config['GOOGLE_CLIENT_ID'],
#         client_secret=app.config['GOOGLE_CLIENT_SECRET'],
#         server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
#         client_kwargs={
#             'scope': 'openid email profile'
#         }
#     )

# @login_bp.route('/login/google', methods=['GET', 'POST'])
# def login_google():
#     """
#     Handle both OAuth redirect and direct credential verification
#     """
#     if request.method == 'POST':
#         # Handle direct credential from frontend (Google Identity Services)
#         try:
#             data = request.get_json()
#             credential = data.get('credential')
            
#             if not credential:
#                 return jsonify({'error': 'No credential provided'}), 400
            
#             # Verify the credential with Google
#             try:
#                 # Verify the token
#                 idinfo = id_token.verify_oauth2_token(
#                     credential, 
#                     google_requests.Request(), 
#                     os.getenv('GOOGLE_CLIENT_ID')
#                 )
                
#                 # Get user info
#                 email = idinfo.get('email')
#                 name = idinfo.get('name')
                
#                 # Check if this is the authorized user
#                 if email != AUTHORIZED_EMAIL:
#                     return jsonify({
#                         'error': 'Access denied. You are not authorized to access this application.'
#                     }), 403
                
#                 # Create JWT token
#                 secret_key = current_app.config['SECRET_KEY']
#                 payload = {
#                     'name': name,
#                     'email': email,
#                     'role': 'admin',  # Since you're the only user, you're the admin
#                     'exp': datetime.now(tz=ZoneInfo('UTC')) + timedelta(days=1)  # Token expires in 1 day
#                 }
#                 token = jwt.encode(payload, secret_key, algorithm='HS256')
                
#                 # User data to return
#                 user_data = {
#                     'name': name,
#                     'email': email,
#                     'role': 'admin'
#                 }
                
#                 return jsonify({
#                     'token': token,
#                     'user': user_data,
#                     'message': 'Authentication successful'
#                 }), 200
                
#             except ValueError as e:
#                 # Invalid token
#                 logging.error(f"Invalid Google token: {str(e)}")
#                 return jsonify({'error': 'Invalid Google token'}), 400
                
#         except Exception as e:
#             logging.error(f"Google authentication error: {str(e)}")
#             return jsonify({
#                 'error': 'Authentication failed',
#                 'details': str(e)
#             }), 500
    
#     else:
#         # Handle OAuth redirect (fallback method)
#         redirect_uri = os.getenv('GOOGLE_REDIRECT_URI') 
#         return oauth.google.authorize_redirect(redirect_uri)

# @login_bp.route('/login/google/callback')
# def google_auth_callback():
#     """
#     Handle Google OAuth2 callback (fallback method)
#     Only allow login for the authorized email
#     """
#     try:
#         # Complete the OAuth flow
#         token = oauth.google.authorize_access_token()
#         user_info = oauth.google.parse_id_token(token, nonce=session.get("nonce"))
        
#         # Get user info
#         email = user_info.get('email')
#         name = user_info.get('name')
        
#         # Check if this is the authorized user
#         if email != AUTHORIZED_EMAIL:
#             return jsonify({
#                 'message': 'Access denied. You are not authorized to access this application.'
#             }), 403
        
#         # Create payload for JWT
#         secret_key = current_app.config['SECRET_KEY']
#         payload = {
#             'name': name,
#             'email': email,
#             'role': 'admin',  # Since you're the only user, you're the admin
#             'exp': datetime.now(tz=ZoneInfo('UTC')) + timedelta(days=1)  # Token expires in 1 day
#         }
#         jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
        
#         # Redirect to your frontend with the token
#         # You might want to pass this via a secure method instead of URL params
#         redirect_url = f"https://radiance-of-warriors.vercel.app/armory?token={jwt_token}"
#         return redirect(redirect_url)
        
#     except Exception as e:
#         logging.error(f"Google authentication error: {str(e)}")
#         return jsonify({
#             'message': 'Google authentication failed',
#             'error_details': str(e)
#         }), 500

# @login_bp.route('/verify-token', methods=['GET'])
# def verify_token():
#     """
#     Verify JWT token and return user info
#     """
#     try:
#         # Get token from Authorization header
#         auth_header = request.headers.get('Authorization')
#         if not auth_header or not auth_header.startswith('Bearer '):
#             return jsonify({'error': 'No valid authorization header'}), 401
        
#         token = auth_header.split(' ')[1]
        
#         # Check if token is blacklisted
#         if token in token_blacklist:
#             return jsonify({'error': 'Token has been invalidated'}), 401
        
#         # Verify token
#         secret_key = current_app.config['SECRET_KEY']
#         try:
#             payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
#             # Check if user is still authorized
#             if payload.get('email') != AUTHORIZED_EMAIL:
#                 return jsonify({'error': 'User no longer authorized'}), 403
            
#             # Return user data
#             user_data = {
#                 'name': payload.get('name'),
#                 'email': payload.get('email'),
#                 'role': payload.get('role', 'admin')
#             }
            
#             return jsonify(user_data), 200
            
#         except jwt.ExpiredSignatureError:
#             return jsonify({'error': 'Token has expired'}), 401
#         except jwt.InvalidTokenError:
#             return jsonify({'error': 'Invalid token'}), 401
            
#     except Exception as e:
#         logging.error(f"Token verification error: {str(e)}")
#         return jsonify({'error': 'Token verification failed'}), 500

# @login_bp.route('/logout', methods=['POST'])
# @token_required
# def logout():
#     """
#     Invalidate the current token by adding it to the blacklist
#     """
#     try:
#         auth_header = request.headers.get('Authorization')
#         if auth_header and auth_header.startswith('Bearer '):
#             token = auth_header.split(' ')[1]
#             token_blacklist.add(token)
        
#         return jsonify({'message': 'Successfully logged out'}), 200
#     except Exception as e:
#         logging.error(f"Logout error: {str(e)}")
#         return jsonify({'error': 'Logout failed'}), 500

# @login_bp.route('/auth-status', methods=['GET'])
# def auth_status():
#     """
#     Check authentication status without requiring a token
#     """
#     try:
#         auth_header = request.headers.get('Authorization')
#         if not auth_header or not auth_header.startswith('Bearer '):
#             return jsonify({'authenticated': False}), 200
        
#         token = auth_header.split(' ')[1]
        
#         # Check if token is blacklisted
#         if token in token_blacklist:
#             return jsonify({'authenticated': False}), 200
        
#         # Verify token
#         secret_key = current_app.config['SECRET_KEY']
#         try:
#             payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
#             # Check if user is still authorized
#             if payload.get('email') != AUTHORIZED_EMAIL:
#                 return jsonify({'authenticated': False}), 200
            
#             return jsonify({
#                 'authenticated': True,
#                 'user': {
#                     'name': payload.get('name'),
#                     'email': payload.get('email'),
#                     'role': payload.get('role', 'admin')
#                 }
#             }), 200
            
#         except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
#             return jsonify({'authenticated': False}), 200
            
#     except Exception as e:
#         logging.error(f"Auth status check error: {str(e)}")
#         return jsonify({'authenticated': False}), 200


import logging
import jwt
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from zoneinfo import ZoneInfo
from middlewares.auth import token_required
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

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

@login_bp.route('/login/google', methods=['GET', 'POST'])
def login_google():
    """
    Handle both OAuth redirect and direct credential verification
    """
    if request.method == 'POST':
        # Handle direct credential from frontend (Google Identity Services)
        try:
            data = request.get_json()
            credential = data.get('credential')
            
            if not credential:
                return jsonify({'error': 'No credential provided'}), 400
            
            # Verify the credential with Google
            try:
                # Verify the token
                idinfo = id_token.verify_oauth2_token(
                    credential, 
                    google_requests.Request(), 
                    os.getenv('GOOGLE_CLIENT_ID')
                )
                
                # Get user info
                email = idinfo.get('email')
                name = idinfo.get('name')
                
                # Check if this is the authorized user
                if email != AUTHORIZED_EMAIL:
                    return jsonify({
                        'error': 'Access denied. You are not authorized to access this application.'
                    }), 403
                
                # Create JWT token
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
                
                return jsonify({
                    'token': token,
                    'user': user_data,
                    'message': 'Authentication successful'
                }), 200
                
            except ValueError as e:
                # Invalid token
                logging.error(f"Invalid Google token: {str(e)}")
                return jsonify({'error': 'Invalid Google token'}), 400
                
        except Exception as e:
            logging.error(f"Google authentication error: {str(e)}")
            return jsonify({
                'error': 'Authentication failed',
                'details': str(e)
            }), 500
    
    else:
        # Handle OAuth redirect (fallback method)
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI') 
        return oauth.google.authorize_redirect(redirect_uri)

@login_bp.route('/login/google/callback')
def google_auth_callback():
    """
    Handle Google OAuth2 callback (fallback method)
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
        jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        # Redirect to your frontend with the token
        # Store user info in session for potential silent auth
        session['user_email'] = email
        session['user_name'] = name
        session.permanent = True  # Make session permanent
        
        redirect_url = f"https://radiance-of-warriors.vercel.app/armory?token={jwt_token}"
        return redirect(redirect_url)
        
    except Exception as e:
        logging.error(f"Google authentication error: {str(e)}")
        return jsonify({
            'message': 'Google authentication failed',
            'error_details': str(e)
        }), 500

@login_bp.route('/verify-token', methods=['GET'])
def verify_token():
    """
    Verify JWT token and return user info
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Check if token is blacklisted
        if token in token_blacklist:
            return jsonify({'error': 'Token has been invalidated'}), 401
        
        # Verify token
        secret_key = current_app.config['SECRET_KEY']
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Check if user is still authorized
            if payload.get('email') != AUTHORIZED_EMAIL:
                return jsonify({'error': 'User no longer authorized'}), 403
            
            # Return user data
            user_data = {
                'name': payload.get('name'),
                'email': payload.get('email'),
                'role': payload.get('role', 'admin')
            }
            
            return jsonify(user_data), 200
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
    except Exception as e:
        logging.error(f"Token verification error: {str(e)}")
        return jsonify({'error': 'Token verification failed'}), 500

@login_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Invalidate the current token by adding it to the blacklist
    """
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            token_blacklist.add(token)
        
        return jsonify({'message': 'Successfully logged out'}), 200
    except Exception as e:
        logging.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@login_bp.route('/get-token', methods=['GET'])
def get_token():
    """
    Get JWT token for authenticated session
    """
    try:
        # Check if user has an active session
        user_email = session.get('user_email')
        user_name = session.get('user_name')
        
        if not user_email or user_email != AUTHORIZED_EMAIL:
            return jsonify({'error': 'No active session'}), 401
        
        # Create JWT token
        secret_key = current_app.config['SECRET_KEY']
        payload = {
            'name': user_name,
            'email': user_email,
            'role': 'admin',
            'exp': datetime.now(tz=ZoneInfo('UTC')) + timedelta(days=1)
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        return jsonify({'token': token}), 200
        
    except Exception as e:
        logging.error(f"Get token error: {str(e)}")
        return jsonify({'error': 'Failed to get token'}), 500

@login_bp.route('/auth-status', methods=['GET'])
def auth_status():
    """
    Check authentication status including session-based auth
    """
    try:
        # First check JWT token if provided
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # Check if token is blacklisted
            if token not in token_blacklist:
                # Verify token
                secret_key = current_app.config['SECRET_KEY']
                try:
                    payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                    
                    # Check if user is still authorized
                    if payload.get('email') == AUTHORIZED_EMAIL:
                        return jsonify({
                            'authenticated': True,
                            'user': {
                                'name': payload.get('name'),
                                'email': payload.get('email'),
                                'role': payload.get('role', 'admin')
                            }
                        }), 200
                        
                except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                    pass
        
        # Check session-based auth
        user_email = session.get('user_email')
        user_name = session.get('user_name')
        
        if user_email == AUTHORIZED_EMAIL:
            return jsonify({
                'authenticated': True,
                'user': {
                    'name': user_name,
                    'email': user_email,
                    'role': 'admin'
                }
            }), 200
        
        return jsonify({'authenticated': False}), 200
            
    except Exception as e:
        logging.error(f"Auth status check error: {str(e)}")
        return jsonify({'authenticated': False}), 200