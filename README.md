# m3u8 Extractor

A Python script that extracts m3u8 URLs from a website.

## Features

- Fetches a website category page and scrolls to load all videos
- Scrapes the page to find m3u8 video URLs
- Generates an RSS feed as an HTML webpage with embedded feed and video listings

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Usage

```bash
python m3u8_extractor.py
```

The script will:
1. Fetch the website from the configured URL
2. Scroll through the page to load all videos
3. Extract m3u8 URLs from the page
4. Extract article publication times from each page's meta properties
5. Generate an HTML webpage with:
   - Embedded RSS XML feed
   - Formatted display of all extracted videos with clickable links
   - Feed metadata and article publication times

## Output Files

- **rss.html**: HTML webpage containing:
  - Embedded RSS feed in XML format
  - Formatted list of all extracted videos
  - Clickable links to both page URLs and m3u8 URLs
  - Article publication times from page meta properties

## Configuration

Edit the `category_url` variable in the `if __name__ == "__main__":` section to use a different website URL.

## How it works

1. **Fetch Page**: Loads the category page and scrolls to dynamically load all videos
2. **Extract Links**: Finds all video page URLs from the loaded content
3. **Scrape Pages**: Visits each page and searches for m3u8 URLs using regex patterns, also extracts the `article:published_time` meta property
4. **Generate Feed**: Creates an HTML webpage with an embedded RSS feed and formatted video listings, using actual publication times

## Notes

- The script includes error handling for network timeouts and failures
- Uses User-Agent header to avoid being blocked by some servers
- Uses Playwright for dynamic page scrolling to load all content
- Progress indicators show which page is being processed
- Both successful and failed extractions are logged
- The generated HTML file can be viewed in any web browser
- The embedded RSS feed can be used in RSS feed readers
