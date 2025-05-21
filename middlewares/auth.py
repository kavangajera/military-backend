import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from zoneinfo import ZoneInfo
import os

token_blacklist = set()
AUTHORIZED_EMAIL = os.getenv('AUTHORIZED_EMAIL') 

def token_required(f):
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        # Check if token is blacklisted
        if token in token_blacklist:
            return jsonify({'message': 'Token has been revoked!'}), 401
        
        try:
            # Decode the token
            secret_key = current_app.config['SECRET_KEY']
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Check if the decoded email matches the authorized email
            if payload['email'] != AUTHORIZED_EMAIL:
                return jsonify({'message': 'Unauthorized access!'}), 403
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
            
        return f(*args, **kwargs)
    
    # Preserve the original function name and docstring
    decorated.__name__ = f.__name__
    decorated.__doc__ = f.__doc__
    
    return decorated