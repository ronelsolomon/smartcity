"""
Vacancy Watch - Smart Cities Intelligence System
Blends Montgomery AL city property data with real estate listing trends
using free web scraping with requests and BeautifulSoup.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
from free_scraper import FreeWebScraper, ScrapingConfig, quick_scrape
from montgomery_scraper import MontgomeryDataScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Free Scraper Configuration
SCRAPER_CONFIG = ScrapingConfig(
    use_selenium=os.getenv("USE_SELENIUM", "false").lower() == "true",
    headless=os.getenv("HEADLESS_MODE", "true").lower() == "true",
    timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
    delay_range=(1, 3),
    max_retries=3,
    rotate_user_agents=True,
    respect_robots_txt=True
)

# Montgomery AL Open Data (Socrata)
MONTGOMERY_BASE = "https://opendata.montgomeryal.gov/resource"
SOCRATA_APP_TOKEN = os.getenv("SOCRATA_APP_TOKEN", "")  # optional but recommended

# Real-estate listing sites to crawl for vacancy/listing signals
REAL_ESTATE_URLS = [
    "https://www.zillow.com/montgomery-al/",
    "https://www.realtor.com/realestateandhomes-search/Montgomery_AL",
    "https://www.trulia.com/AL/Montgomery/",
]

# Known Montgomery open datasets (Socrata endpoint slugs)
MONTGOMERY_DATASETS = {
    "permits":      "building-permits",          # construction activity
    "violations":   "code-violations",           # blight / vacancy signals
    "properties":   "property-assessments",      # parcel master data
    "vacancies":    "vacant-properties",         # city-flagged vacancies
    "traffic":      "traffic-incidents",         # infrastructure signal
}

POLL_INTERVAL_SEC = 15   # seconds between snapshot status checks
POLL_MAX_TRIES    = 40   # max polling attempts (~10 min total)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Property:
    parcel_id:        str
    address:          str
    owner:            str            = ""
    assessed_value:   float          = 0.0
    city_vacant_flag: bool           = False
    open_violations:  int            = 0
    recent_permits:   int            = 0
    listing_price:    Optional[float]= None
    listing_source:   str            = ""
    days_on_market:   Optional[int]  = None
    vacancy_score:    float          = 0.0
    signals:          list           = field(default_factory=list)

@dataclass
class TrafficIncident:
    incident_id: str
    location:    str
    type:        str
    date:        str
    severity:    str = "unknown"

@dataclass
class ConstructionPermit:
    permit_id:  str
    address:    str
    type:       str
    issued_date:str
    value:      float = 0.0

@dataclass
class VacancyWatchReport:
    generated_at:         str
    total_properties:     int
    high_risk_vacancies:  list
    construction_hotspots:list
    traffic_alerts:       list
    real_estate_trends:   dict
    summary:              dict

# ---------------------------------------------------------------------------
# Free Web Scraper Client
# ---------------------------------------------------------------------------

class FreeScraperClient:
    """Free web scraping client using requests + BeautifulSoup"""

    def __init__(self, config: ScrapingConfig = None):
        self.config = config or SCRAPER_CONFIG
        self.scraper = None

    def _get_scraper(self):
        """Get scraper instance (lazy initialization)"""
        if not self.scraper:
            self.scraper = FreeWebScraper(self.config)
        return self.scraper

    def trigger(self, urls: list[str], output_format: str = "markdown") -> str:
        """Trigger a crawl job and return job_id (compatibility method)"""
        job_id = f"job_{int(time.time())}_{hash(','.join(urls)) % 10000}"
        log.info("Crawl job triggered. job_id=%s, urls=%d", job_id, len(urls))
        return job_id

    def poll_until_ready(self, job_id: str) -> list[dict]:
        """Poll and return results (compatibility method)"""
        scraper = self._get_scraper()
        # For free scraper, we run synchronously
        urls = []  # Would need to track URLs per job_id in production
        results = scraper.crawl(urls)
        return results.get('results', [])

    def crawl(self, urls: list[str]) -> list[dict]:
        """Convenience: direct crawl"""
        scraper = self._get_scraper()
        try:
            results = scraper.crawl(urls)
            return results.get('results', [])
        finally:
            if self.scraper:
                self.scraper.close()
                self.scraper = None

    def close(self):
        """Clean up resources"""
        if self.scraper:
            self.scraper.close()
            self.scraper = None

# ---------------------------------------------------------------------------
# Montgomery Open Data client
# ---------------------------------------------------------------------------

class MontgomeryDataClient:
    """Fetches data from Montgomery AL Socrata Open Data portal."""

    def __init__(self, app_token: str = ""):
        self.session = requests.Session()
        self.headers = {"X-App-Token": app_token} if app_token else {}
        self.use_demo_data = True  # Force demo data due to API issues

    def _get(self, dataset_slug: str, params: dict | None = None) -> list[dict]:
        # Try real API first, then fall back to demo data
        if not self.use_demo_data:
            url  = f"{MONTGOMERY_BASE}/{dataset_slug}.json"
            try:
                resp = self.session.get(url, headers=self.headers, params=params or {}, timeout=20)
                if resp.status_code == 404:
                    log.warning("Dataset '%s' not found (404). Returning empty list.", dataset_slug)
                    return []
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.JSONDecodeError as e:
                log.error("Failed to decode JSON from %s: %s. Response content: %s", url, str(e), resp.text[:200])
                log.warning("Dataset '%s' returned invalid JSON. Falling back to demo data.", dataset_slug)
                self.use_demo_data = True
            except Exception as e:
                log.error("Error fetching dataset '%s': %s. Falling back to demo data.", dataset_slug, str(e))
                self.use_demo_data = True
        
        # Use demo data
        return self._get_demo_data(dataset_slug)
    
    def _get_demo_data(self, dataset_slug: str) -> list[dict]:
        """Get demo data from local files"""
        demo_file_map = {
            "vacant-properties": "montgomery_vacant_properties.json",
            "code-violations": "montgomery_code_violations.json", 
            "building-permits": "montgomery_building_permits.json",
            "traffic-incidents": "montgomery_traffic_incidents.json"
        }
        
        filename = demo_file_map.get(dataset_slug)
        if not filename:
            log.warning(f"No demo data available for dataset: {dataset_slug}")
            return []
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                log.info(f"Loaded {len(data)} demo records for {dataset_slug}")
                return data
        except FileNotFoundError:
            log.error(f"Demo data file not found: {filename}")
            return []
        except Exception as e:
            log.error(f"Error loading demo data from {filename}: {e}")
            return []

    def get_vacant_properties(self, limit: int = 500) -> list[Property]:
        rows = self._get(MONTGOMERY_DATASETS["vacancies"], {"$limit": limit})
        props = []
        for r in rows:
            props.append(Property(
                parcel_id        = r.get("parcel_id", r.get("objectid", "N/A")),
                address          = r.get("address", r.get("street_address", "Unknown")),
                owner            = r.get("owner_name", ""),
                city_vacant_flag = True,
                signals          = ["city_vacant_registry"],
            ))
        log.info("Loaded %d vacant properties from city registry.", len(props))
        return props

    def get_property_assessments(self, limit: int = 1000) -> list[dict]:
        return self._get(MONTGOMERY_DATASETS["properties"], {"$limit": limit})

    def get_code_violations(self, limit: int = 500) -> list[dict]:
        return self._get(MONTGOMERY_DATASETS["violations"], {"$limit": limit})

    def get_building_permits(self, days_back: int = 90, limit: int = 500) -> list[ConstructionPermit]:
        cutoff = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S")
        rows   = self._get(MONTGOMERY_DATASETS["permits"], {
            "$limit":  limit,
            "$where":  f"issued_date >= '{cutoff}'",
            "$order":  "issued_date DESC",
        })
        permits = []
        for r in rows:
            permits.append(ConstructionPermit(
                permit_id   = r.get("permit_number", r.get("objectid", "N/A")),
                address     = r.get("address", r.get("job_address", "Unknown")),
                type        = r.get("permit_type", r.get("work_type", "General")),
                issued_date = r.get("issued_date", ""),
                value       = float(r.get("job_value", r.get("estimated_cost", 0)) or 0),
            ))
        log.info("Loaded %d recent building permits.", len(permits))
        return permits

    def load_montgomery_open_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load data from Montgomery County Open Data Portal using the specialized scraper"""
        try:
            # Check if we have recent Montgomery data files
            import glob
            montgomery_files = glob.glob('montgomery_*_*.json')
            
            if montgomery_files and not force_refresh:
                # Load existing data
                latest_files = {}
                for file_type in ['building_permits', 'code_violations', 'vacant_properties', 'traffic_incidents']:
                    matching_files = [f for f in montgomery_files if file_type in f]
                    if matching_files:
                        latest_file = max(matching_files, key=os.path.getmtime)
                        # Check if file is recent (less than 24 hours old)
                        file_age = time.time() - os.path.getmtime(latest_file)
                        if file_age < 86400:  # 24 hours
                            with open(latest_file, 'r') as f:
                                latest_files[file_type] = json.load(f)
                
                if latest_files:
                    log.info(f"Loaded {len(latest_files)} Montgomery data types from existing files")
                    return latest_files
            
            # If no recent data or force refresh, crawl new data
            log.info("Crawling fresh Montgomery County open data...")
            scraper = MontgomeryDataScraper()
            crawl_results = scraper.crawl_all_datasets(max_datasets_per_category=2)
            saved_files = scraper.save_crawl_results(crawl_results)
            
            # Load the freshly crawled data
            loaded_data = {}
            for file_type, filename in saved_files.items():
                if file_type in ['building_permits', 'code_violations', 'vacant_properties', 'traffic_incidents']:
                    try:
                        with open(filename, 'r') as f:
                            loaded_data[file_type] = json.load(f)
                            log.info(f"Loaded {len(loaded_data[file_type])} {file_type} records")
                    except Exception as e:
                        log.warning(f"Could not load {filename}: {e}")
            
            return loaded_data
            
        except Exception as e:
            log.error(f"Error loading Montgomery open data: {e}")
            return {}

    def integrate_montgomery_data_with_ml(self) -> Dict[str, Any]:
        """Integrate Montgomery County open data into ML training pipeline"""
        try:
            # Load Montgomery data
            montgomery_data = self.load_montgomery_open_data()
            
            if not montgomery_data:
                log.warning("No Montgomery data available for ML integration")
                return {"success": False, "message": "No Montgomery data available"}
            
            # Convert Montgomery data to ML features
            integrated_features = []
            
            # Process building permits
            if 'building_permits' in montgomery_data:
                permits = montgomery_data['building_permits']
                for permit in permits:
                    feature = {
                        'source': 'montgomery_building_permit',
                        'parcel_id': permit.get('permit_number', ''),
                        'address': permit.get('address', ''),
                        'type': 'permit_activity',
                        'date': permit.get('issued_date', ''),
                        'value': permit.get('value', 0),
                        'permit_type': permit.get('type', ''),
                        'risk_indicators': {
                            'construction_activity': True,
                            'property_investment': permit.get('value', 0) > 0
                        }
                    }
                    integrated_features.append(feature)
            
            # Process code violations
            if 'code_violations' in montgomery_data:
                violations = montgomery_data['code_violations']
                for violation in violations:
                    feature = {
                        'source': 'montgomery_code_violation',
                        'parcel_id': violation.get('case_number', ''),
                        'address': violation.get('address', ''),
                        'type': 'violation',
                        'date': violation.get('violation_date', ''),
                        'violation_type': violation.get('violation_type', ''),
                        'severity': violation.get('severity', 'Unknown'),
                        'risk_indicators': {
                            'code_violation': True,
                            'blight_risk': violation.get('violation_type', '').lower() in ['blight', 'nuisance', 'unsafe'],
                            'high_severity': violation.get('severity', '').lower() in ['high', 'critical']
                        }
                    }
                    integrated_features.append(feature)
            
            # Process vacant properties
            if 'vacant_properties' in montgomery_data:
                vacant_props = montgomery_data['vacant_properties']
                for prop in vacant_props:
                    feature = {
                        'source': 'montgomery_vacant_property',
                        'parcel_id': prop.get('parcel_id', ''),
                        'address': prop.get('address', ''),
                        'type': 'vacancy',
                        'owner': prop.get('owner', ''),
                        'assessed_value': prop.get('assessed_value', 0),
                        'last_inspection': prop.get('last_inspection', ''),
                        'risk_indicators': {
                            'city_vacant': True,
                            'government_owned': 'city' in prop.get('owner', '').lower(),
                            'low_value': prop.get('assessed_value', 0) < 50000
                        }
                    }
                    integrated_features.append(feature)
            
            # Process traffic incidents (as neighborhood indicators)
            if 'traffic_incidents' in montgomery_data:
                incidents = montgomery_data['traffic_incidents']
                for incident in incidents:
                    feature = {
                        'source': 'montgomery_traffic_incident',
                        'address': incident.get('location', incident.get('address', '')),
                        'type': 'traffic_incident',
                        'date': incident.get('incident_date', ''),
                        'incident_type': incident.get('type', ''),
                        'severity': incident.get('severity', ''),
                        'risk_indicators': {
                            'traffic_safety_issue': True,
                            'high_activity_area': True
                        }
                    }
                    integrated_features.append(feature)
            
            # Save integrated features for ML training
            integrated_file = f"montgomery_integrated_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(integrated_file, 'w') as f:
                json.dump(integrated_features, f, indent=2)
            
            log.info(f"Integrated {len(integrated_features)} Montgomery data features for ML training")
            log.info(f"Saved integrated features to {integrated_file}")
            
            return {
                "success": True,
                "integrated_features_count": len(integrated_features),
                "data_sources": list(montgomery_data.keys()),
                "integrated_file": integrated_file,
                "feature_breakdown": {
                    'building_permits': len([f for f in integrated_features if f['source'] == 'montgomery_building_permit']),
                    'code_violations': len([f for f in integrated_features if f['source'] == 'montgomery_code_violation']),
                    'vacant_properties': len([f for f in integrated_features if f['source'] == 'montgomery_vacant_property']),
                    'traffic_incidents': len([f for f in integrated_features if f['source'] == 'montgomery_traffic_incident'])
                }
            }
            
        except Exception as e:
            log.error(f"Error integrating Montgomery data with ML: {e}")
            return {"success": False, "error": str(e)}

    def get_traffic_incidents(self, days_back: int = 30, limit: int = 200) -> list[TrafficIncident]:
        cutoff = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S")
        rows   = self._get(MONTGOMERY_DATASETS["traffic"], {
            "$limit":  limit,
            "$where":  f"incident_date >= '{cutoff}'",
            "$order":  "incident_date DESC",
        })
        incidents = []
        for r in rows:
            incidents.append(TrafficIncident(
                incident_id = r.get("incident_id", r.get("objectid", "N/A")),
                location    = r.get("location", r.get("address", "Unknown")),
                type        = r.get("incident_type", r.get("type", "General")),
                date        = r.get("incident_date", ""),
                severity    = r.get("severity", "unknown"),
            ))
        log.info("Loaded %d recent traffic incidents.", len(incidents))
        return incidents

# ---------------------------------------------------------------------------
# Real-estate trend parser
# ---------------------------------------------------------------------------

def parse_real_estate_signals(crawl_results: list[dict]) -> dict:
    """
    Extract vacancy and pricing signals from crawled real-estate pages.
    In production, parse the markdown/HTML with regex or an LLM.
    """
    trends: dict = {
        "sources_crawled":  len(crawl_results),
        "listing_keywords": {},
        "price_range":      {"min": None, "max": None},
        "vacancy_mentions": 0,
        "raw_snippets":     [],
    }

    vacancy_keywords = [
        "vacant", "foreclosure", "bank owned", "REO",
        "abandoned", "distressed", "price reduced", "days on market",
    ]

    for result in crawl_results:
        url     = result.get("url", "")
        content = result.get("markdown", result.get("content", ""))
        if not content:
            continue

        snippet = content[:600].lower()
        trends["raw_snippets"].append({"url": url, "preview": snippet[:200]})

        for kw in vacancy_keywords:
            if kw in snippet:
                trends["listing_keywords"][kw] = trends["listing_keywords"].get(kw, 0) + 1
                if kw in ("vacant", "abandoned", "foreclosure"):
                    trends["vacancy_mentions"] += 1

        # Naive price extraction (looks for $NNN,NNN patterns)
        import re
        prices = [int(p.replace(",", "")) for p in re.findall(r"\$(\d{2,3},\d{3})", content)]
        if prices:
            cur_min = trends["price_range"]["min"]
            cur_max = trends["price_range"]["max"]
            trends["price_range"]["min"] = min(prices) if cur_min is None else min(cur_min, min(prices))
            trends["price_range"]["max"] = max(prices) if cur_max is None else max(cur_max, max(prices))

    return trends

# ---------------------------------------------------------------------------
# AI-Enhanced Vacancy scoring engine
# ---------------------------------------------------------------------------

def score_property(prop: Property, violations_by_address: dict, permits_by_address: dict, 
                  ml_model=None, adaptive_weights=None) -> Property:
    """Compute a 0-100 vacancy/blight risk score with AI enhancement."""
    
    # Base scoring using traditional method
    base_score = 0.0
    signals = list(prop.signals)

    if prop.city_vacant_flag:
        base_score += 40
        signals.append("city_vacant_registry")

    viol_count = violations_by_address.get(prop.address.lower(), 0)
    if viol_count > 0:
        base_score += min(viol_count * 8, 30)
        signals.append(f"code_violations:{viol_count}")

    permit_count = permits_by_address.get(prop.address.lower(), 0)
    if permit_count == 0 and prop.assessed_value > 0:
        base_score += 10
        signals.append("no_recent_permits")
    elif permit_count > 0:
        base_score -= 10
        signals.append(f"active_permits:{permit_count}")

    if prop.listing_price and prop.assessed_value:
        ratio = prop.listing_price / max(prop.assessed_value, 1)
        if ratio < 0.5:
            base_score += 15
            signals.append("price_below_assessed")

    if prop.days_on_market and prop.days_on_market > 120:
        base_score += 10
        signals.append(f"stale_listing:{prop.days_on_market}d")
    
    # AI Enhancement: Use ML model if available
    if ml_model:
        try:
            from ml_engine import MLFeatures
            # Create ML features for this property
            ml_features = MLFeatures(
                parcel_id=prop.parcel_id,
                address=prop.address,
                assessed_value=prop.assessed_value,
                city_vacant_flag=prop.city_vacant_flag,
                violation_count=viol_count,
                permit_count=permit_count,
                listing_price=prop.listing_price,
                days_on_market=prop.days_on_market,
                price_to_assessed_ratio=(prop.listing_price / max(prop.assessed_value, 1)) if prop.listing_price and prop.assessed_value else None,
                neighborhood_vacancy_rate=0.0,  # Would need neighborhood data
                nearby_permit_activity=0,  # Would need neighborhood data
                historical_violation_trend=0.0,  # Would need historical data
                time_since_last_permit=999,  # Would need permit dates
                property_age_years=None,  # Would need construction year
                zip_code="00000"  # Would need proper zip extraction
            )
            
            # Get ML prediction
            predictions = ml_model.predict([ml_features])
            if predictions:
                pred = predictions[0]
                # Blend traditional score with ML prediction
                ml_score = pred.risk_score
                confidence = pred.confidence
                
                # Adaptive weighting based on confidence
                if confidence > 0.7:
                    final_score = (base_score * 0.3) + (ml_score * 0.7)
                elif confidence > 0.5:
                    final_score = (base_score * 0.6) + (ml_score * 0.4)
                else:
                    final_score = (base_score * 0.8) + (ml_score * 0.2)
                
                # Add AI-detected signals
                signals.extend(pred.key_factors)
                signals.append(f"ai_confidence:{confidence:.2f}")
                
                log.info(f"AI-enhanced scoring for {prop.address}: base={base_score:.1f}, ml={ml_score:.1f}, final={final_score:.1f}")
                
        except Exception as e:
            log.warning(f"ML scoring failed for {prop.address}: {e}. Using base score.")
            final_score = base_score
    else:
        final_score = base_score
    
    # Adaptive scoring with learned weights if available
    if adaptive_weights:
        final_score = apply_adaptive_weights(final_score, prop, adaptive_weights)
    
    prop.vacancy_score = max(0.0, min(100.0, final_score))
    prop.open_violations = viol_count
    prop.recent_permits  = permit_count
    prop.signals = signals
    return prop

def apply_adaptive_weights(base_score: float, prop: Property, weights: dict) -> float:
    """Apply learned adaptive weights to scoring"""
    adjusted_score = base_score
    
    # Apply learned weight adjustments
    if prop.city_vacant_flag and 'city_vacant_weight' in weights:
        adjusted_score += weights['city_vacant_weight']
    
    if prop.assessed_value > 0 and 'value_weight' in weights:
        value_adjustment = weights['value_weight'] * np.log(prop.assessed_value)
        adjusted_score += value_adjustment
    
    # Apply neighborhood adjustment if available
    if 'neighborhood_factor' in weights:
        adjusted_score *= weights['neighborhood_factor']
    
    return max(0.0, min(100.0, adjusted_score))

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class VacancyWatch:
    def __init__(self, scraper_config: ScrapingConfig = None,
                 socrata_token: str = SOCRATA_APP_TOKEN):
        self.scraper = FreeScraperClient(scraper_config or SCRAPER_CONFIG)
        self.city_data = MontgomeryDataClient(socrata_token)
        self._demo_mode = False  # Free scraper is always available
        
        # AI Components
        self.ml_model = None
        self.pattern_learner = None
        self.adaptive_weights = {}
        
        # Initialize AI components if available
        try:
            from ml_engine import VacancyMLModel
            from pattern_learning import PatternLearner
            self.ml_model = VacancyMLModel()
            self.pattern_learner = PatternLearner()
            log.info("AI components initialized successfully")
        except ImportError as e:
            log.warning(f"AI components not available: {e}")
        except Exception as e:
            log.error(f"Error initializing AI components: {e}")
        
        # Load adaptive weights if available
        self._load_adaptive_weights()

    # ------------------------------------------------------------------
    def run(self) -> VacancyWatchReport:
        log.info("=== Vacancy Watch starting ===")

        # 1. Pull city open-data signals
        vacant_props = self.city_data.get_vacant_properties(limit=200)
        violations   = self.city_data.get_code_violations(limit=500)
        permits      = self.city_data.get_building_permits(days_back=90)
        traffic      = self.city_data.get_traffic_incidents(days_back=30)

        # 2. Build lookup dicts (address → count)
        violations_by_addr = {}
        for v in violations:
            addr = v.get("address", v.get("street_address", "")).lower()
            violations_by_addr[addr] = violations_by_addr.get(addr, 0) + 1

        permits_by_addr = {}
        for p in permits:
            addr = p.address.lower()
            permits_by_addr[addr] = permits_by_addr.get(addr, 0) + 1

        # 3. Crawl real-estate sites with AI pattern learning
        log.info("Crawling %d real-estate URLs with free scraper...", len(REAL_ESTATE_URLS))
        try:
            crawl_results      = self.scraper.crawl(REAL_ESTATE_URLS)
            real_estate_trends = parse_real_estate_signals(crawl_results)
            
            # If real crawl fails or returns empty, use demo crawl data
            if not crawl_results or len(crawl_results) == 0:
                log.info("Real crawl returned no results, using demo crawl data")
                try:
                    with open("demo_crawl_results.json", 'r') as f:
                        demo_crawl = json.load(f)
                        crawl_results = demo_crawl
                        real_estate_trends = parse_real_estate_signals(crawl_results)
                        log.info(f"Using {len(crawl_results)} demo crawl results")
                except FileNotFoundError:
                    log.warning("Demo crawl data not found, using trends")
                    real_estate_trends = self._demo_real_estate_trends()
            
            # AI Enhancement: Analyze crawl results for patterns
            if self.pattern_learner:
                pattern_signals = self.pattern_learner.analyze_crawl_results(crawl_results)
                real_estate_trends["ai_signals"] = len(pattern_signals)
                real_estate_trends["pattern_summary"] = self.pattern_learner.get_pattern_summary()
                log.info(f"AI pattern analysis found {len(pattern_signals)} signals")
                
        except Exception as exc:
            log.error("Crawl failed: %s. Using demo trends.", exc)
            real_estate_trends = self._demo_real_estate_trends()

        # 4. Score each property with AI enhancement
        scored = [score_property(p, violations_by_addr, permits_by_addr, 
                                self.ml_model, self.adaptive_weights) for p in vacant_props]
        scored.sort(key=lambda p: p.vacancy_score, reverse=True)
        high_risk = [p for p in scored if p.vacancy_score >= 50]

        # 5. Construction hotspots (top addresses by permit activity)
        hotspot_addr = sorted(permits_by_addr.items(), key=lambda x: x[1], reverse=True)[:10]
        construction_hotspots = [
            {"address": a, "permit_count": c} for a, c in hotspot_addr
        ]

        # 6. Traffic alerts summary
        traffic_alerts = [
            {"location": t.location, "type": t.type, "date": t.date, "severity": t.severity}
            for t in traffic[:20]
        ]

        # 7. Summary statistics with AI insights
        ai_summary = {}
        if self.ml_model:
            ai_summary = self.ml_model.get_model_info()
        
        if self.pattern_learner:
            trend_predictions = self.pattern_learner.predict_trends(days_ahead=30)
            ai_summary["trend_predictions"] = trend_predictions
        
        summary = {
            "total_city_vacant_properties": len(vacant_props),
            "high_risk_count":              len(high_risk),
            "total_violations_indexed":     len(violations),
            "permits_last_90_days":         len(permits),
            "traffic_incidents_last_30d":   len(traffic),
            "avg_vacancy_score":            round(
                sum(p.vacancy_score for p in scored) / max(len(scored), 1), 1),
            "ai_insights":                  ai_summary
        }

        report = VacancyWatchReport(
            generated_at          = datetime.utcnow().isoformat() + "Z",
            total_properties      = len(scored),
            high_risk_vacancies   = [asdict(p) for p in high_risk[:50]],
            construction_hotspots = construction_hotspots,
            traffic_alerts        = traffic_alerts,
            real_estate_trends    = real_estate_trends,
            summary               = summary,
        )
        return report
    
    def _load_adaptive_weights(self):
        """Load adaptive scoring weights from file"""
        weights_file = "ml_models/adaptive_weights.json"
        try:
            if os.path.exists(weights_file):
                with open(weights_file, 'r') as f:
                    self.adaptive_weights = json.load(f)
                log.info("Loaded adaptive scoring weights")
        except Exception as e:
            log.warning(f"Could not load adaptive weights: {e}")
    
    def _save_adaptive_weights(self):
        """Save adaptive scoring weights to file"""
        weights_file = "ml_models/adaptive_weights.json"
        try:
            os.makedirs(os.path.dirname(weights_file), exist_ok=True)
            with open(weights_file, 'w') as f:
                json.dump(self.adaptive_weights, f, indent=2)
            log.info("Saved adaptive scoring weights")
        except Exception as e:
            log.error(f"Error saving adaptive weights: {e}")
    
    def train_ml_model(self, training_data: List[Dict] = None):
        """Train the ML model with historical data"""
        if not self.ml_model:
            log.error("ML model not available")
            return {"status": "unavailable"}
        
        if training_data is None:
            # Generate synthetic training data from current properties
            log.info("Generating synthetic training data")
            training_data = self._generate_training_data()
        
        # If still no data, create demo data
        if len(training_data) < 10:
            log.info("Creating demo training data")
            training_data = self._create_demo_training_data()
        
        try:
            # Extract features and labels
            from ml_engine import MLFeatures
            features = []
            labels = []
            
            for item in training_data:
                feature = MLFeatures(**item['features'])
                features.append(feature)
                labels.append(item['label'])
            
            # Train the model
            result = self.ml_model.train(features, labels)
            log.info(f"ML model training completed: {result}")
            return result
            
        except Exception as e:
            log.error(f"ML model training failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def _create_demo_training_data(self) -> List[Dict]:
        """Create demo training data for testing"""
        demo_data = []
        
        # Vacant properties (label = 1)
        vacant_properties = [
            {
                "features": {
                    "parcel_id": "VAC001",
                    "address": "100 Empty St",
                    "assessed_value": 75000.0,
                    "city_vacant_flag": True,
                    "violation_count": 5,
                    "permit_count": 0,
                    "listing_price": None,
                    "days_on_market": None,
                    "price_to_assessed_ratio": None,
                    "neighborhood_vacancy_rate": 0.20,
                    "nearby_permit_activity": 1,
                    "historical_violation_trend": 2.0,
                    "time_since_last_permit": 999,
                    "property_age_years": 60,
                    "zip_code": "36104"
                },
                "label": 1
            },
            {
                "features": {
                    "parcel_id": "VAC002", 
                    "address": "200 Abandoned Ave",
                    "assessed_value": 50000.0,
                    "city_vacant_flag": True,
                    "violation_count": 8,
                    "permit_count": 0,
                    "listing_price": 45000.0,
                    "days_on_market": 200,
                    "price_to_assessed_ratio": 0.9,
                    "neighborhood_vacancy_rate": 0.25,
                    "nearby_permit_activity": 0,
                    "historical_violation_trend": 3.0,
                    "time_since_last_permit": 999,
                    "property_age_years": 75,
                    "zip_code": "36105"
                },
                "label": 1
            },
            {
                "features": {
                    "parcel_id": "VAC003",
                    "address": "300 Foreclosure Ln",
                    "assessed_value": 120000.0,
                    "city_vacant_flag": True,
                    "violation_count": 2,
                    "permit_count": 0,
                    "listing_price": 80000.0,
                    "days_on_market": 150,
                    "price_to_assessed_ratio": 0.67,
                    "neighborhood_vacancy_rate": 0.15,
                    "nearby_permit_activity": 2,
                    "historical_violation_trend": 1.0,
                    "time_since_last_permit": 999,
                    "property_age_years": 40,
                    "zip_code": "36106"
                },
                "label": 1
            }
        ]
        
        # Occupied properties (label = 0)
        occupied_properties = [
            {
                "features": {
                    "parcel_id": "OCC001",
                    "address": "100 Family Dr",
                    "assessed_value": 250000.0,
                    "city_vacant_flag": False,
                    "violation_count": 0,
                    "permit_count": 3,
                    "listing_price": None,
                    "days_on_market": None,
                    "price_to_assessed_ratio": None,
                    "neighborhood_vacancy_rate": 0.05,
                    "nearby_permit_activity": 12,
                    "historical_violation_trend": 0.0,
                    "time_since_last_permit": 90,
                    "property_age_years": 10,
                    "zip_code": "36104"
                },
                "label": 0
            },
            {
                "features": {
                    "parcel_id": "OCC002",
                    "address": "200 Happy Home Rd",
                    "assessed_value": 180000.0,
                    "city_vacant_flag": False,
                    "violation_count": 0,
                    "permit_count": 1,
                    "listing_price": 195000.0,
                    "days_on_market": 45,
                    "price_to_assessed_ratio": 1.08,
                    "neighborhood_vacancy_rate": 0.03,
                    "nearby_permit_activity": 8,
                    "historical_violation_trend": 0.0,
                    "time_since_last_permit": 200,
                    "property_age_years": 20,
                    "zip_code": "36105"
                },
                "label": 0
            },
            {
                "features": {
                    "parcel_id": "OCC003",
                    "address": "300 Well Maintained Ct",
                    "assessed_value": 320000.0,
                    "city_vacant_flag": False,
                    "violation_count": 0,
                    "permit_count": 2,
                    "listing_price": None,
                    "days_on_market": None,
                    "price_to_assessed_ratio": None,
                    "neighborhood_vacancy_rate": 0.04,
                    "nearby_permit_activity": 15,
                    "historical_violation_trend": 0.0,
                    "time_since_last_permit": 120,
                    "property_age_years": 5,
                    "zip_code": "36106"
                },
                "label": 0
            }
        ]
        
        demo_data.extend(vacant_properties)
        demo_data.extend(occupied_properties)
        
        # Add more variations
        for i in range(4, 15):  # Add 11 more examples
            is_vacant = i % 3 == 0  # Every 3rd property is vacant
            
            if is_vacant:
                demo_data.append({
                    "features": {
                        "parcel_id": f"VAC{i:03d}",
                        "address": f"{i*100} Vacant St",
                        "assessed_value": 60000.0 + (i * 5000),
                        "city_vacant_flag": True,
                        "violation_count": i % 5,
                        "permit_count": 0,
                        "listing_price": 50000.0 + (i * 3000),
                        "days_on_market": 100 + (i * 20),
                        "price_to_assessed_ratio": 0.8 + (i * 0.02),
                        "neighborhood_vacancy_rate": 0.1 + (i * 0.02),
                        "nearby_permit_activity": i % 3,
                        "historical_violation_trend": i * 0.5,
                        "time_since_last_permit": 999,
                        "property_age_years": 30 + (i * 5),
                        "zip_code": f"3610{i % 7}"
                    },
                    "label": 1
                })
            else:
                demo_data.append({
                    "features": {
                        "parcel_id": f"OCC{i:03d}",
                        "address": f"{i*100} Occupied Ave",
                        "assessed_value": 150000.0 + (i * 10000),
                        "city_vacant_flag": False,
                        "violation_count": 0,
                        "permit_count": i % 4 + 1,
                        "listing_price": 160000.0 + (i * 12000),
                        "days_on_market": 30 + (i * 10),
                        "price_to_assessed_ratio": 1.05 + (i * 0.01),
                        "neighborhood_vacancy_rate": 0.02 + (i * 0.01),
                        "nearby_permit_activity": 5 + (i * 2),
                        "historical_violation_trend": 0.0,
                        "time_since_last_permit": 100 + (i * 30),
                        "property_age_years": 5 + (i * 3),
                        "zip_code": f"3610{i % 7}"
                    },
                    "label": 0
                })
        
        return demo_data
    
    def _generate_training_data(self) -> List[Dict]:
        """Generate synthetic training data from current properties"""
        # This is a simplified approach - in practice, you'd use real historical data
        synthetic_data = []
        
        # Get current property data
        try:
            vacant_props = self.city_data.get_vacant_properties(limit=100)
            violations = self.city_data.get_code_violations(limit=200)
            permits = self.city_data.get_building_permits(days_back=90)
            
            # Create lookup dictionaries
            violations_by_addr = {}
            for v in violations:
                addr = v.get("address", "").lower()
                violations_by_addr[addr] = violations_by_addr.get(addr, 0) + 1
            
            permits_by_addr = {}
            for p in permits:
                addr = p.address.lower()
                permits_by_addr[addr] = permits_by_addr.get(addr, 0) + 1
            
            # Generate training examples
            for prop in vacant_props:
                addr = prop.get("address", "").lower()
                
                # Create feature set
                feature_dict = {
                    'parcel_id': prop.get("parcel_id", ""),
                    'address': prop.get("address", ""),
                    'assessed_value': prop.get("assessed_value", 0.0),
                    'city_vacant_flag': True,  # All are vacant in this dataset
                    'violation_count': violations_by_addr.get(addr, 0),
                    'permit_count': permits_by_addr.get(addr, 0),
                    'listing_price': None,
                    'days_on_market': None,
                    'price_to_assessed_ratio': None,
                    'neighborhood_vacancy_rate': 0.1,  # Estimated
                    'nearby_permit_activity': 5,  # Estimated
                    'historical_violation_trend': 0.0,
                    'time_since_last_permit': 999,
                    'property_age_years': 30,  # Estimated
                    'zip_code': '36104'  # Montgomery default
                }
                
                # Label: 1 for vacant (positive class)
                synthetic_data.append({
                    'features': feature_dict,
                    'label': 1
                })
            
            # Add some non-vacant examples (would need real data in practice)
            for i in range(min(50, len(vacant_props))):
                feature_dict = {
                    'parcel_id': f"non_vacant_{i}",
                    'address': f"123 Non Vacant St {i}",
                    'assessed_value': 150000.0,
                    'city_vacant_flag': False,
                    'violation_count': 0,
                    'permit_count': 2,
                    'listing_price': 160000.0,
                    'days_on_market': 45,
                    'price_to_assessed_ratio': 1.07,
                    'neighborhood_vacancy_rate': 0.05,
                    'nearby_permit_activity': 10,
                    'historical_violation_trend': 0.0,
                    'time_since_last_permit': 200,
                    'property_age_years': 15,
                    'zip_code': '36104'
                }
                
                # Label: 0 for non-vacant (negative class)
                synthetic_data.append({
                    'features': feature_dict,
                    'label': 0
                })
                
        except Exception as e:
            log.error(f"Error generating training data: {e}")
        
        return synthetic_data
    
    def add_feedback(self, parcel_id: str, actual_outcome: bool, predicted_score: float):
        """Add feedback for continuous learning"""
        if self.ml_model:
            self.ml_model.add_feedback(parcel_id, actual_outcome, predicted_score/100.0)
            log.info(f"Added feedback for parcel {parcel_id}")
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get status of AI components"""
        status = {
            "ml_model_available": self.ml_model is not None,
            "pattern_learner_available": self.pattern_learner is not None,
            "adaptive_weights_loaded": len(self.adaptive_weights) > 0
        }
        
        if self.ml_model:
            status["model_info"] = self.ml_model.get_model_info()
        
        if self.pattern_learner:
            status["pattern_summary"] = self.pattern_learner.get_pattern_summary()
        
        return status

    # ------------------------------------------------------------------
    @staticmethod
    def _demo_real_estate_trends() -> dict:
        return {
            "sources_crawled":  3,
            "listing_keywords": {
                "foreclosure":    12,
                "price reduced":  27,
                "vacant":          8,
                "days on market":  45,
            },
            "price_range":       {"min": 45000, "max": 389000},
            "vacancy_mentions":  20,
            "raw_snippets": [
                {"url": "https://www.zillow.com/montgomery-al/",
                 "preview": "Demo mode – 347 homes for sale · Median list price $159,000 · 68 foreclosures"},
                {"url": "https://www.realtor.com/realestateandhomes-search/Montgomery_AL",
                 "preview": "Demo mode – Price reduced listings up 14% this quarter"},
            ],
        }

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse, pathlib

    parser = argparse.ArgumentParser(description="Vacancy Watch – Montgomery AL Smart Cities Signal")
    parser.add_argument("--output",  default="vacancy_watch_report.json",
                        help="Output JSON report path")
    parser.add_argument("--use-selenium", action="store_true",
                        help="Use Selenium for JavaScript-heavy sites")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run browser in headless mode")
    parser.add_argument("--socrata-token", default=SOCRATA_APP_TOKEN,
                        help="Montgomery Open Data app token (optional)")
    args = parser.parse_args()

    # Configure scraper based on arguments
    config = ScrapingConfig(
        use_selenium=args.use_selenium,
        headless=args.headless,
        timeout=30,
        delay_range=(1, 3),
        max_retries=3,
        rotate_user_agents=True
    )

    watch = VacancyWatch(scraper_config=config, socrata_token=args.socrata_token)
    try:
        report = watch.run()
        
        out_path = pathlib.Path(args.output)
        out_path.write_text(json.dumps(asdict(report), indent=2))
        log.info("Report written → %s", out_path.resolve())

        # Print summary to stdout
        s = report.summary
        print("\n" + "═" * 55)
        print("  VACANCY WATCH — MONTGOMERY AL")
        print("═" * 55)
        print(f"  Generated : {report.generated_at}")
        print(f"  Vacancies : {s['total_city_vacant_properties']} total | {s['high_risk_count']} high-risk")
        print(f"  Violations: {s['total_violations_indexed']} indexed")
        print(f"  Permits   : {s['permits_last_90_days']} (last 90 days)")
        print(f"  Traffic   : {s['traffic_incidents_last_30d']} incidents (last 30 days)")
        print(f"  Avg score : {s['avg_vacancy_score']} / 100")
        if report.high_risk_vacancies:
            print("\n  TOP HIGH-RISK PROPERTIES:")
            for p in report.high_risk_vacancies[:5]:
                print(f"    [{p['vacancy_score']:>5.1f}] {p['address']}  — {', '.join(p['signals'][:3])}")
        print("═" * 55 + "\n")
    finally:
        watch.scraper.close()


if __name__ == "__main__":
    main()