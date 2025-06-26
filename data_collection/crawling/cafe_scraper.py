import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import re
from urllib.parse import urlparse
import time

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
                extract_css_links=False,  # Extract CSS links (disabled for now)
                extract_meta_links=True,  # Extract meta tag links
                extract_json_ld_links=True,  # Extract JSON-LD structured data links
                extract_microdata_links=False,  # Extract microdata links (disabled for now)
                follow_redirects=True,  # Follow redirects to avoid missing content
                normalize_urls=False,  # Normalize URLs to avoid duplicates
                verbose_logging=verbose,
                timeout=45,  # Longer timeout for slow sites
            )
            # Relax URL restrictions for better coverage
            config.blocked_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.zip', '.doc', '.docx', '.svg', '.ico', '.mp4', '.mp3', '.wav'}
            config.allowed_extensions = {'.html', '.htm', '.php', '.asp', '.aspx', '.jsp', '.cfm', ''}  # Added more web formats
            
            self.crawler = WebCrawler(config)
        else:
            self.crawler = create_coffee_crawler(max_pages=max_pages, verbose=verbose, aggressive=False)
        
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
            logger.info(f"Enhanced crawler configuration:")
            logger.info(f"  - Max pages: {self.crawler.config.max_pages}")
            logger.info(f"  - Max workers: {self.crawler.config.max_workers}")
            logger.info(f"  - Delay between requests: {self.crawler.config.delay_between_requests}s")
            logger.info(f"  - Extract JS links: {self.crawler.config.extract_js_links}")
            logger.info(f"  - Extract CSS links: {self.crawler.config.extract_css_links}")
            logger.info(f"  - Extract meta links: {self.crawler.config.extract_meta_links}")
            logger.info(f"  - Extract JSON-LD links: {self.crawler.config.extract_json_ld_links}")
            logger.info(f"  - Extract microdata links: {self.crawler.config.extract_microdata_links}")
            logger.info(f"  - Follow redirects: {self.crawler.config.follow_redirects}")
            logger.info(f"  - Normalize URLs: {self.crawler.config.normalize_urls}")
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
                'failed_urls': crawl_result.get('failed_urls', []),
                'all_links_found': crawl_result['all_links'],
                'unique_links_found': len(crawl_result['all_links']),
                'pages_vs_links_ratio': len(crawl_result['pages']) / max(len(crawl_result['all_links']), 1),
                'redirect_cache': crawl_result.get('redirect_cache', {}),
                'crawler_stats': crawl_result.get('crawler_stats', {})
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
        """Log detailed statistics about the enhanced crawl"""
        pages = crawl_result['pages']
        all_links = crawl_result['all_links']
        visited_urls = crawl_result['visited_urls']
        failed_urls = crawl_result.get('failed_urls', [])
        redirect_cache = crawl_result.get('redirect_cache', {})
        crawler_stats = crawl_result.get('crawler_stats', {})
        
        logger.info(f"\n{'='*60}")
        logger.info(f"ENHANCED CRAWL STATISTICS")
        logger.info(f"{'='*60}")
        logger.info(f"Pages successfully crawled: {len(pages)}")
        logger.info(f"Failed URLs: {len(failed_urls)}")
        logger.info(f"Total unique links discovered: {len(all_links)}")
        logger.info(f"URLs visited: {len(visited_urls)}")
        logger.info(f"Redirects processed: {len(redirect_cache)}")
        logger.info(f"Coverage ratio: {len(visited_urls)}/{len(all_links)} = {len(visited_urls)/max(len(all_links), 1):.2%}")
        
        if crawler_stats:
            logger.info(f"\nENHANCED EXTRACTION FEATURES:")
            logger.info(f"  - JavaScript link extraction: {'✓' if self.crawler.config.extract_js_links else '✗'}")
            logger.info(f"  - CSS link extraction: {'✓' if self.crawler.config.extract_css_links else '✗'}")
            logger.info(f"  - Meta tag link extraction: {'✓' if self.crawler.config.extract_meta_links else '✗'}")
            logger.info(f"  - JSON-LD link extraction: {'✓' if self.crawler.config.extract_json_ld_links else '✗'}")
            logger.info(f"  - Microdata link extraction: {'✓' if self.crawler.config.extract_microdata_links else '✗'}")
            logger.info(f"  - URL normalization: {'✓' if self.crawler.config.normalize_urls else '✗'}")
            logger.info(f"  - Redirect following: {'✓' if self.crawler.config.follow_redirects else '✗'}")
        
        # Show which URLs were crawled
        logger.info(f"\nCRAWLED PAGES:")
        for i, url in enumerate(visited_urls[:10], 1):
            logger.info(f"  {i}. {url}")
        if len(visited_urls) > 10:
            logger.info(f"  ... and {len(visited_urls) - 10} more")
        
        # Show failed URLs
        if failed_urls:
            logger.info(f"\nFAILED URLS ({len(failed_urls)}):")
            for i, url in enumerate(failed_urls[:5], 1):
                logger.info(f"  {i}. {url}")
            if len(failed_urls) > 5:
                logger.info(f"  ... and {len(failed_urls) - 5} more")
        
        # Show redirects
        if redirect_cache:
            logger.info(f"\nREDIRECTS PROCESSED ({len(redirect_cache)}):")
            for i, (original, redirect) in enumerate(list(redirect_cache.items())[:5], 1):
                logger.info(f"  {i}. {original} → {redirect}")
            if len(redirect_cache) > 5:
                logger.info(f"  ... and {len(redirect_cache) - 5} more")
        
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
        
        logger.info(f"{'='*60}\n")

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

    def discover_and_save_links(self, url: str) -> Dict[str, Any]:
        """
        Phase 1: Discover all links from a website and automatically save them to crawled_links/{site_name}.json
        
        Args:
            url: Starting URL of the cafe website
            
        Returns:
            Dictionary with discovery results summary
        """
        logger.info(f"Starting link discovery phase for: {url}")
        
        try:
            # Extract site name from URL for file naming
            parsed_url = urlparse(url)
            site_name = parsed_url.netloc.replace('www.', '').replace('.', '_')
            
            # Create crawled_links directory and JSON file path
            crawled_links_dir = Path("crawled_links")
            crawled_links_dir.mkdir(exist_ok=True)
            links_file_path = crawled_links_dir / f"{site_name}.json"
            
            # Use the new discovery-only method
            discovery_result = self.crawler.discover_links_only(url)
            
            # Add timestamp
            discovery_result['discovery_metadata']['timestamp'] = datetime.now().isoformat()
            discovery_result['discovery_metadata']['site_name'] = site_name
            
            # Save to JSON file
            with open(links_file_path, 'w', encoding='utf-8') as f:
                json.dump(discovery_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Links discovery completed and saved to: {links_file_path}")
            
            # Print summary
            metadata = discovery_result['discovery_metadata']
            discovered_links = discovery_result['discovered_links']
            
            print(f"\n{'='*60}")
            print(f"LINK DISCOVERY SUMMARY")
            print(f"{'='*60}")
            print(f"Website: {metadata['base_url']}")
            print(f"Site name: {site_name}")
            print(f"Pages scanned: {metadata['total_pages_scanned']}")
            print(f"Total unique links found: {metadata['total_links_found']}")
            print(f"Links saved to: {links_file_path}")
            
            # Show breakdown by discovery method
            method_counts = {}
            type_counts = {'internal': 0, 'external': 0}
            
            for link in discovered_links:
                method = link['discovery_method']
                method_counts[method] = method_counts.get(method, 0) + 1
                type_counts[link['link_type']] += 1
            
            print(f"\nDiscovery method breakdown:")
            for method, count in sorted(method_counts.items()):
                print(f"  - {method}: {count}")
            
            print(f"\nLink type breakdown:")
            print(f"  - Internal links: {type_counts['internal']}")
            print(f"  - External links: {type_counts['external']}")
            
            print(f"\nNext steps:")
            print(f"1. Review and edit the links file: {links_file_path}")
            print(f"2. Change 'status' field to 'keep' for links you want to scrape")
            print(f"3. Run scraping phase with: scrape {site_name}")
            print(f"{'='*60}")
            
            return {
                'base_url': url,
                'site_name': site_name,
                'links_file': str(links_file_path),
                'total_links_found': metadata['total_links_found'],
                'pages_scanned': metadata['total_pages_scanned'],
                'timestamp': metadata['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error during link discovery: {e}")
            raise
        finally:
            self.crawler.close()

    def scrape_from_site_name(self, site_name: str, status_filter: str = "keep") -> Dict[str, Any]:
        """
        Phase 2: Automatically load links and scrape HTML using site name for directory structure.
        Creates scraped_html/{site_name}/ directory structure.
        
        Args:
            site_name: Name of the site (used to find links file and create output directory)
            status_filter: Only scrape links with this status (default: "keep")
            
        Returns:
            Dictionary with scraping results
        """
        # Find the links file
        links_file_path = Path("crawled_links") / f"{site_name}.json"
        
        if not links_file_path.exists():
            raise FileNotFoundError(f"Links file not found: {links_file_path}. Run discovery phase first.")
        
        # Create output directory structure
        scraped_html_dir = Path("scraped_html")
        scraped_html_dir.mkdir(exist_ok=True)
        
        site_output_dir = scraped_html_dir / site_name
        site_output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Scraping HTML for site: {site_name}")
        logger.info(f"Links file: {links_file_path}")
        logger.info(f"Output directory: {site_output_dir}")
        
        # Call the main scraping method
        return self.scrape_from_links_file(str(links_file_path), str(site_output_dir), status_filter)

    def scrape_from_links_file(self, links_file_path: str, output_dir: str, status_filter: str = "keep") -> Dict[str, Any]:
        """
        Phase 2: Load links from JSON file and scrape HTML content from selected links.
        
        Args:
            links_file_path: Path to the links JSON file from Phase 1
            output_dir: Directory to save HTML files
            status_filter: Only scrape links with this status (default: "keep")
            
        Returns:
            Dictionary with scraping results
        """
        logger.info(f"Starting HTML scraping phase from links file: {links_file_path}")
        
        try:
            # Load links from file
            with open(links_file_path, 'r', encoding='utf-8') as f:
                links_data = json.load(f)
            
            # Filter links by status
            all_links = links_data['discovered_links']
            filtered_links = [link for link in all_links if link.get('status') == status_filter]
            
            if not filtered_links:
                logger.warning(f"No links found with status '{status_filter}' in {links_file_path}")
                logger.info(f"Available statuses: {set(link.get('status', 'unknown') for link in all_links)}")
                return {
                    'links_file': links_file_path,
                    'filtered_links_count': 0,
                    'pages_scraped': 0,
                    'status_filter': status_filter
                }
            
            logger.info(f"Found {len(filtered_links)} links to scrape (status: {status_filter})")
            
            # Create output directory
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Scrape HTML from selected links
            scraped_pages = []
            failed_urls = []
            
            logger.info(f"Starting to scrape {len(filtered_links)} URLs...")
            
            for i, link_entry in enumerate(filtered_links):
                url = link_entry['url']
                logger.info(f"Scraping ({i+1}/{len(filtered_links)}): {url}")
                
                try:
                    # Fetch the page
                    page_data = self.crawler._fetch_page(url)
                    if page_data:
                        scraped_pages.append(page_data)
                        
                        # Save HTML file
                        filename = self._create_safe_filename(url, i)
                        file_path = output_path / f"{filename}.html"
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(page_data['html_content'])
                        
                        if self.verbose:
                            logger.info(f"Saved HTML: {file_path}")
                    else:
                        failed_urls.append(url)
                        logger.warning(f"Failed to scrape: {url}")
                        
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    failed_urls.append(url)
                
                # Respect rate limiting
                time.sleep(self.crawler.config.delay_between_requests)
            
            # Save scraping summary
            summary_data = {
                'phase': 'html_scraping',
                'timestamp': datetime.now().isoformat(),
                'links_file_used': links_file_path,
                'status_filter_used': status_filter,
                'total_links_in_file': len(all_links),
                'filtered_links_count': len(filtered_links),
                'successfully_scraped': len(scraped_pages),
                'failed_urls': failed_urls,
                'output_directory': output_dir,
                'base_url': links_data['discovery_metadata']['base_url']
            }
            
            summary_file = output_path / "scraping_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"HTML scraping completed!")
            logger.info(f"  - Successfully scraped: {len(scraped_pages)} pages")
            logger.info(f"  - Failed URLs: {len(failed_urls)}")
            logger.info(f"  - HTML files saved to: {output_dir}")
            logger.info(f"  - Summary saved to: {summary_file}")
            
            return {
                'links_file': links_file_path,
                'output_dir': output_dir,
                'total_links_in_file': len(all_links),
                'filtered_links_count': len(filtered_links),
                'pages_scraped': len(scraped_pages),
                'failed_urls': failed_urls,
                'status_filter': status_filter,
                'timestamp': summary_data['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error during HTML scraping phase: {e}")
            raise

    def load_and_preview_links(self, links_file_path: str, limit: int = 10) -> Dict[str, Any]:
        """
        Load and preview links from a JSON file to help with manual curation.
        
        Args:
            links_file_path: Path to the links JSON file
            limit: Number of links to preview (default: 10)
            
        Returns:
            Dictionary with preview information
        """
        try:
            with open(links_file_path, 'r', encoding='utf-8') as f:
                links_data = json.load(f)
            
            all_links = links_data['discovered_links']
            metadata = links_data['discovery_metadata']
            
            # Generate statistics
            status_counts = {}
            method_counts = {}
            type_counts = {'internal': 0, 'external': 0}
            
            for link in all_links:
                status = link.get('status', 'unknown')
                method = link.get('discovery_method', 'unknown')
                link_type = link.get('link_type', 'unknown')
                
                status_counts[status] = status_counts.get(status, 0) + 1
                method_counts[method] = method_counts.get(method, 0) + 1
                if link_type in type_counts:
                    type_counts[link_type] += 1
            
            print(f"\n{'='*60}")
            print(f"LINKS FILE PREVIEW: {links_file_path}")
            print(f"{'='*60}")
            print(f"Base URL: {metadata['base_url']}")
            print(f"Discovery timestamp: {metadata.get('timestamp', 'N/A')}")
            print(f"Total links: {len(all_links)}")
            print(f"Pages scanned: {metadata['total_pages_scanned']}")
            
            print(f"\nStatus breakdown:")
            for status, count in sorted(status_counts.items()):
                print(f"  - {status}: {count}")
            
            print(f"\nDiscovery method breakdown:")
            for method, count in sorted(method_counts.items()):
                print(f"  - {method}: {count}")
            
            print(f"\nLink type breakdown:")
            for link_type, count in type_counts.items():
                print(f"  - {link_type}: {count}")
            
            print(f"\nSample links (first {limit}):")
            for i, link in enumerate(all_links[:limit], 1):
                status_indicator = "✓" if link.get('status') == 'keep' else "○"
                print(f"  {i}. {status_indicator} [{link.get('discovery_method', 'unknown')}] {link['url']}")
            
            if len(all_links) > limit:
                print(f"  ... and {len(all_links) - limit} more links")
            
            print(f"\nTo mark links for scraping, edit the JSON file and change 'status' to 'keep'")
            print(f"{'='*60}")
            
            return {
                'total_links': len(all_links),
                'status_counts': status_counts,
                'method_counts': method_counts,
                'type_counts': type_counts,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error loading links file: {e}")
            raise

    def update_links_status(self, links_file_path: str, filters: Dict[str, str], output_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Helper function to bulk update link statuses based on various criteria.
        
        Args:
            links_file_path: Path to the links JSON file
            filters: Dictionary of filter criteria and target status
                     Examples:
                     - {'internal_only': 'keep'} - Mark all internal links as 'keep'
                     - {'contains_coffee': 'keep'} - Mark links containing 'coffee' as 'keep'  
                     - {'external': 'skip'} - Mark all external links as 'skip'
                     - {'method_anchor': 'keep'} - Mark all anchor-discovered links as 'keep'
            output_file_path: Optional output file path (default: overwrites input)
            
        Returns:
            Dictionary with update statistics
        """
        try:
            with open(links_file_path, 'r', encoding='utf-8') as f:
                links_data = json.load(f)
            
            all_links = links_data['discovered_links']
            updates = {'keep': 0, 'skip': 0, 'pending': 0}
            
            for link in all_links:
                original_status = link.get('status', 'pending')
                new_status = original_status
                
                # Apply filters
                for filter_name, target_status in filters.items():
                    if filter_name == 'internal_only' and link.get('link_type') == 'internal':
                        new_status = target_status
                    elif filter_name == 'external' and link.get('link_type') == 'external':
                        new_status = target_status
                    elif filter_name.startswith('contains_') and filter_name.replace('contains_', '') in link['url'].lower():
                        new_status = target_status
                    elif filter_name.startswith('method_') and link.get('discovery_method') == filter_name.replace('method_', ''):
                        new_status = target_status
                    elif filter_name.startswith('skip_extension_'):
                        extension = filter_name.replace('skip_extension_', '')
                        if link['url'].lower().endswith(f'.{extension}'):
                            new_status = target_status
                
                if new_status != original_status:
                    link['status'] = new_status
                    updates[new_status] += 1
            
            # Save updated file
            output_path = output_file_path or links_file_path
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(links_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated link statuses and saved to: {output_path}")
            
            return {
                'total_links': len(all_links),
                'updates_applied': updates,
                'output_file': output_path
            }
            
        except Exception as e:
            logger.error(f"Error updating links status: {e}")
            raise


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
        print("Usage:")
        print("  Two-phase workflow (recommended):")
        print("    python3 cafe_scraper.py discover <url> [max_pages]")
        print("    python3 cafe_scraper.py preview <site_name>")
        print("    python3 cafe_scraper.py scrape <site_name> [status_filter]")
        print("")
        print("  Legacy one-phase workflow:")
        print("    python3 cafe_scraper.py <url> [output_dir] [max_pages]")
        print("")
        print("Examples:")
        print("  # Phase 1: Discover links (creates crawled_links/lacabra_com.json)")
        print("  python3 cafe_scraper.py discover https://lacabra.com 300")
        print("  ")
        print("  # Preview links file")
        print("  python3 cafe_scraper.py preview lacabra_com")
        print("  ")
        print("  # Edit crawled_links/lacabra_com.json manually, set status='keep' for desired links")
        print("  ")
        print("  # Phase 2: Scrape HTML (creates scraped_html/lacabra_com/ directory)")
        print("  python3 cafe_scraper.py scrape lacabra_com")
        print("")
        print("Directory structure created:")
        print("  crawled_links/")
        print("    └── {site_name}.json")
        print("  scraped_html/")
        print("    └── {site_name}/")
        print("        ├── 000_page.html")
        print("        ├── 001_page.html")
        print("        └── scraping_summary.json")
        print("")
        print("Options:")
        print("  discover - Phase 1: Find all links and save to crawled_links/{site_name}.json")
        print("  preview  - Preview links file and show statistics")
        print("  scrape   - Phase 2: Scrape HTML from links with status='keep'")
        print("  max_pages - Maximum pages to scan during discovery (default: 200)")
        print("  status_filter - Only scrape links with this status (default: 'keep')")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "discover":
        # Phase 1: Link discovery
        if len(sys.argv) < 3:
            print("Usage: python3 cafe_scraper.py discover <url> [max_pages]")
            print("Example: python3 cafe_scraper.py discover https://lacabra.com 300")
            sys.exit(1)
        
        url = sys.argv[2]
        max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        
        print(f"Phase 1: Discovering links from {url} (max_pages={max_pages})")
        scraper = CafeScraper(max_pages=max_pages, verbose=True, aggressive_crawling=True)
        result = scraper.discover_and_save_links(url)
        print(f"\nDiscovery completed! Found {result['total_links_found']} links.")
        print(f"Next: Edit {result['links_file']} and change 'status' to 'keep' for links you want to scrape.")
        
    elif command == "preview":
        # Preview links file
        if len(sys.argv) < 3:
            print("Usage: python3 cafe_scraper.py preview <site_name>")
            print("Example: python3 cafe_scraper.py preview lacabra_com")
            sys.exit(1)
        
        site_name = sys.argv[2]
        links_file_path = Path("crawled_links") / f"{site_name}.json"
        
        if not links_file_path.exists():
            print(f"Error: Links file not found: {links_file_path}")
            print(f"Run discovery first: python3 cafe_scraper.py discover <url>")
            sys.exit(1)
        
        scraper = CafeScraper()
        scraper.load_and_preview_links(str(links_file_path))
        
    elif command == "scrape":
        # Phase 2: HTML scraping
        if len(sys.argv) < 3:
            print("Usage: python3 cafe_scraper.py scrape <site_name> [status_filter]")
            print("Example: python3 cafe_scraper.py scrape lacabra_com keep")
            sys.exit(1)
        
        site_name = sys.argv[2]
        status_filter = sys.argv[3] if len(sys.argv) > 3 else "keep"
        
        print(f"Phase 2: Scraping HTML for {site_name} (status: {status_filter})")
        scraper = CafeScraper(verbose=True)
        result = scraper.scrape_from_site_name(site_name, status_filter)
        print(f"\nScraping completed! Scraped {result['pages_scraped']} pages to {result['output_dir']}")
        
    else:
        # Legacy one-phase workflow (backward compatibility)
        url = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else f"./scraped_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        
        print(f"Legacy mode: Starting one-phase scrape with max_pages={max_pages}")
        print("Note: Consider using the two-phase workflow for better control:")
        parsed_url = urlparse(url)
        site_name = parsed_url.netloc.replace('www.', '').replace('.', '_')
        print(f"  1. python3 cafe_scraper.py discover {url} {max_pages}")
        print(f"  2. python3 cafe_scraper.py scrape {site_name}")
        print("")
        
        quick_scrape(url, output_dir, max_pages=max_pages, verbose=True) 