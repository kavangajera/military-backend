from flask import Blueprint, jsonify
import os
import requests
from datetime import datetime, timedelta

# Create a Blueprint for news routes
news_bp = Blueprint('news', __name__)

@news_bp.route('/get-latest-news', methods=['GET'])
def get_latest_news():
    """
    Fetch 5 latest military news across the world
    using GNews API
    """
    try:
        # Get API key from environment variables
        api_key = os.getenv('GNEWS_API_KEY')
        
        if not api_key:
            return jsonify({
                "error": "API key not found. Please add GNEWS_API_KEY to your .env file"
            }), 500
        
        # Calculate date for last 7 days (GNews free tier limitation)
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Build the GNews API URL
        url = f"https://gnews.io/api/v4/search"
        
        # Parameters for the API request
        params = {
            'q': 'military OR "armed forces" OR "air force" OR "naval" OR battlefield OR warfare OR "military operation" OR "missile" OR "fighter jet" OR "aircraft carrier" OR "military conflict" OR "troops" OR "military intelligence" OR "operation sindoor"',
            'lang': 'en',
            'country': 'any',
            'max': 5,  # Fetch 5 articles
            'apikey': api_key,
            'from': from_date
        }
        
        # Make the request to GNews API
        response = requests.get(url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Format the news articles
            articles = []
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'content': article.get('content'),
                    'url': article.get('url'),
                    'image': article.get('image'),
                    'publishedAt': article.get('publishedAt'),
                    'source': article.get('source', {}).get('name')
                })
            
            return jsonify({
                "success": True,
                "count": len(articles),
                "news": articles
            }), 200
        
        else:
            return jsonify({
                "error": f"GNews API error: {response.status_code}",
                "details": response.json()
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "error": "Failed to fetch news",
            "details": str(e)
        }), 500