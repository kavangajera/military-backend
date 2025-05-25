import requests
from bs4 import BeautifulSoup
import re
import os
import time
from urllib.parse import urljoin, urlparse
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import logging
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles MongoDB operations for military data"""
    
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI')
        if not self.mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables")
        
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client['militaryDB']
        logger.info("Connected to MongoDB")
    
    def get_or_create_country(self, country_name: str) -> str:
        """Get or create country record and return its ID"""
        countries_collection = self.db['countries']
        
        # Check if country exists
        country = countries_collection.find_one({'name': country_name.lower()})
        if country:
            return str(country['_id'])
        
        # Create new country
        country_doc = {
            'name': country_name.lower(),
            'display_name': country_name.title(),
            'created_at': datetime.utcnow(),
            'last_updated': datetime.utcnow()
        }
        
        result = countries_collection.insert_one(country_doc)
        logger.info(f"Created new country: {country_name}")
        return str(result.inserted_id)
    
    def save_military_data(self, country_id: str, power_type: str, data: List[Dict]) -> bool:
        """Save military data to appropriate collection"""
        collection_name = f"{power_type.lower()}"
        collection = self.db[collection_name]
        
        # Add metadata to each record
        for item in data:
            item['country_id'] = country_id
            item['scraped_at'] = datetime.utcnow()
            item['last_updated'] = datetime.utcnow()
        
        try:
            # Clear existing data for this country and power type
            collection.delete_many({'country_id': country_id})
            
            # Insert new data
            result = collection.insert_many(data)
            logger.info(f"Saved {len(result.inserted_ids)} {power_type} records for country_id: {country_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving {power_type} data: {e}")
            return False
    
    def get_military_data(self, country_id: str, power_type: str) -> List[Dict]:
        """Retrieve military data from database"""
        collection_name = f"{power_type.lower()}"
        collection = self.db[collection_name]
        
        data = list(collection.find({'country_id': country_id}))
        return data
    
    def close_connection(self):
        """Close MongoDB connection"""
        self.client.close()
        logger.info("MongoDB connection closed")

class WebScraper:
    """Handles web scraping operations"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def scrape_military_data(self, power_name: str, country_name: str) -> Optional[List[Dict]]:
        """Scrape military data from warpower website"""
        url = f"https://www.warpower{country_name}.com/{power_name}.php"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"Failed to retrieve webpage. Status code: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            aircraft_elements = soup.find_all('div', class_='mainCol')
            
            military_data = []
            base_url = f"https://www.warpower{country_name}.com/"
            
            for element in aircraft_elements:
                try:
                    data_item = self._extract_element_data(element, base_url)
                    if data_item:
                        military_data.append(data_item)
                        logger.info(f"Successfully scraped data for {data_item['name']}")
                except Exception as e:
                    logger.error(f"Error processing element: {e}")
            
            logger.info(f"Total items scraped: {len(military_data)}")
            return military_data
            
        except Exception as e:
            logger.error(f"Error scraping data: {e}")
            return None
    
    def _extract_element_data(self, element, base_url: str) -> Optional[Dict]:
        """Extract data from a single HTML element"""
        try:
            # Extract service information
            service_element = element.find('span', class_='textWhite textNormal textBold')
            service = service_element.text.strip() if service_element else "Unknown"
            
            # Extract image URL
            img_element = element.find('img', class_='entryImg')
            img_url = urljoin(base_url, img_element['src']) if img_element and img_element.get('src') else None
            
            # Extract assessment information
            assessment_element = element.find('div', class_='assessmentBox')
            assessment = assessment_element.find('span', class_='textNormal textWhite').text.strip() if assessment_element else "Unknown"
            
            # Extract flag and country information
            flag_element = element.find('img', class_='flagMinStyling')
            flag_url = urljoin(base_url, flag_element['src']) if flag_element and flag_element.get('src') else None
            
            # Extract country from flag URL
            country = "Unknown"
            if flag_url:
                country_match = re.search(r'/flags/([^.]+)\.(jpg|png|webp)', flag_url)
                if country_match:
                    country = country_match.group(1).capitalize()
            
            # Extract units count
            units_element = element.find('span', class_='textJumbo')
            units = int(units_element.text.strip()) if units_element else 0
            
            # Extract aircraft name and model
            name_element = element.find('span', class_='textYellowOrange')
            model_element = element.find('span', class_='textWhite textLarge textBold')
            
            aircraft_name = name_element.text.strip() if name_element else "Unknown"
            full_model_text = model_element.text.strip() if model_element else ""
            
            # Extract model in parentheses
            model = "Unknown"
            model_match = re.search(r'\((.*?)\)', full_model_text)
            if model_match:
                model = model_match.group(1).strip()
            
            # Extract role
            role_element = element.find('span', class_='textNormal textLtstGray')
            role = role_element.text.replace('Role:', '').strip() if role_element else "Unknown"
            
            # Extract description
            desc_element = element.find('span', class_='textSmall1 textWhite')
            description = desc_element.text.strip() if desc_element else "No description available"
            
            return {
                "service": service,
                "name": aircraft_name,
                "model": model,
                "country": country,
                "units": units,
                "role": role,
                "assessment": assessment,
                "description": description,
                "image_url": img_url,
                "flag_url": flag_url
            }
            
        except Exception as e:
            logger.error(f"Error extracting element data: {e}")
            return None

class SketchfabIntegrator:
    """Handles Sketchfab API integration"""
    
    def __init__(self, api_token: str = os.getenv('SKETCHFAB_API_KEY')):
        self.api_token = api_token
        self.headers = {'Authorization': f'Token {api_token}'} if api_token else {}
    
    def normalize_name(self, name: str) -> str:
        """Normalize aircraft name for better matching"""
        name = re.sub(r'[^\w\s]', '', name.lower())
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    def get_best_match(self, model_name: str, results: List[Dict], max_results: int = 5) -> Optional[Dict]:
        """Get the best matching Sketchfab model from results"""
        if not results:
            return None
        
        normalized_model = self.normalize_name(model_name)
        
        # Try exact name match
        for model in results[:max_results]:
            if self.normalize_name(model['name']) == normalized_model:
                return model
        
        # Check if model name is contained in Sketchfab name
        for model in results[:max_results]:
            if normalized_model in self.normalize_name(model['name']):
                return model
        
        # Check if any part of model name is in Sketchfab name
        model_parts = normalized_model.split()
        for model in results[:max_results]:
            sketchfab_name = self.normalize_name(model['name'])
            if any(part in sketchfab_name for part in model_parts if len(part) > 2):
                return model
        
        return results[0] if results else None
    
    def get_sketchfab_link(self, model_name: str) -> str:
        """Get Sketchfab embed link for a model"""
        query = model_name.replace(' ', '+')
        url = f'https://api.sketchfab.com/v3/search?type=models&q={query}&sort_by=relevance&count=10'
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.warning(f"Sketchfab API error {response.status_code} for model: {model_name}")
                return "NOT FOUND"
            
            results = response.json().get('results', [])
            if not results:
                logger.info(f"No Sketchfab results found for model: {model_name}")
                return "NOT FOUND"
            
            best_model = self.get_best_match(model_name, results)
            if best_model:
                embed_url = f"https://sketchfab.com/models/{best_model['uid']}/embed"
                logger.info(f"Found Sketchfab model for {model_name}: {best_model['name']}")
                return embed_url
            
            return "NOT FOUND"
            
        except Exception as e:
            logger.error(f"Error fetching Sketchfab data for {model_name}: {e}")
            return "NOT FOUND"
    
    def add_sketchfab_links(self, military_data: List[Dict]) -> List[Dict]:
        """Add Sketchfab embed URLs to military data"""
        total_items = len(military_data)
        
        for i, item in enumerate(military_data):
            model_name = item.get("model", "")
            logger.info(f"Processing Sketchfab link {i+1}/{total_items}: {model_name}")
            
            if model_name and model_name != "Unknown":
                sketchfab_url = self.get_sketchfab_link(model_name)
                item["sketchfab_embed_url"] = sketchfab_url
                time.sleep(0.5)  # Rate limiting
            else:
                item["sketchfab_embed_url"] = "NOT FOUND"
                logger.info(f"No model name found for: {item.get('name', 'Unknown')}")
        
        return military_data

class ImageDownloader:
    """Handles image downloading and local storage"""
    
    def __init__(self, base_dir: str = "images"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(os.path.join(base_dir, 'flags'), exist_ok=True)
    
    def download_image(self, url: str, save_path: str) -> bool:
        """Download an image from URL"""
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                logger.info(f"Successfully downloaded: {save_path}")
                return True
            else:
                logger.warning(f"Failed to download {url}. Status code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False
    
    def process_flag_images(self, military_data: List[Dict]) -> List[Dict]:
        """Download flag images and update URLs to local paths"""
        processed_urls = {}
        download_count = 0
        
        for i, item in enumerate(military_data):
            if 'flag_url' in item and item['flag_url']:
                flag_url = item['flag_url']
                
                # Skip if already processed
                if flag_url in processed_urls:
                    logger.info(f"Using existing flag download for {item['name']}")
                    item['flag_url'] = processed_urls[flag_url]
                    continue
                
                filename = os.path.basename(urlparse(flag_url).path)
                save_path = os.path.join(self.base_dir, 'flags', filename)
                
                logger.info(f"Processing flag for {item['name']} ({i+1}/{len(military_data)})")
                
                if self.download_image(flag_url, save_path):
                    local_path = f"flags/{filename}"
                    item['flag_url'] = local_path
                    processed_urls[flag_url] = local_path
                    download_count += 1
        
        logger.info(f"Downloaded {download_count} unique flag images")
        return military_data

class MilitaryDataPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.scraper = WebScraper()
        self.sketchfab = SketchfabIntegrator()
        self.image_downloader = ImageDownloader()
    
    def run_pipeline(self, country_name: str, power_types: List[str]):
        """Run the complete data pipeline"""
        try:
            logger.info(f"Starting pipeline for {country_name} - {', '.join(power_types)}")
            
            # Get or create country
            country_id = self.db_manager.get_or_create_country(country_name)
            
            for power_type in power_types:
                logger.info(f"Processing {power_type} for {country_name}")
                
                # Step 1: Scrape data
                military_data = self.scraper.scrape_military_data(power_type, country_name.lower())
                if not military_data:
                    logger.warning(f"No data scraped for {power_type}")
                    continue
                
                # Step 2: Add Sketchfab links
                military_data = self.sketchfab.add_sketchfab_links(military_data)
                
                # Step 3: Download and process flag images
                military_data = self.image_downloader.process_flag_images(military_data)
                
                # Step 4: Save to database
                success = self.db_manager.save_military_data(country_id, power_type, military_data)
                if success:
                    logger.info(f"Successfully completed {power_type} pipeline for {country_name}")
                else:
                    logger.error(f"Failed to save {power_type} data for {country_name}")
            
            logger.info(f"Pipeline completed for {country_name}")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        finally:
            self.cleanup()
    
    def get_country_data(self, country_name: str, power_type: str) -> List[Dict]:
        """Retrieve data for a specific country and power type"""
        try:
            country_id = self.db_manager.get_or_create_country(country_name)
            return self.db_manager.get_military_data(country_id, power_type)
        except Exception as e:
            logger.error(f"Error retrieving data: {e}")
            return []
    
    def cleanup(self):
        """Clean up resources"""
        self.db_manager.close_connection()

def main():
    """Main execution function"""
    pipeline = MilitaryDataPipeline()
    
    try:
        # Get user input
        country_name = input("Enter the country name (e.g., 'india', 'russia'): ").strip().lower()
        
        print("Available power types: airpower, navalpower, droneforce, landpower")
        power_input = input("Enter power types (comma-separated, or 'all' for all types): ").strip().lower()
        
        if power_input == 'all':
            power_types = ['airpower', 'navalpower', 'droneforce', 'landpower']
        else:
            power_types = [p.strip() for p in power_input.split(',')]
        
        # Run the pipeline
        pipeline.run_pipeline(country_name, power_types)
        
        # Optional: Display sample data
        for power_type in power_types:
            sample_data = pipeline.get_country_data(country_name, power_type)
            if sample_data:
                print(f"\nSample {power_type} data for {country_name}:")
                print(f"Total records: {len(sample_data)}")
                if sample_data:
                    sample_item = sample_data[0]
                    print(f"Sample record: {sample_item.get('name', 'Unknown')} - {sample_item.get('model', 'Unknown')}")
    
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
    finally:
        pipeline.cleanup()

if __name__ == "__main__":
    main()