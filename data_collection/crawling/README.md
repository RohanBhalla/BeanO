# Cafe Web Scraper 🔍☕

A robust and intelligent web crawler and scraper designed specifically for coffee shop and cafe websites. This system automatically discovers all pages on a cafe website, extracts HTML content, and uses LLM processing to extract structured information about coffee beans and menu items.

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
