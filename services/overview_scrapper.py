import requests
from bs4 import BeautifulSoup
import json
import logging
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WarPowerIndiaScraper:
    def __init__(self):
        self.base_url = "https://www.warpowerindia.com"
        self.target_pages = [
            "airpower.php",
            "landpower.php", 
            "navalpower.php",
            "droneforce.php",
            "china-military-ranks.php",
            "manpower.php"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def get_homepage_content(self):
        """Fetch homepage content"""
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching homepage: {e}")
            return None
    
    def extract_section_divs(self, soup):
        """Extract information from all picTrans divs on homepage"""
        scraped_data = []
        
        # Find all anchor tags with class 'picTrans'
        pic_trans_links = soup.find_all('a', class_='picTrans')
        
        logger.info(f"Found {len(pic_trans_links)} picTrans divs on homepage")
        
        for link in pic_trans_links:
            try:
                # Get the href to determine which section this is
                href = link.get('href', '')
                
                # Check if this is one of our target pages
                page_name = href.lstrip('/')  # Remove leading slash
                if page_name not in self.target_pages:
                    continue
                
                # Extract image URL
                img_tag = link.find('img', class_='wrapperImg')
                image_url = ""
                if img_tag and img_tag.get('src'):
                    image_url = urljoin(self.base_url, img_tag.get('src'))
                
                # Extract title (from span with textLargest class)
                title_span = link.find('span', class_='textLargest')
                title = title_span.get_text(strip=True) if title_span else ""
                
                # Extract description (from span with textLarge class) 
                desc_span = link.find('span', class_='textLarge')
                description = desc_span.get_text(strip=True) if desc_span else ""
                
                # Create the full URL for this section
                full_url = urljoin(self.base_url, href)
                
                section_data = {
                    "url": full_url,
                    "image_url": image_url,
                    "title": title,
                    "description": description
                }
                
                scraped_data.append(section_data)
                logger.info(f"Extracted data for: {page_name}")
                
            except Exception as e:
                logger.error(f"Error extracting data from div: {e}")
                continue
        
        return scraped_data
    
    def save_to_json(self, data, filename="india_overview.json"):
        """Save extracted data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            return False
    
    def run(self):
        """Main execution method"""
        logger.info("Starting War Power India homepage scraper...")
        
        # Get homepage content
        html_content = self.get_homepage_content()
        if not html_content:
            logger.error("Failed to fetch homepage content")
            return
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract section data
        scraped_data = self.extract_section_divs(soup)
        
        if scraped_data:
            # Save to JSON
            if self.save_to_json(scraped_data):
                print(f"\n✅ Scraping completed successfully!")
                print(f"📊 Total sections scraped: {len(scraped_data)}")
                print(f"💾 Data saved to: india_overview.json")
                
                # Show summary of scraped sections
                print(f"\n📋 Scraped sections:")
                for i, item in enumerate(scraped_data, 1):
                    section_name = item['url'].split('/')[-1]
                    print(f"  {i}. {section_name}: {item['title']}")
                
                # Show sample data structure
                if scraped_data:
                    print(f"\n🔍 Sample entry structure:")
                    sample = scraped_data[0]
                    for key, value in sample.items():
                        display_value = value[:60] + "..." if len(str(value)) > 60 else value
                        print(f"  {key}: {display_value}")
                        
            else:
                logger.error("Failed to save data to JSON")
        else:
            logger.warning("No matching sections found on homepage")
            print("❌ No data was scraped. Please check if the website structure has changed.")

def main():
    scraper = WarPowerIndiaScraper()
    scraper.run()

if __name__ == "__main__":
    main()


