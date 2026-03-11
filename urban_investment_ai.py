"""
Urban Investment AI - Enhanced Decision Making
Age demographics analysis, partnership opportunities, and service recommendations
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import logging

log = logging.getLogger(__name__)

@dataclass
class DemographicProfile:
    """Age demographic profile for a district/area"""
    district_id: str
    district_name: str
    total_population: int
    age_groups: Dict[str, int]  # age ranges and counts
    median_age: float
    youth_percentage: float  # 0-18
    young_adult_percentage: float  # 19-35
    middle_aged_percentage: float  # 36-55
    senior_percentage: float  # 56+
    household_income_median: float
    education_level: Dict[str, float]  # education percentages
    employment_rate: float
    population_density: float  # people per sq mile
    
@dataclass
class PartnershipOpportunity:
    """Partnership opportunity for commercial development"""
    location: str
    district_id: str
    partnership_type: str  # "public_private", "community", "educational", "healthcare"
    city_department: str  # relevant city department
    opportunity_score: float  # 0-100
    description: str
    benefits: List[str]
    requirements: List[str]
    estimated_timeline: str  # months
    success_probability: float
    funding_available: bool
    community_support_score: float
    
@dataclass
class ServiceRecommendation:
    """Service type recommendation for commercial development"""
    location: str
    district_id: str
    service_category: str  # "retail", "entertainment", "healthcare", "education", "food_service"
    specific_services: List[str]
    confidence_score: float  # 0-100
    market_demand_score: float  # 0-100
    demographic_alignment: float  # 0-100
    estimated_revenue_potential: str  # low/medium/high
    competition_level: str  # low/medium/high
    investment_required: str  # low/medium/high
    target_demographics: List[str]
    peak_hours: str
    seasonal_factors: List[str]

class DemographicsAnalyzer:
    """AI-powered demographics analysis for investment decisions"""
    
    def __init__(self, data_path: str = "data"):
        self.data_path = data_path
        self.model_path = os.path.join(os.getcwd(), "ml_models")
        os.makedirs(self.model_path, exist_ok=True)
        
        # ML components
        self.demographics_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.income_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        # Model files
        self.demographics_model_file = os.path.join(self.model_path, "demographics_predictor.pkl")
        self.income_model_file = os.path.join(self.model_path, "income_predictor.pkl")
        self.scaler_file = os.path.join(self.model_path, "demographics_scaler.pkl")
        
        # Load models if available
        self._load_models()
    
    def _load_models(self):
        """Load trained models if available"""
        try:
            import pickle
            if os.path.exists(self.demographics_model_file):
                with open(self.demographics_model_file, 'rb') as f:
                    self.demographics_predictor = pickle.load(f)
                log.info("Loaded demographics predictor model")
            
            if os.path.exists(self.income_model_file):
                with open(self.income_model_file, 'rb') as f:
                    self.income_predictor = pickle.load(f)
                log.info("Loaded income predictor model")
            
            if os.path.exists(self.scaler_file):
                with open(self.scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                log.info("Loaded demographics scaler")
        except Exception as e:
            log.warning(f"Could not load demographics models: {e}")
    
    def analyze_district_demographics(self, district_data: List[Dict]) -> List[DemographicProfile]:
        """Analyze age demographics by district"""
        profiles = []
        
        for district in district_data:
            try:
                # Extract age group data
                age_groups = district.get('age_groups', {})
                total_pop = district.get('total_population', 0)
                
                if total_pop == 0:
                    continue
                
                # Calculate age percentages
                youth_pop = sum(age_groups.get(age, 0) for age in ['0-4', '5-9', '10-14', '15-17', '18'])
                young_adult_pop = sum(age_groups.get(age, 0) for age in ['19-24', '25-29', '30-34', '35'])
                middle_aged_pop = sum(age_groups.get(age, 0) for age in ['36-40', '41-45', '46-50', '51-54', '55'])
                senior_pop = sum(age_groups.get(age, 0) for age in ['56-60', '61-65', '66-70', '71-75', '76-80', '80+'])
                
                # Calculate median age (simplified)
                median_age = district.get('median_age', self._calculate_median_age(age_groups))
                
                profile = DemographicProfile(
                    district_id=district.get('district_id', ''),
                    district_name=district.get('district_name', ''),
                    total_population=total_pop,
                    age_groups=age_groups,
                    median_age=median_age,
                    youth_percentage=(youth_pop / total_pop) * 100 if total_pop > 0 else 0,
                    young_adult_percentage=(young_adult_pop / total_pop) * 100 if total_pop > 0 else 0,
                    middle_aged_percentage=(middle_aged_pop / total_pop) * 100 if total_pop > 0 else 0,
                    senior_percentage=(senior_pop / total_pop) * 100 if total_pop > 0 else 0,
                    household_income_median=district.get('median_household_income', 0),
                    education_level=district.get('education_level', {}),
                    employment_rate=district.get('employment_rate', 0),
                    population_density=district.get('population_density', 0)
                )
                profiles.append(profile)
                
            except Exception as e:
                log.warning(f"Error processing district {district.get('district_name', 'Unknown')}: {e}")
                continue
        
        log.info(f"Analyzed demographics for {len(profiles)} districts")
        return profiles
    
    def _calculate_median_age(self, age_groups: Dict[str, int]) -> float:
        """Calculate median age from age group data"""
        total_pop = sum(age_groups.values())
        if total_pop == 0:
            return 35.0  # default median
        
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
    
    def predict_demographic_trends(self, profiles: List[DemographicProfile], years_ahead: int = 5) -> Dict[str, Dict]:
        """Predict demographic trends using ML"""
        trends = {}
        
        try:
            # Prepare features for ML prediction
            features = []
            for profile in profiles:
                feature_vector = [
                    profile.youth_percentage,
                    profile.young_adult_percentage,
                    profile.middle_aged_percentage,
                    profile.senior_percentage,
                    profile.household_income_median,
                    profile.employment_rate,
                    profile.population_density
                ]
                features.append(feature_vector)
            
            if len(features) < 5:
                log.warning("Insufficient data for demographic trend prediction")
                return self._rule_based_trends(profiles, years_ahead)
            
            X = np.array(features)
            X_scaled = self.scaler.fit_transform(X)
            
            # Predict future demographics (simplified - in practice would use time series)
            for i, profile in enumerate(profiles):
                district_trends = {}
                
                # Age group shifts (simplified assumptions)
                aging_rate = 0.02  # 2% of population ages up each year
                youth_change = -profile.youth_percentage * aging_rate * years_ahead
                senior_change = profile.senior_percentage * aging_rate * years_ahead
                
                district_trends['youth_percentage_change'] = youth_change
                district_trends['senior_percentage_change'] = senior_change
                district_trends['young_adult_percentage_change'] = -youth_change * 0.5
                district_trends['middle_aged_percentage_change'] = -senior_change * 0.3
                
                # Income growth prediction
                income_growth_rate = 0.03  # 3% annual income growth
                district_trends['income_growth'] = profile.household_income_median * ((1 + income_growth_rate) ** years_ahead - 1)
                
                # Population change
                population_change = profile.population_density * 0.01 * years_ahead  # 1% annual growth
                district_trends['population_density_change'] = population_change
                
                trends[profile.district_id] = district_trends
            
        except Exception as e:
            log.warning(f"ML demographic prediction failed: {e}. Using rule-based trends.")
            return self._rule_based_trends(profiles, years_ahead)
        
        return trends
    
    def _rule_based_trends(self, profiles: List[DemographicProfile], years_ahead: int) -> Dict[str, Dict]:
        """Rule-based demographic trend prediction"""
        trends = {}
        
        for profile in profiles:
            district_trends = {}
            
            # Simple aging assumptions
            aging_factor = years_ahead * 0.02
            district_trends['youth_percentage_change'] = -profile.youth_percentage * aging_factor
            district_trends['senior_percentage_change'] = profile.senior_percentage * aging_factor
            district_trends['young_adult_percentage_change'] = profile.youth_percentage * aging_factor * 0.3
            district_trends['middle_aged_percentage_change'] = 0
            
            # Income growth
            district_trends['income_growth'] = profile.household_income_median * 0.1 * years_ahead
            
            # Population change
            district_trends['population_density_change'] = profile.population_density * 0.05 * years_ahead
            
            trends[profile.district_id] = district_trends
        
        return trends

class PartnershipOpportunityAnalyzer:
    """AI-powered partnership opportunity identification"""
    
    def __init__(self):
        self.opportunity_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.success_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        
    def identify_partnership_opportunities(self, demographic_data: List[Dict],  # Changed from List[DemographicProfile]
                                       city_data: Dict[str, Any], 
                                       property_data: List[Dict]) -> List[PartnershipOpportunity]:
        """Identify partnership opportunities for commercial development"""
        opportunities = []
        
        # Convert demographic data to profiles if needed
        if demographic_data and isinstance(demographic_data[0], dict):
            demographics_analyzer = DemographicsAnalyzer()
            demographic_profiles = demographics_analyzer.analyze_district_demographics(demographic_data)
        else:
            demographic_profiles = demographic_data
        
        for profile in demographic_profiles:
            district_opportunities = self._analyze_district_opportunities(profile, city_data, property_data)
            opportunities.extend(district_opportunities)
        
        # Sort by opportunity score
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        log.info(f"Identified {len(opportunities)} partnership opportunities")
        return opportunities[:20]  # Return top 20
    
    def _analyze_district_opportunities(self, profile: DemographicProfile, 
                                       city_data: Dict[str, Any], 
                                       property_data: List[Dict]) -> List[PartnershipOpportunity]:
        """Analyze opportunities for a specific district"""
        opportunities = []
        
        # Youth-focused opportunities
        if profile.youth_percentage > 25:
            opportunity = PartnershipOpportunity(
                location=profile.district_name,
                district_id=profile.district_id,
                partnership_type="public_private",
                city_department="Parks & Recreation",
                opportunity_score=self._calculate_youth_opportunity_score(profile),
                description="Youth entertainment and education center partnership",
                benefits=["Increased youth engagement", "Community development", "Reduced juvenile delinquency"],
                requirements=["City land allocation", "Private investment", "Community support"],
                estimated_timeline="18-24 months",
                success_probability=0.75,
                funding_available=True,
                community_support_score=0.8
            )
            opportunities.append(opportunity)
        
        # Senior-focused opportunities
        if profile.senior_percentage > 30:
            opportunity = PartnershipOpportunity(
                location=profile.district_name,
                district_id=profile.district_id,
                partnership_type="public_private",
                city_department="Senior Services",
                opportunity_score=self._calculate_senior_opportunity_score(profile),
                description="Senior healthcare and wellness center partnership",
                benefits=["Improved senior care access", "Health outcomes", "Economic development"],
                requirements=["Healthcare provider partnership", "Zoning approvals", "Funding"],
                estimated_timeline="24-36 months",
                success_probability=0.82,
                funding_available=True,
                community_support_score=0.85
            )
            opportunities.append(opportunity)
        
        # Economic development opportunities
        if profile.employment_rate < 0.85 and profile.young_adult_percentage > 20:
            opportunity = PartnershipOpportunity(
                location=profile.district_name,
                district_id=profile.district_id,
                partnership_type="community",
                city_department="Economic Development",
                opportunity_score=self._calculate_economic_opportunity_score(profile),
                description="Workforce development and job training partnership",
                benefits=["Job creation", "Skills development", "Business attraction"],
                requirements=["Training facilities", "Business partnerships", "Grant funding"],
                estimated_timeline="12-18 months",
                success_probability=0.78,
                funding_available=False,
                community_support_score=0.75
            )
            opportunities.append(opportunity)
        
        return opportunities
    
    def _calculate_youth_opportunity_score(self, profile: DemographicProfile) -> float:
        """Calculate opportunity score for youth-focused partnerships"""
        score = 0.0
        
        # Youth population factor
        score += min(profile.youth_percentage, 40) * 1.5
        
        # Income factor (moderate income areas have more need)
        if 30000 <= profile.household_income_median <= 60000:
            score += 20
        elif profile.household_income_median < 30000:
            score += 15
        
        # Population density factor
        if profile.population_density > 1000:
            score += 15
        elif profile.population_density > 500:
            score += 10
        
        # Employment rate factor
        if profile.employment_rate < 0.8:
            score += 10
        
        return min(100, score)
    
    def _calculate_senior_opportunity_score(self, profile: DemographicProfile) -> float:
        """Calculate opportunity score for senior-focused partnerships"""
        score = 0.0
        
        # Senior population factor
        score += min(profile.senior_percentage, 50) * 1.2
        
        # Income factor (higher income seniors can support premium services)
        if profile.household_income_median > 50000:
            score += 25
        elif profile.household_income_median > 35000:
            score += 20
        
        # Population density factor
        if profile.population_density > 800:
            score += 15
        
        return min(100, score)
    
    def _calculate_economic_opportunity_score(self, profile: DemographicProfile) -> float:
        """Calculate opportunity score for economic development partnerships"""
        score = 0.0
        
        # Unemployment factor
        score += (1 - profile.employment_rate) * 50
        
        # Young adult population factor
        score += profile.young_adult_percentage * 0.8
        
        # Income factor (lower income areas need more economic development)
        if profile.household_income_median < 40000:
            score += 25
        elif profile.household_income_median < 55000:
            score += 15
        
        # Population density factor
        if profile.population_density > 500:
            score += 10
        
        return min(100, score)

class ServiceRecommendationEngine:
    """AI-powered service type recommendations for commercial development"""
    
    def __init__(self):
        self.service_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.demand_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Service templates based on demographics
        self.service_templates = self._initialize_service_templates()
    
    def _initialize_service_templates(self) -> Dict[str, Dict]:
        """Initialize service recommendation templates"""
        return {
            "youth_entertainment": {
                "service_category": "entertainment",
                "specific_services": ["Gaming arcade", "VR experiences", "E-sports arena", "Fast food", "Bubble tea"],
                "target_demographics": ["youth", "young_adults"],
                "peak_hours": "Afternoons and weekends",
                "seasonal_factors": ["Summer peak", "School holidays"],
                "competition_level": "medium",
                "investment_required": "medium"
            },
            "senior_healthcare": {
                "service_category": "healthcare",
                "specific_services": ["Primary care clinic", "Pharmacy", "Physical therapy", "Senior fitness", "Nutrition counseling"],
                "target_demographics": ["seniors"],
                "peak_hours": "Morning and early afternoon",
                "seasonal_factors": ["Flu season demand", "Winter mobility issues"],
                "competition_level": "low",
                "investment_required": "high"
            },
            "family_retail": {
                "service_category": "retail",
                "specific_services": ["Grocery store", "Family clothing", "Toy store", "Family restaurant", "Childcare"],
                "target_demographics": ["families", "youth", "middle_aged"],
                "peak_hours": "Evenings and weekends",
                "seasonal_factors": ["Back-to-school", "Holiday shopping"],
                "competition_level": "high",
                "investment_required": "medium"
            },
            "young_professional": {
                "service_category": "food_service",
                "specific_services": ["Coffee shop", "Craft brewery", "Fitness center", "Co-working space", "Fast casual dining"],
                "target_demographics": ["young_adults"],
                "peak_hours": "Morning coffee, lunch, after-work",
                "seasonal_factors": ["Summer outdoor seating", "Winter comfort food"],
                "competition_level": "high",
                "investment_required": "medium"
            },
            "community_services": {
                "service_category": "education",
                "specific_services": ["Adult education", "Job training", "Library services", "Community center", "Legal aid"],
                "target_demographics": ["all_ages"],
                "peak_hours": "Varied by service",
                "seasonal_factors": ["Fall enrollment", "Spring job seeking"],
                "competition_level": "low",
                "investment_required": "low"
            }
        }
    
    def recommend_services(self, demographic_data: List[Dict],  # Changed from List[DemographicProfile]
                          partnership_opportunities: List[PartnershipOpportunity]) -> List[ServiceRecommendation]:
        """Generate service recommendations based on demographics and partnerships"""
        recommendations = []
        
        # Convert demographic data to profiles if needed
        if demographic_data and isinstance(demographic_data[0], dict):
            demographics_analyzer = DemographicsAnalyzer()
            demographic_profiles = demographics_analyzer.analyze_district_demographics(demographic_data)
        else:
            demographic_profiles = demographic_data
        
        for profile in demographic_profiles:
            profile_recommendations = self._analyze_profile_services(profile, partnership_opportunities)
            recommendations.extend(profile_recommendations)
        
        # Sort by confidence score
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
        
        log.info(f"Generated {len(recommendations)} service recommendations")
        return recommendations[:25]  # Return top 25
    
    def _analyze_profile_services(self, profile: DemographicProfile,
                                partnership_opportunities: List[PartnershipOpportunity]) -> List[ServiceRecommendation]:
        """Analyze service recommendations for a specific demographic profile"""
        recommendations = []
        
        # Youth-focused services
        if profile.youth_percentage > 20:
            youth_rec = self._create_service_recommendation(
                profile, "youth_entertainment", 
                self._calculate_youth_service_score(profile)
            )
            if youth_rec:
                recommendations.append(youth_rec)
        
        # Senior-focused services
        if profile.senior_percentage > 25:
            senior_rec = self._create_service_recommendation(
                profile, "senior_healthcare",
                self._calculate_senior_service_score(profile)
            )
            if senior_rec:
                recommendations.append(senior_rec)
        
        # Family services
        if profile.youth_percentage > 15 and profile.middle_aged_percentage > 25:
            family_rec = self._create_service_recommendation(
                profile, "family_retail",
                self._calculate_family_service_score(profile)
            )
            if family_rec:
                recommendations.append(family_rec)
        
        # Young professional services
        if profile.young_adult_percentage > 30 and profile.employment_rate > 0.7:
            professional_rec = self._create_service_recommendation(
                profile, "young_professional",
                self._calculate_professional_service_score(profile)
            )
            if professional_rec:
                recommendations.append(professional_rec)
        
        # Community services (always relevant)
        if profile.employment_rate < 0.85 or profile.household_income_median < 45000:
            community_rec = self._create_service_recommendation(
                profile, "community_services",
                self._calculate_community_service_score(profile)
            )
            if community_rec:
                recommendations.append(community_rec)
        
        return recommendations
    
    def _create_service_recommendation(self, profile: DemographicProfile, 
                                     service_type: str, base_score: float) -> Optional[ServiceRecommendation]:
        """Create a service recommendation object"""
        if service_type not in self.service_templates:
            return None
        
        template = self.service_templates[service_type]
        
        # Calculate detailed scores
        confidence_score = min(100, base_score)
        market_demand_score = self._calculate_market_demand(profile, service_type)
        demographic_alignment = self._calculate_demographic_alignment(profile, service_type)
        
        # Estimate revenue potential
        revenue_potential = self._estimate_revenue_potential(profile, service_type)
        
        return ServiceRecommendation(
            location=profile.district_name,
            district_id=profile.district_id,
            service_category=template["service_category"],
            specific_services=template["specific_services"],
            confidence_score=confidence_score,
            market_demand_score=market_demand_score,
            demographic_alignment=demographic_alignment,
            estimated_revenue_potential=revenue_potential,
            competition_level=template["competition_level"],
            investment_required=template["investment_required"],
            target_demographics=template["target_demographics"],
            peak_hours=template["peak_hours"],
            seasonal_factors=template["seasonal_factors"]
        )
    
    def _calculate_youth_service_score(self, profile: DemographicProfile) -> float:
        """Calculate score for youth-focused services"""
        score = profile.youth_percentage * 1.5
        
        # Young adult population also supports youth services
        score += profile.young_adult_percentage * 0.5
        
        # Income factor
        if 25000 <= profile.household_income_median <= 55000:
            score += 15
        
        # Population density
        if profile.population_density > 800:
            score += 10
        
        return score
    
    def _calculate_senior_service_score(self, profile: DemographicProfile) -> float:
        """Calculate score for senior-focused services"""
        score = profile.senior_percentage * 1.3
        
        # Income factor for healthcare services
        if profile.household_income_median > 40000:
            score += 20
        elif profile.household_income_median > 30000:
            score += 15
        
        # Population density
        if profile.population_density > 600:
            score += 10
        
        return score
    
    def _calculate_family_service_score(self, profile: DemographicProfile) -> float:
        """Calculate score for family-oriented services"""
        score = profile.youth_percentage * 1.2
        score += profile.middle_aged_percentage * 0.8
        
        # Income factor
        if profile.household_income_median > 35000:
            score += 15
        
        # Population density
        if profile.population_density > 500:
            score += 10
        
        return score
    
    def _calculate_professional_service_score(self, profile: DemographicProfile) -> float:
        """Calculate score for young professional services"""
        score = profile.young_adult_percentage * 1.4
        
        # Employment and income factors
        score += profile.employment_rate * 30
        if profile.household_income_median > 45000:
            score += 15
        
        # Population density
        if profile.population_density > 1000:
            score += 10
        
        return score
    
    def _calculate_community_service_score(self, profile: DemographicProfile) -> float:
        """Calculate score for community services"""
        score = 30  # Base score for community services
        
        # Need-based factors
        if profile.employment_rate < 0.8:
            score += 20
        
        if profile.household_income_median < 40000:
            score += 15
        
        # Population density
        if profile.population_density > 400:
            score += 10
        
        return score
    
    def _calculate_market_demand(self, profile: DemographicProfile, service_type: str) -> float:
        """Calculate market demand score for a service type"""
        base_demand = 50
        
        # Adjust based on demographic alignment
        if service_type == "youth_entertainment":
            base_demand += profile.youth_percentage * 0.8
        elif service_type == "senior_healthcare":
            base_demand += profile.senior_percentage * 0.7
        elif service_type == "family_retail":
            base_demand += (profile.youth_percentage + profile.middle_aged_percentage) * 0.6
        elif service_type == "young_professional":
            base_demand += profile.young_adult_percentage * 0.9
        elif service_type == "community_services":
            base_demand += (1 - profile.employment_rate) * 40
        
        # Income adjustment
        if profile.household_income_median > 50000:
            base_demand += 10
        elif profile.household_income_median < 30000:
            base_demand -= 10
        
        return min(100, max(0, base_demand))
    
    def _calculate_demographic_alignment(self, profile: DemographicProfile, service_type: str) -> float:
        """Calculate how well a service type aligns with demographics"""
        alignment = 50  # Base alignment
        
        if service_type == "youth_entertainment":
            alignment = profile.youth_percentage * 2
        elif service_type == "senior_healthcare":
            alignment = profile.senior_percentage * 2
        elif service_type == "family_retail":
            alignment = (profile.youth_percentage + profile.middle_aged_percentage) * 1.5
        elif service_type == "young_professional":
            alignment = profile.young_adult_percentage * 2
        elif service_type == "community_services":
            alignment = 70  # Generally good alignment
        
        return min(100, alignment)
    
    def _estimate_revenue_potential(self, profile: DemographicProfile, service_type: str) -> str:
        """Estimate revenue potential based on demographics"""
        # Simplified revenue estimation
        population_score = profile.total_population / 1000  # per 1000 people
        income_score = profile.household_income_median / 1000  # per $1000
        
        potential_score = population_score * income_score
        
        if service_type in ["senior_healthcare", "young_professional"]:
            threshold = 500
        elif service_type in ["youth_entertainment", "family_retail"]:
            threshold = 300
        else:
            threshold = 200
        
        if potential_score > threshold:
            return "high"
        elif potential_score > threshold * 0.5:
            return "medium"
        else:
            return "low"

class UrbanInvestmentAI:
    """Main AI engine for urban investment decision making"""
    
    def __init__(self):
        self.demographics_analyzer = DemographicsAnalyzer()
        self.partnership_analyzer = PartnershipOpportunityAnalyzer()
        self.service_engine = ServiceRecommendationEngine()
    
    def generate_investment_recommendations(self, demographic_data: List[Dict],
                                         city_data: Dict[str, Any],
                                         property_data: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive investment recommendations"""
        
        log.info("Generating comprehensive urban investment recommendations...")
        
        # 1. Analyze demographics
        demographic_profiles = self.demographics_analyzer.analyze_district_demographics(demographic_data)
        
        # 2. Predict demographic trends
        demographic_trends = self.demographics_analyzer.predict_demographic_trends(demographic_profiles, years_ahead=5)
        
        # 3. Identify partnership opportunities
        partnership_opportunities = self.partnership_analyzer.identify_partnership_opportunities(
            demographic_profiles, city_data, property_data
        )
        
        # 4. Generate service recommendations
        service_recommendations = self.service_engine.recommend_services(
            demographic_profiles, partnership_opportunities
        )
        
        # 5. Create comprehensive report
        recommendations = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "demographic_analysis": {
                "profiles_analyzed": len(demographic_profiles),
                "total_population": sum(p.total_population for p in demographic_profiles),
                "average_median_age": sum(p.median_age for p in demographic_profiles) / len(demographic_profiles) if demographic_profiles else 0,
                "demographic_profiles": [asdict(p) for p in demographic_profiles]
            },
            "demographic_trends": demographic_trends,
            "partnership_opportunities": {
                "total_opportunities": len(partnership_opportunities),
                "high_value_opportunities": len([o for o in partnership_opportunities if o.opportunity_score > 70]),
                "opportunities": [asdict(o) for o in partnership_opportunities]
            },
            "service_recommendations": {
                "total_recommendations": len(service_recommendations),
                "high_confidence_recommendations": len([s for s in service_recommendations if s.confidence_score > 70]),
                "recommendations": [asdict(s) for s in service_recommendations]
            },
            "summary": {
                "key_insights": self._generate_key_insights(demographic_profiles, partnership_opportunities, service_recommendations),
                "top_districts": self._identify_top_districts(demographic_profiles, partnership_opportunities),
                "investment_priorities": self._identify_investment_priorities(service_recommendations)
            }
        }
        
        log.info(f"Generated comprehensive recommendations: {len(partnership_opportunities)} opportunities, {len(service_recommendations)} service recommendations")
        
        return recommendations
    
    def _generate_key_insights(self, profiles: List[DemographicProfile], 
                             opportunities: List[PartnershipOpportunity],
                             services: List[ServiceRecommendation]) -> List[str]:
        """Generate key insights from the analysis"""
        insights = []
        
        if profiles:
            avg_youth = sum(p.youth_percentage for p in profiles) / len(profiles)
            avg_senior = sum(p.senior_percentage for p in profiles) / len(profiles)
            
            if avg_youth > 25:
                insights.append(f"High youth population ({avg_yuth:.1f}%) suggests strong entertainment and education opportunities")
            
            if avg_senior > 30:
                insights.append(f"Significant senior population ({avg_senior:.1f}%) indicates healthcare and wellness demand")
        
        if opportunities:
            high_value_ops = [o for o in opportunities if o.opportunity_score > 70]
            if high_value_ops:
                insights.append(f"Found {len(high_value_ops)} high-value partnership opportunities with city departments")
        
        if services:
            high_conf_services = [s for s in services if s.confidence_score > 75]
            if high_conf_services:
                top_categories = {}
                for service in high_conf_services:
                    top_categories[service.service_category] = top_categories.get(service.service_category, 0) + 1
                
                top_category = max(top_categories.items(), key=lambda x: x[1])[0]
                insights.append(f"Strongest service category: {top_category} with {top_categories[top_category]} high-confidence recommendations")
        
        return insights
    
    def _identify_top_districts(self, profiles: List[DemographicProfile], 
                              opportunities: List[PartnershipOpportunity]) -> List[Dict]:
        """Identify top districts for investment"""
        district_scores = {}
        
        for profile in profiles:
            score = 0
            
            # Demographic diversity score
            if profile.youth_percentage > 20:
                score += 20
            if profile.senior_percentage > 25:
                score += 20
            if profile.young_adult_percentage > 25:
                score += 15
            
            # Economic factors
            if profile.employment_rate > 0.8:
                score += 15
            if profile.household_income_median > 45000:
                score += 10
            
            # Population density
            if profile.population_density > 800:
                score += 10
            
            district_scores[profile.district_id] = {
                "district_name": profile.district_name,
                "score": score,
                "population": profile.total_population,
                "key_demographics": self._get_key_demographics(profile)
            }
        
        # Add partnership opportunity scores
        for opportunity in opportunities:
            if opportunity.district_id in district_scores:
                district_scores[opportunity.district_id]["score"] += opportunity.opportunity_score * 0.3
        
        # Sort and return top 5
        top_districts = sorted(district_scores.values(), key=lambda x: x["score"], reverse=True)[:5]
        return top_districts
    
    def _get_key_demographics(self, profile: DemographicProfile) -> List[str]:
        """Get key demographic characteristics"""
        key_demo = []
        
        if profile.youth_percentage > 25:
            key_demo.append("Youth-focused")
        if profile.senior_percentage > 30:
            key_demo.append("Senior-focused")
        if profile.young_adult_percentage > 30:
            key_demo.append("Young professional")
        if profile.employment_rate > 0.85:
            key_demo.append("High employment")
        if profile.household_income_median > 60000:
            key_demo.append("High income")
        
        return key_demo if key_demo else ["Mixed demographics"]
    
    def _identify_investment_priorities(self, services: List[ServiceRecommendation]) -> List[Dict]:
        """Identify investment priorities based on service recommendations"""
        priorities = {}
        
        for service in services:
            category = service.service_category
            
            if category not in priorities:
                priorities[category] = {
                    "category": category,
                    "total_confidence": 0,
                    "high_confidence_count": 0,
                    "avg_market_demand": 0,
                    "locations": []
                }
            
            priorities[category]["total_confidence"] += service.confidence_score
            if service.confidence_score > 70:
                priorities[category]["high_confidence_count"] += 1
            priorities[category]["avg_market_demand"] += service.market_demand_score
            priorities[category]["locations"].append(service.location)
        
        # Calculate averages and sort
        for priority in priorities.values():
            if len(priority["locations"]) > 0:
                priority["avg_market_demand"] /= len(priority["locations"])
                priority["avg_confidence"] = priority["total_confidence"] / len(priority["locations"])
        
        sorted_priorities = sorted(priorities.values(), key=lambda x: x["avg_confidence"], reverse=True)
        
        return sorted_priorities[:5]
