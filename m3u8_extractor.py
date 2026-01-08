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
import argparse

# Register media namespace for RSS
ET.register_namespace('media', 'http://search.yahoo.com/mrss/')

class RSSm3u8Extractor:
    def __init__(self, category_url, limit_first_page=False, max_scrolls=20):
        self.category_url = category_url
        self.videos = []
        self.limit_first_page = limit_first_page
        self.max_scrolls = max_scrolls
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
                try:
                    page.goto(self.category_url, wait_until="load", timeout=30000)
                except Exception as e:
                    print(f"Warning: Page load encountered an issue: {e}")
                    print("Continuing anyway as page may have partially loaded...")
                
                # Scroll to load more content
                last_height = page.evaluate("document.body.scrollHeight")
                scroll_pause_time = 5  # seconds
                scroll_count = 0
                
                print(f"Scrolling to load all videos (max {self.max_scrolls} scrolls)...")
                while scroll_count < self.max_scrolls:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(scroll_pause_time)
                    
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        print("Reached end of page")
                        break
                    
                    last_height = new_height
                    scroll_count += 1
                    print(f"Scroll {scroll_count}/{self.max_scrolls}")
                    
                    # Stop after first scroll if limit_first_page is set
                    if self.limit_first_page:
                        print("Limiting to first page only (--first-page flag set)")
                        break
                
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
        """Extract m3u8 URL and metadata from a page"""
        try:
            response = requests.get(page_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract Open Graph and metadata properties
            metadata = {
                'title': None,
                'description': None,
                'published_time': None,
                'modified_time': None,
                'image': None,
                'image_width': None,
                'image_height': None,
                'author': None,
                'og_url': None
            }
            
            # Extract og:title
            meta_tag = soup.find('meta', property='og:title')
            if meta_tag and meta_tag.get('content'):
                metadata['title'] = meta_tag['content']
            
            # Extract og:description
            meta_tag = soup.find('meta', property='og:description')
            if meta_tag and meta_tag.get('content'):
                metadata['description'] = meta_tag['content']
            
            # Extract article:published_time
            meta_tag = soup.find('meta', property='article:published_time')
            if meta_tag and meta_tag.get('content'):
                metadata['published_time'] = meta_tag['content']
            
            # Extract article:modified_time
            meta_tag = soup.find('meta', property='article:modified_time')
            if meta_tag and meta_tag.get('content'):
                metadata['modified_time'] = meta_tag['content']
            
            # Extract og:image
            meta_tag = soup.find('meta', property='og:image')
            if meta_tag and meta_tag.get('content'):
                metadata['image'] = meta_tag['content']
            
            # Extract og:image:width
            meta_tag = soup.find('meta', property='og:image:width')
            if meta_tag and meta_tag.get('content'):
                metadata['image_width'] = meta_tag['content']
            
            # Extract og:image:height
            meta_tag = soup.find('meta', property='og:image:height')
            if meta_tag and meta_tag.get('content'):
                metadata['image_height'] = meta_tag['content']
            
            # Extract author
            meta_tag = soup.find('meta', attrs={'name': 'author'})
            if meta_tag and meta_tag.get('content'):
                metadata['author'] = meta_tag['content']
            
            # Extract og:url
            meta_tag = soup.find('meta', property='og:url')
            if meta_tag and meta_tag.get('content'):
                metadata['og_url'] = meta_tag['content']
            
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
            
            return m3u8_url, metadata
        except requests.RequestException as e:
            print(f"Error fetching page {page_url}: {e}")
            return None, {}
    
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
        
        print("\nExtracting m3u8 URLs and metadata from each page...")
        for i, page_url in enumerate(page_urls, 1):
            print(f"[{i}/{len(page_urls)}] Processing: {page_url}")
            m3u8_url, metadata = self.extract_m3u8_from_page(page_url)
            
            if m3u8_url:
                self.videos.append({
                    'page_url': page_url,
                    'm3u8_url': m3u8_url,
                    'metadata': metadata
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
        """Generate an RSS feed as an XML file with rich metadata"""
        # Create RSS XML structure with media namespace
        rss = ET.Element('rss', {
            'version': '2.0',
            'xmlns:media': 'http://search.yahoo.com/mrss/'
        })
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
            metadata = video.get('metadata', {})
            
            # Use og:title if available, otherwise fallback to generic title
            item_title = ET.SubElement(item, 'title')
            item_title.text = metadata.get('title') or f'Video - {video["m3u8_url"][:50]}...'
            
            # Use og:url if available, otherwise use page_url
            item_link = ET.SubElement(item, 'link')
            item_link.text = metadata.get('og_url') or video['page_url']
            
            # Use og:description if available
            item_description = ET.SubElement(item, 'description')
            description_text = metadata.get('description') or f'm3u8 URL: {video["m3u8_url"]}'
            item_description.text = description_text
            
            # Add author if available
            if metadata.get('author'):
                item_author = ET.SubElement(item, 'author')
                item_author.text = metadata['author']
            
            item_guid = ET.SubElement(item, 'guid', isPermaLink='false')
            item_guid.text = video['m3u8_url']
            
            # Use published_time from metadata
            pub_date = ET.SubElement(item, 'pubDate')
            pub_date.text = self._format_rss_date(metadata.get('published_time'))
            
            # Add image as media:content if available
            if metadata.get('image'):
                media_content = ET.SubElement(item, '{http://search.yahoo.com/mrss/}content')
                media_content.set('url', metadata['image'])
                media_content.set('type', 'image/jpeg')
                if metadata.get('image_width'):
                    media_content.set('width', metadata['image_width'])
                if metadata.get('image_height'):
                    media_content.set('height', metadata['image_height'])
            
            # Add enclosure for media (important for podcast readers)
            enclosure = ET.SubElement(item, 'enclosure')
            enclosure.set('url', video['m3u8_url'])
            enclosure.set('type', 'application/x-mpegURL')
            enclosure.set('length', '0')
        
        # Convert to string and pretty print
        xml_bytes = ET.tostring(rss, encoding='utf-8')
        # Decode and parse for pretty printing
        try:
            dom = minidom.parseString(xml_bytes)
            xml_str = dom.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
        except Exception as e:
            # If minidom fails, just use the raw XML with basic formatting
            print(f"Warning: Could not pretty-print XML ({e}), using basic formatting")
            xml_str = xml_bytes.decode('utf-8')
        
        # Remove extra blank lines
        xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
        
        # Write XML file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        print(f"\nRSS feed generated: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract m3u8 URLs from fintech.tv category page and generate RSS feed')
    parser.add_argument('--first-page', action='store_true', 
                        help='Only process the first page without scrolling for more content')
    parser.add_argument('--max-scrolls', type=int, default=20, metavar='NUM',
                        help='Maximum number of scrolls to perform (default: 20)')
    args = parser.parse_args()
    
    # Category page URL (loads more videos on scroll)
    category_url = "https://fintech.tv/category/market-movers-the-opening-bell/"
    
    # Create extractor and process
    extractor = RSSm3u8Extractor(category_url, limit_first_page=args.first_page, max_scrolls=args.max_scrolls)
    videos = extractor.process()
    
    # Save results
    if videos:
        extractor.generate_rss_feed()
        print(f"\nSuccessfully extracted {len(videos)} m3u8 URLs")
    else:
        print("\nNo m3u8 URLs were extracted")
