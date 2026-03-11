#!/usr/bin/env python3
"""
Data Source Fix for Montgomery AL
Handles the migration to ArcGIS Hub and creates demo data
"""

import json
import requests
from bs4 import BeautifulSoup
import time
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def create_demo_data():
    """Create realistic demo data for Montgomery AL"""
    demo_data = {
        "vacant_properties": [
            {
                "parcel_id": "R001001234",
                "address": "1234 Bell St",
                "owner": "CITY OF MONTGOMERY",
                "assessed_value": 25000.0,
                "city_vacant_flag": True,
                "last_inspection": "2024-01-15",
                "violation_type": "Blight"
            },
            {
                "parcel_id": "R002005678", 
                "address": "5678 Mobile St",
                "owner": "BANK OF AMERICA",
                "assessed_value": 45000.0,
                "city_vacant_flag": True,
                "last_inspection": "2024-02-01",
                "violation_type": "Foreclosure"
            },
            {
                "parcel_id": "R003009012",
                "address": "9012 Dexter Ave",
                "owner": "UNKNOWN",
                "assessed_value": 35000.0,
                "city_vacant_flag": True,
                "last_inspection": "2023-12-20",
                "violation_type": "Abandoned"
            }
        ],
        "code_violations": [
            {
                "violation_id": "V2024001",
                "address": "1234 Bell St",
                "type": "High Grass/Weeds",
                "date": "2024-01-15",
                "status": "Open",
                "severity": "High"
            },
            {
                "violation_id": "V2024002",
                "address": "1234 Bell St", 
                "type": "Structural Issues",
                "date": "2024-01-20",
                "status": "Open",
                "severity": "Critical"
            },
            {
                "violation_id": "V2024003",
                "address": "5678 Mobile St",
                "type": "Boarded Windows",
                "date": "2024-02-01",
                "status": "Open",
                "severity": "Medium"
            },
            {
                "violation_id": "V2024004",
                "address": "9012 Dexter Ave",
                "type": "Trash/Debris",
                "date": "2023-12-20",
                "status": "Open",
                "severity": "Medium"
            }
        ],
        "building_permits": [
            {
                "permit_number": "P2024001",
                "address": "3456 Commerce St",
                "type": "Commercial Renovation",
                "issued_date": "2024-01-10",
                "value": 150000.0,
                "status": "Active"
            },
            {
                "permit_number": "P2024002",
                "address": "7890 Perry St",
                "type": "Residential Addition",
                "issued_date": "2024-02-15",
                "value": 75000.0,
                "status": "Active"
            },
            {
                "permit_number": "P2024003",
                "address": "2345 Court St",
                "type": "New Construction",
                "issued_date": "2024-01-25",
                "value": 250000.0,
                "status": "Active"
            }
        ],
        "traffic_incidents": [
            {
                "incident_id": "T2024001",
                "location": "Bell St & Mobile St",
                "type": "Accident",
                "date": "2024-02-10",
                "severity": "Minor"
            },
            {
                "incident_id": "T2024002",
                "location": "Dexter Ave & Perry St",
                "type": "Traffic Stop",
                "date": "2024-02-15",
                "severity": "Low"
            }
        ]
    }
    
    return demo_data

def save_demo_data():
    """Save demo data as JSON files"""
    demo_data = create_demo_data()
    
    # Save individual files
    for dataset, data in demo_data.items():
        filename = f"montgomery_{dataset}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        log.info(f"Created {filename} with {len(data)} records")
    
    # Save combined file
    with open("montgomery_demo_data.json", 'w') as f:
        json.dump(demo_data, f, indent=2)
    
    log.info("Demo data files created successfully!")
    return demo_data

def test_arcgis_api():
    """Test if we can find the ArcGIS datasets"""
    try:
        # Try the ArcGIS Hub API
        url = "https://hub.arcgis.com/api/v3/datasets"
        params = {
            'q': 'montgomery al',
            'limit': 10
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            log.info(f"Found {len(data.get('data', []))} datasets")
            return data
        else:
            log.warning(f"ArcGIS API returned {response.status_code}")
            return None
            
    except Exception as e:
        log.error(f"ArcGIS API test failed: {e}")
        return None

def create_html_to_json_converter():
    """Create a simple HTML to JSON converter for Montgomery data"""
    
    def extract_table_data(html_content, table_class=None):
        """Extract data from HTML tables"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if table_class:
            tables = soup.find_all('table', class_=table_class)
        else:
            tables = soup.find_all('table')
        
        data = []
        for table in tables:
            rows = table.find_all('tr')
            
            # Get headers
            headers = []
            header_row = rows[0] if rows else None
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # Get data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            row_data[headers[i]] = cell.get_text(strip=True)
                        else:
                            row_data[f'column_{i}'] = cell.get_text(strip=True)
                    data.append(row_data)
        
        return data
    
    return extract_table_data

if __name__ == "__main__":
    log.info("=== Montgomery Data Fix Script ===")
    
    # 1. Create demo data
    demo_data = save_demo_data()
    
    # 2. Test ArcGIS API
    arcgis_data = test_arcgis_api()
    
    # 3. Create converter function
    converter = create_html_to_json_converter()
    
    log.info("\n=== Summary ===")
    log.info("✅ Demo data created for testing")
    log.info("✅ HTML to JSON converter ready")
    if arcgis_data:
        log.info("✅ ArcGIS API accessible")
    else:
        log.info("⚠️  ArcGIS API not accessible - using demo data")
    
    log.info("\n=== Next Steps ===")
    log.info("1. The AI can now train with demo data:")
    log.info("   curl -X POST http://localhost:5000/api/ai/train")
    log.info("2. Demo data files created:")
    log.info("   - montgomery_vacant_properties.json")
    log.info("   - montgomery_code_violations.json") 
    log.info("   - montgomery_building_permits.json")
    log.info("   - montgomery_traffic_incidents.json")
