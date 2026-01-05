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
    
    def generate_rss_webpage(self, filename='rss.html'):
        """Generate an RSS feed as an HTML webpage"""
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
            pub_date.text = video.get('published_time', datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'))
        
        # Pretty print XML
        xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent='  ')
        # Remove extra blank lines
        xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
        
        # Create HTML webpage with embedded RSS and display
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>m3u8 Video Feed</title>
    <link rel="alternate" type="application/rss+xml" href="#" title="m3u8 Video Feed">
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
        }}
        .feed-info {{
            background-color: #fff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .video-item {{
            background-color: #fff;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #0066cc;
            border-radius: 3px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .video-item h3 {{
            margin-top: 0;
            color: #0066cc;
        }}
        .video-url {{
            word-break: break-all;
            font-family: monospace;
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 3px;
            font-size: 12px;
        }}
        .page-link {{
            color: #0066cc;
            text-decoration: none;
        }}
        .page-link:hover {{
            text-decoration: underline;
        }}
        .timestamp {{
            color: #666;
            font-size: 12px;
        }}
        .rss-link {{
            display: inline-block;
            background-color: #ff6600;
            color: white;
            padding: 10px 15px;
            border-radius: 3px;
            text-decoration: none;
            margin-bottom: 20px;
        }}
        .rss-link:hover {{
            background-color: #e55a00;
        }}
    </style>
</head>
<body>
    <h1>m3u8 Video Feed</h1>
    
    <div class="feed-info">
        <p><strong>Total Videos:</strong> {len(self.videos)}</p>
        <p><strong>Source:</strong> <a href="{self.category_url}" class="page-link">{self.category_url}</a></p>
        <p><strong>Generated:</strong> <span class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></p>
    </div>
    
    <div id="rss-section" style="background-color: #fff; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <h2>RSS Feed</h2>
        <p>RSS feed is embedded below. You can subscribe to this feed in your feed reader:</p>
        <pre style="background-color: #f9f9f9; padding: 10px; overflow-x: auto; border-radius: 3px;"><code>{xml_str}</code></pre>
    </div>
    
    <h2>Videos</h2>
"""
        
        # Add video items
        for i, video in enumerate(self.videos, 1):
            html_content += f"""    <div class="video-item">
        <h3>Video #{i}</h3>
        <p><strong>Page:</strong> <a href="{video['page_url']}" class="page-link" target="_blank">{video['page_url']}</a></p>
        <p><strong>m3u8 URL:</strong></p>
        <div class="video-url"><a href="{video['m3u8_url']}" target="_blank">{video['m3u8_url']}</a></div>
        <p class="timestamp"><strong>Published:</strong> {video.get('published_time', 'Unknown')}</p>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # Write HTML file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nRSS webpage generated: {filename}")


if __name__ == "__main__":
    # Category page URL (loads more videos on scroll)
    category_url = "https://fintech.tv/category/market-movers-the-opening-bell/"
    
    # Create extractor and process
    extractor = RSSm3u8Extractor(category_url)
    videos = extractor.process()
    
    # Save results
    if videos:
        extractor.generate_rss_webpage()
        print(f"\nSuccessfully extracted {len(videos)} m3u8 URLs")
    else:
        print("\nNo m3u8 URLs were extracted")
