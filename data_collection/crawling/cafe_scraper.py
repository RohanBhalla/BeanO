import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import re
from urllib.parse import urlparse

try:
    from .web_crawler import WebCrawler, create_coffee_crawler, CrawlConfig
except ImportError:
    from web_crawler import WebCrawler, create_coffee_crawler, CrawlConfig

logger = logging.getLogger(__name__)

class CafeScraper:
    """
    Main orchestrator for scraping cafe websites
    Saves raw HTML files from each crawled page
    """
    
    def __init__(self, max_pages: int = 200, verbose: bool = True, aggressive_crawling: bool = True):
        """
        Initialize the cafe scraper
        
        Args:
            max_pages: Maximum number of pages to crawl (default: 200)
            verbose: Enable verbose logging to see what's happening (default: True)
            aggressive_crawling: Use more aggressive settings for better coverage (default: True)
        """
        if aggressive_crawling:
            # Create custom config for more thorough crawling
            config = CrawlConfig(
                max_pages=max_pages,
                delay_between_requests=0.8,  # Faster crawling
                max_workers=5,  # More concurrent workers
                follow_external_links=False,  # Stay on same domain
                extract_js_links=True,  # Extract JavaScript links
                verbose_logging=verbose,
                timeout=45,  # Longer timeout for slow sites
            )
            # Relax URL restrictions for better coverage
            config.blocked_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.zip', '.doc', '.docx', '.svg', '.ico', '.mp4', '.mp3', '.wav'}
            config.allowed_extensions = {'.html', '.htm', '.php', '.asp', '.aspx', '.jsp', '.cfm', ''}  # Added more web formats
            
            self.crawler = WebCrawler(config)
        else:
            self.crawler = create_coffee_crawler(max_pages=max_pages, verbose=verbose)
        
        self.verbose = verbose
        
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
        
        if self.verbose:
            logger.info(f"Crawler configuration:")
            logger.info(f"  - Max pages: {self.crawler.config.max_pages}")
            logger.info(f"  - Max workers: {self.crawler.config.max_workers}")
            logger.info(f"  - Delay between requests: {self.crawler.config.delay_between_requests}s")
            logger.info(f"  - Extract JS links: {self.crawler.config.extract_js_links}")
            logger.info(f"  - Follow external links: {self.crawler.config.follow_external_links}")
        
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
            
            # Log detailed statistics if verbose
            if self.verbose:
                self._log_crawl_statistics(crawl_result)
            
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
                'all_links_found': crawl_result['all_links'],
                'unique_links_found': len(crawl_result['all_links']),
                'pages_vs_links_ratio': len(crawl_result['pages']) / max(len(crawl_result['all_links']), 1)
            }
            
            logger.info(f"Scraping completed! Saved {saved_count} HTML files from {len(crawl_result['pages'])} pages")
            logger.info(f"Found {len(crawl_result['all_links'])} unique links total")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            raise
        finally:
            self.crawler.close()
    
    def _log_crawl_statistics(self, crawl_result: Dict):
        """Log detailed statistics about the crawl"""
        pages = crawl_result['pages']
        all_links = crawl_result['all_links']
        visited_urls = crawl_result['visited_urls']
        
        logger.info(f"\n{'='*50}")
        logger.info(f"CRAWL STATISTICS")
        logger.info(f"{'='*50}")
        logger.info(f"Pages successfully crawled: {len(pages)}")
        logger.info(f"Total unique links discovered: {len(all_links)}")
        logger.info(f"URLs visited: {len(visited_urls)}")
        logger.info(f"Coverage ratio: {len(visited_urls)}/{len(all_links)} = {len(visited_urls)/max(len(all_links), 1):.2%}")
        
        # Show which URLs were crawled
        logger.info(f"\nCRAWLED PAGES:")
        for i, url in enumerate(visited_urls[:10], 1):
            logger.info(f"  {i}. {url}")
        if len(visited_urls) > 10:
            logger.info(f"  ... and {len(visited_urls) - 10} more")
        
        # Show discovered but not crawled links
        uncrawled_links = set(all_links) - set(visited_urls)
        if uncrawled_links:
            logger.info(f"\nDISCOVERED BUT NOT CRAWLED ({len(uncrawled_links)} links):")
            for i, url in enumerate(list(uncrawled_links)[:10], 1):
                logger.info(f"  {i}. {url}")
            if len(uncrawled_links) > 10:
                logger.info(f"  ... and {len(uncrawled_links) - 10} more")
            
            if len(visited_urls) >= self.crawler.config.max_pages:
                logger.warning(f"Reached max_pages limit ({self.crawler.config.max_pages}). Increase max_pages to crawl more links.")
        
        logger.info(f"{'='*50}\n")

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
                
                if self.verbose:
                    logger.info(f"Saved HTML file: {file_path}")
                saved_count += 1
            
            # Also save a detailed summary JSON file
            summary_file = output_path / "scraping_summary.json"
            summary_data = {
                'timestamp': datetime.now().isoformat(),
                'base_url': crawl_result['start_url'],
                'base_domain': crawl_result['base_domain'],
                'total_pages': crawl_result['total_pages'],
                'visited_urls': crawl_result['visited_urls'],
                'all_links': crawl_result['all_links'],
                'saved_files': saved_count,
                'crawler_config': {
                    'max_pages': self.crawler.config.max_pages,
                    'max_workers': self.crawler.config.max_workers,
                    'delay_between_requests': self.crawler.config.delay_between_requests,
                    'extract_js_links': self.crawler.config.extract_js_links,
                    'follow_external_links': self.crawler.config.follow_external_links,
                }
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
        print(f"Unique links found: {result.get('unique_links_found', 'N/A')}")
        print(f"Coverage ratio: {result.get('pages_vs_links_ratio', 0):.2%}")
        
        if result.get('crawled_urls'):
            print(f"\nCrawled URLs ({len(result['crawled_urls'])}):")
            for i, url in enumerate(result['crawled_urls'][:10], 1):
                print(f"  {i}. {url}")
            if len(result['crawled_urls']) > 10:
                print(f"  ... and {len(result['crawled_urls']) - 10} more")
        
        if result.get('all_links_found'):
            print(f"\nTotal links discovered: {len(result['all_links_found'])}")
            uncrawled = set(result['all_links_found']) - set(result['crawled_urls'])
            if uncrawled:
                print(f"Links discovered but not crawled: {len(uncrawled)}")
                print("  (Increase max_pages parameter to crawl more links)")


def quick_scrape(url: str, output_dir: Optional[str] = None, max_pages: int = 200, verbose: bool = True) -> Dict[str, Any]:
    """
    Quick utility function to scrape a cafe website and save HTML files
    
    Args:
        url: Cafe website URL
        output_dir: Directory to save HTML files
        max_pages: Maximum number of pages to crawl (default: 200)
        verbose: Enable verbose logging (default: True)
        
    Returns:
        Dictionary with scraping results
    """
    # Create scraper and run
    scraper = CafeScraper(max_pages=max_pages, verbose=verbose, aggressive_crawling=True)
    result = scraper.scrape_cafe_website(url, output_dir)
    scraper.print_summary(result)
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 cafe_scraper.py <url> [output_dir] [max_pages]")
        print("Example: python3 cafe_scraper.py https://example-cafe.com ./scraped_html 300")
        print("\nOptions:")
        print("  url         - Website URL to scrape")
        print("  output_dir  - Directory to save HTML files (default: timestamped directory)")  
        print("  max_pages   - Maximum pages to crawl (default: 200)")
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else f"./scraped_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    
    print(f"Starting scrape with max_pages={max_pages}")
    quick_scrape(url, output_dir, max_pages=max_pages, verbose=True) 