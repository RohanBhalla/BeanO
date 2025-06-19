import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict, Optional
import time
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CrawlConfig:
    """Configuration for web crawler"""
    max_pages: int = 100
    delay_between_requests: float = 1.0
    max_workers: int = 5
    timeout: int = 30
    user_agent: str = "CafeCrawler/1.0 (Friendly Coffee Bot)"
    follow_external_links: bool = False
    allowed_extensions: Set[str] = None
    blocked_extensions: Set[str] = None
    extract_js_links: bool = True
    verbose_logging: bool = False
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = {'.html', '.htm', '.php', '.asp', '.aspx', '.jsp', ''}
        if self.blocked_extensions is None:
            self.blocked_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.zip', '.doc', '.docx', '.svg', '.ico'}

class WebCrawler:
    def __init__(self, config: CrawlConfig = None):
        self.config = config or CrawlConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL should be crawled"""
        try:
            parsed = urlparse(url)
            
            # Check if it's a valid HTTP/HTTPS URL
            if parsed.scheme not in ['http', 'https']:
                if self.config.verbose_logging:
                    logger.debug(f"Rejected URL (invalid scheme): {url}")
                return False
                
            # Check domain restriction
            if not self.config.follow_external_links:
                if parsed.netloc != base_domain:
                    if self.config.verbose_logging:
                        logger.debug(f"Rejected URL (external domain): {url}")
                    return False
            
            # Check file extensions
            path = parsed.path.lower()
            
            # Check blocked extensions
            for ext in self.config.blocked_extensions:
                if path.endswith(ext):
                    if self.config.verbose_logging:
                        logger.debug(f"Rejected URL (blocked extension {ext}): {url}")
                    return False
                    
            # If allowed extensions specified, check them
            if self.config.allowed_extensions:
                has_allowed_ext = any(path.endswith(ext) for ext in self.config.allowed_extensions)
                if not has_allowed_ext and '.' in path.split('/')[-1]:
                    if self.config.verbose_logging:
                        logger.debug(f"Rejected URL (not in allowed extensions): {url}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.warning(f"Error validating URL {url}: {e}")
            return False
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from a page using multiple methods"""
        links = []
        base_domain = urlparse(base_url).netloc
        
        if self.config.verbose_logging:
            logger.debug(f"Extracting links from: {base_url}")
        
        # Method 1: Standard anchor tags with href
        anchor_links = []
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
                
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            if self._is_valid_url(absolute_url, base_domain):
                anchor_links.append(absolute_url)
        
        if self.config.verbose_logging:
            logger.debug(f"Found {len(anchor_links)} anchor links")
        links.extend(anchor_links)
        
        # Method 2: Area tags (image maps)
        area_links = []
        for area in soup.find_all('area', href=True):
            href = area['href'].strip()
            if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
                
            absolute_url = urljoin(base_url, href)
            if self._is_valid_url(absolute_url, base_domain):
                area_links.append(absolute_url)
        
        if area_links and self.config.verbose_logging:
            logger.debug(f"Found {len(area_links)} area links")
        links.extend(area_links)
        
        # Method 3: Form actions
        form_links = []
        for form in soup.find_all('form', action=True):
            action = form['action'].strip()
            if not action or action.startswith('#') or action.startswith('mailto:'):
                continue
                
            absolute_url = urljoin(base_url, action)
            if self._is_valid_url(absolute_url, base_domain):
                form_links.append(absolute_url)
        
        if form_links and self.config.verbose_logging:
            logger.debug(f"Found {len(form_links)} form action links")
        links.extend(form_links)
        
        # Method 4: Data attributes that might contain URLs
        data_links = []
        for element in soup.find_all(attrs={"data-href": True}):
            href = element['data-href'].strip()
            if href and not href.startswith('#'):
                absolute_url = urljoin(base_url, href)
                if self._is_valid_url(absolute_url, base_domain):
                    data_links.append(absolute_url)
        
        for element in soup.find_all(attrs={"data-url": True}):
            href = element['data-url'].strip()
            if href and not href.startswith('#'):
                absolute_url = urljoin(base_url, href)
                if self._is_valid_url(absolute_url, base_domain):
                    data_links.append(absolute_url)
        
        if data_links and self.config.verbose_logging:
            logger.debug(f"Found {len(data_links)} data attribute links")
        links.extend(data_links)
        
        # Method 5: JavaScript links (basic extraction)
        if self.config.extract_js_links:
            js_links = self._extract_js_links(soup, base_url, base_domain)
            if js_links and self.config.verbose_logging:
                logger.debug(f"Found {len(js_links)} JavaScript links")
            links.extend(js_links)
        
        # Remove duplicates while preserving order
        unique_links = []
        seen = set()
        for link in links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)
        
        if self.config.verbose_logging:
            logger.debug(f"Total unique links found: {len(unique_links)}")
        
        return unique_links
    
    def _extract_js_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from JavaScript code (basic patterns)"""
        js_links = []
        
        # Look for URLs in script tags
        for script in soup.find_all('script'):
            if script.string:
                # Common patterns for URLs in JavaScript
                url_patterns = [
                    r'["\']([^"\']*\.(?:html|htm|php|asp|aspx|jsp)[^"\']*)["\']',
                    r'["\']([^"\']*\/[^"\']*)["\']',
                    r'window\.location\s*=\s*["\']([^"\']+)["\']',
                    r'location\.href\s*=\s*["\']([^"\']+)["\']',
                    r'href\s*:\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in url_patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    for match in matches:
                        if match and not match.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                            try:
                                absolute_url = urljoin(base_url, match)
                                if self._is_valid_url(absolute_url, base_domain):
                                    js_links.append(absolute_url)
                            except Exception:
                                continue
        
        # Look for onclick handlers with URLs
        for element in soup.find_all(attrs={"onclick": True}):
            onclick = element['onclick']
            url_matches = re.findall(r'["\']([^"\']+\.(?:html|htm|php|asp|aspx|jsp)[^"\']*)["\']', onclick)
            for match in url_matches:
                try:
                    absolute_url = urljoin(base_url, match)
                    if self._is_valid_url(absolute_url, base_domain):
                        js_links.append(absolute_url)
                except Exception:
                    continue
        
        return js_links
    
    def _clean_html_content(self, soup: BeautifulSoup) -> str:
        """Clean and extract meaningful text content from HTML"""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _fetch_page(self, url: str) -> Optional[Dict]:
        """Fetch a single page and extract content"""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            
            # Only process HTML content
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                logger.warning(f"Skipping non-HTML content: {url}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Extract links
            links = self._extract_links(soup, url)
            
            # Clean HTML content
            clean_text = self._clean_html_content(soup)
            
            return {
                'url': url,
                'title': title_text,
                'html_content': str(soup),
                'clean_text': clean_text,
                'links': links,
                'status_code': response.status_code
            }
            
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            return None
    
    def crawl_website(self, start_url: str) -> Dict:
        """
        Crawl a website starting from the given URL
        
        Returns:
            Dict containing all crawled pages and their content
        """
        logger.info(f"Starting crawl of: {start_url}")
        
        # Initialize tracking sets and lists
        visited_urls: Set[str] = set()
        urls_to_visit: Set[str] = {start_url}
        all_pages: List[Dict] = []
        all_links: Set[str] = set()
        
        base_domain = urlparse(start_url).netloc
        
        while urls_to_visit and len(visited_urls) < self.config.max_pages:
            # Get next batch of URLs to process
            current_batch = list(urls_to_visit)[:self.config.max_workers]
            urls_to_visit -= set(current_batch)
            
            logger.info(f"Processing batch of {len(current_batch)} URLs. Queue size: {len(urls_to_visit)}, Visited: {len(visited_urls)}")
            
            # Process batch concurrently
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_url = {
                    executor.submit(self._fetch_page, url): url 
                    for url in current_batch if url not in visited_urls
                }
                
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    visited_urls.add(url)
                    
                    try:
                        page_data = future.result()
                        if page_data:
                            all_pages.append(page_data)
                            
                            # Add new links to crawl queue
                            new_links = 0
                            for link in page_data['links']:
                                all_links.add(link)
                                if link not in visited_urls and len(visited_urls) < self.config.max_pages:
                                    if link not in urls_to_visit:
                                        urls_to_visit.add(link)
                                        new_links += 1
                            
                            if self.config.verbose_logging:
                                logger.debug(f"Page {url} contributed {new_links} new links to queue")
                                    
                    except Exception as e:
                        logger.error(f"Error processing result for {url}: {e}")
            
            # Respect rate limiting
            if urls_to_visit:
                time.sleep(self.config.delay_between_requests)
        
        logger.info(f"Crawl completed. Visited {len(visited_urls)} pages, found {len(all_links)} total links")
        
        return {
            'start_url': start_url,
            'base_domain': base_domain,
            'pages': all_pages,
            'visited_urls': list(visited_urls),
            'all_links': list(all_links),
            'total_pages': len(all_pages)
        }
    
    def get_page_content_by_keywords(self, crawl_result: Dict, keywords: List[str]) -> List[Dict]:
        """Filter pages that contain specific keywords (useful for finding bean/menu pages)"""
        relevant_pages = []
        
        for page in crawl_result['pages']:
            text_content = page['clean_text'].lower()
            title_content = page['title'].lower()
            
            # Check if page contains any of the keywords
            if any(keyword.lower() in text_content or keyword.lower() in title_content 
                   for keyword in keywords):
                relevant_pages.append(page)
                
        return relevant_pages
    
    def close(self):
        """Close the session"""
        self.session.close()


def create_coffee_crawler(max_pages: int = 100, verbose: bool = False) -> WebCrawler:
    """Create a crawler optimized for coffee shop websites"""
    config = CrawlConfig(
        max_pages=max_pages,
        delay_between_requests=1.5,
        max_workers=3,
        follow_external_links=False,
        extract_js_links=True,
        verbose_logging=verbose,
    )
    return WebCrawler(config) 