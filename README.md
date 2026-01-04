# RSS m3u8 Extractor

A Python script that extracts m3u8 URLs from an RSS feed of video pages.

## Features

- Fetches RSS feed from a given URL
- Extracts individual page URLs from RSS items
- Scrapes each page to find m3u8 video URLs
- Saves results in multiple formats (JSON and text)

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
python rss_m3u8_extractor.py
```

The script will:
1. Fetch the RSS feed from the configured URL
2. Extract all page URLs from RSS items
3. Visit each page and search for m3u8 URLs
4. Save results to:
   - `m3u8_results.json` - Full details with timestamps
   - `m3u8_urls.txt` - Just the m3u8 URLs (one per line)

## Output Files

- **m3u8_results.json**: JSON file containing:
  - Page URL
  - m3u8 URL
  - Extraction timestamp

- **m3u8_urls.txt**: Plain text file with m3u8 URLs (one per line)

## Configuration

Edit the `rss_url` variable in the `if __name__ == "__main__":` section to use a different RSS feed.

## How it works

1. **Fetch RSS**: Downloads and parses the RSS feed
2. **Extract Links**: Gets the URL for each video page from the RSS items
3. **Scrape Pages**: Visits each page and searches for m3u8 URLs using regex patterns
4. **Save Results**: Exports findings to JSON and text formats

## Notes

- The script includes error handling for network timeouts and failures
- Uses User-Agent header to avoid being blocked by some servers
- Progress indicators show which page is being processed
- Both successful and failed extractions are logged
