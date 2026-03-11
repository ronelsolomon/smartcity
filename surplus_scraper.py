"""
Surplus Properties Scraper
Specialized scraper for Montgomery County Surplus City-Owned Properties
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
from montgomery_scraper import MontgomeryDataScraper, MontgomeryDataset

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class SurplusProperty:
    """Surplus City-Owned Property data model"""
    parcel_id: str
    address: str
    owner: str = "CITY OF MONTGOMERY"
    assessed_value: float = 0.0
    property_type: str = ""
    zoning: str = ""
    land_area: float = 0.0
    building_area: float = 0.0
    year_built: Optional[int] = None
    status: str = "Available"
    listing_date: Optional[str] = None
    minimum_bid: Optional[float] = None
    sale_price: Optional[float] = None
    description: str = ""
    coordinates: Optional[Dict[str, float]] = None
    neighborhood: str = ""
    acquisition_eligibility: Dict[str, Any] = None
    development_potential: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.acquisition_eligibility is None:
            self.acquisition_eligibility = {}
        if self.development_potential is None:
            self.development_potential = {}

class SurplusPropertiesScraper:
    """Specialized scraper for Montgomery County Surplus Properties"""
    
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
        
        # Surplus properties specific endpoints
        self.surplus_endpoints = {
            'map_view': '/maps/a59f54009a6f4ca4ba946d38d3f03c3a',
            'api_endpoint': '/resource/surplus-city-owned-property.json',
            'dataset_page': '/datasets/surplus-city-owned-property'
        }
        
        # Eligibility requirements for acquisition
        self.eligibility_requirements = {
            'tax_standing': True,
            'no_liens': True,
            'no_violations': True,
            'not_foreclosure_owner': True
        }
    
    def discover_surplus_datasets(self) -> List[MontgomeryDataset]:
        """Discover surplus property datasets"""
        datasets = []
        
        try:
            # Check the specific surplus properties map page
            map_url = urljoin(self.base_url, self.surplus_endpoints['map_view'])
            try:
                response = self.session.get(map_url, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for data download links
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        text = link.get_text().strip().lower()
                        
                        if any(keyword in text for keyword in ['download', 'data', 'csv', 'json', 'export']):
                            if 'surplus' in text or 'city-owned' in text:
                                full_url = urljoin(self.base_url, href)
                                datasets.append(MontgomeryDataset(
                                    name="Surplus City-Owned Properties",
                                    description="City-owned surplus properties available for acquisition",
                                    url=full_url,
                                    format='json' if '.json' in href else 'csv',
                                    category='surplus_properties'
                                ))
                                log.info(f"Found surplus dataset: {full_url}")
            
            except Exception as e:
                log.warning(f"Failed to scrape map page: {e}")
            
            # Try API endpoints
            api_url = urljoin(self.base_url, self.surplus_endpoints['api_endpoint'])
            try:
                response = self.session.get(api_url, timeout=10)
                if response.status_code == 200:
                    datasets.append(MontgomeryDataset(
                        name="Surplus City-Owned Properties API",
                        description="API endpoint for surplus properties",
                        url=api_url,
                        format='json',
                        category='surplus_properties'
                    ))
                    log.info(f"Found surplus API: {api_url}")
            except Exception as e:
                log.debug(f"API endpoint not available: {e}")
            
            # If no specific datasets found, use the main Montgomery scraper
            if not datasets:
                log.info("No specific surplus datasets found, using general Montgomery scraper")
                montgomery_scraper = MontgomeryDataScraper(self.base_url)
                all_datasets = montgomery_scraper.discover_datasets()
                
                # Filter for surplus-related datasets
                surplus_keywords = ['surplus', 'city-owned', 'disposition', 'sale', 'auction']
                for dataset in all_datasets:
                    if any(keyword in dataset.name.lower() or keyword in dataset.description.lower() 
                          for keyword in surplus_keywords):
                        dataset.category = 'surplus_properties'
                        datasets.append(dataset)
        
        except Exception as e:
            log.error(f"Error discovering surplus datasets: {e}")
        
        return datasets
    
    def download_surplus_data(self, dataset: MontgomeryDataset) -> List[SurplusProperty]:
        """Download and parse surplus property data"""
        properties = []
        
        try:
            if dataset.format == 'json':
                properties = self._download_json_data(dataset.url)
            elif dataset.format == 'csv':
                properties = self._download_csv_data(dataset.url)
            else:
                # Try to scrape as web page
                properties = self._scrape_web_data(dataset.url)
        
        except Exception as e:
            log.error(f"Error downloading surplus data from {dataset.url}: {e}")
        
        return properties
    
    def _download_json_data(self, url: str) -> List[SurplusProperty]:
        """Download and parse JSON data"""
        properties = []
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                raw_properties = data
            elif isinstance(data, dict) and 'data' in data:
                raw_properties = data['data']
            else:
                log.warning(f"Unexpected JSON structure from {url}")
                return properties
            
            for prop_data in raw_properties:
                property = self._parse_property_data(prop_data)
                if property:
                    properties.append(property)
        
        except Exception as e:
            log.error(f"Error parsing JSON data: {e}")
        
        return properties
    
    def _download_csv_data(self, url: str) -> List[SurplusProperty]:
        """Download and parse CSV data"""
        properties = []
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            df = pd.read_csv(pd.StringIO(response.text))
            
            for _, row in df.iterrows():
                property = self._parse_property_data(row.to_dict())
                if property:
                    properties.append(property)
        
        except Exception as e:
            log.error(f"Error parsing CSV data: {e}")
        
        return properties
    
    def _scrape_web_data(self, url: str) -> List[SurplusProperty]:
        """Scrape data from web page"""
        properties = []
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for property listings
            property_elements = soup.find_all(['div', 'tr'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['property', 'parcel', 'listing', 'item']
            ))
            
            for element in property_elements:
                # Extract property information from the element
                prop_data = self._extract_property_from_element(element)
                if prop_data:
                    property = self._parse_property_data(prop_data)
                    if property:
                        properties.append(property)
        
        except Exception as e:
            log.error(f"Error scraping web data: {e}")
        
        return properties
    
    def _extract_property_from_element(self, element) -> Dict[str, Any]:
        """Extract property data from HTML element"""
        prop_data = {}
        
        try:
            text = element.get_text().strip()
            
            # Try to extract common property fields
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'address' in key:
                        prop_data['address'] = value
                    elif 'parcel' in key:
                        prop_data['parcel_id'] = value
                    elif 'value' in key or 'price' in key:
                        # Extract numeric value
                        import re
                        numbers = re.findall(r'[\d,]+\.?\d*', value.replace('$', '').replace(',', ''))
                        if numbers:
                            prop_data['assessed_value'] = float(numbers[0])
                    elif 'type' in key:
                        prop_data['property_type'] = value
                    elif 'zoning' in key:
                        prop_data['zoning'] = value
                    elif 'status' in key:
                        prop_data['status'] = value
        
        except Exception as e:
            log.debug(f"Error extracting property from element: {e}")
        
        return prop_data
    
    def _parse_property_data(self, raw_data: Dict[str, Any]) -> Optional[SurplusProperty]:
        """Parse raw property data into SurplusProperty object"""
        try:
            # Extract common fields with flexible mapping
            parcel_id = (raw_data.get('parcel_id') or raw_data.get('parcel') or 
                        raw_data.get('PARCEL_ID') or raw_data.get('Parcel ID') or 
                        f"P{int(time.time())}_{hash(str(raw_data)) % 10000}")
            
            address = (raw_data.get('address') or raw_data.get('street_address') or 
                      raw_data.get('ADDRESS') or raw_data.get('Address') or "Unknown")
            
            assessed_value = 0.0
            value_fields = ['assessed_value', 'value', 'price', 'minimum_bid', 'sale_price',
                          'ASSESSED_VALUE', 'VALUE', 'PRICE', 'MINIMUM_BID']
            for field in value_fields:
                if field in raw_data and raw_data[field]:
                    try:
                        value = str(raw_data[field]).replace('$', '').replace(',', '')
                        assessed_value = float(value)
                        break
                    except (ValueError, TypeError):
                        continue
            
            property_type = (raw_data.get('property_type') or raw_data.get('type') or 
                           raw_data.get('PROPERTY_TYPE') or raw_data.get('Type') or "")
            
            zoning = (raw_data.get('zoning') or raw_data.get('zoning_district') or 
                     raw_data.get('ZONING') or raw_data.get('Zoning') or "")
            
            status = (raw_data.get('status') or raw_data.get('property_status') or 
                     raw_data.get('STATUS') or raw_data.get('Status') or "Available")
            
            # Create SurplusProperty object
            property = SurplusProperty(
                parcel_id=str(parcel_id),
                address=str(address),
                assessed_value=assessed_value,
                property_type=property_type,
                zoning=zoning,
                status=status,
                description=raw_data.get('description', ''),
                neighborhood=raw_data.get('neighborhood', ''),
                year_built=self._safe_int(raw_data.get('year_built')),
                land_area=self._safe_float(raw_data.get('land_area')),
                building_area=self._safe_float(raw_data.get('building_area')),
                minimum_bid=self._safe_float(raw_data.get('minimum_bid')),
                sale_price=self._safe_float(raw_data.get('sale_price')),
                listing_date=raw_data.get('listing_date'),
                coordinates=self._parse_coordinates(raw_data)
            )
            
            # Calculate acquisition eligibility
            property.acquisition_eligibility = self._calculate_eligibility(property)
            
            # Calculate development potential
            property.development_potential = self._calculate_development_potential(property)
            
            return property
        
        except Exception as e:
            log.error(f"Error parsing property data: {e}")
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int"""
        try:
            if value is None or value == '':
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float"""
        try:
            if value is None or value == '':
                return None
            return float(str(value).replace('$', '').replace(',', ''))
        except (ValueError, TypeError):
            return None
    
    def _parse_coordinates(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Parse coordinates from raw data"""
        try:
            # Try different coordinate field names
            lat_fields = ['latitude', 'lat', 'LAT', 'LATITUDE']
            lon_fields = ['longitude', 'lon', 'lng', 'LONG', 'LONGITUDE']
            
            lat = None
            lon = None
            
            for field in lat_fields:
                if field in raw_data and raw_data[field]:
                    lat = float(raw_data[field])
                    break
            
            for field in lon_fields:
                if field in raw_data and raw_data[field]:
                    lon = float(raw_data[field])
                    break
            
            if lat is not None and lon is not None:
                return {'latitude': lat, 'longitude': lon}
            
            # Try to parse from a single coordinate field
            coord_fields = ['coordinates', 'coords', 'location', 'geometry']
            for field in coord_fields:
                if field in raw_data and raw_data[field]:
                    coord_str = str(raw_data[field])
                    # Try to parse as "lat, lon" or JSON
                    if ',' in coord_str:
                        try:
                            lat_str, lon_str = coord_str.split(',')
                            return {'latitude': float(lat_str), 'longitude': float(lon_str)}
                        except ValueError:
                            continue
                    elif coord_str.startswith('[') and coord_str.endswith(']'):
                        try:
                            coords = json.loads(coord_str)
                            return {'latitude': float(coords[1]), 'longitude': float(coords[0])}
                        except (json.JSONDecodeError, IndexError):
                            continue
        
        except Exception as e:
            log.debug(f"Error parsing coordinates: {e}")
        
        return None
    
    def _calculate_eligibility(self, property: SurplusProperty) -> Dict[str, Any]:
        """Calculate acquisition eligibility for a property"""
        eligibility = {
            'eligible': True,
            'requirements_met': [],
            'requirements_not_met': [],
            'score': 100,
            'notes': []
        }
        
        # Check assessed value (should be reasonable)
        if property.assessed_value > 0 and property.assessed_value < 1000000:
            eligibility['requirements_met'].append('reasonable_assessed_value')
        elif property.assessed_value >= 1000000:
            eligibility['requirements_not_met'].append('high_value_property')
            eligibility['score'] -= 20
            eligibility['notes'].append('High-value property may have additional requirements')
        else:
            eligibility['requirements_not_met'].append('no_assessed_value')
            eligibility['score'] -= 10
            eligibility['notes'].append('No assessed value available')
        
        # Check property status
        if property.status.lower() in ['available', 'for sale', 'open']:
            eligibility['requirements_met'].append('available_status')
        else:
            eligibility['requirements_not_met'].append('unavailable_status')
            eligibility['score'] -= 30
            eligibility['notes'].append(f'Property status: {property.status}')
        
        # Check zoning (some zones may have restrictions)
        if property.zoning:
            eligibility['requirements_met'].append('has_zoning')
            # Check for residential-friendly zoning
            residential_zones = ['r-1', 'r-2', 'r-3', 'residential', 'mixed-use']
            if any(zone in property.zoning.lower() for zone in residential_zones):
                eligibility['requirements_met'].append('residential_friendly_zoning')
                eligibility['score'] += 10
        else:
            eligibility['requirements_not_met'].append('no_zoning')
            eligibility['score'] -= 5
            eligibility['notes'].append('Zoning information not available')
        
        # Determine overall eligibility
        eligibility['eligible'] = eligibility['score'] >= 70
        eligibility['grade'] = self._get_eligibility_grade(eligibility['score'])
        
        return eligibility
    
    def _calculate_development_potential(self, property: SurplusProperty) -> Dict[str, Any]:
        """Calculate development potential for a property"""
        potential = {
            'overall_score': 50,
            'potential_uses': [],
            'advantages': [],
            'challenges': [],
            'estimated_investment_range': {'min': 0, 'max': 0},
            'development_timeline_months': 12,
            'market_potential': 'medium'
        }
        
        score = 50  # Base score
        
        # Size-based scoring
        if property.land_area and property.land_area > 0:
            if property.land_area > 10000:  # Large lot
                score += 20
                potential['advantages'].append('large_lot_size')
                potential['potential_uses'].extend(['multi_family', 'commercial', 'mixed_use'])
            elif property.land_area > 5000:  # Medium lot
                score += 10
                potential['advantages'].append('medium_lot_size')
                potential['potential_uses'].extend(['single_family', 'duplex'])
            else:  # Small lot
                potential['challenges'].append('small_lot_size')
                potential['potential_uses'].append('single_family')
        else:
            potential['challenges'].append('unknown_lot_size')
        
        # Location-based scoring (if neighborhood info available)
        if property.neighborhood:
            potential['advantages'].append('identified_neighborhood')
            score += 5
        
        # Zoning-based potential
        if property.zoning:
            zoning_lower = property.zoning.lower()
            if 'commercial' in zoning_lower:
                potential['potential_uses'].append('commercial')
                score += 15
            elif 'residential' in zoning_lower:
                potential['potential_uses'].append('residential')
                score += 10
            elif 'mixed' in zoning_lower:
                potential['potential_uses'].extend(['residential', 'commercial'])
                score += 20
        
        # Building condition scoring
        if property.year_built:
            age = 2024 - property.year_built
            if age < 20:
                potential['advantages'].append('relatively_new')
                score += 10
            elif age > 50:
                potential['challenges'].append('older_structure')
                score -= 10
        
        # Investment estimation
        base_investment = property.assessed_value * 0.3 if property.assessed_value > 0 else 50000
        potential['estimated_investment_range'] = {
            'min': base_investment,
            'max': base_investment * 3
        }
        
        # Timeline estimation
        if property.building_area and property.building_area > 0:
            potential['development_timeline_months'] = 18  # Renovation
        else:
            potential['development_timeline_months'] = 12  # New construction
        
        # Market potential
        if score > 70:
            potential['market_potential'] = 'high'
        elif score > 50:
            potential['market_potential'] = 'medium'
        else:
            potential['market_potential'] = 'low'
        
        potential['overall_score'] = max(0, min(100, score))
        
        return potential
    
    def _get_eligibility_grade(self, score: int) -> str:
        """Get eligibility grade based on score"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def generate_demo_surplus_properties(self, count: int = 20) -> List[SurplusProperty]:
        """Generate demo surplus properties for testing"""
        import random
        
        demo_properties = []
        streets = ['Dexter Ave', 'Bell St', 'Mobile St', 'Jackson St', 'Perry Hill Rd', 
                  'Eastern Blvd', 'Atlanta Hwy', 'Vista Dr', 'Carmichael Rd', 'Woodley Rd']
        neighborhoods = ['Downtown', 'Cottage Hill', 'Garden City', 'Capitol Heights', 'Old Cloverdale']
        
        property_types = ['Single Family', 'Vacant Land', 'Commercial', 'Mixed Use', 'Duplex']
        zoning_codes = ['R-1', 'R-2', 'C-1', 'C-2', 'M-1', 'PUD']
        
        for i in range(count):
            property = SurplusProperty(
                parcel_id=f"S{i+1:04d}{random.randint(100, 999)}",
                address=f"{random.randint(100, 9999)} {random.choice(streets)}",
                assessed_value=random.uniform(15000, 150000),
                property_type=random.choice(property_types),
                zoning=random.choice(zoning_codes),
                land_area=random.uniform(3000, 15000),
                building_area=random.uniform(0, 2500) if random.random() > 0.3 else 0,
                year_built=random.randint(1950, 2000) if random.random() > 0.4 else None,
                status=random.choice(['Available', 'For Sale', 'Pending', 'Under Contract']),
                minimum_bid=random.uniform(10000, 50000) if random.random() > 0.5 else None,
                description=f"Surplus city-owned property in {random.choice(neighborhoods)}",
                neighborhood=random.choice(neighborhoods),
                listing_date=(datetime.now() - timedelta(days=random.randint(1, 180))).strftime('%Y-%m-%d'),
                coordinates={
                    'latitude': 32.3617 + random.uniform(-0.1, 0.1),
                    'longitude': -86.2792 + random.uniform(-0.1, 0.1)
                }
            )
            
            # Calculate eligibility and potential
            property.acquisition_eligibility = self._calculate_eligibility(property)
            property.development_potential = self._calculate_development_potential(property)
            
            demo_properties.append(property)
        
        return demo_properties
    
    def save_surplus_properties(self, properties: List[SurplusProperty], filename: str = None) -> str:
        """Save surplus properties to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"montgomery_surplus_properties_{timestamp}.json"
        
        # Convert to serializable format
        data = [asdict(prop) for prop in properties]
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        log.info(f"Saved {len(properties)} surplus properties to {filename}")
        return filename
