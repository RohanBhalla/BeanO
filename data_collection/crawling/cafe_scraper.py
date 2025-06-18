import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import re
from urllib.parse import urlparse

try:
    from .web_crawler import WebCrawler, create_coffee_crawler
except ImportError:
    from web_crawler import WebCrawler, create_coffee_crawler

logger = logging.getLogger(__name__)

class CafeScraper:
    """
    Main orchestrator for scraping cafe websites
    Saves raw HTML files from each crawled page
    """
    
    def __init__(self):
        self.crawler = create_coffee_crawler()
        
    def scrape_cafe_website(self, url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete pipeline to scrape a cafe website and save HTML files
        
        Args:
            url: Starting URL of the cafe website
            output_dir: Optional directory path to save HTML files
            
        Returns:
            Dictionary with summary of scraping results
        """
        logger.info(f"Starting complete scrape of cafe website: {url}")
        
        try:
            # Step 1: Crawl the website
            logger.info("Step 1: Crawling website...")
            crawl_result = self.crawler.crawl_website(url)
            
            if not crawl_result['pages']:
                logger.error(f"No pages found during crawl of {url}")
                return {
                    'base_url': url,
                    'timestamp': datetime.now().isoformat(),
                    'pages_saved': 0,
                    'total_pages': 0
                }
            
            logger.info(f"Crawled {len(crawl_result['pages'])} pages")
            
            # Step 2: Save HTML files
            if output_dir:
                saved_count = self.save_html_files(crawl_result, output_dir)
            else:
                saved_count = 0
                logger.info("No output directory specified, skipping file save")
            
            # Create summary
            result = {
                'base_url': url,
                'timestamp': datetime.now().isoformat(),
                'pages_saved': saved_count,
                'total_pages': len(crawl_result['pages']),
                'crawled_urls': crawl_result['visited_urls'],
                'all_links_found': crawl_result['all_links']
            }
            
            logger.info(f"Scraping completed! Saved {saved_count} HTML files from {len(crawl_result['pages'])} pages")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise
        finally:
            self.crawler.close()
    
    def save_html_files(self, crawl_result: Dict, output_dir: str) -> int:
        """Save HTML content from each page to separate files"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            saved_count = 0
            
            for i, page in enumerate(crawl_result['pages']):
                if 'html_content' not in page or not page['html_content']:
                    logger.warning(f"No HTML content found for page: {page.get('url', 'unknown')}")
                    continue
                
                # Create a safe filename from the URL
                filename = self._create_safe_filename(page['url'], i)
                file_path = output_path / f"{filename}.html"
                
                # Save HTML content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(page['html_content'])
                
                logger.info(f"Saved HTML file: {file_path}")
                saved_count += 1
            
            # Also save a summary JSON file
            summary_file = output_path / "scraping_summary.json"
            summary_data = {
                'timestamp': datetime.now().isoformat(),
                'base_url': crawl_result['start_url'],
                'base_domain': crawl_result['base_domain'],
                'total_pages': crawl_result['total_pages'],
                'visited_urls': crawl_result['visited_urls'],
                'all_links': crawl_result['all_links'],
                'saved_files': saved_count
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Summary saved to: {summary_file}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error saving HTML files: {e}")
            return 0
    
    def _create_safe_filename(self, url: str, index: int) -> str:
        """Create a safe filename from URL"""
        try:
            parsed = urlparse(url)
            
            # Start with domain
            domain = parsed.netloc.replace('www.', '')
            
            # Add path components
            path_parts = [part for part in parsed.path.split('/') if part]
            
            if path_parts:
                filename_parts = [domain] + path_parts
                filename = '_'.join(filename_parts)
            else:
                filename = f"{domain}_home"
            
            # Clean the filename
            filename = re.sub(r'[^\w\-_.]', '_', filename)
            filename = re.sub(r'_+', '_', filename)
            filename = filename.strip('_')
            
            # Add index to ensure uniqueness
            filename = f"{index:03d}_{filename}"
            
            # Limit length
            if len(filename) > 200:
                filename = filename[:200]
            
            return filename
            
        except Exception as e:
            logger.warning(f"Error creating filename for {url}: {e}")
            return f"{index:03d}_page"
    
    def load_summary(self, input_dir: str) -> Dict[str, Any]:
        """Load scraping summary from directory"""
        try:
            summary_file = Path(input_dir) / "scraping_summary.json"
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading summary: {e}")
            raise
    
    def print_summary(self, result: Dict[str, Any]):
        """Print a human-readable summary of scraping results"""
        print(f"\n{'='*60}")
        print(f"CAFE SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"Website: {result['base_url']}")
        print(f"Scraped at: {result['timestamp']}")
        print(f"Total pages crawled: {result['total_pages']}")
        print(f"HTML files saved: {result['pages_saved']}")
        
        if result.get('crawled_urls'):
            print(f"\nCrawled URLs ({len(result['crawled_urls'])}):")
            for i, url in enumerate(result['crawled_urls'][:10], 1):
                print(f"  {i}. {url}")
            if len(result['crawled_urls']) > 10:
                print(f"  ... and {len(result['crawled_urls']) - 10} more")
        
        if result.get('all_links_found'):
            print(f"\nTotal links found: {len(result['all_links_found'])}")


def quick_scrape(url: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick utility function to scrape a cafe website and save HTML files
    
    Args:
        url: Cafe website URL
        output_dir: Directory to save HTML files
        
    Returns:
        Dictionary with scraping results
    """
    # Create scraper and run
    scraper = CafeScraper()
    result = scraper.scrape_cafe_website(url, output_dir)
    scraper.print_summary(result)
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 cafe_scraper.py <url> [output_dir]")
        print("Example: python3 cafe_scraper.py https://example-cafe.com ./scraped_html")
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else f"./scraped_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    quick_scrape(url, output_dir) 