import requests
from bs4 import BeautifulSoup
import json
import re
import os
from urllib.parse import urljoin

def scrape_aircraft_data(power_name,country_name):
    """
    Scrape aircraft information from warpowerindia.com and store in JSON format
    """
    # Send a request to the website
    url=f"https://www.warpower{country_name}.com/{power_name}.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return None
    
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all aircraft elements (based on the provided structure)
    aircraft_elements = soup.find_all('div', class_='mainCol')
    
    aircraft_data = []
    country_name = country_name.lower()
    base_url = f"https://www.warpower{country_name}.com/"
    
    # Process each aircraft element
    for element in aircraft_elements:
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
            
            # Extract country from flag URL if possible
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
            
            # Extract model in parentheses if it exists
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
            
            # Compile all information
            aircraft_info = {
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
            
            aircraft_data.append(aircraft_info)
            print(f"Successfully scraped data for {aircraft_name}")
            
        except Exception as e:
            print(f"Error processing an aircraft element: {e}")
    
    print(f"Total aircraft scraped: {len(aircraft_data)}")
    return aircraft_data

def save_to_json(data, filename="aircraft_data_india.json"):
    """
    Save the scraped data to a JSON file
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Data successfully saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving data to file: {e}")
        return False

def main():
    # Scrape the aircraft data
    power_name = input("Enter the power name (e.g., 'russia'): ").strip().lower()
    country_name = input("Enter the country name (e.g., 'russia'): ").strip().lower()
    data = scrape_aircraft_data(power_name, country_name)
    
    if data:
        # Save to JSON file
        filename = f"{power_name}_data_{country_name}.json"
        save_to_json(data, filename)
        
        # Print sample of the data
        print("\nSample of scraped data:")
        if len(data) > 0:
            print(json.dumps(data[0], indent=4))

if __name__ == "__main__":
    main()