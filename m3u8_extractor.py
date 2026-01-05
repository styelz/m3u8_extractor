import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json
from datetime import datetime
import time
from playwright.sync_api import sync_playwright
import xml.etree.ElementTree as ET
from xml.dom import minidom

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
        """Extract m3u8 URL and published time from a page"""
        try:
            response = requests.get(page_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract article:published_time meta property
            published_time = None
            meta_tag = soup.find('meta', property='article:published_time')
            if meta_tag and meta_tag.get('content'):
                published_time = meta_tag['content']
            
            # Look for m3u8 URL in various common patterns
            patterns = [
                r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
                r'"([^"]*\.m3u8[^"]*)"',
                r"'([^']*\.m3u8[^']*)'",
            ]
            
            m3u8_url = None
            for pattern in patterns:
                matches = re.findall(pattern, html_content)
                if matches:
                    # Return first match
                    m3u8_url = matches[0]
                    if isinstance(m3u8_url, tuple):
                        m3u8_url = m3u8_url[0]
                    m3u8_url = m3u8_url.strip()
                    break
            
            return m3u8_url, published_time
        except requests.RequestException as e:
            print(f"Error fetching page {page_url}: {e}")
            return None, None
    
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
            m3u8_url, published_time = self.extract_m3u8_from_page(page_url)
            
            if m3u8_url:
                self.videos.append({
                    'page_url': page_url,
                    'm3u8_url': m3u8_url,
                    'published_time': published_time
                })
                print(f"  ✓ Found m3u8: {m3u8_url[:80]}...")
            else:
                print(f"  ✗ No m3u8 URL found")
        
        return self.videos
    

    
    def _format_rss_date(self, date_str):
        """Convert ISO 8601 date to RFC 2822 format for RSS compatibility"""
        if not date_str:
            return datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        try:
            # Try parsing ISO 8601 format
            if 'T' in date_str:
                # Remove timezone info and parse
                date_str_clean = date_str.replace('+00:00', '').replace('Z', '')
                dt = datetime.fromisoformat(date_str_clean)
            else:
                # Already in standard format or other format
                return date_str
            
            return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        except:
            return datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    def generate_rss_feed(self, filename='rss.xml'):
        """Generate an RSS feed as an XML file"""
        # Create RSS XML structure
        rss = ET.Element('rss', version='2.0')
        channel = ET.SubElement(rss, 'channel')
        
        # Add channel metadata
        title = ET.SubElement(channel, 'title')
        title.text = 'm3u8 Video Feed'
        
        link = ET.SubElement(channel, 'link')
        link.text = self.category_url
        
        description = ET.SubElement(channel, 'description')
        description.text = 'Extracted m3u8 URLs from video pages'
        
        last_build_date = ET.SubElement(channel, 'lastBuildDate')
        last_build_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        # Add items for each video
        for video in self.videos:
            item = ET.SubElement(channel, 'item')
            
            item_title = ET.SubElement(item, 'title')
            item_title.text = f'Video - {video["m3u8_url"][:50]}...'
            
            item_link = ET.SubElement(item, 'link')
            item_link.text = video['page_url']
            
            item_description = ET.SubElement(item, 'description')
            item_description.text = f'm3u8 URL: {video["m3u8_url"]}'
            
            item_guid = ET.SubElement(item, 'guid', isPermaLink='false')
            item_guid.text = video['m3u8_url']
            
            pub_date = ET.SubElement(item, 'pubDate')
            pub_date.text = self._format_rss_date(video.get('published_time'))
            
            # Add enclosure for media (important for podcast readers)
            enclosure = ET.SubElement(item, 'enclosure')
            enclosure.set('url', video['m3u8_url'])
            enclosure.set('type', 'application/x-mpegURL')
            enclosure.set('length', '0')
        
        # Pretty print XML
        xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent='  ')
        # Remove extra blank lines
        xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
        
        # Write XML file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        print(f"\nRSS feed generated: {filename}")


if __name__ == "__main__":
    # Category page URL (loads more videos on scroll)
    category_url = "https://fintech.tv/category/market-movers-the-opening-bell/"
    
    # Create extractor and process
    extractor = RSSm3u8Extractor(category_url)
    videos = extractor.process()
    
    # Save results
    if videos:
        extractor.generate_rss_feed()
        print(f"\nSuccessfully extracted {len(videos)} m3u8 URLs")
    else:
        print("\nNo m3u8 URLs were extracted")
