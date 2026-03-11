"""
Free Web Scraper - Alternative to Bright Data Crawl API
Uses requests, BeautifulSoup, and Selenium for web scraping
"""

import os
import json
import time
import logging
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Optional Selenium for JavaScript-heavy sites
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.warning("Selenium not available. Some sites may not scrape properly.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Request configuration
REQUEST_TIMEOUT = 30
REQUEST_DELAY = (1, 3)  # Random delay between requests in seconds
MAX_RETRIES = 3
ROTATE_USER_AGENTS = True

# Selenium configuration (if available)
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH", None)  # Auto-detect if None
HEADLESS_MODE = True

@dataclass
class ScrapingConfig:
    """Configuration for free web scraper"""
    use_selenium: bool = False
    headless: bool = True
    timeout: int = 30
    delay_range: tuple = (1, 3)
    max_retries: int = 3
    rotate_user_agents: bool = True
    respect_robots_txt: bool = True

@dataclass
class ScrapedResult:
    """Result from web scraping"""
    url: str
    title: str = ""
    content: str = ""
    markdown: str = ""
    html: str = ""
    status_code: int = 200
    error: str = ""
    scrape_method: str = "requests"  # requests or selenium
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

class FreeWebScraper:
    """Free alternative to Bright Data Crawl API"""
    
    def __init__(self, config: ScrapingConfig = None):
        self.config = config or ScrapingConfig()
        self.session = requests.Session()
        self.ua = UserAgent() if self.config.rotate_user_agents else None
        self.driver = None
        
        # Setup session headers
        self._setup_session()
        
        # Setup Selenium if needed
        if self.config.use_selenium and SELENIUM_AVAILABLE:
            self._setup_selenium()

    def _setup_session(self):
        """Setup requests session with headers"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if self.ua:
            headers['User-Agent'] = self.ua.random
        else:
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        self.session.headers.update(headers)

    def _setup_selenium(self):
        """Setup Selenium WebDriver"""
        if not SELENIUM_AVAILABLE:
            log.warning("Selenium not available, falling back to requests")
            return
            
        try:
            options = Options()
            if self.config.headless:
                options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # Random user agent
            if self.ua:
                options.add_argument(f'--user-agent={self.ua.random}')
            
            if CHROME_DRIVER_PATH:
                self.driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
                
            self.driver.set_page_load_timeout(self.config.timeout)
            log.info("Selenium WebDriver initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize Selenium: {e}")
            self.driver = None

    def _random_delay(self):
        """Add random delay to avoid rate limiting"""
        delay = random.uniform(*self.config.delay_range)
        time.sleep(delay)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common unwanted characters
        unwanted = ['\t', '\r', '\x0b', '\x0c']
        for char in unwanted:
            text = text.replace(char, '')
        
        return text.strip()

    def _html_to_markdown(self, html: str, url: str) -> str:
        """Convert HTML to markdown-like format"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        markdown_parts = []
        
        # Extract title
        title = soup.find('title')
        if title:
            markdown_parts.append(f"# {self._clean_text(title.get_text())}\n")
        
        # Extract main content
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
            text = self._clean_text(tag.get_text())
            if not text:
                continue
                
            if tag.name.startswith('h'):
                level = int(tag.name[1])
                markdown_parts.append(f"{'#' * (level + 1)} {text}\n")
            elif tag.name == 'li':
                markdown_parts.append(f"- {text}\n")
            else:
                markdown_parts.append(f"{text}\n")
        
        # Extract links
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = self._clean_text(link.get_text())
            if href and text:
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    base_url = urlparse(url)
                    href = f"{base_url.scheme}://{base_url.netloc}{href}"
                markdown_parts.append(f"[{text}]({href})\n")
        
        return '\n'.join(markdown_parts)

    def scrape_with_requests(self, url: str) -> ScrapedResult:
        """Scrape URL using requests + BeautifulSoup"""
        result = ScrapedResult(url=url, scrape_method="requests")
        
        for attempt in range(self.config.max_retries):
            try:
                # Rotate user agent if enabled
                if self.ua and attempt > 0:
                    self.session.headers['User-Agent'] = self.ua.random
                
                response = self.session.get(url, timeout=self.config.timeout)
                result.status_code = response.status_code
                
                if response.status_code == 200:
                    result.html = response.text
                    
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract title
                    title_tag = soup.find('title')
                    if title_tag:
                        result.title = self._clean_text(title_tag.get_text())
                    
                    # Extract text content
                    for script in soup(["script", "style"]):
                        script.decompose()
                    result.content = self._clean_text(soup.get_text())
                    
                    # Convert to markdown
                    result.markdown = self._html_to_markdown(response.text, url)
                    
                    # Add metadata
                    result.metadata = {
                        'content_length': len(result.content),
                        'html_length': len(result.html),
                        'word_count': len(result.content.split()),
                        'response_headers': dict(response.headers),
                        'final_url': response.url
                    }
                    
                    log.info(f"Successfully scraped {url} with requests")
                    return result
                else:
                    result.error = f"HTTP {response.status_code}"
                    log.warning(f"HTTP {response.status_code} for {url}")
                    
            except Exception as e:
                result.error = str(e)
                log.error(f"Request failed for {url} (attempt {attempt + 1}): {e}")
                
                if attempt < self.config.max_retries - 1:
                    self._random_delay()
        
        return result

    def scrape_with_selenium(self, url: str) -> ScrapedResult:
        """Scrape URL using Selenium for JavaScript-heavy sites"""
        if not self.driver:
            log.warning("Selenium not available, falling back to requests")
            return self.scrape_with_requests(url)
        
        result = ScrapedResult(url=url, scrape_method="selenium")
        
        try:
            self.driver.get(url)
            result.status_code = 200
            
            # Wait for page to load
            WebDriverWait(self.driver, self.config.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract title
            title = self.driver.title
            if title:
                result.title = self._clean_text(title)
            
            # Extract page source
            html = self.driver.page_source
            result.html = html
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract text content
            for script in soup(["script", "style"]):
                script.decompose()
            result.content = self._clean_text(soup.get_text())
            
            # Convert to markdown
            result.markdown = self._html_to_markdown(html, url)
            
            # Add metadata
            result.metadata = {
                'content_length': len(result.content),
                'html_length': len(result.html),
                'word_count': len(result.content.split()),
                'current_url': self.driver.current_url,
                'window_handles': len(self.driver.window_handles)
            }
            
            log.info(f"Successfully scraped {url} with Selenium")
            return result
            
        except TimeoutException:
            result.error = "Page load timeout"
            result.status_code = 408
        except WebDriverException as e:
            result.error = f"WebDriver error: {str(e)}"
            result.status_code = 500
        except Exception as e:
            result.error = str(e)
            result.status_code = 500
        
        log.error(f"Selenium failed for {url}: {result.error}")
        return result

    def scrape_urls(self, urls: List[str]) -> List[ScrapedResult]:
        """Scrape multiple URLs"""
        results = []
        
        for i, url in enumerate(urls):
            log.info(f"Scraping URL {i+1}/{len(urls)}: {url}")
            
            # Add delay between requests (except first one)
            if i > 0:
                self._random_delay()
            
            # Choose scraping method
            if self.config.use_selenium and self.driver:
                result = self.scrape_with_selenium(url)
            else:
                result = self.scrape_with_requests(url)
            
            results.append(result)
        
        return results

    def crawl(self, urls: List[str]) -> Dict[str, Any]:
        """Main crawl method - compatible with Bright Data interface"""
        results = self.scrape_urls(urls)
        
        # Convert to Bright Data-like format
        crawl_results = []
        successful = 0
        failed = 0
        
        for result in results:
            if result.status_code == 200 and not result.error:
                successful += 1
                crawl_results.append({
                    'url': result.url,
                    'title': result.title,
                    'content': result.content,
                    'markdown': result.markdown,
                    'html': result.html,
                    'status': 'success',
                    'scraped_at': result.scraped_at,
                    'metadata': result.metadata
                })
            else:
                failed += 1
                crawl_results.append({
                    'url': result.url,
                    'error': result.error,
                    'status': 'failed',
                    'status_code': result.status_code,
                    'scraped_at': result.scraped_at
                })
        
        return {
            'results': crawl_results,
            'summary': {
                'total_urls': len(urls),
                'successful': successful,
                'failed': failed,
                'success_rate': (successful / len(urls) * 100) if urls else 0,
                'crawl_time': datetime.utcnow().isoformat() + "Z"
            }
        }

    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.session.close()

# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def create_scraper(use_selenium: bool = False, headless: bool = True) -> FreeWebScraper:
    """Create a configured scraper instance"""
    config = ScrapingConfig(
        use_selenium=use_selenium,
        headless=headless,
        timeout=REQUEST_TIMEOUT,
        delay_range=REQUEST_DELAY,
        max_retries=MAX_RETRIES,
        rotate_user_agents=ROTATE_USER_AGENTS
    )
    return FreeWebScraper(config)

def quick_scrape(urls: List[str], use_selenium: bool = False) -> Dict[str, Any]:
    """Quick scrape function for simple use cases"""
    scraper = create_scraper(use_selenium=use_selenium)
    try:
        return scraper.crawl(urls)
    finally:
        scraper.close()

if __name__ == "__main__":
    # Test the scraper
    test_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://python.org"
    ]
    
    print("Testing free web scraper...")
    result = quick_scrape(test_urls)
    
    print(f"\nCrawl Summary:")
    print(f"Total URLs: {result['summary']['total_urls']}")
    print(f"Successful: {result['summary']['successful']}")
    print(f"Failed: {result['summary']['failed']}")
    print(f"Success Rate: {result['summary']['success_rate']:.1f}%")
    
    print("\nSample Results:")
    for i, res in enumerate(result['results'][:2]):
        print(f"\n{i+1}. {res['url']}")
        print(f"   Status: {res.get('status', 'unknown')}")
        if res.get('title'):
            print(f"   Title: {res['title'][:50]}...")
        if res.get('error'):
            print(f"   Error: {res['error']}")
