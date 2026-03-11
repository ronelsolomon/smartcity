"""
Demo Data Generator for Urban Investment AI
Generates realistic demographic data for Montgomery districts
"""

import json
import random
from datetime import datetime
from typing import List, Dict

def generate_montgomery_demographics() -> List[Dict]:
    """Generate realistic demographic data for Montgomery districts"""
    
    # Define Montgomery districts with realistic characteristics
    districts = [
        {
            "district_id": "D001",
            "district_name": "Downtown Montgomery",
            "base_population": 8500,
            "youth_heavy": False,
            "senior_heavy": False,
            "income_level": "medium",
            "urban_density": "high"
        },
        {
            "district_id": "D002", 
            "district_name": "Old Cloverdale",
            "base_population": 6200,
            "youth_heavy": False,
            "senior_heavy": True,
            "income_level": "high",
            "urban_density": "medium"
        },
        {
            "district_id": "D003",
            "district_name": "Capitol Heights",
            "base_population": 7800,
            "youth_heavy": True,
            "senior_heavy": False,
            "income_level": "low",
            "urban_density": "high"
        },
        {
            "district_id": "D004",
            "district_name": "Bellevue Park",
            "base_population": 5400,
            "youth_heavy": False,
            "senior_heavy": False,
            "income_level": "medium_high",
            "urban_density": "medium"
        },
        {
            "district_id": "D005",
            "district_name": "Garden District",
            "base_population": 4800,
            "youth_heavy": False,
            "senior_heavy": True,
            "income_level": "high",
            "urban_density": "low"
        },
        {
            "district_id": "D006",
            "district_name": "Chisholm",
            "base_population": 9200,
            "youth_heavy": True,
            "senior_heavy": False,
            "income_level": "low_medium",
            "urban_density": "medium"
        },
        {
            "district_id": "D007",
            "district_name": "Mobile Square",
            "base_population": 6800,
            "youth_heavy": False,
            "senior_heavy": False,
            "income_level": "medium",
            "urban_density": "high"
        },
        {
            "district_id": "D008",
            "district_name": "Highland Park",
            "base_population": 5500,
            "youth_heavy": True,
            "senior_heavy": False,
            "income_level": "low",
            "urban_density": "medium"
        }
    ]
    
    demographic_data = []
    
    for district in districts:
        # Generate age distribution based on district characteristics
        age_groups = generate_age_distribution(district)
        
        # Calculate derived metrics
        total_pop = sum(age_groups.values())
        median_age = calculate_median_age(age_groups)
        
        # Generate income based on district income level
        median_income = generate_median_income(district["income_level"])
        
        # Generate employment rate
        employment_rate = generate_employment_rate(district["income_level"])
        
        # Generate education levels
        education_levels = generate_education_levels(district["income_level"])
        
        # Calculate population density
        population_density = generate_population_density(district["urban_density"])
        
        district_data = {
            "district_id": district["district_id"],
            "district_name": district["district_name"],
            "total_population": total_pop,
            "age_groups": age_groups,
            "median_age": median_age,
            "median_household_income": median_income,
            "employment_rate": employment_rate,
            "education_level": education_levels,
            "population_density": population_density,
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
        
        demographic_data.append(district_data)
    
    return demographic_data

def generate_age_distribution(district: Dict) -> Dict[str, int]:
    """Generate realistic age distribution for a district"""
    base_pop = district["base_population"]
    
    # Base age distribution percentages (US average)
    age_percentages = {
        "0-4": 6.1,
        "5-9": 6.4,
        "10-14": 6.5,
        "15-17": 4.2,
        "18": 1.2,
        "19-24": 9.2,
        "25-29": 7.0,
        "30-34": 6.8,
        "35-40": 7.5,
        "41-45": 7.3,
        "46-50": 7.0,
        "51-54": 6.2,
        "55-60": 6.8,
        "61-65": 5.5,
        "66-70": 4.1,
        "71-75": 3.2,
        "76-80": 2.1,
        "80+": 2.8
    }
    
    # Adjust based on district characteristics
    if district["youth_heavy"]:
        # Increase youth and young adult percentages
        age_percentages["0-4"] *= 1.3
        age_percentages["5-9"] *= 1.3
        age_percentages["10-14"] *= 1.3
        age_percentages["15-17"] *= 1.3
        age_percentages["19-24"] *= 1.4
        age_percentages["25-29"] *= 1.3
        age_percentages["30-34"] *= 1.2
        
        # Decrease senior percentages
        age_percentages["55-60"] *= 0.7
        age_percentages["61-65"] *= 0.6
        age_percentages["66-70"] *= 0.5
        age_percentages["71-75"] *= 0.4
        age_percentages["76-80"] *= 0.3
        age_percentages["80+"] *= 0.3
    
    elif district["senior_heavy"]:
        # Increase senior percentages
        age_percentages["55-60"] *= 1.4
        age_percentages["61-65"] *= 1.5
        age_percentages["66-70"] *= 1.6
        age_percentages["71-75"] *= 1.7
        age_percentages["76-80"] *= 1.8
        age_percentages["80+"] *= 2.0
        
        # Decrease youth percentages
        age_percentages["0-4"] *= 0.6
        age_percentages["5-9"] *= 0.6
        age_percentages["10-14"] *= 0.6
        age_percentages["15-17"] *= 0.5
        age_percentages["19-24"] *= 0.7
    
    # Normalize to 100%
    total_percentage = sum(age_percentages.values())
    age_percentages = {age: (pct / total_percentage) * 100 for age, pct in age_percentages.items()}
    
    # Convert to actual population counts
    age_groups = {age: int(base_pop * pct / 100) for age, pct in age_percentages.items()}
    
    return age_groups

def calculate_median_age(age_groups: Dict[str, int]) -> float:
    """Calculate median age from age groups"""
    total_pop = sum(age_groups.values())
    if total_pop == 0:
        return 35.0
    
    cumulative = 0
    for age_range, count in age_groups.items():
        cumulative += count
        if cumulative >= total_pop / 2:
            # Extract middle of age range
            if '-' in age_range:
                start, end = age_range.split('-')
                return (int(start) + int(end)) / 2
            else:
                return float(age_range)
    
    return 35.0

def generate_median_income(income_level: str) -> int:
    """Generate median household income based on income level"""
    income_ranges = {
        "low": (25000, 40000),
        "low_medium": (35000, 50000),
        "medium": (45000, 65000),
        "medium_high": (55000, 85000),
        "high": (75000, 120000)
    }
    
    min_income, max_income = income_ranges.get(income_level, (45000, 65000))
    return random.randint(min_income, max_income)

def generate_employment_rate(income_level: str) -> float:
    """Generate employment rate based on income level"""
    base_rates = {
        "low": 0.72,
        "low_medium": 0.78,
        "medium": 0.84,
        "medium_high": 0.89,
        "high": 0.93
    }
    
    base_rate = base_rates.get(income_level, 0.84)
    # Add some variation
    variation = random.uniform(-0.05, 0.05)
    return max(0.65, min(0.95, base_rate + variation))

def generate_education_levels(income_level: str) -> Dict[str, float]:
    """Generate education level percentages based on income level"""
    if income_level == "high":
        return {
            "high_school_or_less": 15.2,
            "some_college": 24.8,
            "bachelor_degree": 35.5,
            "graduate_degree": 24.5
        }
    elif income_level == "medium_high":
        return {
            "high_school_or_less": 28.4,
            "some_college": 31.2,
            "bachelor_degree": 28.6,
            "graduate_degree": 11.8
        }
    elif income_level == "medium":
        return {
            "high_school_or_less": 42.1,
            "some_college": 28.5,
            "bachelor_degree": 21.3,
            "graduate_degree": 8.1
        }
    elif income_level == "low_medium":
        return {
            "high_school_or_less": 58.3,
            "some_college": 25.2,
            "bachelor_degree": 13.8,
            "graduate_degree": 2.7
        }
    else:  # low
        return {
            "high_school_or_less": 71.5,
            "some_college": 20.3,
            "bachelor_degree": 7.2,
            "graduate_degree": 1.0
        }

def generate_population_density(density_level: str) -> float:
    """Generate population density per square mile"""
    density_ranges = {
        "low": (200, 800),
        "medium": (800, 2000),
        "high": (2000, 5000)
    }
    
    min_density, max_density = density_ranges.get(density_level, (800, 2000))
    return random.uniform(min_density, max_density)

def save_demo_demographics():
    """Save demo demographic data to file"""
    demographic_data = generate_montgomery_demographics()
    
    filename = f"montgomery_demographics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump(demographic_data, f, indent=2)
    
    print(f"Generated demo demographics data: {filename}")
    print(f"Total districts: {len(demographic_data)}")
    print(f"Total population: {sum(d['total_population'] for d in demographic_data):,}")
    
    return filename

if __name__ == "__main__":
    save_demo_demographics()
