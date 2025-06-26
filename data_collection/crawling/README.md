# Cafe Scraper - Enhanced Two-Phase Web Crawling

An intelligent web scraper designed specifically for crawling cafe and restaurant websites with a two-phase approach that gives you full control over what gets scraped.

## New Two-Phase Workflow

### Overview
The scraper now operates in two distinct phases:

1. **Phase 1: Link Discovery** - Discovers all links and saves them to a JSON file for manual curation
2. **Phase 2: HTML Scraping** - Scrapes HTML content only from the links you've approved

This approach gives you complete control over what gets scraped and allows for efficient link filtering.

### Directory Structure

The scraper automatically creates and organizes directories:

```
project_root/
├── crawled_links/
│   ├── lacabra_com.json
│   ├── bluebottle_com.json
│   └── ... (one JSON file per site)
└── scraped_html/
    ├── lacabra_com/
    │   ├── 000_lacabra_com_home.html
    │   ├── 001_lacabra_com_coffee.html
    │   ├── 002_lacabra_com_locations.html
    │   ├── ...
    │   └── scraping_summary.json
    └── bluebottle_com/
        ├── 000_bluebottle_com_home.html
        └── ...
```

## Usage

### Phase 1: Link Discovery

Discover all links from a website and save them for review:

```bash
# Basic discovery (scans up to 200 pages)
python3 cafe_scraper.py discover https://lacabra.com

# Discovery with custom page limit
python3 cafe_scraper.py discover https://lacabra.com 500
```

This creates `crawled_links/lacabra_com.json` with all discovered links.

### Manual Link Curation

After discovery, edit the JSON file to mark which links you want to scrape:

```bash
# Preview the discovered links
python3 cafe_scraper.py preview lacabra_com
```

Edit `crawled_links/lacabra_com.json` and change the `status` field:
- `"status": "keep"` - Links you want to scrape
- `"status": "skip"` - Links to ignore
- `"status": "pending"` - Default status (ignored during scraping)

### Phase 2: HTML Scraping

Scrape HTML content from approved links:

```bash
# Scrape all links marked as "keep"
python3 cafe_scraper.py scrape lacabra_com

# Scrape links with a different status
python3 cafe_scraper.py scrape lacabra_com pending
```

This creates `scraped_html/lacabra_com/` with all the HTML files.

## Link Discovery Features

The enhanced crawler discovers links through multiple methods:

- **Standard anchor tags** (`<a href="...">`)
- **JavaScript links** (URLs in JS code, event handlers)
- **Meta tags** (canonical, next/prev, redirects)
- **Form actions** (`<form action="...">`)
- **Data attributes** (`data-href`, `data-url`, etc.)
- **CSS content** (background images, @import)
- **JSON-LD structured data** (schema.org markup)
- **Microdata** (itemid, itemprop URLs)
- **HTTP headers** (Link header, redirects)
- **HTML comments** (commented URLs)

## JSON File Format

The links file contains detailed metadata for each discovered link:

```json
{
  "discovery_metadata": {
    "base_url": "https://lacabra.com",
    "site_name": "lacabra_com",
    "timestamp": "2024-01-01T12:00:00",
    "total_pages_scanned": 45,
    "total_links_found": 234
  },
  "discovered_links": [
    {
      "url": "https://lacabra.com/coffee",
      "source_page": "https://lacabra.com/",
      "discovery_method": "anchor",
      "link_type": "internal",
      "status": "pending",
      "notes": ""
    }
  ],
  "source_pages": [...]
}
```

## Legacy One-Phase Mode

The original workflow is still supported for backward compatibility:

```bash
# Old style - does discovery and scraping in one go
python3 cafe_scraper.py https://lacabra.com ./output_dir 200
```

## Advanced Usage

### Bulk Link Status Updates

You can programmatically update link statuses:

```python
from cafe_scraper import CafeScraper

scraper = CafeScraper()

# Mark all internal links as "keep"
scraper.update_links_status(
    "crawled_links/lacabra_com.json", 
    {"internal_only": "keep"}
)

# Skip all external links
scraper.update_links_status(
    "crawled_links/lacabra_com.json", 
    {"external": "skip"}
)

# Keep only links containing "coffee" or "menu"
scraper.update_links_status(
    "crawled_links/lacabra_com.json", 
    {"contains_coffee": "keep", "contains_menu": "keep"}
)
```

### Configuration Options

```python
# Create scraper with custom settings
scraper = CafeScraper(
    max_pages=500,           # Pages to scan during discovery
    verbose=True,            # Detailed logging
    aggressive_crawling=True # Enhanced link discovery
)
```

## Benefits of Two-Phase Approach

1. **Full Control** - Review every link before scraping
2. **Efficiency** - Only scrape the content you need
3. **Transparency** - See exactly what links were discovered and how
4. **Flexibility** - Re-run scraping with different link selections
5. **Speed** - Link discovery is much faster than full scraping
6. **Organization** - Automatic directory structure and naming

## Requirements

- Python 3.7+
- requests
- beautifulsoup4
- pathlib

Install dependencies:
```bash
pip install -r requirements.txt
```

## Features ✨

### 🕷️ Intelligent Web Crawling

- **Automatic Link Discovery**: Recursively finds and crawls all pages on a cafe website
- **Respectful Crawling**: Built-in rate limiting and polite crawling practices
- **Concurrent Processing**: Multi-threaded crawling for efficiency
- **Smart Filtering**: Automatically filters out irrelevant content (images, PDFs, etc.)

### 🧠 LLM-Powered Data Extraction

- **Flexible Structure Recognition**: Works with any cafe website layout without manual configuration
- **Structured Data Output**: Extracts information into well-defined Pydantic models
- **Multiple LLM Support**: Works with OpenAI API, local models, or mock data for testing

### 📊 Comprehensive Data Models

- **Level 1 Bean Info**: Name, weight, price, producer, region, roast level, flavor notes, grind type
- **Level 2 Specialty Info**: Farm, altitude, process, Agtron roast level, brew types, bean type, variety
- **Menu Information**: Beverage names, descriptions, prices, sizes, categories, ingredients

## Installation 🚀

1. **Clone or download the files** to your project directory

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Optional: Set up OpenAI API** (for best results):
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

## Quick Start 🏃‍♂️

### Basic Usage (Mock LLM)

```python
from data_collection.crawling import quick_scrape

# Simple scrape with mock LLM (no API key needed)
result = quick_scrape("https://example-cafe.com")
print(f"Found {len(result.coffee_beans)} coffee beans")
```

### Advanced Usage (OpenAI)

```python
from data_collection.crawling import CafeScraper, LLMConfig

# Configure for OpenAI
llm_config = LLMConfig(
    model_type="openai",
    model_name="gpt-3.5-turbo",
    api_key="your-api-key"
)

# Create scraper and run
scraper = CafeScraper(llm_config)
result = scraper.scrape_cafe_website(
    url="https://example-cafe.com",
    output_file="results/cafe_data.json"
)

# Print summary
scraper.print_summary(result)
```

### Command Line Usage

```bash
# Basic usage
python cafe_scraper.py https://example-cafe.com

# With output file
python cafe_scraper.py https://example-cafe.com results/cafe.json

# With OpenAI API key
python cafe_scraper.py https://example-cafe.com results/cafe.json sk-your-api-key
```

## Data Models 📋

### Coffee Bean Information

```python
# Level 1: General Information
BeanInfo(
    name="Ethiopian Yirgacheffe",
    weight="12oz",
    price="$18.99",
    producer="Konga Cooperative",
    region="Yirgacheffe, Ethiopia",
    roast_level="medium",
    flavor_notes=["citrus", "floral", "bright acidity"],
    grind_type="whole"
)

# Level 2: Specialty Information
SpecialtyBeanInfo(
    farm="Konga Cooperative",
    altitude="1800-2000 masl",
    process="washed",
    agtron_roast_level="55",
    suitable_brew_types=["pour_over", "drip"],
    bean_type="arabica",
    variety="Heirloom"
)
```

### Menu Items

```python
MenuItem(
    name="Cappuccino",
    description="Espresso with steamed milk and foam",
    price="$4.50",
    sizes=["8oz", "12oz", "16oz"],
    category="espresso drinks",
    ingredients=["espresso", "steamed milk", "foam"]
)
```

## Configuration ⚙️

### Crawler Configuration

```python
from data_collection.crawling import CrawlConfig, WebCrawler

config = CrawlConfig(
    max_pages=30,                    # Maximum pages to crawl
    delay_between_requests=1.5,      # Seconds between requests
    max_workers=3,                   # Concurrent workers
    timeout=30,                      # Request timeout
    follow_external_links=False,     # Stay on same domain
    user_agent="CafeCrawler/1.0"     # Custom user agent
)

crawler = WebCrawler(config)
```

### LLM Configuration

```python
from data_collection.crawling import LLMConfig

config = LLMConfig(
    model_type="openai",        # "openai", "local", or "mock"
    model_name="gpt-3.5-turbo", # Model to use
    api_key="your-key",         # API key
    temperature=0.1,            # Creativity level (0-1)
    max_tokens=2000,           # Max response length
    chunk_size=4000            # Text chunk size for processing
)
```

## Examples 📚

### Run All Examples

```bash
python example_usage.py
```

### Custom Processing

```python
from data_collection.crawling import CafeScraper

scraper = CafeScraper()

# Scrape website
result = scraper.scrape_cafe_website("https://cafe.com")

# Access specific data
for bean in result.coffee_beans:
    print(f"Bean: {bean.basic_info.name}")
    print(f"Price: {bean.basic_info.price}")
    print(f"Region: {bean.basic_info.region}")

    if bean.specialty_info:
        print(f"Farm: {bean.specialty_info.farm}")
        print(f"Process: {bean.specialty_info.process}")

# Access menu
if result.menu:
    for item in result.menu.items:
        print(f"Drink: {item.name} - {item.price}")
```

### Load Previously Scraped Data

```python
scraper = CafeScraper()

# Load from file
data = scraper.load_results("results/cafe_data.json")

# Generate summary
summary = scraper.get_summary(data)
print(f"Found {summary['coffee_beans']['total_count']} beans")
```

## Output Format 📄

The scraper generates JSON output with the following structure:

```json
{
  "cafe_name": "Example Cafe",
  "base_url": "https://example-cafe.com",
  "timestamp": "2024-01-15T10:30:00",
  "coffee_beans": [
    {
      "basic_info": {
        "name": "Ethiopian Yirgacheffe",
        "weight": "12oz",
        "price": "$18.99",
        "producer": "Konga Cooperative",
        "region": "Yirgacheffe, Ethiopia",
        "roast_level": "medium",
        "flavor_notes": ["citrus", "floral"],
        "grind_type": "whole"
      },
      "specialty_info": {
        "farm": "Konga Cooperative",
        "altitude": "1800-2000 masl",
        "process": "washed",
        "bean_type": "arabica",
        "variety": "Heirloom"
      },
      "source_url": "https://example-cafe.com/coffee/ethiopian"
    }
  ],
  "menu": {
    "items": [
      {
        "name": "Cappuccino",
        "description": "Espresso with steamed milk",
        "price": "$4.50",
        "sizes": ["8oz", "12oz"],
        "category": "espresso drinks"
      }
    ],
    "cafe_name": "Example Cafe",
    "source_url": "https://example-cafe.com/menu"
  },
  "all_urls_crawled": ["https://example-cafe.com", "..."]
}
```

## Architecture 🏗️

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebCrawler    │───▶│  LLMProcessor   │───▶│  CafeScraper    │
│                 │    │                 │    │                 │
│ • Discovers URLs│    │ • Extracts data │    │ • Orchestrates  │
│ • Downloads HTML│    │ • Uses LLM      │    │ • Saves results │
│ • Cleans content│    │ • Structures    │    │ • Generates     │
│                 │    │   output        │    │   summaries     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## LLM Integration 🤖

### OpenAI API (Recommended)

- Best accuracy for data extraction
- Requires API key and credits
- Supports GPT-3.5-turbo and GPT-4

### Local Models

- Free to use after initial setup
- Requires more computational resources
- Privacy-focused (no data sent externally)

### Mock Mode

- Perfect for testing and development
- Returns example data structure
- No external dependencies

## Best Practices 🌟

### Respectful Crawling

- Built-in rate limiting (1.5s between requests)
- Conservative parallelism (3 workers max)
- Proper user agent identification
- Respects robots.txt (implement if needed)

### Data Quality

- LLM prompts designed for coffee-specific extraction
- Structured output validation with Pydantic
- Fallback handling for missing information
- Source URL tracking for verification

### Performance

- Concurrent crawling with ThreadPoolExecutor
- Intelligent page filtering
- Chunked text processing for large pages
- Memory-efficient HTML processing

## Troubleshooting 🔧

### Common Issues

**No data extracted:**

- Check if the website has coffee/bean information
- Verify LLM is working (try mock mode first)
- Ensure pages are accessible (check status codes)

**Crawler not finding pages:**

- Website might use JavaScript navigation
- Check if links are in standard `<a>` tags
- Verify domain restrictions in config

**LLM errors:**

- Check API key is valid
- Verify internet connection for API calls
- Try reducing chunk_size or max_tokens

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed crawling and processing logs
```

## Contributing 🤝

This scraper is designed to be extensible:

1. **Add new LLM providers** in `llm_processor.py`
2. **Enhance data models** in `models.py`
3. **Improve crawling logic** in `web_crawler.py`
4. **Add new output formats** in `cafe_scraper.py`

## License 📝

This project is designed for educational and research purposes. Please ensure you comply with websites' terms of service and robots.txt when scraping.

---

**Happy Coffee Scraping! ☕🔍**
