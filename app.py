from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from routes.news import news_bp
from routes.military_info_power import military_bp
from routes.dynamic_scraper import dynamic_scraper_bp
import os
app = Flask(__name__)
CORS(app)
load_dotenv()


# Register blueprints
app.register_blueprint(news_bp, url_prefix='/api')
app.register_blueprint(military_bp, url_prefix='/api/military')
app.register_blueprint(dynamic_scraper_bp, url_prefix='/api')


@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Military API!"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
