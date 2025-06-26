import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlunparse
from typing import Set, List, Dict, Optional
import time
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import json

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
    extract_css_links: bool = True
    extract_meta_links: bool = True
    extract_json_ld_links: bool = True
    extract_microdata_links: bool = True
    follow_redirects: bool = True
    normalize_urls: bool = False
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
        
        # Track URLs that returned redirects to avoid duplicate processing
        self.redirect_cache = {}
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments, sorting query parameters, etc."""
        if not self.config.normalize_urls:
            return url
            
        try:
            parsed = urlparse(url)
            
            # Remove fragment
            parsed = parsed._replace(fragment='')
            
            # Sort query parameters for consistency
            if parsed.query:
                query_dict = parse_qs(parsed.query, keep_blank_values=True)
                sorted_query = '&'.join(f'{k}={v[0]}' for k, v in sorted(query_dict.items()))
                parsed = parsed._replace(query=sorted_query)
            
            # Remove trailing slash from path (except for root)
            if parsed.path != '/' and parsed.path.endswith('/'):
                parsed = parsed._replace(path=parsed.path.rstrip('/'))
                
            return urlunparse(parsed)
            
        except Exception as e:
            logger.warning(f"Error normalizing URL {url}: {e}")
            return url
        
    def _smart_url_join(self, base_url: str, potential_url: str) -> str:
        """
        Intelligently join URLs handling common malformation patterns.
        Replaces simple urljoin() to handle edge cases like duplicate domains,
        missing protocols, and malformed JavaScript-extracted URLs.
        """
        if not potential_url or not potential_url.strip():
            return None
            
        url = potential_url.strip()
        base_parsed = urlparse(base_url)
        base_domain = base_parsed.netloc
        
        # Case 1: Already absolute URL - return as-is
        if url.startswith(('http://', 'https://')):
            return url
        
        # Case 2: Protocol-relative URL (//example.com/path)
        if url.startswith('//'):
            return base_parsed.scheme + ':' + url
        
        # Case 3: URL starts with domain name but missing protocol
        # This catches cases like "www.lacolombe.com/products/coffee"
        # BUT: Check for duplication first and defer to Case 4 if found
        if self._looks_like_domain_url(url, base_domain):
            # Check for domain duplication first
            domain_count = url.count(base_domain)
            if domain_count > 1:
                # Has duplication - let Case 4 handle it
                pass  
            else:
                # No duplication - handle normally
                # Check if it's the same domain as base
                if url.startswith(base_domain):
                    return base_parsed.scheme + '://' + url
                else:
                    # Different domain, assume https
                    return 'https://' + url
        
        # Case 4: Handle duplicate domain paths - IMPROVED
        # e.g., url="www.lacolombe.com/products/www.lacolombe.com/products/coffee"
        if base_domain in url and not url.startswith(('http://', 'https://')):
            domain_count = url.count(base_domain)
            if domain_count > 1:
                # Multiple domain occurrences - likely a malformed URL with duplication
                # Strategy: Split by domain and rebuild using only the last meaningful part
                parts = url.split(base_domain)
                if len(parts) >= 3:  # We have at least 2 domain occurrences
                    # Take the last part which should be the actual path
                    last_part = parts[-1]
                    # Rebuild: domain + last_part
                    cleaned_url = base_domain + last_part
                    return base_parsed.scheme + '://' + cleaned_url
                else:
                    # Fallback: find last occurrence and use from there
                    last_domain_index = url.rfind(base_domain)
                    cleaned_url = url[last_domain_index:]
                    return base_parsed.scheme + '://' + cleaned_url
            else:
                # Single domain occurrence - add protocol
                domain_index = url.find(base_domain)
                if domain_index >= 0:
                    cleaned_url = url[domain_index:]
                    return base_parsed.scheme + '://' + cleaned_url
        
        # Case 5: URL contains path that duplicates base path
        # e.g., url="/products/www.lacolombe.com/products/coffee"
        if base_domain in url:
            domain_start = url.find(base_domain)
            if domain_start > 0:
                # Take everything from domain onwards
                cleaned_url = url[domain_start:]
                return base_parsed.scheme + '://' + cleaned_url
        
        # Case 6: Fragment or anchor only
        if url.startswith('#'):
            return base_url + url
        
        # Case 7: Query parameters only
        if url.startswith('?'):
            return base_url + url
        
        # Case 8: Regular relative URL - use standard urljoin
        try:
            result = urljoin(base_url, url)
            
            # Validate the result doesn't have duplicate domain paths
            result_parsed = urlparse(result)
            path = result_parsed.path
            
            # Check for duplicate domain in path
            if base_domain in path and path.count(base_domain) > 1:
                # Clean up duplicate domain in path
                domain_parts = path.split(base_domain)
                if len(domain_parts) > 2:
                    # Keep only the last occurrence
                    cleaned_path = base_domain + domain_parts[-1]
                    result = urlunparse(result_parsed._replace(path='/' + cleaned_path))
            
            return result
        except Exception as e:
            logger.warning(f"Error joining URLs: base='{base_url}', url='{url}', error={e}")
            return None
    
    def _validate_final_url(self, url: str) -> str:
        """
        Final validation and cleanup of URLs before returning from smart_url_join.
        Ensures the URL is well-formed and catches any remaining edge cases.
        """
        if not url:
            return None
            
        try:
            parsed = urlparse(url)
            
            # Must have valid scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return None
            
            # Check for obviously malformed results
            if self._is_malformed_url(url):
                logger.debug(f"Final validation rejected malformed URL: {url}")
                return None
                
            return url
            
        except Exception as e:
            logger.debug(f"Final URL validation error for {url}: {e}")
            return None
    
    def _looks_like_domain_url(self, url: str, base_domain: str) -> bool:
        """
        Check if a URL looks like it starts with a domain name.
        Helps detect URLs missing protocols.
        """
        # Check if it starts with www. or the base domain
        if url.startswith('www.') or url.startswith(base_domain):
            return True
            
        # Check if it looks like domain.tld/path pattern
        parts = url.split('/')
        if len(parts) > 0:
            first_part = parts[0]
            # Simple check for domain-like pattern (contains dots, no spaces)
            if '.' in first_part and ' ' not in first_part and len(first_part) > 3:
                # Additional check: no special chars that wouldn't be in domain
                if not any(char in first_part for char in ['(', ')', '"', "'", '\\', ';']):
                    return True
        
        return False
    
    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL should be crawled"""
        if not url:
            return False
            
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
            
            # Additional validation: check for obviously malformed URLs
            if self._is_malformed_url(url):
                if self.config.verbose_logging:
                    logger.debug(f"Rejected URL (malformed): {url}")
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
    
    def _is_malformed_url(self, url: str) -> bool:
        """
        Check for obviously malformed URLs that should be rejected.
        """
        # Check for duplicate protocols
        if url.count('://') > 1:
            return True
        
        # Check for duplicate domains in the URL
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain and domain in parsed.path:
            # Count occurrences of domain in the full URL
            if url.count(domain) > 2:  # Once in netloc, maybe once in path is ok, more is suspicious
                return True
        
        # Check for malformed path patterns
        path = parsed.path
        if '//' in path and path != '//':  # Double slashes (except for protocol)
            return True
        
        # Check for extremely long URLs (likely malformed)
        if len(url) > 2000:
            return True
        
        # Check for URLs with invalid characters
        invalid_chars = ['<', '>', '"', '`', '{', '}', '|', '^']
        if any(char in url for char in invalid_chars):
            return True
        
        return False
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str, response_headers: Dict = None) -> List[str]:
        """Extract all links from a page using multiple comprehensive methods"""
        links = []
        base_domain = urlparse(base_url).netloc
        
        if self.config.verbose_logging:
            logger.debug(f"Extracting links from: {base_url}")
        
        # Method 1: Standard anchor tags with href
        anchor_links = self._extract_anchor_links(soup, base_url, base_domain)
        links.extend(anchor_links)
        
        # Method 2: Area tags (image maps)
        area_links = self._extract_area_links(soup, base_url, base_domain)
        links.extend(area_links)
        
        # Method 3: Form actions
        form_links = self._extract_form_links(soup, base_url, base_domain)
        links.extend(form_links)
        
        # Method 4: Data attributes that might contain URLs
        data_links = self._extract_data_attribute_links(soup, base_url, base_domain)
        links.extend(data_links)
        
        # Method 5: JavaScript links (enhanced extraction)
        if self.config.extract_js_links:
            js_links = self._extract_js_links(soup, base_url, base_domain)
            links.extend(js_links)
        
        # Method 6: CSS links (background images, @import, etc.)
        if self.config.extract_css_links:
            css_links = self._extract_css_links(soup, base_url, base_domain)
            links.extend(css_links)
        
        # Method 7: Meta tags with URLs
        if self.config.extract_meta_links:
            meta_links = self._extract_meta_links(soup, base_url, base_domain)
            links.extend(meta_links)
        
        # Method 8: JSON-LD structured data
        if self.config.extract_json_ld_links:
            json_ld_links = self._extract_json_ld_links(soup, base_url, base_domain)
            links.extend(json_ld_links)
        
        # Method 9: Microdata attributes
        if self.config.extract_microdata_links:
            microdata_links = self._extract_microdata_links(soup, base_url, base_domain)
            links.extend(microdata_links)
        
        # Method 10: Link headers from HTTP response
        if response_headers:
            header_links = self._extract_header_links(response_headers, base_url, base_domain)
            links.extend(header_links)
        
        # Method 11: Comments that might contain URLs
        comment_links = self._extract_comment_links(soup, base_url, base_domain)
        links.extend(comment_links)
        
        # Normalize and deduplicate links
        normalized_links = []
        seen = set()
        for link in links:
            normalized_link = self._normalize_url(link)
            if normalized_link not in seen:
                normalized_links.append(normalized_link)
                seen.add(normalized_link)
        
        if self.config.verbose_logging:
            logger.debug(f"Total unique links found: {len(normalized_links)}")
            logger.debug(f"Link extraction breakdown:")
            logger.debug(f"  - Anchor links: {len(anchor_links)}")
            logger.debug(f"  - Area links: {len(area_links)}")
            logger.debug(f"  - Form links: {len(form_links)}")
            logger.debug(f"  - Data attribute links: {len(data_links)}")
            if self.config.extract_js_links:
                logger.debug(f"  - JavaScript links: {len(js_links)}")
            if self.config.extract_css_links:
                logger.debug(f"  - CSS links: {len(css_links)}")
            if self.config.extract_meta_links:
                logger.debug(f"  - Meta links: {len(meta_links)}")
            if self.config.extract_json_ld_links:
                logger.debug(f"  - JSON-LD links: {len(json_ld_links)}")
            if self.config.extract_microdata_links:
                logger.debug(f"  - Microdata links: {len(microdata_links)}")
            if response_headers:
                logger.debug(f"  - Header links: {len(header_links)}")
            logger.debug(f"  - Comment links: {len(comment_links)}")
        
        return normalized_links
    
    def _extract_anchor_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract links from anchor tags with enhanced attribute support"""
        anchor_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
                
            # Convert relative URLs to absolute
            absolute_url = self._smart_url_join(base_url, href)
            
            if self._is_valid_url(absolute_url, base_domain):
                anchor_links.append(absolute_url)
        
        # Also check for links in aria-label and title attributes that might contain URLs
        for element in soup.find_all(['a', 'button', 'div'], attrs={'aria-label': True}):
            aria_label = element.get('aria-label', '')
            urls = re.findall(r'https?://[^\s<>"]+', aria_label)
            for url in urls:
                if self._is_valid_url(url, base_domain):
                    anchor_links.append(url)
        
        return anchor_links
    
    def _extract_area_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract links from area tags (image maps)"""
        area_links = []
        for area in soup.find_all('area', href=True):
            href = area['href'].strip()
            if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
                
            absolute_url = self._smart_url_join(base_url, href)
            if self._is_valid_url(absolute_url, base_domain):
                area_links.append(absolute_url)
        
        return area_links
    
    def _extract_form_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract links from form actions"""
        form_links = []
        for form in soup.find_all('form', action=True):
            action = form['action'].strip()
            if not action or action.startswith('#') or action.startswith('mailto:'):
                continue
                
            absolute_url = self._smart_url_join(base_url, action)
            if self._is_valid_url(absolute_url, base_domain):
                form_links.append(absolute_url)
        
        return form_links
    
    def _extract_data_attribute_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract links from various data attributes"""
        data_links = []
        
        # Common data attributes that might contain URLs
        data_attributes = [
            'data-href', 'data-url', 'data-link', 'data-src', 'data-target',
            'data-action', 'data-path', 'data-route', 'data-endpoint',
            'data-ajax-url', 'data-load-url', 'data-redirect-url'
        ]
        
        for attr in data_attributes:
            for element in soup.find_all(attrs={attr: True}):
                href = element[attr].strip()
                if href and not href.startswith('#') and not href.startswith('javascript:'):
                    absolute_url = self._smart_url_join(base_url, href)
                    if self._is_valid_url(absolute_url, base_domain):
                        data_links.append(absolute_url)
        
        return data_links
    
    def _extract_js_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from JavaScript code with enhanced but safer patterns"""
        js_links = []
        
        # More conservative patterns for URLs in JavaScript
        url_patterns = [
            # Explicit location assignments (most reliable)
            r'window\.location\s*=\s*["\']([^"\']+)["\']',
            r'location\.href\s*=\s*["\']([^"\']+)["\']',
            r'location\.assign\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'location\.replace\s*\(\s*["\']([^"\']+)["\']\s*\)',
            
            # AJAX and fetch URLs (with stricter context)
            r'fetch\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'\.ajax\s*\(\s*["\']([^"\']+)["\']\s*\)',
            r'xhr\.open\s*\(\s*["\'][^"\']*["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
            
            # Object properties with URL-like keys
            r'url\s*:\s*["\']([^"\']+)["\']',
            r'endpoint\s*:\s*["\']([^"\']+)["\']',
            r'action\s*:\s*["\']([^"\']+)["\']',
            
            # Router/framework paths (more specific)
            r'path\s*:\s*["\']([^"\']+)["\']',
            r'route\s*:\s*["\']([^"\']+)["\']',
            
            # Quoted URLs that look like actual paths (safer pattern)
            r'["\']([\/][a-zA-Z0-9\/_-]+)["\']',
            r'["\']([a-zA-Z0-9][a-zA-Z0-9\/_-]*\.(?:html|htm|php|asp|aspx|jsp|py)(?:\?[^"\']*)?)["\']',
        ]
        
        # Look for URLs in script tags
        for script in soup.find_all('script'):
            if script.string:
                script_content = script.string
                
                for pattern in url_patterns:
                    matches = re.findall(pattern, script_content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        # Handle tuple results from complex patterns
                        if isinstance(match, tuple):
                            match = ''.join(match)
                        
                        # Enhanced validation for JavaScript extracted URLs
                        if self._is_valid_js_url(match, base_url, base_domain):
                            try:
                                absolute_url = self._smart_url_join(base_url, match)
                                if self._is_valid_url(absolute_url, base_domain):
                                    js_links.append(absolute_url)
                            except Exception:
                                continue
        
        # Look for onclick and other event handlers with URLs
        event_attributes = ['onclick', 'onload', 'onchange', 'onsubmit', 'ondblclick']
        for attr in event_attributes:
            for element in soup.find_all(attrs={attr: True}):
                event_code = element[attr]
                url_matches = re.findall(r'["\']([^"\']+\.(?:html|htm|php|asp|aspx|jsp)[^"\']*)["\']', event_code)
                for match in url_matches:
                    try:
                        absolute_url = self._smart_url_join(base_url, match)
                        if self._is_valid_url(absolute_url, base_domain):
                            js_links.append(absolute_url)
                    except Exception:
                        continue
        
        return js_links
    
    def _is_valid_js_url(self, url: str, base_url: str, base_domain: str) -> bool:
        """Validate URLs extracted from JavaScript to filter out code fragments"""
        if not url or len(url.strip()) == 0:
            return False
            
        # Remove quotes and whitespace
        url = url.strip('\'"')
        
        # Skip obviously invalid URLs
        invalid_prefixes = [
            'javascript:', 'mailto:', 'tel:', '#', 'data:', 'blob:', 'about:',
            ');', '};', '{', '}', '(', ')', '[', ']', '/*', '*/', '//', 
            'var ', 'let ', 'const ', 'function', 'return', 'if(', 'for(',
            'window.', 'document.', 'console.', '$('
        ]
        
        for prefix in invalid_prefixes:
            if url.startswith(prefix):
                return False
        
        # Skip URLs containing obvious code patterns
        invalid_patterns = [
            r'[{}();]',  # Contains code characters
            r'^\s*[A-Z_]+\s*$',  # All caps (likely constants)
            r'\\{2,}',  # Multiple backslashes
            r'["\'].*["\']',  # Contains nested quotes
            r'^\d+$',  # Only numbers
            r'[<>]',  # Contains HTML brackets
            r'\s{2,}',  # Multiple spaces
            r'^[^a-zA-Z0-9/._-]',  # Starts with invalid character for URL
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, url):
                return False
        
        # Enhanced validation: check for domain duplication patterns
        # This catches cases like "www.lacolombe.com/products/www.lacolombe.com/products/coffee"
        if base_domain in url:
            domain_count = url.count(base_domain)
            if domain_count > 1:
                # Multiple occurrences of the domain in the URL is suspicious
                return False
        
        # Check for path duplication patterns
        # Look for repeated path segments that suggest malformed URLs
        if '/' in url:
            path_parts = url.split('/')
            # Check if any path segment appears multiple times (excluding empty segments)
            non_empty_parts = [part for part in path_parts if part]
            if len(non_empty_parts) != len(set(non_empty_parts)):
                # Has duplicate path segments, likely malformed
                return False
        
        # Must contain valid URL characters only
        if not re.match(r'^[a-zA-Z0-9\/_.-]+(?:\?[a-zA-Z0-9&=._-]*)?(?:#[a-zA-Z0-9._-]*)?$', url):
            return False
        
        # Skip very short paths that are likely not real URLs
        if len(url) < 2:
            return False
            
        # Skip if it looks like a variable name or code fragment
        if url.replace('/', '').replace('-', '').replace('_', '').replace('.', '').isalnum() and len(url) < 5:
            return False
        
        # Enhanced check for relative URLs
        if not url.startswith(('http://', 'https://')):
            # For relative URLs, be more strict about validation
            if not url.startswith('/') and '.' not in url and '/' not in url:
                # Single word without path separators or extensions
                return False
            
            # Check if it looks like a domain without protocol
            if self._looks_like_domain_url(url, base_domain):
                # Allow domain-like URLs
                return True
            
            # For path-like URLs, ensure they make sense
            if url.startswith('/'):
                # Absolute path - should be valid
                return True
            elif '/' in url or '.' in url:
                # Relative path with some structure
                return True
            else:
                # Single token, likely not a valid URL
                return False
        
        return True
    
    def _extract_css_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from CSS content"""
        css_links = []
        
        # Look for URLs in style tags
        for style in soup.find_all('style'):
            if style.string:
                css_content = style.string
                
                # Extract URLs from CSS
                css_url_pattern = r'url\s*\(\s*["\']?([^"\')]+)["\']?\s*\)'
                matches = re.findall(css_url_pattern, css_content, re.IGNORECASE)
                
                for match in matches:
                    if self._is_valid_css_url(match):
                        try:
                            absolute_url = self._smart_url_join(base_url, match)
                            if self._is_valid_url(absolute_url, base_domain):
                                css_links.append(absolute_url)
                        except Exception:
                            continue
        
        # Check style attributes on elements
        for element in soup.find_all(attrs={'style': True}):
            style_content = element['style']
            css_url_pattern = r'url\s*\(\s*["\']?([^"\')]+)["\']?\s*\)'
            matches = re.findall(css_url_pattern, style_content, re.IGNORECASE)
            
            for match in matches:
                if self._is_valid_css_url(match):
                    try:
                        absolute_url = self._smart_url_join(base_url, match)
                        if self._is_valid_url(absolute_url, base_domain):
                            css_links.append(absolute_url)
                    except Exception:
                        continue
        
        return css_links
    
    def _is_valid_css_url(self, url: str) -> bool:
        """Validate URLs extracted from CSS to filter out invalid ones"""
        if not url or len(url.strip()) == 0:
            return False
            
        url = url.strip('\'"')
        
        # Skip data URLs, fragments, and other non-navigable URLs
        if url.startswith(('data:', '#', 'javascript:', 'mailto:', 'tel:')):
            return False
            
        # Skip URLs that are clearly not navigation links (images, fonts, etc.)
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'}
        font_extensions = {'.woff', '.woff2', '.ttf', '.otf', '.eot'}
        other_assets = {'.css', '.js', '.json', '.xml'}
        
        url_lower = url.lower()
        for ext in image_extensions | font_extensions | other_assets:
            if url_lower.endswith(ext):
                return False
                
        # Only accept URLs that look like navigation paths
        if url.startswith('/') and not any(url_lower.endswith(ext) for ext in {'.html', '.htm', '.php', '.asp', '.aspx', '.jsp'}):
            # Accept directory-like paths
            if '.' in url.split('/')[-1]:  # Has extension but not a page extension
                return False
                
        return True
    
    def _extract_meta_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from meta tags"""
        meta_links = []
        
        # Meta refresh redirects
        for meta in soup.find_all('meta', attrs={'http-equiv': 'refresh'}):
            content = meta.get('content', '')
            # Extract URL from refresh meta tag (format: "5; url=http://example.com")
            match = re.search(r'url\s*=\s*([^;]+)', content, re.IGNORECASE)
            if match:
                url = match.group(1).strip('\'"')
                absolute_url = self._smart_url_join(base_url, url)
                if self._is_valid_url(absolute_url, base_domain):
                    meta_links.append(absolute_url)
        
        # Canonical URLs
        for link in soup.find_all('link', rel='canonical'):
            href = link.get('href')
            if href:
                absolute_url = self._smart_url_join(base_url, href)
                if self._is_valid_url(absolute_url, base_domain):
                    meta_links.append(absolute_url)
        
        # Other link relations that might point to pages
        link_rels = ['next', 'prev', 'alternate', 'related', 'author', 'help']
        for rel in link_rels:
            for link in soup.find_all('link', rel=rel):
                href = link.get('href')
                if href:
                    absolute_url = self._smart_url_join(base_url, href)
                    if self._is_valid_url(absolute_url, base_domain):
                        meta_links.append(absolute_url)
        
        return meta_links
    
    def _extract_json_ld_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from JSON-LD structured data"""
        json_ld_links = []
        
        # Find JSON-LD script tags
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string:
                try:
                    data = json.loads(script.string)
                    
                    # Recursively extract URLs from JSON structure
                    def extract_urls_from_json(obj):
                        urls = []
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if key in ['url', 'sameAs', 'mainEntityOfPage', 'image', 'logo'] and isinstance(value, str):
                                    if value.startswith(('http://', 'https://', '/')):
                                        urls.append(value)
                                elif isinstance(value, (dict, list)):
                                    urls.extend(extract_urls_from_json(value))
                        elif isinstance(obj, list):
                            for item in obj:
                                urls.extend(extract_urls_from_json(item))
                        return urls
                    
                    urls = extract_urls_from_json(data)
                    for url in urls:
                        absolute_url = self._smart_url_join(base_url, url)
                        if self._is_valid_url(absolute_url, base_domain):
                            json_ld_links.append(absolute_url)
                            
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return json_ld_links
    
    def _extract_microdata_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from microdata attributes"""
        microdata_links = []
        
        # Common microdata attributes that might contain URLs
        microdata_attrs = ['itemid', 'itemtype']
        
        for attr in microdata_attrs:
            for element in soup.find_all(attrs={attr: True}):
                value = element[attr]
                if value.startswith(('http://', 'https://', '/')):
                    absolute_url = self._smart_url_join(base_url, value)
                    if self._is_valid_url(absolute_url, base_domain):
                        microdata_links.append(absolute_url)
        
        # Extract from itemprop attributes that commonly contain URLs
        url_itemprops = ['url', 'sameAs', 'mainEntityOfPage', 'image', 'logo']
        for prop in url_itemprops:
            for element in soup.find_all(attrs={'itemprop': prop}):
                # Check href, src, or content attributes
                for attr in ['href', 'src', 'content']:
                    value = element.get(attr)
                    if value and value.startswith(('http://', 'https://', '/')):
                        absolute_url = self._smart_url_join(base_url, value)
                        if self._is_valid_url(absolute_url, base_domain):
                            microdata_links.append(absolute_url)
        
        return microdata_links
    
    def _extract_header_links(self, response_headers: Dict, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from HTTP response headers"""
        header_links = []
        
        # Parse Link header (RFC 5988)
        link_header = response_headers.get('Link', '')
        if link_header:
            # Parse Link header format: <url>; rel="relation", <url2>; rel="relation2"
            link_pattern = r'<([^>]+)>\s*;\s*rel\s*=\s*["\']?([^"\';\s]+)["\']?'
            matches = re.findall(link_pattern, link_header)
            
            for url, rel in matches:
                # Common relations that might point to pages
                if rel in ['next', 'prev', 'canonical', 'alternate', 'related']:
                    absolute_url = self._smart_url_join(base_url, url)
                    if self._is_valid_url(absolute_url, base_domain):
                        header_links.append(absolute_url)
        
        return header_links
    
    def _extract_comment_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Extract URLs from HTML comments"""
        comment_links = []
        
        # Find all comments in the HTML
        comments = soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--'))
        
        for comment in comments:
            # Look for URLs in comments
            url_pattern = r'https?://[^\s<>"]+|/[^\s<>"]*'
            matches = re.findall(url_pattern, str(comment))
            
            for match in matches:
                if not match.startswith(('javascript:', 'mailto:', 'tel:')):
                    try:
                        absolute_url = self._smart_url_join(base_url, match)
                        if self._is_valid_url(absolute_url, base_domain):
                            comment_links.append(absolute_url)
                    except Exception:
                        continue
        
        return comment_links
    
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
        """Fetch a single page and extract content with enhanced error handling"""
        try:
            logger.info(f"Fetching: {url}")
            
            # Handle redirects if configured
            if self.config.follow_redirects:
                response = self.session.get(url, timeout=self.config.timeout, allow_redirects=True)
                # Track redirects to avoid duplicate processing
                if response.url != url:
                    self.redirect_cache[url] = response.url
                    if self.config.verbose_logging:
                        logger.debug(f"URL {url} redirected to {response.url}")
            else:
                response = self.session.get(url, timeout=self.config.timeout, allow_redirects=False)
            
            response.raise_for_status()
            
            # Only process HTML content
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                logger.warning(f"Skipping non-HTML content: {url} (content-type: {content_type})")
                return None
            
            # Check for empty response
            if not response.content:
                logger.warning(f"Empty response from {url}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Extract links with response headers
            links = self._extract_links(soup, url, dict(response.headers))
            
            # Clean HTML content
            clean_text = self._clean_html_content(soup)
            
            # Get final URL (after redirects)
            final_url = response.url if hasattr(response, 'url') else url
            
            return {
                'url': final_url,
                'original_url': url if final_url != url else None,
                'title': title_text,
                'html_content': str(soup),
                'clean_text': clean_text,
                'links': links,
                'status_code': response.status_code,
                'content_type': content_type,
                'response_headers': dict(response.headers)
            }
            
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            return None
    
    def crawl_website(self, start_url: str) -> Dict:
        """
        Crawl a website starting from the given URL with enhanced link discovery
        
        Returns:
            Dict containing all crawled pages and their content
        """
        logger.info(f"Starting enhanced crawl of: {start_url}")
        
        # Normalize the starting URL
        start_url = self._normalize_url(start_url)
        
        # Initialize tracking sets and lists
        visited_urls: Set[str] = set()
        urls_to_visit: Set[str] = {start_url}
        all_pages: List[Dict] = []
        all_links: Set[str] = set()
        failed_urls: Set[str] = set()
        
        base_domain = urlparse(start_url).netloc
        
        logger.info(f"Enhanced crawler configuration:")
        logger.info(f"  - Extract JS links: {self.config.extract_js_links}")
        logger.info(f"  - Extract CSS links: {self.config.extract_css_links}")
        logger.info(f"  - Extract meta links: {self.config.extract_meta_links}")
        logger.info(f"  - Extract JSON-LD links: {self.config.extract_json_ld_links}")
        logger.info(f"  - Extract microdata links: {self.config.extract_microdata_links}")
        logger.info(f"  - Follow redirects: {self.config.follow_redirects}")
        logger.info(f"  - Normalize URLs: {self.config.normalize_urls}")
        
        while urls_to_visit and len(visited_urls) < self.config.max_pages:
            # Get next batch of URLs to process
            current_batch = list(urls_to_visit)[:self.config.max_workers]
            urls_to_visit -= set(current_batch)
            
            logger.info(f"Processing batch of {len(current_batch)} URLs. Queue size: {len(urls_to_visit)}, Visited: {len(visited_urls)}")
            
            # Process batch concurrently
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_url = {
                    executor.submit(self._fetch_page, url): url 
                    for url in current_batch if url not in visited_urls and url not in failed_urls
                }
                
                for future in as_completed(future_to_url):
                    original_url = future_to_url[future]
                    visited_urls.add(original_url)
                    
                    try:
                        page_data = future.result()
                        if page_data:
                            all_pages.append(page_data)
                            
                            # Track the final URL if it's different (due to redirects)
                            final_url = page_data['url']
                            if final_url != original_url:
                                visited_urls.add(final_url)
                            
                            # Add new links to crawl queue
                            new_links = 0
                            duplicate_links = 0
                            invalid_links = 0
                            
                            for link in page_data['links']:
                                all_links.add(link)
                                
                                # Check if we should crawl this link
                                if (link not in visited_urls and 
                                    link not in failed_urls and 
                                    len(visited_urls) < self.config.max_pages):
                                    
                                    # Check for redirected URLs to avoid duplicates
                                    is_duplicate = False
                                    for cached_url, redirect_url in self.redirect_cache.items():
                                        if link == redirect_url and cached_url in visited_urls:
                                            is_duplicate = True
                                            duplicate_links += 1
                                            break
                                    
                                    if not is_duplicate and link not in urls_to_visit:
                                        urls_to_visit.add(link)
                                        new_links += 1
                                else:
                                    if link in visited_urls or link in failed_urls:
                                        duplicate_links += 1
                                    else:
                                        invalid_links += 1
                            
                            if self.config.verbose_logging:
                                logger.debug(f"Page {original_url} contributed {new_links} new links to queue")
                                logger.debug(f"  - Duplicate/failed links skipped: {duplicate_links}")
                                logger.debug(f"  - Invalid links skipped: {invalid_links}")
                                logger.debug(f"  - Total links found on page: {len(page_data['links'])}")
                        else:
                            failed_urls.add(original_url)
                            if self.config.verbose_logging:
                                logger.debug(f"Failed to process {original_url}")
                                    
                    except Exception as e:
                        logger.error(f"Error processing result for {original_url}: {e}")
                        failed_urls.add(original_url)
            
            # Respect rate limiting
            if urls_to_visit:
                time.sleep(self.config.delay_between_requests)
        
        # Generate comprehensive statistics
        total_unique_links = len(all_links)
        pages_crawled = len(all_pages)
        urls_failed = len(failed_urls)
        coverage_ratio = pages_crawled / max(total_unique_links, 1)
        
        logger.info(f"Enhanced crawl completed!")
        logger.info(f"  - Pages successfully crawled: {pages_crawled}")
        logger.info(f"  - Failed URLs: {urls_failed}")
        logger.info(f"  - Total unique links discovered: {total_unique_links}")
        logger.info(f"  - Coverage ratio: {coverage_ratio:.2%}")
        logger.info(f"  - Redirect cache entries: {len(self.redirect_cache)}")
        
        return {
            'start_url': start_url,
            'base_domain': base_domain,
            'pages': all_pages,
            'visited_urls': list(visited_urls),
            'failed_urls': list(failed_urls),
            'all_links': list(all_links),
            'total_pages': len(all_pages),
            'redirect_cache': dict(self.redirect_cache),
            'crawler_stats': {
                'pages_crawled': pages_crawled,
                'urls_failed': urls_failed,
                'total_unique_links': total_unique_links,
                'coverage_ratio': coverage_ratio
            }
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

    def discover_links_only(self, start_url: str) -> Dict:
        """
        Discover all links from a website without fetching full HTML content.
        This is much faster and focuses only on link discovery for manual curation.
        
        Returns:
            Dict containing discovered links with metadata for manual filtering
        """
        logger.info(f"Starting link discovery for: {start_url}")
        
        # Normalize the starting URL
        start_url = self._normalize_url(start_url)
        
        # Initialize tracking sets and lists
        visited_urls: Set[str] = set()
        urls_to_visit: Set[str] = {start_url}
        all_discovered_links: List[Dict] = []
        source_pages: List[Dict] = []
        failed_urls: Set[str] = set()
        
        base_domain = urlparse(start_url).netloc
        
        logger.info(f"Link discovery configuration:")
        logger.info(f"  - Max pages to scan: {self.config.max_pages}")
        logger.info(f"  - Enhanced link extraction: {self.config.extract_js_links}")
        
        while urls_to_visit and len(visited_urls) < self.config.max_pages:
            # Get next batch of URLs to process
            current_batch = list(urls_to_visit)[:self.config.max_workers]
            urls_to_visit -= set(current_batch)
            
            logger.info(f"Scanning batch of {len(current_batch)} URLs for links. Queue: {len(urls_to_visit)}, Scanned: {len(visited_urls)}")
            
            # Process batch concurrently
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_url = {
                    executor.submit(self._fetch_page_for_links_only, url): url 
                    for url in current_batch if url not in visited_urls and url not in failed_urls
                }
                
                for future in as_completed(future_to_url):
                    original_url = future_to_url[future]
                    visited_urls.add(original_url)
                    
                    try:
                        page_data = future.result()
                        if page_data:
                            source_pages.append({
                                'url': page_data['url'],
                                'original_url': page_data.get('original_url'),
                                'title': page_data['title'],
                                'links_found': len(page_data['links']),
                                'fetch_status': 'success',
                                'discovery_methods': page_data.get('discovery_methods', [])
                            })
                            
                            # Process discovered links
                            for link_data in page_data['links_with_metadata']:
                                # Add source information
                                link_entry = {
                                    'url': link_data['url'],
                                    'source_page': page_data['url'],
                                    'discovery_method': link_data['discovery_method'],
                                    'link_type': 'internal' if urlparse(link_data['url']).netloc == base_domain else 'external',
                                    'status': 'pending',  # For manual review
                                    'notes': ''
                                }
                                all_discovered_links.append(link_entry)
                                
                                # Add to crawl queue if internal and not yet visited
                                link_url = link_data['url']
                                if (link_entry['link_type'] == 'internal' and 
                                    link_url not in visited_urls and 
                                    link_url not in failed_urls and 
                                    len(visited_urls) < self.config.max_pages):
                                    urls_to_visit.add(link_url)
                        else:
                            failed_urls.add(original_url)
                            source_pages.append({
                                'url': original_url,
                                'title': 'Failed to fetch',
                                'links_found': 0,
                                'fetch_status': 'failed'
                            })
                                    
                    except Exception as e:
                        logger.error(f"Error processing {original_url}: {e}")
                        failed_urls.add(original_url)
            
            # Respect rate limiting
            if urls_to_visit:
                time.sleep(self.config.delay_between_requests)
        
        # Remove duplicates from discovered links
        unique_links = []
        seen_urls = set()
        for link in all_discovered_links:
            if link['url'] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link['url'])
        
        logger.info(f"Link discovery completed!")
        logger.info(f"  - Pages scanned: {len(source_pages)}")
        logger.info(f"  - Unique links discovered: {len(unique_links)}")
        logger.info(f"  - Failed URLs: {len(failed_urls)}")
        
        return {
            'discovery_metadata': {
                'base_url': start_url,
                'base_domain': base_domain,
                'total_pages_scanned': len(source_pages),
                'total_links_found': len(unique_links),
                'failed_urls_count': len(failed_urls),
                'crawler_config': {
                    'max_pages': self.config.max_pages,
                    'extract_js_links': self.config.extract_js_links,
                    'extract_css_links': self.config.extract_css_links,
                    'extract_meta_links': self.config.extract_meta_links,
                    'extract_json_ld_links': self.config.extract_json_ld_links,
                    'extract_microdata_links': self.config.extract_microdata_links,
                }
            },
            'discovered_links': unique_links,
            'source_pages': source_pages,
            'failed_urls': list(failed_urls)
        }

    def _fetch_page_for_links_only(self, url: str) -> Optional[Dict]:
        """Lightweight page fetch focused only on link extraction"""
        try:
            logger.info(f"Scanning for links: {url}")
            
            response = self.session.get(url, timeout=self.config.timeout, allow_redirects=self.config.follow_redirects)
            response.raise_for_status()
            
            # Only process HTML content
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                logger.warning(f"Skipping non-HTML content: {url}")
                return None
            
            if not response.content:
                logger.warning(f"Empty response from {url}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Extract links with metadata about discovery method
            links_with_metadata = self._extract_links_with_metadata(soup, url, dict(response.headers))
            links = [link['url'] for link in links_with_metadata]
            
            # Get final URL (after redirects)
            final_url = response.url if hasattr(response, 'url') else url
            
            return {
                'url': final_url,
                'original_url': url if final_url != url else None,
                'title': title_text,
                'links': links,
                'links_with_metadata': links_with_metadata,
                'status_code': response.status_code,
                'discovery_methods': list(set(link['discovery_method'] for link in links_with_metadata))
            }
            
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            return None

    def _extract_links_with_metadata(self, soup: BeautifulSoup, base_url: str, response_headers: Dict = None) -> List[Dict]:
        """Enhanced link extraction that tracks the discovery method for each link"""
        links_with_metadata = []
        base_domain = urlparse(base_url).netloc
        
        # Method 1: Standard anchor tags
        anchor_links = self._extract_anchor_links(soup, base_url, base_domain)
        for link in anchor_links:
            links_with_metadata.append({
                'url': link,
                'discovery_method': 'anchor'
            })
        
        # Method 2: JavaScript links
        if self.config.extract_js_links:
            js_links = self._extract_js_links(soup, base_url, base_domain)
            for link in js_links:
                links_with_metadata.append({
                    'url': link,
                    'discovery_method': 'javascript'
                })
        
        # Method 3: Meta links
        if self.config.extract_meta_links:
            meta_links = self._extract_meta_links(soup, base_url, base_domain)
            for link in meta_links:
                links_with_metadata.append({
                    'url': link,
                    'discovery_method': 'meta'
                })
        
        # Method 4: Form actions
        form_links = self._extract_form_links(soup, base_url, base_domain)
        for link in form_links:
            links_with_metadata.append({
                'url': link,
                'discovery_method': 'form'
            })
        
        # Method 5: Data attributes
        data_links = self._extract_data_attribute_links(soup, base_url, base_domain)
        for link in data_links:
            links_with_metadata.append({
                'url': link,
                'discovery_method': 'data_attribute'
            })
        
        # Method 6: CSS links
        if self.config.extract_css_links:
            css_links = self._extract_css_links(soup, base_url, base_domain)
            for link in css_links:
                links_with_metadata.append({
                    'url': link,
                    'discovery_method': 'css'
                })
        
        # Method 7: JSON-LD structured data
        if self.config.extract_json_ld_links:
            json_ld_links = self._extract_json_ld_links(soup, base_url, base_domain)
            for link in json_ld_links:
                links_with_metadata.append({
                    'url': link,
                    'discovery_method': 'json_ld'
                })
        
        # Method 8: Microdata
        if self.config.extract_microdata_links:
            microdata_links = self._extract_microdata_links(soup, base_url, base_domain)
            for link in microdata_links:
                links_with_metadata.append({
                    'url': link,
                    'discovery_method': 'microdata'
                })
        
        # Method 9: HTTP headers
        if response_headers:
            header_links = self._extract_header_links(response_headers, base_url, base_domain)
            for link in header_links:
                links_with_metadata.append({
                    'url': link,
                    'discovery_method': 'http_header'
                })
        
        # Method 10: Comments
        comment_links = self._extract_comment_links(soup, base_url, base_domain)
        for link in comment_links:
            links_with_metadata.append({
                'url': link,
                'discovery_method': 'comment'
            })
        
        # Normalize URLs and remove duplicates
        normalized_links = []
        seen = set()
        for link_data in links_with_metadata:
            normalized_url = self._normalize_url(link_data['url'])
            if normalized_url not in seen:
                normalized_links.append({
                    'url': normalized_url,
                    'discovery_method': link_data['discovery_method']
                })
                seen.add(normalized_url)
        
        return normalized_links


def create_coffee_crawler(max_pages: int = 100, verbose: bool = False, aggressive: bool = True) -> WebCrawler:
    """Create a crawler optimized for coffee shop websites with enhanced link discovery"""
    if aggressive:
        config = CrawlConfig(
            max_pages=max_pages,
            delay_between_requests=1.0,  # Faster crawling
            max_workers=5,  # More concurrent workers
            follow_external_links=False,
            extract_js_links=True,
            extract_css_links=True,
            extract_meta_links=True,
            extract_json_ld_links=True,
            extract_microdata_links=True,
            follow_redirects=True,
            normalize_urls=True,
            verbose_logging=verbose,
        )
    else:
        config = CrawlConfig(
            max_pages=max_pages,
            delay_between_requests=1.5,
            max_workers=3,
            follow_external_links=False,
            extract_js_links=True,
            extract_css_links=False,  # Disabled for conservative mode
            extract_meta_links=True,
            extract_json_ld_links=False,  # Disabled for conservative mode
            extract_microdata_links=False,  # Disabled for conservative mode
            follow_redirects=True,
            normalize_urls=True,
            verbose_logging=verbose,
        )
    return WebCrawler(config) 