#!/usr/bin/env python3

# NOTE: This script requires Python 3! Use: python3 example_usage.py
"""
Example usage of the Cafe Scraper system

This script demonstrates how to scrape coffee shop websites to extract
structured information about coffee beans and menu items.
"""

import os
import logging
from cafe_scraper import quick_scrape, CafeScraper, LLMConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example_basic_scrape():
    """Basic example using mock LLM (no API key needed)"""
    print("=== Basic Scrape Example (Mock LLM) ===")
    
    # Example cafe website (replace with actual URL)
    cafe_url = "https://www.partnerscoffee.com/"
    
    try:
        # Quick scrape with mock LLM
        result = quick_scrape(
            url=cafe_url,
            output_file="results/partners_coffee.json"
        )
        
        print(f"\nBasic scrape completed!")
        print(f"Found {len(result.coffee_beans)} coffee beans")
        print(f"Found {len(result.menu.items) if result.menu else 0} menu items")
        
    except Exception as e:
        print(f"Error in basic scrape: {e}")

def example_openai_scrape():
    """Advanced example using OpenAI API"""
    print("\n=== Advanced Scrape Example (OpenAI LLM) ===")
    
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  No OpenAI API key found in OPENAI_API_KEY environment variable")
        print("   Skipping OpenAI example...")
        return
    
    cafe_url = "https://example-cafe.com"
    
    try:
        # Configure LLM for better extraction
        llm_config = LLMConfig(
            model_type="openai",
            model_name="gpt-3.5-turbo",
            api_key=api_key,
            temperature=0.1,
            max_tokens=2000
        )
        
        # Create scraper with custom config
        scraper = CafeScraper(llm_config)
        
        result = scraper.scrape_cafe_website(
            url=cafe_url,
            output_file="results/example_cafe_openai.json"
        )
        
        scraper.print_summary(result)
        
        # Access specific data
        if result.coffee_beans:
            print("\n=== Detailed Bean Information ===")
            for bean in result.coffee_beans[:2]:  # Show first 2 beans
                print(f"\nBean: {bean.basic_info.name}")
                print(f"  Price: {bean.basic_info.price}")
                print(f"  Region: {bean.basic_info.region}")
                print(f"  Roast: {bean.basic_info.roast_level}")
                if bean.basic_info.flavor_notes:
                    print(f"  Flavors: {', '.join(bean.basic_info.flavor_notes)}")
                
                if bean.specialty_info:
                    print(f"  Farm: {bean.specialty_info.farm}")
                    print(f"  Process: {bean.specialty_info.process}")
                    print(f"  Altitude: {bean.specialty_info.altitude}")
        
    except Exception as e:
        print(f"Error in advanced scrape: {e}")

def example_custom_configuration():
    """Example with custom crawler and LLM configuration"""
    print("\n=== Custom Configuration Example ===")
    
    from web_crawler import WebCrawler, CrawlConfig
    
    # Custom crawler config
    crawl_config = CrawlConfig(
        max_pages=10,  # Limit to 10 pages for faster testing
        delay_between_requests=2.0,  # Be extra respectful
        max_workers=2,  # Conservative parallelism
        follow_external_links=False,
        timeout=15
    )
    
    # Custom LLM config
    llm_config = LLMConfig(
        model_type="mock",  # Using mock for this example
        temperature=0.2,
        max_tokens=1500
    )
    
    # Create custom scraper
    crawler = WebCrawler(crawl_config)
    scraper = CafeScraper(llm_config)
    scraper.crawler = crawler
    
    cafe_url = "https://example-cafe.com"
    
    try:
        result = scraper.scrape_cafe_website(
            url=cafe_url,
            output_file="results/example_cafe_custom.json"
        )
        
        # Generate and display summary
        summary = scraper.get_summary(result)
        print(f"\nCustom scrape completed!")
        print(f"Crawled {summary['total_pages_crawled']} pages")
        print(f"Found {summary['coffee_beans']['total_count']} beans")
        print(f"Found {summary['menu']['total_items']} menu items")
        
    except Exception as e:
        print(f"Error in custom scrape: {e}")

def example_load_and_analyze():
    """Example of loading previously scraped data"""
    print("\n=== Load and Analyze Example ===")
    
    try:
        scraper = CafeScraper()
        
        # Try to load previously saved data
        result_files = [
            "results/example_cafe_basic.json",
            "results/example_cafe_openai.json", 
            "results/example_cafe_custom.json"
        ]
        
        for file_path in result_files:
            if os.path.exists(file_path):
                print(f"\nLoading data from: {file_path}")
                data = scraper.load_results(file_path)
                scraper.print_summary(data)
                break
        else:
            print("No previous results found to load")
            
    except Exception as e:
        print(f"Error loading data: {e}")

def main():
    """Run all examples"""
    print("🔍 CAFE SCRAPER EXAMPLES")
    print("=" * 50)
    
    # Create results directory
    os.makedirs("results", exist_ok=True)
    
    # Run examples
    example_basic_scrape()
    example_openai_scrape() 
    example_custom_configuration()
    example_load_and_analyze()
    
    print("\n✅ All examples completed!")
    print("\n💡 To scrape a real cafe website:")
    print("   python cafe_scraper.py <URL> [output_file] [api_key]")
    print("\n   Example:")
    print("   python cafe_scraper.py https://bluebottlecoffee.com results/bluebottle.json")

if __name__ == "__main__":
    main() 