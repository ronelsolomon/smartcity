"""
Montgomery County Open Data Scraper
Specialized scraper for Montgomery County AL open data portal
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import pandas as pd
from free_scraper import FreeWebScraper, ScrapingConfig, quick_scrape

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class MontgomeryDataset:
    """Montgomery County dataset metadata"""
    name: str
    description: str
    url: str
    download_url: Optional[str] = None
    format: str = "json"  # json, csv, api
    category: str = ""
    last_updated: Optional[str] = None
    record_count: Optional[int] = None
    size: Optional[str] = None

class MontgomeryDataScraper:
    """Specialized scraper for Montgomery County Open Data Portal"""
    
    def __init__(self, base_url: str = "https://opendata.montgomeryal.gov"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Key datasets for vacancy watch
        self.target_datasets = {
            'building_permits': {
                'keywords': ['permit', 'building', 'construction'],
                'priority': 'high'
            },
            'code_violations': {
                'keywords': ['violation', 'code', 'enforcement'],
                'priority': 'high'
            },
            'vacant_properties': {
                'keywords': ['vacant', 'vacancy', 'abandoned'],
                'priority': 'high'
            },
            'traffic_incidents': {
                'keywords': ['traffic', 'incident', 'accident'],
                'priority': 'medium'
            },
            'property_assessments': {
                'keywords': ['property', 'assessment', 'tax'],
                'priority': 'medium'
            },
            'real_estate': {
                'keywords': ['real estate', 'property', 'housing'],
                'priority': 'medium'
            }
        }
    
    def discover_datasets(self) -> List[MontgomeryDataset]:
        """Discover available datasets on the portal"""
        datasets = []
        
        try:
            # Try common API endpoints first
            api_endpoints = [
                '/api/v1/catalog',
                '/api/datasets',
                '/datasets.json',
                '/search?q=',
                '/data.json'
            ]
            
            for endpoint in api_endpoints:
                url = urljoin(self.base_url, endpoint)
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        datasets.extend(self._parse_api_response(data, url))
                        log.info(f"Found {len(datasets)} datasets via {endpoint}")
                        break
                except Exception as e:
                    log.debug(f"API endpoint {endpoint} failed: {e}")
                    continue
            
            # If API fails, scrape the main page
            if not datasets:
                datasets = self._scrape_main_page()
            
        except Exception as e:
            log.error(f"Error discovering datasets: {e}")
        
        return datasets
    
    def _parse_api_response(self, data: Dict, source_url: str) -> List[MontgomeryDataset]:
        """Parse API response for dataset information"""
        datasets = []
        
        # Handle different API formats
        if 'results' in data:
            items = data['results']
        elif 'datasets' in data:
            items = data['datasets']
        elif 'data' in data:
            items = data['data']
        elif isinstance(data, list):
            items = data
        else:
            items = [data]
        
        for item in items:
            try:
                dataset = MontgomeryDataset(
                    name=item.get('name', item.get('title', '')),
                    description=item.get('description', ''),
                    url=item.get('url', item.get('web_uri', '')),
                    download_url=item.get('download_url', item.get('resource', {}).get('url')),
                    format=self._detect_format(item),
                    category=item.get('category', item.get('theme', '')),
                    last_updated=item.get('modified', item.get('last_updated')),
                    record_count=item.get('record_count', item.get('num_records')),
                    size=item.get('size', item.get('file_size'))
                )
                datasets.append(dataset)
            except Exception as e:
                log.warning(f"Error parsing dataset item: {e}")
                continue
        
        return datasets
    
    def _scrape_main_page(self) -> List[MontgomeryDataset]:
        """Scrape the main portal page for datasets"""
        datasets = []
        
        try:
            response = self.session.get(self.base_url, timeout=15)
            if response.status_code != 200:
                return datasets
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for dataset links
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text().strip()
                
                # Check if link might be a dataset
                if any(keyword in text.lower() for keywords in self.target_datasets.values() 
                       for keyword in keywords['keywords']):
                    
                    dataset = MontgomeryDataset(
                        name=text,
                        description=text,
                        url=urljoin(self.base_url, href),
                        format='html'
                    )
                    datasets.append(dataset)
            
        except Exception as e:
            log.error(f"Error scraping main page: {e}")
        
        return datasets
    
    def _detect_format(self, item: Dict) -> str:
        """Detect dataset format from item metadata"""
        # Check for explicit format
        if 'format' in item:
            return item['format']
        
        # Check URL patterns
        url = item.get('url', '') or item.get('download_url', '')
        if url.endswith('.json'):
            return 'json'
        elif url.endswith('.csv'):
            return 'csv'
        elif 'api' in url.lower():
            return 'api'
        
        return 'json'  # Default assumption
    
    def download_dataset(self, dataset: MontgomeryDataset) -> Dict[str, Any]:
        """Download and parse dataset"""
        result = {
            'dataset_name': dataset.name,
            'success': False,
            'data': None,
            'error': '',
            'record_count': 0,
            'downloaded_at': datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            if dataset.format == 'api':
                result = self._download_api_data(dataset)
            elif dataset.format == 'csv':
                result = self._download_csv_data(dataset)
            elif dataset.format == 'json':
                result = self._download_json_data(dataset)
            else:
                # Try to scrape HTML page
                result = self._scrape_html_data(dataset)
                
        except Exception as e:
            result['error'] = str(e)
            log.error(f"Error downloading dataset {dataset.name}: {e}")
        
        return result
    
    def _download_api_data(self, dataset: MontgomeryDataset) -> Dict[str, Any]:
        """Download data from API endpoint"""
        result = {
            'dataset_name': dataset.name,
            'success': False,
            'data': None,
            'error': '',
            'record_count': 0,
            'downloaded_at': datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            # Add common API parameters
            url = dataset.url
            if '?' not in url:
                url += '?$limit=1000'  # Common Socrata API parameter
            else:
                url += '&$limit=1000'
            
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                # Handle paginated responses
                if isinstance(data, list):
                    result['data'] = data
                    result['record_count'] = len(data)
                elif 'data' in data:
                    result['data'] = data['data']
                    result['record_count'] = len(data['data'])
                else:
                    result['data'] = data
                    result['record_count'] = 1 if data else 0
                
                result['success'] = True
                log.info(f"Downloaded {result['record_count']} records from {dataset.name}")
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _download_csv_data(self, dataset: MontgomeryDataset) -> Dict[str, Any]:
        """Download and parse CSV data"""
        result = {
            'dataset_name': dataset.name,
            'success': False,
            'data': None,
            'error': '',
            'record_count': 0,
            'downloaded_at': datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            response = self.session.get(dataset.download_url or dataset.url, timeout=30)
            if response.status_code == 200:
                # Parse CSV
                df = pd.read_csv(pd.StringIO(response.text))
                result['data'] = df.to_dict('records')
                result['record_count'] = len(df)
                result['success'] = True
                log.info(f"Downloaded {result['record_count']} records from CSV {dataset.name}")
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _download_json_data(self, dataset: MontgomeryDataset) -> Dict[str, Any]:
        """Download JSON data"""
        result = {
            'dataset_name': dataset.name,
            'success': False,
            'data': None,
            'error': '',
            'record_count': 0,
            'downloaded_at': datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            response = self.session.get(dataset.download_url or dataset.url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    result['data'] = data
                    result['record_count'] = len(data)
                elif isinstance(data, dict):
                    result['data'] = data
                    result['record_count'] = 1
                else:
                    result['data'] = [data]
                    result['record_count'] = 1
                
                result['success'] = True
                log.info(f"Downloaded {result['record_count']} records from JSON {dataset.name}")
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _scrape_html_data(self, dataset: MontgomeryDataset) -> Dict[str, Any]:
        """Scrape data from HTML page"""
        result = {
            'dataset_name': dataset.name,
            'success': False,
            'data': None,
            'error': '',
            'record_count': 0,
            'downloaded_at': datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            # Use the free scraper for HTML pages
            scraper_result = quick_scrape([dataset.url], use_selenium=True)
            
            if scraper_result['summary']['successful'] > 0:
                scraped_data = scraper_result['results'][0]
                result['data'] = {
                    'url': dataset.url,
                    'title': scraped_data.get('title', ''),
                    'content': scraped_data.get('content', ''),
                    'markdown': scraped_data.get('markdown', '')
                }
                result['record_count'] = 1
                result['success'] = True
                log.info(f"Scraped HTML content from {dataset.name}")
            else:
                result['error'] = "Failed to scrape HTML page"
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def categorize_datasets(self, datasets: List[MontgomeryDataset]) -> Dict[str, List[MontgomeryDataset]]:
        """Categorize datasets by type for vacancy watch"""
        categorized = {
            'building_permits': [],
            'code_violations': [],
            'vacant_properties': [],
            'traffic_incidents': [],
            'property_assessments': [],
            'real_estate': [],
            'other': []
        }
        
        for dataset in datasets:
            categorized_flag = False
            
            for category, config in self.target_datasets.items():
                if any(keyword in dataset.name.lower() or keyword in dataset.description.lower() 
                       for keyword in config['keywords']):
                    categorized[category].append(dataset)
                    categorized_flag = True
                    break
            
            if not categorized_flag:
                categorized['other'].append(dataset)
        
        return categorized
    
    def crawl_all_datasets(self, max_datasets_per_category: int = 3) -> Dict[str, Any]:
        """Crawl all relevant datasets"""
        log.info("Starting Montgomery County data crawl...")
        
        # Discover datasets
        datasets = self.discover_datasets()
        log.info(f"Discovered {len(datasets)} datasets")
        
        # Categorize datasets
        categorized = self.categorize_datasets(datasets)
        
        # Download data from key categories
        crawl_results = {
            'discovered_datasets': len(datasets),
            'categories': {},
            'downloads': {},
            'summary': {
                'total_downloads': 0,
                'successful_downloads': 0,
                'failed_downloads': 0,
                'total_records': 0
            },
            'crawled_at': datetime.utcnow().isoformat() + "Z"
        }
        
        for category, category_datasets in categorized.items():
            if category == 'other':
                continue  # Skip other categories for now
            
            crawl_results['categories'][category] = len(category_datasets)
            
            # Limit downloads per category
            datasets_to_download = category_datasets[:max_datasets_per_category]
            
            for dataset in datasets_to_download:
                log.info(f"Downloading {category} dataset: {dataset.name}")
                download_result = self.download_dataset(dataset)
                
                if category not in crawl_results['downloads']:
                    crawl_results['downloads'][category] = []
                
                crawl_results['downloads'][category].append(download_result)
                crawl_results['summary']['total_downloads'] += 1
                
                if download_result['success']:
                    crawl_results['summary']['successful_downloads'] += 1
                    crawl_results['summary']['total_records'] += download_result['record_count']
                else:
                    crawl_results['summary']['failed_downloads'] += 1
        
        log.info(f"Crawl completed: {crawl_results['summary']['successful_downloads']}/{crawl_results['summary']['total_downloads']} downloads successful")
        
        return crawl_results
    
    def save_crawl_results(self, results: Dict[str, Any], output_dir: str = ".") -> Dict[str, str]:
        """Save crawl results to files"""
        saved_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save main results
            results_file = f"montgomery_crawl_results_{timestamp}.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            saved_files['results'] = results_file
            
            # Save individual category data
            for category, downloads in results['downloads'].items():
                category_data = []
                for download in downloads:
                    if download['success'] and download['data']:
                        category_data.extend(download['data'] if isinstance(download['data'], list) else [download['data']])
                
                if category_data:
                    category_file = f"montgomery_{category}_{timestamp}.json"
                    with open(category_file, 'w') as f:
                        json.dump(category_data, f, indent=2)
                    saved_files[category] = category_file
                    log.info(f"Saved {len(category_data)} records to {category_file}")
            
        except Exception as e:
            log.error(f"Error saving crawl results: {e}")
        
        return saved_files

def crawl_montgomery_data() -> Dict[str, Any]:
    """Convenience function to crawl Montgomery data"""
    scraper = MontgomeryDataScraper()
    results = scraper.crawl_all_datasets()
    saved_files = scraper.save_crawl_results(results)
    results['saved_files'] = saved_files
    return results

if __name__ == "__main__":
    # Test the scraper
    print("Testing Montgomery County Data Scraper...")
    results = crawl_montgomery_data()
    
    print(f"\nCrawl Summary:")
    print(f"Discovered Datasets: {results['discovered_datasets']}")
    print(f"Total Downloads: {results['summary']['total_downloads']}")
    print(f"Successful: {results['summary']['successful_downloads']}")
    print(f"Failed: {results['summary']['failed_downloads']}")
    print(f"Total Records: {results['summary']['total_records']}")
    
    if results.get('saved_files'):
        print(f"\nSaved Files:")
        for file_type, filename in results['saved_files'].items():
            print(f"  {file_type}: {filename}")
