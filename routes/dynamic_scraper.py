from flask import Blueprint, request, jsonify
import logging
from typing import List, Dict
import threading
from concurrent.futures import ThreadPoolExecutor

# Import your existing classes (assuming they're in a separate module)
# If the classes are in the same file, you can import them directly

from models.scrapper import (
    MilitaryDataPipeline, 
    DatabaseManager, 
    WebScraper, 
    SketchfabIntegrator
)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Blueprint
dynamic_scraper_bp = Blueprint('dynamic_scraper', __name__)

# Global variable to track scraping status
scraping_status = {}

def run_scraping_pipeline(country_name: str, power_types: List[str], task_id: str):
    """Run the scraping pipeline in a separate thread"""
    try:
        scraping_status[task_id] = {
            'status': 'running',
            'message': f'Initializing pipeline for {country_name}',
            'progress': 5,  # Set initial progress
            'total_power_types': len(power_types),
            'completed_power_types': 0,
            'current_power_type': None,
            'data': {}
        }
        
        pipeline = MilitaryDataPipeline()
        
        # Update progress for pipeline initialization
        scraping_status[task_id]['progress'] = 10
        scraping_status[task_id]['message'] = f'Getting country information for {country_name}'
        
        # Get or create country
        country_id = pipeline.db_manager.get_or_create_country(country_name)
        
        # Update progress after country setup
        scraping_status[task_id]['progress'] = 15
        
        for i, power_type in enumerate(power_types):
            scraping_status[task_id]['current_power_type'] = power_type
            
            # Calculate base progress for this power type
            base_progress = 15 + (i * 80 / len(power_types))  # 15% initial + 80% for processing
            
            # Step 1: Scrape data
            scraping_status[task_id]['message'] = f'Scraping {power_type} data for {country_name}'
            scraping_status[task_id]['progress'] = base_progress + (10 / len(power_types))
            
            logger.info(f"Processing {power_type} for {country_name}")
            
            military_data = pipeline.scraper.scrape_military_data(power_type, country_name.lower())
            if not military_data:
                logger.warning(f"No data scraped for {power_type}")
                scraping_status[task_id]['data'][power_type] = {
                    'status': 'failed',
                    'message': 'No data found',
                    'count': 0
                }
                # Update progress even for failed items
                scraping_status[task_id]['completed_power_types'] += 1
                scraping_status[task_id]['progress'] = 15 + (scraping_status[task_id]['completed_power_types'] * 80 / len(power_types))
                continue
            
            # Step 2: Add Sketchfab links
            scraping_status[task_id]['message'] = f'Adding Sketchfab links for {power_type}'
            scraping_status[task_id]['progress'] = base_progress + (40 / len(power_types))
            military_data = pipeline.sketchfab.add_sketchfab_links(military_data)
            
            # Step 3: Save to database
            scraping_status[task_id]['message'] = f'Saving {power_type} data to database'
            scraping_status[task_id]['progress'] = base_progress + (70 / len(power_types))
            success = pipeline.db_manager.save_military_data(country_id, power_type, military_data)
            
            # Update progress after completion
            scraping_status[task_id]['completed_power_types'] += 1
            scraping_status[task_id]['progress'] = 15 + (scraping_status[task_id]['completed_power_types'] * 80 / len(power_types))
            
            if success:
                scraping_status[task_id]['data'][power_type] = {
                    'status': 'success',
                    'message': 'Data saved successfully',
                    'count': len(military_data)
                }
                logger.info(f"Successfully completed {power_type} pipeline for {country_name}")
            else:
                scraping_status[task_id]['data'][power_type] = {
                    'status': 'failed',
                    'message': 'Failed to save data',
                    'count': 0
                }
                logger.error(f"Failed to save {power_type} data for {country_name}")
        
        # Mark as completed
        scraping_status[task_id]['status'] = 'completed'
        scraping_status[task_id]['message'] = f'Pipeline completed for {country_name}'
        scraping_status[task_id]['progress'] = 100
        
        pipeline.cleanup()
        
    except Exception as e:
        scraping_status[task_id]['status'] = 'error'
        scraping_status[task_id]['message'] = f'Pipeline error: {str(e)}'
        scraping_status[task_id]['progress'] = 0  # Reset progress on error
        logger.error(f"Pipeline error: {e}")

# Debug endpoint to check status directly
@dynamic_scraper_bp.route('/debug/status', methods=['GET'])
def debug_all_status():
    """Debug endpoint to see all current task statuses"""
    return jsonify({
        'success': True,
        'all_tasks': scraping_status
    }), 200

@dynamic_scraper_bp.route('/scrape', methods=['POST'])
def create_military_tables():
    """
    POST endpoint to create military data tables in MongoDB
    
    Expected JSON payload:
    {
        "country_name": "india",
        "power": "airpower" or "all" or ["airpower", "navalpower"]
    }
    """
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if 'country_name' not in data:
            return jsonify({
                'success': False,
                'message': 'country_name is required'
            }), 400
        
        if 'power' not in data:
            return jsonify({
                'success': False,
                'message': 'power is required'
            }), 400
        
        country_name = data['country_name'].strip().lower()
        power_input = data['power']
        
        # Validate country name
        if not country_name:
            return jsonify({
                'success': False,
                'message': 'country_name cannot be empty'
            }), 400
        
        # Process power types
        available_power_types = ['airpower', 'navalpower', 'droneforce', 'landpower']
        
        if isinstance(power_input, str):
            if power_input.lower() == 'all':
                power_types = available_power_types
            else:
                power_input = power_input.strip().lower()
                if power_input not in available_power_types:
                    return jsonify({
                        'success': False,
                        'message': f'Invalid power type. Available types: {", ".join(available_power_types)}'
                    }), 400
                power_types = [power_input]
        elif isinstance(power_input, list):
            power_types = []
            for power in power_input:
                power = power.strip().lower()
                if power not in available_power_types:
                    return jsonify({
                        'success': False,
                        'message': f'Invalid power type: {power}. Available types: {", ".join(available_power_types)}'
                    }), 400
                power_types.append(power)
        else:
            return jsonify({
                'success': False,
                'message': 'power must be a string or list of strings'
            }), 400
        
        # Generate unique task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Start scraping in background thread
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(run_scraping_pipeline, country_name, power_types, task_id)
        
        return jsonify({
            'success': True,
            'message': 'Scraping pipeline started',
            'task_id': task_id,
            'country_name': country_name,
            'power_types': power_types,
            'status_url': f'/api/dynamic_scraper/status/{task_id}'
        }), 202
        
    except Exception as e:
        logger.error(f"Error in create_military_tables: {e}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@dynamic_scraper_bp.route('/status/<task_id>', methods=['GET'])
def get_scraping_status(task_id: str):
    """
    GET endpoint to check the status of a scraping task
    """
    try:
        if task_id not in scraping_status:
            return jsonify({
                'success': False,
                'message': 'Task not found'
            }), 404
        
        status_info = scraping_status[task_id]
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            **status_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_scraping_status: {e}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@dynamic_scraper_bp.route('/data/<country_name>/<power_type>', methods=['GET'])
def get_country_data(country_name: str, power_type: str):
    """
    GET endpoint to retrieve scraped data for a specific country and power type
    """
    try:
        # Validate power type
        available_power_types = ['airpower', 'navalpower', 'droneforce', 'landpower']
        if power_type.lower() not in available_power_types:
            return jsonify({
                'success': False,
                'message': f'Invalid power type. Available types: {", ".join(available_power_types)}'
            }), 400
        
        pipeline = MilitaryDataPipeline()
        data = pipeline.get_country_data(country_name.lower(), power_type.lower())
        pipeline.cleanup()
        
        # Convert ObjectId to string for JSON serialization
        for item in data:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            if 'country_id' in item:
                item['country_id'] = str(item['country_id'])
        
        return jsonify({
            'success': True,
            'country_name': country_name,
            'power_type': power_type,
            'total_records': len(data),
            'data': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_country_data: {e}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@dynamic_scraper_bp.route('/countries', methods=['GET'])
def get_available_countries():
    """
    GET endpoint to retrieve all available countries in the database
    """
    try:
        db_manager = DatabaseManager()
        countries_collection = db_manager.db['countries']
        
        countries = list(countries_collection.find({}, {'_id': 0, 'name': 1, 'display_name': 1}))
        db_manager.close_connection()
        
        return jsonify({
            'success': True,
            'total_countries': len(countries),
            'countries': countries
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_available_countries: {e}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@dynamic_scraper_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET endpoint for health check
    """
    try:
        # Test database connection
        db_manager = DatabaseManager()
        db_manager.close_connection()
        
        return jsonify({
            'success': True,
            'message': 'Dynamic scraper service is healthy',
            'available_power_types': ['airpower', 'navalpower', 'droneforce', 'landpower']
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'message': f'Service unhealthy: {str(e)}'
        }), 500

# Error handlers
@dynamic_scraper_bp.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint not found'
    }), 404

@dynamic_scraper_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500