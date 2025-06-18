import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from .web_crawler import WebCrawler, create_coffee_crawler
    from .llm_processor import LLMProcessor, LLMConfig
    from .models import ScrapedData
except ImportError:
    from web_crawler import WebCrawler, create_coffee_crawler
    from llm_processor import LLMProcessor, LLMConfig
    from models import ScrapedData

logger = logging.getLogger(__name__)

class CafeScraper:
    """
    Main orchestrator for scraping cafe websites
    Combines web crawling with LLM processing to extract structured data
    """
    
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.crawler = create_coffee_crawler()
        self.llm_processor = LLMProcessor(llm_config)
        
    def scrape_cafe_website(self, url: str, output_file: Optional[str] = None) -> ScrapedData:
        """
        Complete pipeline to scrape a cafe website
        
        Args:
            url: Starting URL of the cafe website
            output_file: Optional file path to save results as JSON
            
        Returns:
            ScrapedData object with all extracted information
        """
        logger.info(f"Starting complete scrape of cafe website: {url}")
        
        try:
            # Step 1: Crawl the website
            logger.info("Step 1: Crawling website...")
            crawl_result = self.crawler.crawl_website(url)
            
            if not crawl_result['pages']:
                logger.error(f"No pages found during crawl of {url}")
                return ScrapedData(base_url=url, timestamp=datetime.now().isoformat())
            
            logger.info(f"Crawled {len(crawl_result['pages'])} pages")
            
            # Step 2: Process with LLM
            logger.info("Step 2: Processing content with LLM...")
            scraped_data = self.llm_processor.process_crawled_data(crawl_result)
            scraped_data.timestamp = datetime.now().isoformat()
            
            # Step 3: Save results if requested
            if output_file:
                self.save_results(scraped_data, output_file)
            
            # Log summary
            bean_count = len(scraped_data.coffee_beans)
            menu_count = len(scraped_data.menu.items) if scraped_data.menu else 0
            logger.info(f"Scraping completed! Found {bean_count} coffee beans and {menu_count} menu items")
            
            return scraped_data
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise
        finally:
            self.crawler.close()
    
    def save_results(self, scraped_data: ScrapedData, output_file: str):
        """Save scraped data to JSON file"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict for JSON serialization
            data_dict = scraped_data.dict()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def load_results(self, input_file: str) -> ScrapedData:
        """Load previously scraped data from JSON file"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data_dict = json.load(f)
            
            return ScrapedData(**data_dict)
            
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            raise
    
    def get_summary(self, scraped_data: ScrapedData) -> Dict[str, Any]:
        """Generate a summary of scraped data"""
        summary = {
            "cafe_name": scraped_data.cafe_name,
            "base_url": scraped_data.base_url,
            "timestamp": scraped_data.timestamp,
            "total_pages_crawled": len(scraped_data.all_urls_crawled),
            "coffee_beans": {
                "total_count": len(scraped_data.coffee_beans),
                "beans_with_specialty_info": len([b for b in scraped_data.coffee_beans if b.specialty_info]),
                "unique_regions": list(set(b.basic_info.region for b in scraped_data.coffee_beans if b.basic_info.region)),
                "roast_levels": list(set(b.basic_info.roast_level for b in scraped_data.coffee_beans if b.basic_info.roast_level))
            },
            "menu": {
                "total_items": len(scraped_data.menu.items) if scraped_data.menu else 0,
                "categories": list(set(item.category for item in scraped_data.menu.items if item.category)) if scraped_data.menu else []
            }
        }
        
        return summary
    
    def print_summary(self, scraped_data: ScrapedData):
        """Print a human-readable summary of scraped data"""
        summary = self.get_summary(scraped_data)
        
        print(f"\n{'='*60}")
        print(f"CAFE SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"Cafe: {summary['cafe_name'] or 'Unknown'}")
        print(f"URL: {summary['base_url']}")
        print(f"Scraped at: {summary['timestamp']}")
        print(f"Pages crawled: {summary['total_pages_crawled']}")
        
        print(f"\n{'Coffee Beans:'}")
        print(f"- Total beans found: {summary['coffee_beans']['total_count']}")
        print(f"- Beans with specialty info: {summary['coffee_beans']['beans_with_specialty_info']}")
        if summary['coffee_beans']['unique_regions']:
            print(f"- Regions: {', '.join(summary['coffee_beans']['unique_regions'])}")
        if summary['coffee_beans']['roast_levels']:
            print(f"- Roast levels: {', '.join(summary['coffee_beans']['roast_levels'])}")
        
        print(f"\n{'Menu:'}")
        print(f"- Total menu items: {summary['menu']['total_items']}")
        if summary['menu']['categories']:
            print(f"- Categories: {', '.join(summary['menu']['categories'])}")
        
        if scraped_data.coffee_beans:
            print(f"\n{'Sample Coffee Beans:'}")
            for i, bean in enumerate(scraped_data.coffee_beans[:3], 1):
                print(f"{i}. {bean.basic_info.name or 'Unnamed'}")
                if bean.basic_info.price:
                    print(f"   Price: {bean.basic_info.price}")
                if bean.basic_info.region:
                    print(f"   Region: {bean.basic_info.region}")
                if bean.basic_info.flavor_notes:
                    print(f"   Flavor Notes: {', '.join(bean.basic_info.flavor_notes)}")
        
        if scraped_data.menu and scraped_data.menu.items:
            print(f"\n{'Sample Menu Items:'}")
            for i, item in enumerate(scraped_data.menu.items[:5], 1):
                print(f"{i}. {item.name}")
                if item.price:
                    print(f"   Price: {item.price}")
                if item.description:
                    print(f"   Description: {item.description}")


def quick_scrape(url: str, output_file: Optional[str] = None, api_key: Optional[str] = None) -> ScrapedData:
    """
    Quick utility function to scrape a cafe website
    
    Args:
        url: Cafe website URL
        output_file: Optional file to save results
        api_key: Optional OpenAI API key for better LLM processing
        
    Returns:
        ScrapedData object
    """
    # Configure LLM
    llm_config = LLMConfig()
    if api_key:
        llm_config.api_key = api_key
        llm_config.model_type = "openai"
    else:
        llm_config.model_type = "mock"  # Use mock for testing
    
    # Create scraper and run
    scraper = CafeScraper(llm_config)
    result = scraper.scrape_cafe_website(url, output_file)
    scraper.print_summary(result)
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 cafe_scraper.py <url> [output_file] [api_key]")
        sys.exit(1)
    
    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    api_key = sys.argv[3] if len(sys.argv) > 3 else None
    
    quick_scrape(url, output_file, api_key) 