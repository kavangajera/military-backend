import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_gfp_data(url):
    """
    Scrape Global Firepower military data from the given URL
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        print(f"Fetching data from: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all containers - both clickable and non-clickable
        clickable_containers = soup.find_all('div', class_='specsGenContainers picTrans3 zoom')
        non_clickable_containers = soup.find_all('div', class_='specsGenContainers')
        
        # Filter out clickable containers from non-clickable to avoid duplicates
        non_clickable_only = [c for c in non_clickable_containers if 'picTrans3' not in c.get('class', [])]
        
        all_containers = clickable_containers + non_clickable_only
        
        print(f"Found {len(all_containers)} data containers")
        
        data = []
        
        for container in all_containers:
            entry = extract_container_data(container)
            if entry:
                data.append(entry)
        
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def extract_container_data(container):
    """
    Extract data from a single container div
    """
    try:
        # Check if it's a clickable container (has link)
        parent_link = container.find_parent('a')
        is_clickable = parent_link is not None
        
        # Extract ranking information
        rank_info = {}
        rank_box = container.find('div', class_='specsRankBox')
        if rank_box:
            rank_text = rank_box.get_text(strip=True)
            rank_match = re.search(r'(\d+)/(\d+)', rank_text)
            if rank_match:
                rank_info = {
                    'current_rank': int(rank_match.group(1)),
                    'total_countries': int(rank_match.group(2))
                }
        
        # Extract label (yellow text)
        label_span = container.find('span', class_='textLarge textYellow textBold textShadow')
        if not label_span:
            # Try alternative for non-clickable containers
            label_span = container.find('span', class_='textLarge textDkGray textBold')
        
        label = label_span.get_text(strip=True) if label_span else None
        
        # Extract main value (white text)
        value_span = container.find('span', class_='textWhite textShadow')
        value_text = value_span.get_text(strip=True) if value_span else None
        
        # Extract percentage if present (gray text)
        percentage_span = container.find('span', class_='textLtrGray') or container.find('span', class_='textDkGray')
        percentage = None
        if percentage_span:
            pct_text = percentage_span.get_text(strip=True)
            # Extract percentage value
            pct_match = re.search(r'\(([\d.]+)%\)', pct_text)
            if pct_match:
                percentage = float(pct_match.group(1))
        
        # Parse numeric value
        numeric_value = None
        if value_text:
            clean_value = re.sub(r'[,\s]', '', value_text)
            try:
                numeric_value = int(clean_value) if '.' not in clean_value else float(clean_value)
            except ValueError:
                numeric_value = value_text
        
        # Get link information if clickable
        link_info = {}
        if is_clickable and parent_link:
            link_info = {
                'href': parent_link.get('href'),
                'title': parent_link.get('title')
            }
        
        # Only return entry if we have meaningful data
        if label and value_text:
            return {
                'label': label,
                'value': value_text,
                'numeric_value': numeric_value,
                'percentage': percentage,
                'ranking': rank_info,
                'is_clickable': is_clickable,
                'link_info': link_info if link_info else None
            }
        
        return None
        
    except Exception as e:
        print(f"Error processing container: {e}")
        return None

def scrape_from_html_file(html_content):
    """
    Scrape from HTML content (for testing with provided HTML)
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all containers
        clickable_containers = soup.find_all('div', class_='specsGenContainers picTrans3 zoom')
        non_clickable_containers = soup.find_all('div', class_='specsGenContainers')
        
        # Filter out clickable containers from non-clickable
        non_clickable_only = [c for c in non_clickable_containers if 'picTrans3' not in c.get('class', [])]
        
        all_containers = clickable_containers + non_clickable_only
        
        print(f"Found {len(all_containers)} data containers")
        
        data = []
        for container in all_containers:
            entry = extract_container_data(container)
            if entry:
                data.append(entry)
        
        return data
        
    except Exception as e:
        print(f"Error processing HTML: {e}")
        return None

def save_to_json(data, filename):
    """Save data to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving JSON: {e}")

# Test with the provided HTML content
if __name__ == "__main__":
    # Test HTML from the document
    test_html = '''
    <div class="contentSpecs" style="max-height: 778px;">
        <a href="/total-population-by-country.php" title="Total populations listed by country">
            <div class="specsGenContainers picTrans3 zoom">
                <div class="smallGraphIcon"><img class="noBorder" src="/imgs/misc/graph-red.gif" alt="Small graph icon"></div>
                <div class="specsRankBox">
                    <span class="textSmall1 textBold textLtrGray">
                        <span class="textWhite">2</span>/<span class="textLtrGray">145</span>
                    </span>
                </div>
            <span class="textLarge textYellow textBold textShadow">Total Population:</span>
                <br>
            <span class="textLarge textWhite textShadow">1,409,128,296</span>
        </div></a>
        
        <a href="/available-military-manpower.php" title="Available military manpower listed by country">
            <div class="specsGenContainers picTrans3 zoom">
                <div class="smallGraphIcon"><img class="noBorder" src="/imgs/misc/graph-red.gif" alt="Small graph icon"></div>
                <div class="specsRankBox">
                    <span class="textSmall1 textBold textLtrGray">
                        <span class="textWhite">2</span>/<span class="textLtrGray">145</span>
                    </span>
                </div>
            <span class="textLarge textYellow textBold textShadow">Available Manpower</span>
                <br>
            <span class="textLarge">
                <span class="textWhite textShadow">662,290,299</span> <span class="textLtrGray">(47.0%)</span>
            </span>
        </div></a>
        
        <div class="specsGenContainers" style="background-image:linear-gradient(to bottom,#FC0,#F90); cursor:auto;">
            <span class="textLarge textDkGray textBold">Tot Mil. Personnel (est.)</span>
                <br>
            <span class="textLarge">
                <span class="textWhite textShadow">5,137,550</span> <span class="textDkGray">(0.4%)</span>
            </span>
        </div>
    </div>
    '''
    
    print("Testing with provided HTML structure:")
    data = scrape_from_html_file(test_html)
    
    if data:
        print(f"\nSuccessfully extracted {len(data)} entries:")
        for i, entry in enumerate(data, 1):
            print(f"\n{i}. {entry['label']}")
            print(f"   Value: {entry['value']}")
            print(f"   Numeric: {entry['numeric_value']}")
            if entry['percentage']:
                print(f"   Percentage: {entry['percentage']}%")
            if entry['ranking']:
                print(f"   Rank: {entry['ranking']['current_rank']}/{entry['ranking']['total_countries']}")
            if entry['link_info']:
                print(f"   Link: {entry['link_info']['href']}")
        
        # Save sample data
        save_to_json(data, 'sample_military_data.json')
        
        print(f"\n{'-'*50}")
        print("JSON structure preview:")
        print(json.dumps(data[0], indent=2))
    
    print(f"\n{'-'*50}")
    print("To scrape live data from Global Firepower:")
    print("url = 'https://www.globalfirepower.com/country-military-strength-detail.php?country_id=india'")
    print("data = scrape_gfp_data(url)")
    print("save_to_json(data, 'india_military_data.json')")