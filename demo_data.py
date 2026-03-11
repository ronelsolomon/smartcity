"""
Demo Data Generator for Vacancy Watch
Creates sample Montgomery AL data when APIs are unavailable
"""

import json
from datetime import datetime, timedelta
import random

def generate_demo_properties():
    """Generate sample Montgomery AL property data"""
    streets = [
        "Dexter Ave", "Commerce St", "Washington Ave", "Perry St", 
        "Madison Ave", "Bibb St", "Coosa St", "Mobile St",
        "Highland Ave", "Cotton St", "Fairview Ave", "Rosa Parks Ave"
    ]
    
    properties = []
    for i in range(50):
        street = random.choice(streets)
        number = random.randint(100, 9999)
        address = f"{number} {street}, Montgomery, AL"
        
        # Generate realistic Montgomery data
        assessed_value = random.randint(25000, 150000)
        vacancy_score = random.uniform(0, 100)
        
        properties.append({
            "parcel_id": f"PAR-{i:06d}",
            "address": address,
            "owner_name": f"Owner {i} {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])}",
            "assessed_value": assessed_value,
            "city_vacant_flag": vacancy_score > 70,
            "open_violations": random.randint(0, 5) if vacancy_score > 60 else 0,
            "recent_permits": random.randint(0, 3) if vacancy_score < 40 else 0,
            "listing_price": int(assessed_value * random.uniform(0.8, 1.5)) if vacancy_score > 50 else None,
            "listing_source": random.choice(["zillow", "realtor.com", "trulia"]) if vacancy_score > 50 else "",
            "days_on_market": random.randint(30, 180) if vacancy_score > 50 else None,
            "vacancy_score": vacancy_score,
            "signals": ["vacant_registry"] if vacancy_score > 70 else []
        })
    
    return properties

def generate_demo_violations():
    """Generate sample code violations"""
    violation_types = [
        "Overgrown vegetation", "Structural damage", "Abandoned vehicle",
        "Trash accumulation", "Unsafe structure", "Code violation"
    ]
    
    violations = []
    for i in range(100):
        violations.append({
            "violation_id": f"VIOL-{i:06d}",
            "address": f"{random.randint(100, 9999)} {random.choice(['Dexter Ave', 'Commerce St', 'Washington Ave'])}, Montgomery, AL",
            "violation_type": random.choice(violation_types),
            "violation_date": (datetime.utcnow() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
            "status": random.choice(["open", "closed", "pending"]),
            "severity": random.choice(["low", "medium", "high"])
        })
    
    return violations

def generate_demo_permits():
    """Generate sample building permits"""
    permit_types = [
        "New construction", "Renovation", "Repair", "Demolition",
        "Electrical", "Plumbing", "HVAC", "Roofing"
    ]
    
    permits = []
    for i in range(75):
        issue_date = datetime.utcnow() - timedelta(days=random.randint(1, 90))
        permits.append({
            "permit_number": f"PERM-{i:06d}",
            "address": f"{random.randint(100, 9999)} {random.choice(['Madison Ave', 'Bibb St', 'Coosa St'])}, Montgomery, AL",
            "permit_type": random.choice(permit_types),
            "issued_date": issue_date.strftime("%Y-%m-%d"),
            "job_value": random.randint(1000, 50000),
            "status": random.choice(["issued", "completed", "expired"])
        })
    
    return permits

def generate_demo_traffic():
    """Generate sample traffic incidents"""
    incident_types = [
        "Accident", "Road hazard", "Construction", "Signal outage",
        "Debris on road", "Flooding", "Vehicle fire"
    ]
    
    incidents = []
    for i in range(40):
        incident_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
        incidents.append({
            "incident_id": f"INC-{i:06d}",
            "location": f"{random.choice(['Highland Ave', 'Cotton St', 'Fairview Ave'])} & {random.choice(['Dexter Ave', 'Commerce St'])}, Montgomery, AL",
            "incident_type": random.choice(incident_types),
            "incident_date": incident_date.strftime("%Y-%m-%d"),
            "severity": random.choice(["minor", "moderate", "major"]),
            "status": random.choice(["cleared", "under investigation", "pending"])
        })
    
    return incidents

def save_demo_data():
    """Save all demo data to JSON files"""
    print("Generating demo data for Montgomery AL...")
    
    # Generate and save properties
    properties = generate_demo_properties()
    with open('demo_properties.json', 'w') as f:
        json.dump(properties, f, indent=2)
    print(f"Generated {len(properties)} demo properties")
    
    # Generate and save violations
    violations = generate_demo_violations()
    with open('demo_violations.json', 'w') as f:
        json.dump(violations, f, indent=2)
    print(f"Generated {len(violations)} demo violations")
    
    # Generate and save permits
    permits = generate_demo_permits()
    with open('demo_permits.json', 'w') as f:
        json.dump(permits, f, indent=2)
    print(f"Generated {len(permits)} demo permits")
    
    # Generate and save traffic incidents
    traffic = generate_demo_traffic()
    with open('demo_traffic.json', 'w') as f:
        json.dump(traffic, f, indent=2)
    print(f"Generated {len(traffic)} demo traffic incidents")
    
    print("\nDemo data saved! You can now run:")
    print("python vacancy_watch_with_demo.py")

if __name__ == "__main__":
    save_demo_data()
