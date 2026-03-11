#!/usr/bin/env python3
"""
Create demo crawl results for pattern learning
"""

import json
from datetime import datetime, timedelta

def create_demo_crawl_results():
    """Create realistic crawl results for pattern learning"""
    
    crawl_results = [
        {
            "url": "https://www.zillow.com/montgomery-al/",
            "status_code": 200,
            "content": """
            Montgomery AL Homes for Sale
            347 homes for sale in Montgomery, AL
            Median list price: $159,000
            68 foreclosure listings available
            Price reduced listings up 14% this quarter
            25 vacant properties showing distress signals
            Average days on market: 45 days
            12 bank owned properties (REO)
            """,
            "markdown": """
            # Montgomery AL Real Estate Market
            
            **Market Overview:**
            - 347 active listings
            - Median price: $159,000
            - 68 foreclosures available
            - 25 vacant/distressed properties
            
            **Trend Indicators:**
            - Price reduced listings: +14% (quarterly increase)
            - Bank owned properties: 12 REO listings
            - Average DOM: 45 days
            - Vacancy signals: 7.2% of listings
            
            **Distress Keywords:**
            - Foreclosure: 68 mentions
            - Vacant: 25 mentions  
            - Bank owned: 12 mentions
            - Price reduced: 48 mentions
            """,
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "url": "https://www.realtor.com/realestateandhomes-search/Montgomery_AL",
            "status_code": 200,
            "content": """
            Montgomery AL Real Estate
            285 properties for sale
            15 foreclosure properties
            8 vacant lots available
            3 abandoned properties listed
            Average price: $165,000
            """,
            "markdown": """
            # Montgomery AL Real Estate Report
            
            **Inventory:**
            - 285 total properties
            - 15 foreclosure properties
            - 8 vacant lots
            - 3 abandoned properties
            
            **Pricing:**
            - Average: $165,000
            - Foreclosure discount: 25% below market
            - Vacant property discount: 30% below market
            
            **Market Signals:**
            - High foreclosure activity: 5.3% of market
            - Vacant land opportunities: 8 lots available
            - Abandoned properties: 3 requiring renovation
            """,
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "url": "https://www.trulia.com/AL/Montgomery/",
            "status_code": 200,
            "content": """
            Trulia Montgomery AL
            198 homes for sale
            42 distressed properties
            18 price reduced listings
            9 bank owned homes
            Market trending downward
            """,
            "markdown": """
            # Trulia Montgomery Market Analysis
            
            **Current Market:**
            - 198 active listings
            - 42 distressed properties (21.2%)
            - 18 price reduced listings
            - 9 bank owned homes
            
            **Market Trends:**
            - Overall market: trending downward
            - Distress rate: 21.2% (elevated)
            - Price reductions: 9.1% of listings
            - Bank owned: 4.5% of market
            
            **Risk Indicators:**
            - High distress concentration
            - Downward price pressure
            - Bank ownership increasing
            """,
            "timestamp": datetime.utcnow().isoformat()
        }
    ]
    
    return crawl_results

def save_demo_crawl_data():
    """Save demo crawl results"""
    crawl_data = create_demo_crawl_results()
    
    with open("demo_crawl_results.json", 'w') as f:
        json.dump(crawl_data, f, indent=2)
    
    print(f"Created {len(crawl_data)} demo crawl results")
    print("File saved: demo_crawl_results.json")
    
    return crawl_data

if __name__ == "__main__":
    data = save_demo_crawl_data()
    
    print("\n=== Demo Crawl Data Summary ===")
    for result in data:
        print(f"URL: {result['url']}")
        print(f"Content length: {len(result['content'])} chars")
        print(f"Keywords: foreclosure, vacant, bank owned, price reduced")
        print("---")
