# m3u8 Extractor

A Python script that extracts m3u8 URLs from a website.

## Features

- Fetches a website category page and scrolls to load all videos
- Scrapes the page to find m3u8 video URLs
- Generates a standard RSS feed XML file

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

### Command-line Options

- `--first-page`: Only process the first page without scrolling for more content

```bash
python m3u8_extractor.py --first-page
```

The script will:
1. Fetch the website from the configured URL
2. Scroll through the page to load all videos (or stop after the first page if `--first-page` is used)
3. Extract m3u8 URLs from the page
4. Extract article publication times from each page's meta properties
5. Generate an RSS XML feed file

## Output Files

- **rss.xml**: Standard RSS feed in XML format containing:
  - Channel metadata (title, link, description, last build date)
  - Feed items for each extracted video
  - Links to original page URLs and m3u8 URLs
  - Publication times from page meta properties

## Configuration

Edit the `category_url` variable in the `if __name__ == "__main__":` section to use a different website URL.

## How it works

1. **Fetch Page**: Loads the category page and scrolls to dynamically load all videos
2. **Extract Links**: Finds all video page URLs from the loaded content
3. **Scrape Pages**: Visits each page and searches for m3u8 URLs using regex patterns, also extracts the `article:published_time` meta property
4. **Generate Feed**: Creates an RSS XML feed with metadata and video entries

## Notes

- The script includes error handling for network timeouts and failures
- Uses User-Agent header to avoid being blocked by some servers
- Uses Playwright for dynamic page scrolling to load all content
- Progress indicators show which page is being processed
- Both successful and failed extractions are logged
- The generated RSS file is compatible with standard RSS feed readers
