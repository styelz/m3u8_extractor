import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json
from datetime import datetime
import time
from playwright.sync_api import sync_playwright

class RSSm3u8Extractor:
    def __init__(self, category_url):
        self.category_url = category_url
        self.videos = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_category_page_with_scroll(self):
        """Fetch category page and scroll to load all videos"""
        try:
            with sync_playwright() as p:
                print("Launching browser...")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                print(f"Loading page: {self.category_url}")
                page.goto(self.category_url, wait_until="networkidle")
                
                # Scroll to load more content
                last_height = page.evaluate("document.body.scrollHeight")
                scroll_pause_time = 2
                max_scrolls = 20  # Limit scrolls to avoid infinite scrolling
                scroll_count = 0
                
                print("Scrolling to load all videos...")
                while scroll_count < max_scrolls:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(scroll_pause_time)
                    
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        print("Reached end of page")
                        break
                    
                    last_height = new_height
                    scroll_count += 1
                    print(f"Scroll {scroll_count}/{max_scrolls}")
                
                # Get page content
                html_content = page.content()
                browser.close()
                
                return BeautifulSoup(html_content, 'html.parser')
            
        except Exception as e:
            print(f"Error loading page: {e}")
            return None
    
    def extract_page_urls_from_content(self, soup):
        """Extract video page URLs from the category page"""
        if not soup:
            return []
        
        page_urls = []
        
        # Look for article links or post links
        # Common patterns: article elements, post divs, or links containing the domain
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '').strip()
            
            # Filter for fintech.tv article links (but not the category page itself)
            if 'fintech.tv' in href and href != self.category_url and not href.endswith('/feed/'):
                # Make sure it's not a category or tag page
                if '/category/' not in href and '/tag/' not in href:
                    if href not in page_urls:
                        page_urls.append(href)
        
        return page_urls
    
    def extract_m3u8_from_page(self, page_url):
        """Extract m3u8 URL from a page"""
        try:
            response = requests.get(page_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            
            # Look for m3u8 URL in various common patterns
            patterns = [
                r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
                r'"([^"]*\.m3u8[^"]*)"',
                r"'([^']*\.m3u8[^']*)'",
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    # Return first match
                    m3u8_url = matches[0]
                    if isinstance(m3u8_url, tuple):
                        m3u8_url = m3u8_url[0]
                    return m3u8_url.strip()
            
            return None
        except requests.RequestException as e:
            print(f"Error fetching page {page_url}: {e}")
            return None
    
    def process(self):
        """Main processing function"""
        print("Fetching category page with dynamic content...")
        soup = self.fetch_category_page_with_scroll()
        
        if not soup:
            print("Failed to fetch category page")
            return []
        
        print("Extracting video page URLs...")
        page_urls = self.extract_page_urls_from_content(soup)
        print(f"Found {len(page_urls)} video page URLs")
        
        print("\nExtracting m3u8 URLs from each page...")
        for i, page_url in enumerate(page_urls, 1):
            print(f"[{i}/{len(page_urls)}] Processing: {page_url}")
            m3u8_url = self.extract_m3u8_from_page(page_url)
            
            if m3u8_url:
                self.videos.append({
                    'page_url': page_url,
                    'm3u8_url': m3u8_url,
                    'extracted_at': datetime.now().isoformat()
                })
                print(f"  ✓ Found m3u8: {m3u8_url[:80]}...")
            else:
                print(f"  ✗ No m3u8 URL found")
        
        return self.videos
    
    def save_results(self, filename='m3u8_results.json'):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.videos, f, indent=2)
        print(f"\nResults saved to {filename}")
    
    def save_m3u8_list(self, filename='m3u8_urls.txt'):
        """Save m3u8 URLs to text file"""
        with open(filename, 'w') as f:
            for video in self.videos:
                f.write(f"{video['m3u8_url']}\n")
        print(f"m3u8 URLs saved to {filename}")


if __name__ == "__main__":
    # Category page URL (loads more videos on scroll)
    category_url = "https://fintech.tv/category/market-movers-the-opening-bell/"
    
    # Create extractor and process
    extractor = RSSm3u8Extractor(category_url)
    videos = extractor.process()
    
    # Save results
    if videos:
        extractor.save_results()
        extractor.save_m3u8_list()
        print(f"\nSuccessfully extracted {len(videos)} m3u8 URLs")
    else:
        print("\nNo m3u8 URLs were extracted")
