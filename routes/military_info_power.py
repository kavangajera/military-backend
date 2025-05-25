from flask import Blueprint, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
military_bp = Blueprint('military', __name__)

class MilitaryDataService:
    """Service class for handling military data operations"""
    
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI')
        if not self.mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables")
        
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client['militaryDB']
    
    def get_country_id(self, country_name: str):
        """Get country ID by name"""
        try:
            country = self.db['countries'].find_one({'name': country_name.lower()})
            return str(country['_id']) if country else None
        except Exception as e:
            logger.error(f"Error getting country ID for {country_name}: {e}")
            return None
    
    def get_military_power_data(self, country_name: str, power_type: str):
        """Get military power data for a specific country and power type"""
        try:
            # Validate power type
            valid_power_types = ['airpower', 'navalpower', 'droneforce', 'landpower']
            if power_type.lower() not in valid_power_types:
                return None, f"Invalid power type. Valid types: {', '.join(valid_power_types)}"
            
            # Get country ID
            country_id = self.get_country_id(country_name)
            if not country_id:
                return None, f"Country '{country_name}' not found"
            
            # Get military data
            collection = self.db[power_type.lower()]
            cursor = collection.find({'country_id': country_id})
            
            # Convert to list and clean up MongoDB-specific fields
            data = []
            for doc in cursor:
                # Remove MongoDB-specific fields
                doc.pop('_id', None)
                doc.pop('country_id', None)
                doc.pop('scraped_at', None)
                doc.pop('last_updated', None)
                
                data.append(doc)
            
            return data, None
            
        except Exception as e:
            logger.error(f"Error getting military data for {country_name}/{power_type}: {e}")
            return None, f"Database error: {str(e)}"
    
    def get_country_summary(self, country_name: str):
        """Get summary of all military powers for a country"""
        try:
            country_id = self.get_country_id(country_name)
            if not country_id:
                return None, f"Country '{country_name}' not found"
            
            summary = {}
            power_types = ['airpower', 'navalpower', 'droneforce', 'landpower']
            
            for power_type in power_types:
                collection = self.db[power_type]
                count = collection.count_documents({'country_id': country_id})
                summary[power_type] = {
                    'total_units': count,
                    'endpoint': f"/{country_name}/{power_type}"
                }
            
            return summary, None
            
        except Exception as e:
            logger.error(f"Error getting country summary for {country_name}: {e}")
            return None, f"Database error: {str(e)}"
    
    def get_all_countries(self):
        """Get list of all available countries"""
        try:
            countries = self.db['countries'].find({}, {'name': 1, 'display_name': 1})
            country_list = []
            
            for country in countries:
                country_list.append({
                    'name': country['name'],
                    'display_name': country['display_name'],
                    'endpoints': {
                        'summary': f"/{country['name']}",
                        'airpower': f"/{country['name']}/airpower",
                        'navalpower': f"/{country['name']}/navalpower",
                        'droneforce': f"/{country['name']}/droneforce",
                        'landpower': f"/{country['name']}/landpower"
                    }
                })
            
            return country_list, None
            
        except Exception as e:
            logger.error(f"Error getting countries list: {e}")
            return None, f"Database error: {str(e)}"
    
    def close_connection(self):
        """Close database connection"""
        self.client.close()

# Initialize service
military_service = MilitaryDataService()

@military_bp.route('/', methods=['GET'])
def get_available_countries():
    """Get list of all available countries and their endpoints"""
    try:
        countries, error = military_service.get_all_countries()
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Available countries and endpoints',
            'total_countries': len(countries),
            'countries': countries
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_available_countries: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@military_bp.route('/<string:country_name>', methods=['GET'])
def get_country_summary(country_name):
    """Get summary of all military powers for a specific country"""
    try:
        summary, error = military_service.get_country_summary(country_name)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 404
        
        return jsonify({
            'success': True,
            'country': country_name.title(),
            'military_powers': summary
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_country_summary: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@military_bp.route('/<string:country_name>/<string:power_type>', methods=['GET'])
def get_military_power_data(country_name, power_type):
    """Get military power data for a specific country and power type"""
    try:
        # Get query parameters for filtering/pagination
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', default=0, type=int)
        search = request.args.get('search', '').strip()
        
        data, error = military_service.get_military_power_data(country_name, power_type)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 404
        
        # Apply filtering if search parameter is provided
        if search:
            filtered_data = []
            search_lower = search.lower()
            for item in data:
                if (search_lower in item.get('name', '').lower() or 
                    search_lower in item.get('model', '').lower() or 
                    search_lower in item.get('role', '').lower()):
                    filtered_data.append(item)
            data = filtered_data
        
        # Apply pagination if limit is provided
        total_records = len(data)
        if limit:
            data = data[offset:offset + limit]
        
        # Prepare response
        response_data = {
            'success': True,
            'country': country_name.title(),
            'power_type': power_type.title(),
            'total_records': total_records,
            'data': data
        }
        
        # Add pagination info if applicable
        if limit:
            response_data['pagination'] = {
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_records,
                'next_offset': offset + limit if offset + limit < total_records else None
            }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in get_military_power_data: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@military_bp.route('/search', methods=['GET'])
def search_military_data():
    """Search across all military data"""
    try:
        query = request.args.get('q', '').strip()
        country_filter = request.args.get('country', '').strip()
        power_type_filter = request.args.get('power_type', '').strip()
        limit = request.args.get('limit', default=50, type=int)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query parameter "q" is required'
            }), 400
        
        results = []
        power_types = ['airpower', 'navalpower', 'droneforce', 'landpower']
        
        # Filter power types if specified
        if power_type_filter:
            if power_type_filter.lower() in power_types:
                power_types = [power_type_filter.lower()]
            else:
                return jsonify({
                    'success': False,
                    'error': f'Invalid power_type. Valid types: {", ".join(power_types)}'
                }), 400
        
        # Search across power types
        for power_type in power_types:
            collection = military_service.db[power_type]
            
            # Build search filter
            search_filter = {
                '$or': [
                    {'name': {'$regex': query, '$options': 'i'}},
                    {'model': {'$regex': query, '$options': 'i'}},
                    {'role': {'$regex': query, '$options': 'i'}},
                    {'description': {'$regex': query, '$options': 'i'}}
                ]
            }
            
            # Add country filter if specified
            if country_filter:
                country_id = military_service.get_country_id(country_filter)
                if country_id:
                    search_filter['country_id'] = country_id
            
            # Execute search
            cursor = collection.find(search_filter).limit(limit)
            
            for doc in cursor:
                # Clean up document
                doc.pop('_id', None)
                doc.pop('country_id', None)
                doc.pop('scraped_at', None)
                doc.pop('last_updated', None)
                
                # Add metadata
                doc['power_type'] = power_type
                doc['endpoint'] = f"/{doc.get('country', 'unknown')}/{power_type}"
                
                results.append(doc)
        
        return jsonify({
            'success': True,
            'query': query,
            'total_results': len(results),
            'results': results[:limit]  # Ensure we don't exceed limit
        }), 200
        
    except Exception as e:
        logger.error(f"Error in search_military_data: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# Error handlers
@military_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@military_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

# Cleanup on app teardown
# @military_bp.teardown_app_request
# def close_db_connection(error):
#     """Close database connection when app context tears down"""
#     if hasattr(military_service, 'client'):
#         military_service.close_connection()