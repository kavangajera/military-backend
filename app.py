from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from routes.news import news_bp
from routes.login import login_bp, setup_google_oauth
import os
app = Flask(__name__)
CORS(app)
load_dotenv()


client_id = os.getenv('GOOGLE_CLIENT_ID')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
# Generate a secure secret key
# app.config['SECRET_KEY'] = secrets.token_hex(32)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Google OAuth configuration
app.config['GOOGLE_CLIENT_ID'] = client_id  # Replace with your Google Client ID
app.config['GOOGLE_CLIENT_SECRET'] = client_secret # Replace with your Google Client Secret

setup_google_oauth(app)

# Register blueprints
app.register_blueprint(news_bp, url_prefix='/api')
app.register_blueprint(login_bp, url_prefix='/api')

@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Military API!"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
