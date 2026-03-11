"""
Vacancy Watch Web Application
Flask backend with free web scraping integration
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from dataclasses import dataclass, asdict
import requests
from urllib.parse import urlencode
from free_scraper import FreeWebScraper, ScrapingConfig, quick_scrape
from zoning_scraper import ZoningScraper, scrape_zoning_for_properties
from montgomery_scraper import MontgomeryDataScraper, crawl_montgomery_data

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
CORS(app)

# ---------------------------------------------------------------------------
# Free Scraper Configuration
# ---------------------------------------------------------------------------

@dataclass
class ScraperSettings:
    use_selenium: bool = False
    headless: bool = True
    timeout: int = 30
    delay_min: int = 1
    delay_max: int = 3
    max_retries: int = 3
    rotate_user_agents: bool = True
    respect_robots_txt: bool = True

class FreeScraperClient:
    """Free web scraping client for Flask app"""

    def __init__(self, settings: ScraperSettings):
        self.settings = settings
        self.config = ScrapingConfig(
            use_selenium=settings.use_selenium,
            headless=settings.headless,
            timeout=settings.timeout,
            delay_range=(settings.delay_min, settings.delay_max),
            max_retries=settings.max_retries,
            rotate_user_agents=settings.rotate_user_agents,
            respect_robots_txt=settings.respect_robots_txt
        )

    def crawl_urls(self, urls: List[str]) -> Dict[str, Any]:
        """Crawl URLs and return results"""
        try:
            scraper = FreeWebScraper(self.config)
            results = scraper.crawl(urls)
            scraper.close()
            return results
        except Exception as e:
            log.error(f"Scraping failed: {e}")
            return {
                'results': [],
                'summary': {
                    'total_urls': len(urls),
                    'successful': 0,
                    'failed': len(urls),
                    'success_rate': 0,
                    'crawl_time': datetime.utcnow().isoformat() + "Z",
                    'error': str(e)
                }
            }

# ---------------------------------------------------------------------------
# Settings Storage
# ---------------------------------------------------------------------------

def get_settings() -> Dict[str, Any]:
    """Get scraper settings from session"""
    default_settings = {
        "use_selenium": False,
        "headless": True,
        "timeout": 30,
        "delay_min": 1,
        "delay_max": 3,
        "max_retries": 3,
        "rotate_user_agents": True,
        "respect_robots_txt": True,
    }
    return session.get('scraper_settings', default_settings)

def save_settings(settings: Dict[str, Any]):
    """Save scraper settings to session"""
    session['scraper_settings'] = settings

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    return jsonify(get_settings())

@app.route('/api/settings', methods=['POST'])
def save_settings_api():
    settings = request.json
    save_settings(settings)
    return jsonify({"status": "saved"})

@app.route('/api/scraper/test', methods=['POST'])
def test_scraper():
    """Test scraper with a simple URL"""
    settings = get_settings()
    try:
        config = ScraperSettings(**settings)
        client = FreeScraperClient(config)
        # Test with a simple URL
        test_urls = ["https://httpbin.org/html"]
        results = client.crawl_urls(test_urls)
        
        if results['summary']['successful'] > 0:
            return jsonify({"status": "success", "message": "Scraper test successful"})
        else:
            return jsonify({"status": "error", "message": "Scraper test failed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/scraper/crawl', methods=['POST'])
def crawl_urls():
    """Crawl URLs"""
    settings = get_settings()
    urls = request.json.get('urls', [])
    
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400
        
    try:
        config = ScraperSettings(**settings)
        client = FreeScraperClient(config)
        result = client.crawl_urls(urls)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Frontend Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/latest-report')
def latest_report():
    """Return the most recent vacancy watch report"""
    try:
        # Try to find the most recent report file
        import glob
        report_files = glob.glob('*_report.json')
        
        if report_files:
            # Get the most recently modified file
            latest_file = max(report_files, key=os.path.getmtime)
            with open(latest_file, 'r') as f:
                return jsonify(json.load(f))
        else:
            # Fallback to demo report
            if os.path.exists('demo_report.json'):
                with open('demo_report.json', 'r') as f:
                    return jsonify(json.load(f))
            else:
                # Return empty structure
                return jsonify({
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "total_properties": 0,
                    "high_risk_vacancies": [],
                    "construction_hotspots": [],
                    "traffic_alerts": [],
                    "real_estate_trends": {
                        "sources_crawled": 0,
                        "listing_keywords": {},
                        "price_range": {"min": 0, "max": 0},
                        "vacancy_mentions": 0
                    },
                    "summary": {
                        "total_city_vacant_properties": 0,
                        "high_risk_count": 0,
                        "total_violations_indexed": 0,
                        "permits_last_90_days": 0,
                        "traffic_incidents_last_30d": 0,
                        "avg_vacancy_score": 0.0
                    }
                })
    except Exception as e:
        log.error(f"Error loading latest report: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    """Get AI system status"""
    try:
        from vacancy_watch import VacancyWatch
        watch = VacancyWatch()
        
        # Check if trained models exist
        model_files_exist = (
            os.path.exists("ml_models/vacancy_classifier.pkl") and
            os.path.exists("ml_models/anomaly_detector.pkl")
        )
        
        status = watch.get_ai_status()
        
        # Update model info if files exist but show as not trained
        if model_files_exist and not status["model_info"]["models_trained"]:
            try:
                # Load the actual model info
                with open("ml_models/model_metadata.json", 'r') as f:
                    metadata = json.load(f)
                    status["model_info"] = {
                        "models_trained": True,
                        "model_accuracy": metadata.get('accuracy', 0.0),
                        "feature_importance": metadata.get('feature_importance', {}),
                        "last_training": metadata.get('last_updated'),
                        "training_history": metadata.get('training_history', [])
                    }
            except:
                pass
        
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/train', methods=['POST'])
def train_ai_model():
    """Train the AI model"""
    try:
        from vacancy_watch import VacancyWatch
        watch = VacancyWatch()
        result = watch.train_ml_model()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/feedback', methods=['POST'])
def add_ai_feedback():
    """Add feedback for continuous learning"""
    try:
        data = request.json
        parcel_id = data.get('parcel_id')
        actual_outcome = data.get('actual_outcome')
        predicted_score = data.get('predicted_score')
        
        if not all([parcel_id, actual_outcome is not None, predicted_score is not None]):
            return jsonify({"error": "Missing required fields"}), 400
        
        from vacancy_watch import VacancyWatch
        watch = VacancyWatch()
        watch.add_feedback(parcel_id, actual_outcome, predicted_score)
        
        return jsonify({"status": "success", "message": "Feedback added"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/predict', methods=['POST'])
def predict_vacancy():
    """Predict vacancy for specific properties"""
    try:
        data = request.json
        properties = data.get('properties', [])
        
        if not properties:
            return jsonify({"error": "No properties provided"}), 400
        
        from vacancy_watch import VacancyWatch
        watch = VacancyWatch()
        
        if not watch.ml_model:
            return jsonify({"error": "ML model not available"}), 503
        
        # Convert to ML features and predict
        from ml_engine import MLFeatures
        features = []
        for prop in properties:
            feature = MLFeatures(
                parcel_id=prop.get('parcel_id', ''),
                address=prop.get('address', ''),
                assessed_value=prop.get('assessed_value', 0.0),
                city_vacant_flag=prop.get('city_vacant_flag', False),
                violation_count=prop.get('violation_count', 0),
                permit_count=prop.get('permit_count', 0),
                listing_price=prop.get('listing_price'),
                days_on_market=prop.get('days_on_market'),
                price_to_assessed_ratio=prop.get('price_to_assessed_ratio'),
                neighborhood_vacancy_rate=prop.get('neighborhood_vacancy_rate', 0.0),
                nearby_permit_activity=prop.get('nearby_permit_activity', 0),
                historical_violation_trend=prop.get('historical_violation_trend', 0.0),
                time_since_last_permit=prop.get('time_since_last_permit', 999),
                property_age_years=prop.get('property_age_years'),
                zip_code=prop.get('zip_code', '00000')
            )
            features.append(feature)
        
        predictions = watch.ml_model.predict(features)
        results = []
        
        for i, pred in enumerate(predictions):
            results.append({
                'parcel_id': properties[i].get('parcel_id'),
                'address': properties[i].get('address'),
                'vacancy_probability': pred.vacancy_probability,
                'risk_score': pred.risk_score,
                'confidence': pred.confidence,
                'key_factors': pred.key_factors,
                'anomaly_score': pred.anomaly_score,
                'predicted_time_to_vacancy': pred.predicted_time_to_vacancy
            })
        
        return jsonify({"predictions": results})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/patterns', methods=['GET'])
def get_patterns():
    """Get learned patterns and trend predictions"""
    try:
        from vacancy_watch import VacancyWatch
        watch = VacancyWatch()
        
        if not watch.pattern_learner:
            return jsonify({"error": "Pattern learner not available"}), 503
        
        pattern_summary = watch.pattern_learner.get_pattern_summary()
        trend_predictions = watch.pattern_learner.predict_trends(days_ahead=30)
        
        return jsonify({
            "pattern_summary": pattern_summary,
            "trend_predictions": trend_predictions
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Zoning Data API Routes
# ---------------------------------------------------------------------------

@app.route('/api/zoning/districts', methods=['GET'])
def get_zoning_districts():
    """Get all zoning districts and their regulations"""
    try:
        scraper = ZoningScraper()
        results = scraper.scrape_zoning_data()  # Get general zoning districts
        
        if results['success']:
            return jsonify(results)
        else:
            return jsonify({"error": results.get('error', 'Failed to fetch zoning data')}), 500
            
    except Exception as e:
        log.error(f"Error fetching zoning districts: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/zoning/lookup', methods=['POST'])
def lookup_zoning():
    """Look up zoning information for specific addresses"""
    try:
        data = request.json
        addresses = data.get('addresses', [])
        
        if not addresses:
            return jsonify({"error": "No addresses provided"}), 400
        
        scraper = ZoningScraper()
        results = scraper.scrape_zoning_data(addresses)
        
        if results['success']:
            return jsonify(results)
        else:
            return jsonify({"error": results.get('error', 'Failed to lookup zoning')}), 500
            
    except Exception as e:
        log.error(f"Error in zoning lookup: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/zoning/properties', methods=['POST'])
def get_property_zoning():
    """Get zoning information for existing properties"""
    try:
        data = request.json
        properties = data.get('properties', [])
        
        if not properties:
            return jsonify({"error": "No properties provided"}), 400
        
        results = scrape_zoning_for_properties(properties)
        
        if results['success']:
            return jsonify(results)
        else:
            return jsonify({"error": results.get('error', 'Failed to fetch property zoning')}), 500
            
    except Exception as e:
        log.error(f"Error fetching property zoning: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/zoning/enrich', methods=['POST'])
def enrich_properties_with_zoning():
    """Enrich existing property data with zoning information"""
    try:
        # Get existing properties from latest report
        import glob
        property_files = glob.glob('*_properties.json') or glob.glob('demo_properties.json')
        
        if not property_files:
            return jsonify({"error": "No property data found"}), 404
        
        # Load the most recent property data
        properties_file = max(property_files, key=os.path.getmtime)
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Enrich with zoning data
        results = scrape_zoning_for_properties(properties)
        
        if results['success']:
            # Save enriched data
            enriched_file = properties_file.replace('.json', '_with_zoning.json')
            with open(enriched_file, 'w') as f:
                json.dump(results['data'], f, indent=2)
            
            return jsonify({
                "success": True,
                "message": f"Enriched {len(results['data'])} properties with zoning data",
                "enriched_file": enriched_file,
                "zoning_summary": results.get('zoning_summary', {}),
                "timestamp": results['timestamp']
            })
        else:
            return jsonify({"error": results.get('error', 'Failed to enrich properties')}), 500
            
    except Exception as e:
        log.error(f"Error enriching properties with zoning: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Montgomery Data API Routes
# ---------------------------------------------------------------------------

@app.route('/api/montgomery/discover', methods=['GET'])
def discover_montgomery_datasets():
    """Discover available Montgomery County datasets"""
    try:
        scraper = MontgomeryDataScraper()
        datasets = scraper.discover_datasets()
        categorized = scraper.categorize_datasets(datasets)
        
        return jsonify({
            "success": True,
            "total_datasets": len(datasets),
            "categories": {k: len(v) for k, v in categorized.items()},
            "datasets": [
                {
                    "name": ds.name,
                    "description": ds.description,
                    "url": ds.url,
                    "format": ds.format,
                    "category": ds.category,
                    "last_updated": ds.last_updated,
                    "record_count": ds.record_count
                } for ds in datasets
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error discovering Montgomery datasets: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/montgomery/crawl', methods=['POST'])
def crawl_montgomery_data():
    """Crawl Montgomery County open data"""
    try:
        data = request.json or {}
        max_datasets = data.get('max_datasets', 3)
        
        scraper = MontgomeryDataScraper()
        results = scraper.crawl_all_datasets(max_datasets_per_category=max_datasets)
        saved_files = scraper.save_crawl_results(results)
        
        return jsonify({
            "success": True,
            "results": results,
            "saved_files": saved_files,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error crawling Montgomery data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/montgomery/download/<dataset_name>', methods=['POST'])
def download_montgomery_dataset(dataset_name):
    """Download a specific Montgomery dataset"""
    try:
        data = request.json or {}
        dataset_url = data.get('url')
        dataset_format = data.get('format', 'json')
        
        if not dataset_url:
            return jsonify({"error": "Dataset URL required"}), 400
        
        from montgomery_scraper import MontgomeryDataset
        dataset = MontgomeryDataset(
            name=dataset_name,
            description="",
            url=dataset_url,
            format=dataset_format
        )
        
        scraper = MontgomeryDataScraper()
        result = scraper.download_dataset(dataset)
        
        return jsonify(result)
        
    except Exception as e:
        log.error(f"Error downloading Montgomery dataset {dataset_name}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/montgomery/analyze', methods=['POST'])
def analyze_montgomery_data():
    """Analyze Montgomery County open data"""
    try:
        # Get the most recent Montgomery data files
        import glob
        montgomery_files = glob.glob('montgomery_*_*.json')
        
        if not montgomery_files:
            return jsonify({"error": "No Montgomery data files found"}), 404
        
        # Load the most recent data files
        analysis_results = {}
        
        for file_type in ['building_permits', 'code_violations', 'vacant_properties', 'traffic_incidents']:
            matching_files = [f for f in montgomery_files if file_type in f]
            if matching_files:
                latest_file = max(matching_files, key=os.path.getmtime)
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                    
                # Basic analysis
                analysis_results[file_type] = {
                    'file_name': latest_file,
                    'record_count': len(data),
                    'file_size': os.path.getsize(latest_file),
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(latest_file)).isoformat(),
                    'sample_data': data[:3] if data else []
                }
                
                # Add specific analysis based on data type
                if file_type == 'building_permits' and data:
                    analysis_results[file_type]['analysis'] = analyze_building_permits(data)
                elif file_type == 'code_violations' and data:
                    analysis_results[file_type]['analysis'] = analyze_code_violations(data)
                elif file_type == 'vacant_properties' and data:
                    analysis_results[file_type]['analysis'] = analyze_vacant_properties(data)
                elif file_type == 'traffic_incidents' and data:
                    analysis_results[file_type]['analysis'] = analyze_traffic_incidents(data)
        
        return jsonify({
            "success": True,
            "analysis": analysis_results,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error analyzing Montgomery data: {e}")
        return jsonify({"error": str(e)}), 500

def analyze_building_permits(permits):
    """Analyze building permits data"""
    if not permits:
        return {}
    
    # Extract key metrics
    total_value = sum(p.get('value', 0) for p in permits if isinstance(p.get('value'), (int, float)))
    permit_types = {}
    addresses = set()
    
    for permit in permits:
        permit_type = permit.get('type', 'Unknown')
        permit_types[permit_type] = permit_types.get(permit_type, 0) + 1
        
        address = permit.get('address', '')
        if address:
            addresses.add(address)
    
    return {
        'total_permits': len(permits),
        'total_value': total_value,
        'average_value': total_value / len(permits) if permits else 0,
        'unique_addresses': len(addresses),
        'permit_types': permit_types,
        'high_value_permits': len([p for p in permits if p.get('value', 0) > 100000])
    }

def analyze_code_violations(violations):
    """Analyze code violations data"""
    if not violations:
        return {}
    
    violation_types = {}
    addresses = set()
    severity_counts = {}
    
    for violation in violations:
        v_type = violation.get('violation_type', violation.get('type', 'Unknown'))
        violation_types[v_type] = violation_types.get(v_type, 0) + 1
        
        address = violation.get('address', '')
        if address:
            addresses.add(address)
        
        severity = violation.get('severity', 'Unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    return {
        'total_violations': len(violations),
        'unique_addresses': len(addresses),
        'violation_types': violation_types,
        'severity_distribution': severity_counts,
        'most_common_violation': max(violation_types.items(), key=lambda x: x[1])[0] if violation_types else None
    }

def analyze_vacant_properties(properties):
    """Analyze vacant properties data"""
    if not properties:
        return {}
    
    total_assessed_value = sum(p.get('assessed_value', 0) for p in properties if isinstance(p.get('assessed_value'), (int, float)))
    owners = {}
    zip_codes = set()
    
    for prop in properties:
        owner = prop.get('owner', 'Unknown')
        owners[owner] = owners.get(owner, 0) + 1
        
        zip_code = prop.get('zip_code', '')
        if zip_code:
            zip_codes.add(zip_code)
    
    return {
        'total_vacant_properties': len(properties),
        'total_assessed_value': total_assessed_value,
        'average_assessed_value': total_assessed_value / len(properties) if properties else 0,
        'unique_owners': len(owners),
        'top_owners': sorted(owners.items(), key=lambda x: x[1], reverse=True)[:5],
        'zip_codes': list(zip_codes)
    }

def analyze_traffic_incidents(incidents):
    """Analyze traffic incidents data"""
    if not incidents:
        return {}
    
    incident_types = {}
    locations = set()
    severity_counts = {}
    
    for incident in incidents:
        i_type = incident.get('type', incident.get('incident_type', 'Unknown'))
        incident_types[i_type] = incident_types.get(i_type, 0) + 1
        
        location = incident.get('location', incident.get('address', ''))
        if location:
            locations.add(location)
        
        severity = incident.get('severity', 'Unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    return {
        'total_incidents': len(incidents),
        'unique_locations': len(locations),
        'incident_types': incident_types,
        'severity_distribution': severity_counts,
        'most_common_incident': max(incident_types.items(), key=lambda x: x[1])[0] if incident_types else None
    }

@app.route('/api/montgomery/status', methods=['GET'])
def montgomery_data_status():
    """Get status of Montgomery data integration"""
    try:
        import glob
        
        # Check for existing Montgomery data files
        montgomery_files = glob.glob('montgomery_*_*.json')
        
        # Get file information
        file_info = {}
        for file_path in montgomery_files:
            stat = os.stat(file_path)
            file_info[file_path] = {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'records': 0
            }
            
            # Try to count records
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        file_info[file_path]['records'] = len(data)
                    elif isinstance(data, dict) and 'data' in data:
                        file_info[file_path]['records'] = len(data['data'])
            except:
                pass
        
        return jsonify({
            "has_data": len(montgomery_files) > 0,
            "file_count": len(montgomery_files),
            "files": file_info,
            "last_crawl": max([f['modified'] for f in file_info.values()]) if file_info else None,
            "total_records": sum(f['records'] for f in file_info.values()),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error getting Montgomery data status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/montgomery/integrate-ml', methods=['POST'])
def integrate_montgomery_ml():
    """Integrate Montgomery County data with ML pipeline"""
    try:
        from vacancy_watch import VacancyWatch
        
        watch = VacancyWatch()
        result = watch.integrate_montgomery_data_with_ml()
        
        return jsonify(result)
        
    except Exception as e:
        log.error(f"Error integrating Montgomery data with ML: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Surplus Properties API Routes
# ---------------------------------------------------------------------------

@app.route('/api/surplus/discover', methods=['GET'])
def discover_surplus_datasets():
    """Discover available surplus properties datasets"""
    try:
        from surplus_scraper import SurplusPropertiesScraper
        
        scraper = SurplusPropertiesScraper()
        datasets = scraper.discover_surplus_datasets()
        
        return jsonify({
            "success": True,
            "datasets": [
                {
                    "name": ds.name,
                    "description": ds.description,
                    "url": ds.url,
                    "format": ds.format,
                    "category": ds.category,
                    "last_updated": ds.last_updated,
                    "record_count": ds.record_count
                } for ds in datasets
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error discovering surplus datasets: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/crawl', methods=['POST'])
def crawl_surplus_properties():
    """Crawl surplus properties data"""
    try:
        data = request.json or {}
        max_datasets = data.get('max_datasets', 5)
        
        from surplus_scraper import SurplusPropertiesScraper
        
        scraper = SurplusPropertiesScraper()
        datasets = scraper.discover_surplus_datasets()
        
        all_properties = []
        crawled_count = 0
        
        for dataset in datasets[:max_datasets]:
            try:
                properties = scraper.download_surplus_data(dataset)
                all_properties.extend(properties)
                crawled_count += 1
                log.info(f"Crawled {len(properties)} properties from {dataset.name}")
            except Exception as e:
                log.warning(f"Failed to crawl {dataset.name}: {e}")
        
        # Save crawled data
        if all_properties:
            filename = scraper.save_surplus_properties(all_properties)
            
            return jsonify({
                "success": True,
                "properties_count": len(all_properties),
                "datasets_crawled": crawled_count,
                "saved_file": filename,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            # Generate demo data if no real data found
            demo_properties = scraper.generate_demo_surplus_properties(25)
            filename = scraper.save_surplus_properties(demo_properties)
            
            return jsonify({
                "success": True,
                "properties_count": len(demo_properties),
                "datasets_crawled": 0,
                "saved_file": filename,
                "demo_data": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        
    except Exception as e:
        log.error(f"Error crawling surplus properties: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/properties', methods=['GET'])
def get_surplus_properties():
    """Get surplus properties data"""
    try:
        import glob
        
        # Look for surplus properties files
        surplus_files = glob.glob('*surplus_properties*.json')
        
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        # Load the most recent file
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            properties = json.load(f)
        
        # Apply filters if provided
        filters = request.args.to_dict()
        
        if filters:
            filtered_properties = []
            for prop in properties:
                include = True
                
                # Status filter
                if 'status' in filters and prop.get('status', '').lower() != filters['status'].lower():
                    include = False
                
                # Property type filter
                if 'property_type' in filters and prop.get('property_type', '').lower() != filters['property_type'].lower():
                    include = False
                
                # Minimum assessed value filter
                if 'min_value' in filters:
                    try:
                        min_val = float(filters['min_value'])
                        if prop.get('assessed_value', 0) < min_val:
                            include = False
                    except ValueError:
                        pass
                
                # Eligibility filter
                if 'eligible' in filters:
                    eligible_only = filters['eligible'].lower() == 'true'
                    is_eligible = prop.get('acquisition_eligibility', {}).get('eligible', False)
                    if eligible_only != is_eligible:
                        include = False
                
                if include:
                    filtered_properties.append(prop)
            
            properties = filtered_properties
        
        # Sort results
        sort_by = request.args.get('sort_by', 'assessed_value')
        sort_order = request.args.get('sort_order', 'desc')
        
        reverse = sort_order.lower() == 'desc'
        properties.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        paginated_properties = properties[start_idx:end_idx]
        
        return jsonify({
            "success": True,
            "properties": paginated_properties,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": len(properties),
                "pages": (len(properties) + per_page - 1) // per_page
            },
            "filters_applied": bool(filters),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error getting surplus properties: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/analyze', methods=['POST'])
def analyze_surplus_properties():
    """Analyze surplus properties data"""
    try:
        import glob
        
        # Get surplus properties data
        surplus_files = glob.glob('*surplus_properties*.json')
        
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            properties = json.load(f)
        
        analysis = {
            'total_properties': len(properties),
            'total_assessed_value': sum(p.get('assessed_value', 0) for p in properties),
            'average_assessed_value': 0,
            'property_types': {},
            'zoning_distribution': {},
            'neighborhood_distribution': {},
            'status_distribution': {},
            'eligibility_summary': {},
            'development_potential_summary': {},
            'investment_opportunities': [],
            'high_potential_properties': []
        }
        
        if properties:
            analysis['average_assessed_value'] = analysis['total_assessed_value'] / len(properties)
        
        # Analyze distributions
        for prop in properties:
            # Property types
            prop_type = prop.get('property_type', 'Unknown')
            analysis['property_types'][prop_type] = analysis['property_types'].get(prop_type, 0) + 1
            
            # Zoning
            zoning = prop.get('zoning', 'Unknown')
            analysis['zoning_distribution'][zoning] = analysis['zoning_distribution'].get(zoning, 0) + 1
            
            # Neighborhoods
            neighborhood = prop.get('neighborhood', 'Unknown')
            analysis['neighborhood_distribution'][neighborhood] = analysis['neighborhood_distribution'].get(neighborhood, 0) + 1
            
            # Status
            status = prop.get('status', 'Unknown')
            analysis['status_distribution'][status] = analysis['status_distribution'].get(status, 0) + 1
            
            # Eligibility
            eligibility = prop.get('acquisition_eligibility', {})
            if eligibility.get('eligible', False):
                grade = eligibility.get('grade', 'Unknown')
                analysis['eligibility_summary'][grade] = analysis['eligibility_summary'].get(grade, 0) + 1
            
            # Development potential
            potential = prop.get('development_potential', {})
            potential_score = potential.get('overall_score', 0)
            market_potential = potential.get('market_potential', 'Unknown')
            analysis['development_potential_summary'][market_potential] = analysis['development_potential_summary'].get(market_potential, 0) + 1
            
            # Investment opportunities (good value + high potential)
            if (prop.get('assessed_value', 0) < 100000 and 
                potential_score > 70 and 
                eligibility.get('eligible', False)):
                analysis['investment_opportunities'].append({
                    'parcel_id': prop.get('parcel_id'),
                    'address': prop.get('address'),
                    'assessed_value': prop.get('assessed_value'),
                    'potential_score': potential_score,
                    'estimated_investment': potential.get('estimated_investment_range', {})
                })
            
            # High potential properties
            if potential_score > 80:
                analysis['high_potential_properties'].append({
                    'parcel_id': prop.get('parcel_id'),
                    'address': prop.get('address'),
                    'potential_score': potential_score,
                    'potential_uses': potential.get('potential_uses', []),
                    'market_potential': market_potential
                })
        
        # Sort investment opportunities by value
        analysis['investment_opportunities'].sort(key=lambda x: x.get('assessed_value', 0))
        
        # Sort high potential properties by score
        analysis['high_potential_properties'].sort(key=lambda x: x.get('potential_score', 0), reverse=True)
        
        # Limit results
        analysis['investment_opportunities'] = analysis['investment_opportunities'][:10]
        analysis['high_potential_properties'] = analysis['high_potential_properties'][:10]
        
        return jsonify({
            "success": True,
            "analysis": analysis,
            "source_file": latest_file,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error analyzing surplus properties: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/export', methods=['POST'])
def export_surplus_properties():
    """Export surplus properties with custom formatting"""
    try:
        data = request.json
        export_format = data.get('format', 'json')
        filters = data.get('filters', {})
        include_analysis = data.get('include_analysis', False)
        
        import glob
        
        # Get surplus properties data
        surplus_files = glob.glob('*surplus_properties*.json')
        
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            properties = json.load(f)
        
        # Apply filters
        if filters:
            filtered_properties = []
            for prop in properties:
                include = True
                
                for key, value in filters.items():
                    if key in prop and str(prop[key]).lower() != str(value).lower():
                        include = False
                        break
                
                if include:
                    filtered_properties.append(prop)
            
            properties = filtered_properties
        
        # Prepare export data
        export_data = {
            'export_info': {
                'timestamp': datetime.utcnow().isoformat() + "Z",
                'total_properties': len(properties),
                'filters_applied': filters,
                'format': export_format
            },
            'properties': properties
        }
        
        if include_analysis:
            # Add basic analysis
            export_data['summary'] = {
                'total_assessed_value': sum(p.get('assessed_value', 0) for p in properties),
                'average_assessed_value': sum(p.get('assessed_value', 0) for p in properties) / len(properties) if properties else 0,
                'eligible_properties': len([p for p in properties if p.get('acquisition_eligibility', {}).get('eligible', False)]),
                'high_potential_properties': len([p for p in properties if p.get('development_potential', {}).get('overall_score', 0) > 70])
            }
        
        # Generate export file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if export_format == 'csv':
            import pandas as pd
            
            # Flatten nested data for CSV
            flattened_properties = []
            for prop in properties:
                flat_prop = {
                    'parcel_id': prop.get('parcel_id'),
                    'address': prop.get('address'),
                    'assessed_value': prop.get('assessed_value'),
                    'property_type': prop.get('property_type'),
                    'zoning': prop.get('zoning'),
                    'status': prop.get('status'),
                    'neighborhood': prop.get('neighborhood'),
                    'eligible': prop.get('acquisition_eligibility', {}).get('eligible', False),
                    'eligibility_grade': prop.get('acquisition_eligibility', {}).get('grade', ''),
                    'potential_score': prop.get('development_potential', {}).get('overall_score', 0),
                    'market_potential': prop.get('development_potential', {}).get('market_potential', ''),
                    'min_investment': prop.get('development_potential', {}).get('estimated_investment_range', {}).get('min', 0),
                    'max_investment': prop.get('development_potential', {}).get('estimated_investment_range', {}).get('max', 0)
                }
                flattened_properties.append(flat_prop)
            
            df = pd.DataFrame(flattened_properties)
            filename = f"surplus_properties_export_{timestamp}.csv"
            df.to_csv(filename, index=False)
            
        else:  # JSON format
            filename = f"surplus_properties_export_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
        
        return jsonify({
            "success": True,
            "export_file": filename,
            "properties_exported": len(properties),
            "format": export_format,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error exporting surplus properties: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/report', methods=['POST'])
def generate_surplus_report():
    """Generate comprehensive acquisition report"""
    try:
        data = request.json
        property_ids = data.get('property_ids', [])
        report_type = data.get('report_type', 'acquisition')
        
        import glob
        
        # Get surplus properties data
        surplus_files = glob.glob('*surplus_properties*.json')
        
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            all_properties = json.load(f)
        
        # Filter properties for report
        if property_ids:
            properties = [p for p in all_properties if p.get('parcel_id') in property_ids]
        else:
            # Use top 10 high-potential properties
            properties = sorted(all_properties, 
                              key=lambda x: x.get('development_potential', {}).get('overall_score', 0), 
                              reverse=True)[:10]
        
        # Generate report
        report = {
            'report_info': {
                'generated_at': datetime.utcnow().isoformat() + "Z",
                'report_type': report_type,
                'properties_count': len(properties),
                'total_assessed_value': sum(p.get('assessed_value', 0) for p in properties),
                'source_file': latest_file
            },
            'executive_summary': {
                'key_findings': [],
                'recommendations': [],
                'investment_summary': {}
            },
            'property_details': [],
            'market_analysis': {},
            'next_steps': []
        }
        
        # Analyze properties for report
        eligible_count = 0
        high_potential_count = 0
        total_investment_range = {'min': 0, 'max': 0}
        
        for prop in properties:
            eligibility = prop.get('acquisition_eligibility', {})
            potential = prop.get('development_potential', {})
            
            if eligibility.get('eligible', False):
                eligible_count += 1
            
            if potential.get('overall_score', 0) > 70:
                high_potential_count += 1
            
            investment_range = potential.get('estimated_investment_range', {})
            total_investment_range['min'] += investment_range.get('min', 0)
            total_investment_range['max'] += investment_range.get('max', 0)
            
            # Add property detail
            report['property_details'].append({
                'parcel_id': prop.get('parcel_id'),
                'address': prop.get('address'),
                'assessed_value': prop.get('assessed_value'),
                'property_type': prop.get('property_type'),
                'zoning': prop.get('zoning'),
                'eligibility': {
                    'eligible': eligibility.get('eligible', False),
                    'grade': eligibility.get('grade', ''),
                    'score': eligibility.get('score', 0)
                },
                'development_potential': {
                    'score': potential.get('overall_score', 0),
                    'uses': potential.get('potential_uses', []),
                    'market_potential': potential.get('market_potential', ''),
                    'investment_range': investment_range
                }
            })
        
        # Generate executive summary
        report['executive_summary']['key_findings'] = [
            f"{eligible_count} of {len(properties)} properties meet basic acquisition eligibility",
            f"{high_potential_count} properties show high development potential",
            f"Total assessed value: ${sum(p.get('assessed_value', 0) for p in properties):,.2f}",
            f"Estimated investment range: ${total_investment_range['min']:,.2f} - ${total_investment_range['max']:,.2f}"
        ]
        
        report['executive_summary']['recommendations'] = [
            "Prioritize Grade A and B eligible properties",
            "Focus on properties with residential-friendly zoning",
            "Consider neighborhood revitalization impact",
            "Evaluate infrastructure requirements for each site"
        ]
        
        report['executive_summary']['investment_summary'] = {
            'total_properties': len(properties),
            'eligible_properties': eligible_count,
            'high_potential_properties': high_potential_count,
            'estimated_total_investment': total_investment_range,
            'average_investment_per_property': {
                'min': total_investment_range['min'] / len(properties) if properties else 0,
                'max': total_investment_range['max'] / len(properties) if properties else 0
            }
        }
        
        # Generate next steps
        report['next_steps'] = [
            "Verify property status and availability",
            "Conduct site visits for top priority properties",
            "Review zoning regulations and restrictions",
            "Assess infrastructure and utility requirements",
            "Evaluate community impact and support",
            "Prepare acquisition applications and documentation"
        ]
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"surplus_properties_report_{timestamp}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return jsonify({
            "success": True,
            "report_file": report_filename,
            "summary": report['executive_summary'],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error generating surplus report: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/analytics/advanced', methods=['POST'])
def advanced_surplus_analytics():
    """Advanced analytics and cost-benefit calculator for surplus properties"""
    try:
        import glob
        
        # Get surplus properties data
        surplus_files = glob.glob('*surplus_properties*.json')
        
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            properties = json.load(f)
        
        data = request.json
        analysis_type = data.get('analysis_type', 'comprehensive')
        property_ids = data.get('property_ids', [])
        
        # Filter properties if specific IDs provided
        if property_ids:
            analysis_properties = [p for p in properties if p.get('parcel_id') in property_ids]
        else:
            analysis_properties = properties
        
        # Perform advanced analysis
        analytics = {
            'market_analysis': analyze_market_trends(analysis_properties),
            'cost_benefit_analysis': analyze_cost_benefits(analysis_properties),
            'neighborhood_impact': analyze_neighborhood_impact(analysis_properties),
            'development_feasibility': analyze_development_feasibility(analysis_properties),
            'investment_ranking': rank_investment_opportunities(analysis_properties),
            'risk_assessment': assess_investment_risks(analysis_properties)
        }
        
        return jsonify({
            "success": True,
            "analytics": analytics,
            "analysis_type": analysis_type,
            "properties_analyzed": len(analysis_properties),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error in advanced analytics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/analytics/market', methods=['POST'])
def market_trend_analysis():
    """Market trend analysis for surplus properties"""
    try:
        import glob
        
        surplus_files = glob.glob('*surplus_properties*.json')
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            properties = json.load(f)
        
        market_analysis = analyze_market_trends(properties)
        
        return jsonify({
            "success": True,
            "market_analysis": market_analysis,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error in market trend analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/analytics/cost-benefit', methods=['POST'])
def cost_benefit_calculator():
    """Cost-benefit calculator for specific properties"""
    try:
        data = request.json
        property_ids = data.get('property_ids', [])
        development_scenarios = data.get('development_scenarios', ['residential', 'commercial', 'mixed_use'])
        
        import glob
        
        surplus_files = glob.glob('*surplus_properties*.json')
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            all_properties = json.load(f)
        
        # Filter properties
        target_properties = [p for p in all_properties if p.get('parcel_id') in property_ids]
        
        cost_benefit_results = {}
        for property in target_properties:
            cost_benefit_results[property['parcel_id']] = calculate_property_cost_benefit(property, development_scenarios)
        
        return jsonify({
            "success": True,
            "cost_benefit_analysis": cost_benefit_results,
            "properties_analyzed": len(target_properties),
            "scenarios_evaluated": development_scenarios,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error in cost-benefit calculator: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/export/enhanced', methods=['POST'])
def enhanced_surplus_export():
    """Enhanced export with multiple formats and analytics"""
    try:
        import glob
        import csv
        from io import StringIO
        
        data = request.json
        export_format = data.get('format', 'json')
        include_analytics = data.get('include_analytics', False)
        property_ids = data.get('property_ids', [])
        
        # Get surplus properties data
        surplus_files = glob.glob('*surplus_properties*.json')
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            all_properties = json.load(f)
        
        # Filter properties if specific IDs provided
        if property_ids:
            export_properties = [p for p in all_properties if p.get('parcel_id') in property_ids]
        else:
            export_properties = all_properties
        
        # Generate analytics if requested
        analytics = None
        if include_analytics:
            analytics = {
                'market_analysis': analyze_market_trends(export_properties),
                'cost_benefit_analysis': analyze_cost_benefits(export_properties),
                'investment_ranking': rank_investment_opportunities(export_properties)[:10],  # Top 10
                'risk_assessment': assess_investment_risks(export_properties)
            }
        
        # Export based on format
        if export_format == 'json':
            export_data = {
                'properties': export_properties,
                'analytics': analytics,
                'export_metadata': {
                    'total_properties': len(export_properties),
                    'export_date': datetime.utcnow().isoformat() + "Z",
                    'includes_analytics': include_analytics,
                    'source_file': latest_file
                }
            }
            
            filename = f"surplus_properties_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        elif export_format == 'csv':
            # Create CSV with flattened data
            output = StringIO()
            writer = csv.writer(output)
            
            # Header row
            headers = [
                'parcel_id', 'address', 'assessed_value', 'property_type', 'zoning',
                'land_area', 'building_area', 'neighborhood', 'status',
                'opportunity_score', 'development_potential', 'market_potential',
                'eligible', 'eligibility_grade', 'risk_level'
            ]
            writer.writerow(headers)
            
            # Data rows
            for prop in export_properties:
                row = [
                    prop.get('parcel_id', ''),
                    prop.get('address', ''),
                    prop.get('assessed_value', 0),
                    prop.get('property_type', ''),
                    prop.get('zoning', ''),
                    prop.get('land_area', 0),
                    prop.get('building_area', 0),
                    prop.get('neighborhood', ''),
                    prop.get('status', ''),
                    prop.get('development_potential', {}).get('overall_score', 0),
                    prop.get('development_potential', {}).get('market_potential', ''),
                    prop.get('development_potential', {}).get('market_potential', ''),
                    prop.get('acquisition_eligibility', {}).get('eligible', False),
                    prop.get('acquisition_eligibility', {}).get('grade', ''),
                    'Medium'  # Default risk level
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            filename = f"surplus_properties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='') as f:
                f.write(csv_content)
        
        elif export_format == 'excel':
            # Create Excel-style CSV with multiple sheets (as separate files)
            base_filename = f"surplus_properties_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Main properties file
            properties_filename = f"{base_filename}_properties.csv"
            with open(properties_filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Parcel ID', 'Address', 'Value', 'Type', 'Zoning', 'Score', 'Eligible'])
                for prop in export_properties:
                    writer.writerow([
                        prop.get('parcel_id', ''),
                        prop.get('address', ''),
                        prop.get('assessed_value', 0),
                        prop.get('property_type', ''),
                        prop.get('zoning', ''),
                        prop.get('development_potential', {}).get('overall_score', 0),
                        prop.get('acquisition_eligibility', {}).get('eligible', False)
                    ])
            
            # Analytics file if requested
            if analytics:
                analytics_filename = f"{base_filename}_analytics.csv"
                with open(analytics_filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Market summary
                    market = analytics.get('market_analysis', {}).get('market_summary', {})
                    writer.writerow(['Market Summary'])
                    writer.writerow(['Total Properties', market.get('total_properties', 0)])
                    writer.writerow(['Average Value', market.get('avg_assessed_value', 0)])
                    writer.writerow([])
                    
                    # Top opportunities
                    writer.writerow(['Top Investment Opportunities'])
                    writer.writerow(['Rank', 'Parcel ID', 'Address', 'Investment Score'])
                    for opp in analytics.get('investment_ranking', [])[:10]:
                        writer.writerow([
                            opp.get('rank', 0),
                            opp.get('parcel_id', ''),
                            opp.get('address', ''),
                            opp.get('investment_score', 0)
                        ])
            
            filename = properties_filename
        
        return jsonify({
            "success": True,
            "export_file": filename,
            "format": export_format,
            "properties_exported": len(export_properties),
            "includes_analytics": include_analytics,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error in enhanced export: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/surplus/report/acquisition-comprehensive', methods=['POST'])
def comprehensive_acquisition_report():
    """Generate comprehensive acquisition report with detailed analysis"""
    try:
        import glob
        
        data = request.json
        property_ids = data.get('property_ids', [])
        report_type = data.get('report_type', 'comprehensive')
        
        # Get surplus properties data
        surplus_files = glob.glob('*surplus_properties*.json')
        if not surplus_files:
            return jsonify({"error": "No surplus properties data found"}), 404
        
        latest_file = max(surplus_files, key=os.path.getmtime)
        with open(latest_file, 'r') as f:
            all_properties = json.load(f)
        
        # Filter properties if specific IDs provided
        if property_ids:
            report_properties = [p for p in all_properties if p.get('parcel_id') in property_ids]
        else:
            report_properties = all_properties
        
        # Generate comprehensive report
        report = {
            'executive_summary': generate_executive_summary(report_properties),
            'market_analysis': analyze_market_trends(report_properties),
            'investment_opportunities': rank_investment_opportunities(report_properties)[:20],
            'risk_assessment': assess_investment_risks(report_properties),
            'cost_benefit_analysis': analyze_cost_benefits(report_properties),
            'neighborhood_impact': analyze_neighborhood_impact(report_properties),
            'development_feasibility': analyze_development_feasibility(report_properties),
            'acquisition_strategy': generate_acquisition_strategy(report_properties),
            'implementation_timeline': generate_implementation_timeline(report_properties),
            'financial_projections': generate_financial_projections(report_properties)
        }
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"surplus_acquisition_report_{timestamp}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return jsonify({
            "success": True,
            "report_file": report_filename,
            "report_type": report_type,
            "properties_analyzed": len(report_properties),
            "summary": report['executive_summary'],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error generating comprehensive report: {e}")
        return jsonify({"error": str(e)}), 500

def generate_executive_summary(properties):
    """Generate executive summary for acquisition report"""
    if not properties:
        return {"error": "No properties to analyze"}
    
    total_properties = len(properties)
    total_value = sum(p.get('assessed_value', 0) for p in properties)
    avg_value = total_value / total_properties if total_properties > 0 else 0
    
    high_opportunity = len([p for p in properties 
                          if p.get('development_potential', {}).get('overall_score', 0) > 80])
    
    eligible_properties = len([p for p in properties 
                             if p.get('acquisition_eligibility', {}).get('eligible', False)])
    
    # Calculate potential ROI
    total_potential_value = sum(
        p.get('assessed_value', 0) * 1.5 for p in properties 
        if p.get('development_potential', {}).get('overall_score', 0) > 80
    )
    potential_roi = ((total_potential_value - total_value) / total_value * 100) if total_value > 0 else 0
    
    return {
        'overview': {
            'total_properties': total_properties,
            'total_assessed_value': total_value,
            'average_property_value': avg_value,
            'high_opportunity_properties': high_opportunity,
            'eligible_for_acquisition': eligible_properties
        },
        'key_metrics': {
            'potential_roi_percentage': potential_roi,
            'opportunity_rate': (high_opportunity / total_properties * 100) if total_properties > 0 else 0,
            'eligibility_rate': (eligible_properties / total_properties * 100) if total_properties > 0 else 0,
            'estimated_development_timeline': '18-24 months'
        },
        'recommendations': [
            f'Prioritize acquisition of {high_opportunity} high-opportunity properties',
            f'Focus on {eligible_properties} immediately eligible properties',
            'Develop phased acquisition strategy based on opportunity scores',
            'Establish partnerships for development financing',
            'Engage with city planning officials early in process'
        ],
        'next_steps': [
            'Conduct detailed due diligence on top 10 properties',
            'Secure financing commitments for acquisition phase',
            'Engage legal counsel for acquisition procedures',
            'Establish development timeline and milestones',
            'Begin community outreach and stakeholder engagement'
        ]
    }

def generate_acquisition_strategy(properties):
    """Generate acquisition strategy recommendations"""
    if not properties:
        return {}
    
    # Categorize properties by priority
    high_priority = []
    medium_priority = []
    low_priority = []
    
    for prop in properties:
        score = prop.get('development_potential', {}).get('overall_score', 0)
        eligible = prop.get('acquisition_eligibility', {}).get('eligible', False)
        
        if score > 80 and eligible:
            high_priority.append(prop)
        elif score > 60:
            medium_priority.append(prop)
        else:
            low_priority.append(prop)
    
    strategy = {
        'acquisition_phases': {
            'phase_1': {
                'description': 'Immediate acquisition (0-6 months)',
                'properties': len(high_priority),
                'estimated_investment': sum(p.get('assessed_value', 0) for p in high_priority),
                'criteria': 'High opportunity score and acquisition eligible',
                'actions': [
                    'Execute purchase agreements',
                    'Complete due diligence',
                    'Secure financing',
                    'Begin development planning'
                ]
            },
            'phase_2': {
                'description': 'Strategic acquisition (6-18 months)',
                'properties': len(medium_priority),
                'estimated_investment': sum(p.get('assessed_value', 0) for p in medium_priority),
                'criteria': 'Moderate opportunity scores',
                'actions': [
                    'Market analysis and validation',
                    'Zoning and feasibility studies',
                    'Partnership development',
                    'Community engagement'
                ]
            },
            'phase_3': {
                'description': 'Opportunistic acquisition (18-36 months)',
                'properties': len(low_priority),
                'estimated_investment': sum(p.get('assessed_value', 0) for p in low_priority),
                'criteria': 'Lower priority or higher risk properties',
                'actions': [
                    'Monitor market conditions',
                    'Evaluate development potential',
                    'Consider alternative uses',
                    'Strategic land banking'
                ]
            }
        },
        'financing_strategy': {
            'capital_requirements': {
                'total_acquisition_cost': sum(p.get('assessed_value', 0) for p in properties),
                'development_costs': sum(p.get('assessed_value', 0) * 0.4 for p in properties),
                'contingency_fund': sum(p.get('assessed_value', 0) * 0.1 for p in properties),
                'total_capital_needed': sum(p.get('assessed_value', 0) * 1.5 for p in properties)
            },
            'funding_sources': [
                'Municipal bonds and tax increment financing',
                'Public-private partnerships',
                'Community development financial institutions',
                'Private equity and real estate investment trusts',
                'Federal and state grant programs'
            ]
        },
        'risk_mitigation': {
            'primary_risks': [
                'Acquisition eligibility complications',
                'Environmental remediation requirements',
                'Market demand fluctuations',
                'Financing availability',
                'Community opposition'
            ],
            'mitigation_strategies': [
                'Early engagement with city officials',
            'Comprehensive environmental assessments',
            'Market validation studies',
            'Diversified funding sources',
            'Proactive community outreach'
            ]
        }
    }
    
    return strategy

def generate_implementation_timeline(properties):
    """Generate implementation timeline for property acquisition and development"""
    if not properties:
        return {}
    
    timeline = {
        'phase_1_preparation': {
            'duration': '3 months',
            'start_date': 'Month 1',
            'key_activities': [
                'Finalize acquisition strategy',
                'Secure initial financing commitments',
                'Establish project team and governance',
                'Engage legal and financial advisors',
                'Begin due diligence processes'
            ],
            'deliverables': [
                'Acquisition strategy document',
                'Financing plan and commitments',
                'Project governance structure',
                'Legal framework for acquisitions'
            ]
        },
        'phase_2_acquisition': {
            'duration': '12 months',
            'start_date': 'Month 4',
            'key_activities': [
                'Execute purchase agreements for priority properties',
                'Complete due diligence and title searches',
                'Secure zoning approvals and variances',
                'Obtain necessary permits and clearances',
                'Finalize development partnerships'
            ],
            'deliverables': [
                'Acquired properties portfolio',
                'Development permits and approvals',
                'Partnership agreements',
                'Construction-ready sites'
            ]
        },
        'phase_3_development': {
            'duration': '18 months',
            'start_date': 'Month 16',
            'key_activities': [
                'Site preparation and infrastructure',
                'Construction and development activities',
                'Marketing and leasing programs',
                'Property management setup',
                'Community integration programs'
            ],
            'deliverables': [
                'Completed development projects',
                'Occupied properties',
                'Revenue-generating assets',
                'Community benefits realized'
            ]
        },
        'phase_4_optimization': {
            'duration': 'Ongoing',
            'start_date': 'Month 34',
            'key_activities': [
                'Property performance monitoring',
                'Portfolio optimization',
                'Additional acquisition opportunities',
                'Community impact assessment',
                'Strategic planning for expansion'
            ],
            'deliverables': [
                'Performance dashboards and reports',
                'Optimized property portfolio',
                'Expansion pipeline',
                'Community impact reports',
                'Strategic growth plan'
            ]
        }
    }
    
    return timeline

def generate_financial_projections(properties):
    """Generate financial projections for the acquisition and development program"""
    if not properties:
        return {}
    
    # Calculate base financial metrics
    total_acquisition_cost = sum(p.get('assessed_value', 0) for p in properties)
    total_development_cost = total_acquisition_cost * 0.4  # 40% development cost
    total_soft_costs = total_development_cost * 0.2  # 20% soft costs
    total_investment = total_acquisition_cost + total_development_cost + total_soft_costs
    
    # Project revenue based on development potential
    high_potential_properties = [p for p in properties 
                               if p.get('development_potential', {}).get('overall_score', 0) > 80]
    
    projected_revenue = 0
    for prop in high_potential_properties:
        assessed_value = prop.get('assessed_value', 0)
        projected_revenue += assessed_value * 2.5  # 2.5x return on high-potential properties
    
    # Calculate returns
    gross_profit = projected_revenue - total_investment
    roi_percentage = (gross_profit / total_investment * 100) if total_investment > 0 else 0
    
    projections = {
        'investment_summary': {
            'total_acquisition_cost': total_acquisition_cost,
            'total_development_cost': total_development_cost,
            'total_soft_costs': total_soft_costs,
            'total_investment_required': total_investment,
            'properties_in_portfolio': len(properties)
        },
        'revenue_projections': {
            'year_1': projected_revenue * 0.3,  # 30% in first year
            'year_2': projected_revenue * 0.5,  # 50% in second year
            'year_3': projected_revenue * 0.7,  # 70% in third year
            'year_5': projected_revenue,  # Full realization by year 5
            'total_projected_revenue': projected_revenue
        },
        'financial_metrics': {
            'gross_profit': gross_profit,
            'roi_percentage': roi_percentage,
            'payback_period_years': total_investment / (projected_revenue / 5) if projected_revenue > 0 else 999,
            'net_present_value': gross_profit * 0.85,  # Discounted cash flow
            'internal_rate_of_return': roi_percentage * 0.8  # Conservative IRR estimate
        },
        'cash_flow_analysis': {
            'initial_investment': -total_investment,
            'year_1_cash_flow': (projected_revenue * 0.3) - (total_investment * 0.1),
            'year_2_cash_flow': (projected_revenue * 0.5) - (total_investment * 0.05),
            'year_3_cash_flow': (projected_revenue * 0.7) - (total_investment * 0.02),
            'year_4_cash_flow': (projected_revenue * 0.9),
            'year_5_cash_flow': projected_revenue
        },
        'sensitivity_analysis': {
            'best_case': {
                'revenue_multiplier': 3.0,
                'roi_percentage': roi_percentage * 1.5,
                'assumptions': 'Favorable market conditions, cost efficiencies'
            },
            'base_case': {
                'revenue_multiplier': 2.5,
                'roi_percentage': roi_percentage,
                'assumptions': 'Current market conditions, standard costs'
            },
            'worst_case': {
                'revenue_multiplier': 1.8,
                'roi_percentage': roi_percentage * 0.6,
                'assumptions': 'Challenging market conditions, cost overruns'
            }
        }
    }
    
    return projections

# ---------------------------------------------------------------------------
# Legacy Montgomery Data API Routes (for compatibility)
# ---------------------------------------------------------------------------

@app.route('/api/montgomery/analyze-legacy', methods=['POST'])
def analyze_montgomery_data_legacy():
    """Analyze Montgomery County open data (legacy endpoint)"""
    try:
        # Import and run the Montgomery data analyzer
        from montgomery_data_analysis import MontgomeryDataAnalyzer
        
        analyzer = MontgomeryDataAnalyzer()
        permits_analysis, violations_analysis = analyzer.generate_report()
        
        # Convert numpy/pandas types to native Python types for JSON serialization
        def convert_types(obj):
            if hasattr(obj, 'item'):  # numpy types
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v) for v in obj]
            else:
                return obj
        
        permits_analysis = convert_types(permits_analysis) if permits_analysis else {}
        violations_analysis = convert_types(violations_analysis) if violations_analysis else {}
        
        return jsonify({
            "permits": permits_analysis,
            "violations": violations_analysis,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        log.error(f"Error analyzing Montgomery data: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Advanced Analytics Functions for Surplus Properties
# ---------------------------------------------------------------------------

def analyze_market_trends(properties):
    """Analyze market trends for surplus properties"""
    if not properties:
        return {}
    
    # Value distribution analysis
    values = [p.get('assessed_value', 0) for p in properties if p.get('assessed_value')]
    if not values:
        return {"error": "No property values available"}
    
    # Calculate market metrics
    avg_value = sum(values) / len(values)
    median_value = sorted(values)[len(values) // 2]
    
    # Property type distribution
    type_distribution = {}
    for prop in properties:
        prop_type = prop.get('property_type', 'Unknown')
        type_distribution[prop_type] = type_distribution.get(prop_type, 0) + 1
    
    # Neighborhood analysis
    neighborhood_analysis = {}
    for prop in properties:
        neighborhood = prop.get('neighborhood', 'Unknown')
        if neighborhood not in neighborhood_analysis:
            neighborhood_analysis[neighborhood] = {
                'count': 0,
                'total_value': 0,
                'avg_value': 0,
                'high_potential': 0
            }
        
        neighborhood_analysis[neighborhood]['count'] += 1
        neighborhood_analysis[neighborhood]['total_value'] += prop.get('assessed_value', 0)
        
        if prop.get('development_potential', {}).get('overall_score', 0) > 80:
            neighborhood_analysis[neighborhood]['high_potential'] += 1
    
    # Calculate averages for each neighborhood
    for neighborhood in neighborhood_analysis:
        if neighborhood_analysis[neighborhood]['count'] > 0:
            neighborhood_analysis[neighborhood]['avg_value'] = (
                neighborhood_analysis[neighborhood]['total_value'] / 
                neighborhood_analysis[neighborhood]['count']
            )
    
    return {
        'market_summary': {
            'total_properties': len(properties),
            'avg_assessed_value': avg_value,
            'median_assessed_value': median_value,
            'value_range': {'min': min(values), 'max': max(values)}
        },
        'property_type_distribution': type_distribution,
        'neighborhood_analysis': neighborhood_analysis,
        'market_indicators': {
            'high_value_properties': len([v for v in values if v > avg_value * 1.5]),
            'low_value_properties': len([v for v in values if v < avg_value * 0.5]),
            'value_volatility': (max(values) - min(values)) / avg_value if avg_value > 0 else 0
        }
    }

def analyze_cost_benefits(properties):
    """Cost-benefit analysis for surplus properties"""
    cost_benefit_results = []
    
    for prop in properties:
        assessed_value = prop.get('assessed_value', 0)
        development_potential = prop.get('development_potential', {})
        eligibility = prop.get('acquisition_eligibility', {})
        
        # Estimate costs
        acquisition_cost = assessed_value * 1.1  # 10% acquisition premium
        development_cost = assessed_value * 0.3  # 30% of assessed value for development
        holding_cost = assessed_value * 0.05  # 5% annual holding cost
        total_cost = acquisition_cost + development_cost + holding_cost
        
        # Estimate benefits
        market_value_multiplier = 1.5 if development_potential.get('overall_score', 0) > 80 else 1.3
        projected_value = assessed_value * market_value_multiplier
        gross_benefit = projected_value - assessed_value
        
        # Calculate ROI
        roi = ((gross_benefit - total_cost) / total_cost) * 100 if total_cost > 0 else 0
        
        # Risk adjustment
        risk_factor = 1.0
        if not eligibility.get('eligible', False):
            risk_factor *= 0.7  # Higher risk for ineligible properties
        
        adjusted_roi = roi * risk_factor
        
        cost_benefit_results.append({
            'parcel_id': prop.get('parcel_id'),
            'address': prop.get('address'),
            'cost_analysis': {
                'acquisition_cost': acquisition_cost,
                'development_cost': development_cost,
                'holding_cost': holding_cost,
                'total_cost': total_cost
            },
            'benefit_analysis': {
                'projected_market_value': projected_value,
                'gross_benefit': gross_benefit,
                'net_benefit': gross_benefit - total_cost
            },
            'roi_metrics': {
                'raw_roi': roi,
                'adjusted_roi': adjusted_roi,
                'payback_period_years': total_cost / (gross_benefit / 5) if gross_benefit > 0 else 999,
                'risk_adjusted_score': adjusted_roi * (development_potential.get('overall_score', 0) / 100)
            }
        })
    
    return cost_benefit_results

def analyze_neighborhood_impact(properties):
    """Analyze neighborhood impact of surplus property development"""
    neighborhood_impacts = {}
    
    for prop in properties:
        neighborhood = prop.get('neighborhood', 'Unknown')
        if neighborhood not in neighborhood_impacts:
            neighborhood_impacts[neighborhood] = {
                'properties_count': 0,
                'total_investment_needed': 0,
                'potential_new_units': 0,
                'revitalization_score': 0,
                'economic_impact': {
                    'jobs_created': 0,
                    'tax_revenue_increase': 0,
                    'property_value_increase': 0
                },
                'social_impact': {
                    'housing_units_added': 0,
                    'commercial_spaces_added': 0,
                    'community_benefits': []
                }
            }
        
        # Update neighborhood metrics
        neighborhood_impacts[neighborhood]['properties_count'] += 1
        
        # Estimate investment needs
        investment = prop.get('assessed_value', 0) * 0.4  # 40% of assessed value
        neighborhood_impacts[neighborhood]['total_investment_needed'] += investment
        
        # Estimate potential units based on property type
        prop_type = prop.get('property_type', '').lower()
        land_area = prop.get('land_area', 0)
        
        if 'single family' in prop_type and land_area > 5000:
            units = 1
        elif 'multi family' in prop_type or land_area > 10000:
            units = int(land_area / 2000)  # 1 unit per 2000 sq ft
        elif 'commercial' in prop_type:
            units = 1  # Commercial space
        else:
            units = 0
        
        neighborhood_impacts[neighborhood]['potential_new_units'] += units
        
        # Economic impact estimates
        if units > 0:
            jobs_per_unit = 2.5  # Construction jobs
            neighborhood_impacts[neighborhood]['economic_impact']['jobs_created'] += jobs_per_unit * units
            
            # Tax revenue estimate (2% of property value annually)
            tax_revenue = prop.get('assessed_value', 0) * 0.02
            neighborhood_impacts[neighborhood]['economic_impact']['tax_revenue_increase'] += tax_revenue
        
        # Social impact
        if 'residential' in prop_type:
            neighborhood_impacts[neighborhood]['social_impact']['housing_units_added'] += units
        elif 'commercial' in prop_type:
            neighborhood_impacts[neighborhood]['social_impact']['commercial_spaces_added'] += 1
        
        # Revitalization score based on opportunity potential
        potential_score = prop.get('development_potential', {}).get('overall_score', 0)
        neighborhood_impacts[neighborhood]['revitalization_score'] += potential_score
    
    # Calculate average revitalization score
    for neighborhood in neighborhood_impacts:
        if neighborhood_impacts[neighborhood]['properties_count'] > 0:
            neighborhood_impacts[neighborhood]['revitalization_score'] /= neighborhood_impacts[neighborhood]['properties_count']
    
    return neighborhood_impacts

def analyze_development_feasibility(properties):
    """Analyze development feasibility for surplus properties"""
    feasibility_results = []
    
    for prop in properties:
        feasibility_score = 100  # Start with perfect score
        feasibility_factors = []
        
        # Zoning analysis
        zoning = prop.get('zoning', '').upper()
        if not zoning:
            feasibility_score -= 20
            feasibility_factors.append('Unknown zoning - high risk')
        elif 'R-' in zoning or 'C-' in zoning:
            feasibility_factors.append('Clear zoning designation')
        else:
            feasibility_score -= 10
            feasibility_factors.append('Complex zoning requirements')
        
        # Physical constraints
        land_area = prop.get('land_area', 0)
        if land_area < 3000:
            feasibility_score -= 15
            feasibility_factors.append('Small lot size limits development')
        
        building_area = prop.get('building_area', 0)
        if building_area > 0:
            feasibility_score -= 10
            feasibility_factors.append('Existing structure requires demolition')
        
        # Location factors
        neighborhood = prop.get('neighborhood', '').lower()
        if 'downtown' in neighborhood:
            feasibility_score += 10
            feasibility_factors.append('Prime downtown location')
        
        # Environmental constraints
        if prop.get('development_potential', {}).get('risk_factors', []):
            risks = prop.get('development_potential', {}).get('risk_factors', [])
            for risk in risks:
                if 'environmental' in risk.lower():
                    feasibility_score -= 15
                    feasibility_factors.append('Environmental constraints present')
        
        # Market demand
        potential_score = prop.get('development_potential', {}).get('overall_score', 0)
        if potential_score > 80:
            feasibility_score += 10
            feasibility_factors.append('High market demand')
        elif potential_score < 40:
            feasibility_score -= 20
            feasibility_factors.append('Low market demand')
        
        # Determine feasibility category
        if feasibility_score >= 80:
            feasibility_category = 'High'
        elif feasibility_score >= 60:
            feasibility_category = 'Medium'
        elif feasibility_score >= 40:
            feasibility_category = 'Low'
        else:
            feasibility_category = 'Very Low'
        
        feasibility_results.append({
            'parcel_id': prop.get('parcel_id'),
            'address': prop.get('address'),
            'feasibility_score': max(0, feasibility_score),
            'feasibility_category': feasibility_category,
            'feasibility_factors': feasibility_factors,
            'development_recommendations': generate_development_recommendations(prop, feasibility_score)
        })
    
    return feasibility_results

def generate_development_recommendations(property, feasibility_score):
    """Generate development recommendations based on feasibility analysis"""
    recommendations = []
    
    prop_type = property.get('property_type', '').lower()
    land_area = property.get('land_area', 0)
    zoning = property.get('zoning', '').upper()
    
    if feasibility_score >= 80:
        if 'R-' in zoning and land_area > 5000:
            recommendations.append('Proceed with residential development')
        if 'C-' in zoning:
            recommendations.append('Consider commercial redevelopment')
        if land_area > 10000:
            recommendations.append('Mixed-use development viable')
    elif feasibility_score >= 60:
        recommendations.append('Conduct detailed feasibility study')
        recommendations.append('Explore zoning variances if needed')
    else:
        recommendations.append('Significant challenges identified')
        recommendations.append('Consider alternative uses or partnership')
    
    # Specific recommendations based on property characteristics
    if 'vacant land' in prop_type and land_area > 10000:
        recommendations.append('Large-scale development opportunity')
    
    if property.get('development_potential', {}).get('overall_score', 0) > 80:
        recommendations.append('High market potential - expedite development')
    
    return recommendations

def rank_investment_opportunities(properties):
    """Rank investment opportunities using multiple criteria"""
    ranked_properties = []
    
    for prop in properties:
        # Calculate investment score
        investment_score = 0
        
        # Value factor (lower is better)
        assessed_value = prop.get('assessed_value', 0)
        if assessed_value > 0 and assessed_value < 50000:
            investment_score += 25
        elif assessed_value < 100000:
            investment_score += 15
        
        # Development potential
        potential_score = prop.get('development_potential', {}).get('overall_score', 0)
        investment_score += (potential_score / 100) * 30
        
        # Eligibility
        if prop.get('acquisition_eligibility', {}).get('eligible', False):
            investment_score += 20
        
        # Location bonus
        neighborhood = prop.get('neighborhood', '').lower()
        if 'downtown' in neighborhood:
            investment_score += 15
        
        # Zoning flexibility
        zoning = prop.get('zoning', '').upper()
        if 'R-' in zoning or 'C-' in zoning or 'MIXED' in zoning:
            investment_score += 10
        
        ranked_properties.append({
            'parcel_id': prop.get('parcel_id'),
            'address': prop.get('address'),
            'investment_score': investment_score,
            'rank': 0,  # Will be set after sorting
            'key_factors': {
                'value_score': 25 if assessed_value < 50000 else (15 if assessed_value < 100000 else 0),
                'development_potential': (potential_score / 100) * 30,
                'eligibility_bonus': 20 if prop.get('acquisition_eligibility', {}).get('eligible', False) else 0,
                'location_bonus': 15 if 'downtown' in neighborhood else 0,
                'zoning_bonus': 10 if ('R-' in zoning or 'C-' in zoning or 'MIXED' in zoning) else 0
            }
        })
    
    # Sort by investment score and assign ranks
    ranked_properties.sort(key=lambda x: x['investment_score'], reverse=True)
    for i, prop in enumerate(ranked_properties):
        prop['rank'] = i + 1
    
    return ranked_properties

def assess_investment_risks(properties):
    """Assess investment risks for surplus properties"""
    risk_assessments = []
    
    for prop in properties:
        risk_factors = []
        risk_level = 'Low'
        risk_score = 0  # Higher score = higher risk
        
        # Financial risk
        assessed_value = prop.get('assessed_value', 0)
        if assessed_value > 200000:
            risk_score += 20
            risk_factors.append('High acquisition cost')
        
        # Regulatory risk
        eligibility = prop.get('acquisition_eligibility', {})
        if not eligibility.get('eligible', False):
            risk_score += 30
            risk_factors.append('Acquisition eligibility issues')
        
        # Market risk
        potential = prop.get('development_potential', {})
        if potential.get('overall_score', 0) < 40:
            risk_score += 25
            risk_factors.append('Low market potential')
        
        # Environmental risk
        if 'environmental_constraints' in potential.get('risk_factors', []):
            risk_score += 20
            risk_factors.append('Environmental constraints')
        
        # Location risk
        neighborhood = prop.get('neighborhood', '').lower()
        if neighborhood == 'unknown':
            risk_score += 15
            risk_factors.append('Unknown neighborhood characteristics')
        
        # Physical risk
        building_area = prop.get('building_area', 0)
        if building_area > 0:
            risk_score += 10
            risk_factors.append('Existing structure complications')
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = 'High'
        elif risk_score >= 40:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        # Generate mitigation strategies
        mitigation_strategies = []
        if 'High acquisition cost' in risk_factors:
            mitigation_strategies.append('Seek financing partnerships')
        if 'Acquisition eligibility issues' in risk_factors:
            mitigation_strategies.append('Address eligibility requirements early')
        if 'Low market potential' in risk_factors:
            mitigation_strategies.append('Consider alternative development scenarios')
        if 'Environmental constraints' in risk_factors:
            mitigation_strategies.append('Conduct environmental assessment')
        
        risk_assessments.append({
            'parcel_id': prop.get('parcel_id'),
            'address': prop.get('address'),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'mitigation_strategies': mitigation_strategies,
            'recommended_due_diligence': generate_due_diligence_checklist(risk_factors)
        })
    
    return risk_assessments

def generate_due_diligence_checklist(risk_factors):
    """Generate due diligence checklist based on risk factors"""
    checklist = [
        'Verify property title and ownership',
        'Conduct property survey and boundary verification',
        'Review zoning regulations and restrictions',
        'Assess environmental conditions and constraints',
        'Evaluate infrastructure availability and costs',
        'Analyze market conditions and demand',
        'Review acquisition eligibility requirements'
    ]
    
    # Add specific items based on identified risks
    if 'High acquisition cost' in risk_factors:
        checklist.append('Secure financing and investment partners')
    
    if 'Acquisition eligibility issues' in risk_factors:
        checklist.append('Consult with city planning department')
        checklist.append('Review acquisition procedures and requirements')
    
    if 'Environmental constraints' in risk_factors:
        checklist.append('Phase I environmental site assessment')
        checklist.append('Review environmental regulations and permits')
    
    if 'Existing structure complications' in risk_factors:
        checklist.append('Structural inspection and assessment')
        checklist.append('Demolition cost analysis')
    
    return checklist

def calculate_property_cost_benefit(property, development_scenarios):
    """Calculate cost-benefit analysis for specific development scenarios"""
    scenario_results = {}
    assessed_value = property.get('assessed_value', 0)
    land_area = property.get('land_area', 0)
    
    for scenario in development_scenarios:
        # Scenario-specific assumptions
        if scenario == 'residential':
            if land_area > 5000:
                units = min(int(land_area / 4000), 4)  # Max 4 units
                unit_value = 150000  # Average residential unit value
                development_multiplier = 0.4  # 40% of assessed value for development
            else:
                units = 1
                unit_value = 120000
                development_multiplier = 0.3
        
        elif scenario == 'commercial':
            units = 1
            unit_value = assessed_value * 2  # Commercial typically 2x value
            development_multiplier = 0.5
        
        elif scenario == 'mixed_use':
            if land_area > 10000:
                units = 2  # 2 mixed-use units
                unit_value = 200000
                development_multiplier = 0.6
            else:
                units = 1
                unit_value = 175000
                development_multiplier = 0.45
        
        else:
            continue
        
        # Calculate costs
        acquisition_cost = assessed_value * 1.1
        development_cost = assessed_value * development_multiplier
        soft_costs = development_cost * 0.2  # Architecture, permits, etc.
        total_costs = acquisition_cost + development_cost + soft_costs
        
        # Calculate benefits
        gross_revenue = units * unit_value
        operating_costs = gross_revenue * 0.3  # 30% operating costs
        net_revenue = gross_revenue - operating_costs
        
        # Calculate ROI
        roi = ((net_revenue - total_costs) / total_costs) * 100 if total_costs > 0 else 0
        
        # Calculate payback period
        annual_cash_flow = (net_revenue - total_costs) / 10  # 10-year project life
        payback_period = total_costs / annual_cash_flow if annual_cash_flow > 0 else 999
        
        scenario_results[scenario] = {
            'development_summary': {
                'units': units,
                'unit_value': unit_value,
                'gross_revenue': gross_revenue,
                'net_revenue': net_revenue
            },
            'cost_breakdown': {
                'acquisition_cost': acquisition_cost,
                'development_cost': development_cost,
                'soft_costs': soft_costs,
                'total_costs': total_costs
            },
            'financial_metrics': {
                'roi_percentage': roi,
                'payback_period_years': payback_period,
                'net_present_value': net_revenue - total_costs,
                'profit_margin': ((net_revenue - total_costs) / net_revenue) * 100 if net_revenue > 0 else 0
            },
            'feasibility_rating': 'High' if roi > 15 else ('Medium' if roi > 5 else 'Low')
        }
    
    return scenario_results

# ---------------------------------------------------------------------------
# Urban Investment AI API Routes
# ---------------------------------------------------------------------------

@app.route('/api/urban-investment/demographics', methods=['GET'])
def get_demographics():
    """Get demographic data for Montgomery districts"""
    try:
        import glob
        
        # Look for demographic data files
        demo_files = glob.glob('montgomery_demographics_*.json')
        
        if demo_files:
            # Load the most recent demographic data
            latest_file = max(demo_files, key=os.path.getmtime)
            with open(latest_file, 'r') as f:
                demographics = json.load(f)
            
            return jsonify({
                "success": True,
                "source_file": latest_file,
                "districts": len(demographics),
                "total_population": sum(d['total_population'] for d in demographics),
                "demographics": demographics,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        else:
            # Generate demo demographics if none exists
            from demo_demographics import save_demo_demographics
            demo_file = save_demo_demographics()
            
            with open(demo_file, 'r') as f:
                demographics = json.load(f)
            
            return jsonify({
                "success": True,
                "source_file": demo_file,
                "districts": len(demographics),
                "total_population": sum(d['total_population'] for d in demographics),
                "demographics": demographics,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "generated": True
            })
            
    except Exception as e:
        log.error(f"Error getting demographics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/urban-investment/analyze', methods=['POST'])
def analyze_urban_investment():
    """Generate comprehensive urban investment recommendations"""
    try:
        from urban_investment_ai import UrbanInvestmentAI
        
        # Get demographic data
        import glob
        demo_files = glob.glob('montgomery_demographics_*.json')
        if not demo_files:
            # Generate demo data first
            from demo_demographics import save_demo_demographics
            demo_file = save_demo_demographics()
            demo_files = [demo_file]
        
        with open(max(demo_files, key=os.path.getmtime), 'r') as f:
            demographic_data = json.load(f)
        
        # Get city data (use existing Montgomery data)
        city_data = {}
        city_files = glob.glob('montgomery_*_*.json')
        for file_type in ['building_permits', 'code_violations', 'vacant_properties', 'traffic_incidents']:
            matching_files = [f for f in city_files if file_type in f]
            if matching_files:
                latest_file = max(matching_files, key=os.path.getmtime)
                with open(latest_file, 'r') as f:
                    city_data[file_type] = json.load(f)
        
        # Get property data
        property_files = glob.glob('*_properties.json') or glob.glob('demo_properties.json')
        property_data = []
        if property_files:
            latest_file = max(property_files, key=os.path.getmtime)
            with open(latest_file, 'r') as f:
                property_data = json.load(f)
        
        # Generate recommendations
        ai_engine = UrbanInvestmentAI()
        recommendations = ai_engine.generate_investment_recommendations(
            demographic_data, city_data, property_data
        )
        
        return jsonify({
            "success": True,
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error in urban investment analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/urban-investment/partnerships', methods=['GET'])
def get_partnership_opportunities():
    """Get partnership opportunities for commercial development"""
    try:
        from urban_investment_ai import PartnershipOpportunityAnalyzer
        from demo_demographics import generate_montgomery_demographics
        
        # Get demographic data
        import glob
        demo_files = glob.glob('montgomery_demographics_*.json')
        if demo_files:
            with open(max(demo_files, key=os.path.getmtime), 'r') as f:
                demographic_data = json.load(f)
        else:
            demographic_data = generate_montgomery_demographics()
        
        # Get city data
        city_data = {}
        city_files = glob.glob('montgomery_*_*.json')
        for file_type in ['building_permits', 'code_violations', 'vacant_properties']:
            matching_files = [f for f in city_files if file_type in f]
            if matching_files:
                latest_file = max(matching_files, key=os.path.getmtime)
                with open(latest_file, 'r') as f:
                    city_data[file_type] = json.load(f)
        
        # Get property data
        property_files = glob.glob('*_properties.json') or glob.glob('demo_properties.json')
        property_data = []
        if property_files:
            latest_file = max(property_files, key=os.path.getmtime)
            with open(latest_file, 'r') as f:
                property_data = json.load(f)
        
        # Analyze partnerships
        analyzer = PartnershipOpportunityAnalyzer()
        opportunities = analyzer.identify_partnership_opportunities(
            demographic_data, city_data, property_data
        )
        
        return jsonify({
            "success": True,
            "total_opportunities": len(opportunities),
            "high_value_opportunities": len([o for o in opportunities if o.opportunity_score > 70]),
            "opportunities": [asdict(o) for o in opportunities],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error getting partnership opportunities: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/urban-investment/services', methods=['GET'])
def get_service_recommendations():
    """Get service type recommendations for commercial development"""
    try:
        from urban_investment_ai import ServiceRecommendationEngine
        from demo_demographics import generate_montgomery_demographics
        
        # Get demographic data
        import glob
        demo_files = glob.glob('montgomery_demographics_*.json')
        if demo_files:
            with open(max(demo_files, key=os.path.getmtime), 'r') as f:
                demographic_data = json.load(f)
        else:
            demographic_data = generate_montgomery_demographics()
        
        # Generate service recommendations
        engine = ServiceRecommendationEngine()
        recommendations = engine.recommend_services(demographic_data, [])
        
        return jsonify({
            "success": True,
            "total_recommendations": len(recommendations),
            "high_confidence_recommendations": len([s for s in recommendations if s.confidence_score > 70]),
            "recommendations": [asdict(s) for s in recommendations],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error getting service recommendations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/urban-investment/district/<district_id>', methods=['GET'])
def get_district_analysis(district_id):
    """Get detailed analysis for a specific district"""
    try:
        from urban_investment_ai import UrbanInvestmentAI
        
        # Get demographic data
        import glob
        demo_files = glob.glob('montgomery_demographics_*.json')
        if not demo_files:
            return jsonify({"error": "No demographic data available"}), 404
        
        with open(max(demo_files, key=os.path.getmtime), 'r') as f:
            demographic_data = json.load(f)
        
        # Find the specific district
        district_data = None
        for district in demographic_data:
            if district['district_id'] == district_id:
                district_data = district
                break
        
        if not district_data:
            return jsonify({"error": f"District {district_id} not found"}), 404
        
        # Generate district-specific analysis
        ai_engine = UrbanInvestmentAI()
        
        # Analyze just this district
        recommendations = ai_engine.generate_investment_recommendations(
            [district_data], {}, []
        )
        
        # Extract district-specific insights
        district_insights = {
            "district_info": district_data,
            "demographic_analysis": recommendations.get("demographic_analysis", {}),
            "trends": recommendations.get("demographic_trends", {}).get(district_id, {}),
            "opportunities": [o for o in recommendations.get("partnership_opportunities", {}).get("opportunities", []) 
                            if o.get("district_id") == district_id],
            "services": [s for s in recommendations.get("service_recommendations", {}).get("recommendations", []) 
                       if s.get("district_id") == district_id],
            "summary": recommendations.get("summary", {})
        }
        
        return jsonify({
            "success": True,
            "district_analysis": district_insights,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error getting district analysis: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/urban-investment/compare', methods=['POST'])
def compare_districts():
    """Compare multiple districts for investment potential"""
    try:
        data = request.json
        district_ids = data.get('district_ids', [])
        
        if len(district_ids) < 2:
            return jsonify({"error": "At least 2 districts required for comparison"}), 400
        
        # Get demographic data
        import glob
        demo_files = glob.glob('montgomery_demographics_*.json')
        if not demo_files:
            return jsonify({"error": "No demographic data available"}), 404
        
        with open(max(demo_files, key=os.path.getmtime), 'r') as f:
            demographic_data = json.load(f)
        
        # Filter for requested districts
        comparison_districts = [d for d in demographic_data if d['district_id'] in district_ids]
        
        if len(comparison_districts) != len(district_ids):
            return jsonify({"error": "One or more districts not found"}), 404
        
        # Generate comparison metrics
        comparison = {
            "districts_compared": len(comparison_districts),
            "comparison_metrics": {},
            "rankings": {}
        }
        
        # Calculate comparison metrics
        metrics = ['total_population', 'median_age', 'median_household_income', 'employment_rate', 'population_density']
        
        for metric in metrics:
            comparison["comparison_metrics"][metric] = {}
            scores = []
            
            for district in comparison_districts:
                value = district.get(metric, 0)
                comparison["comparison_metrics"][metric][district['district_id']] = value
                scores.append((district['district_id'], value))
            
            # Rank by metric
            if metric == 'median_age':
                # Lower median age = higher rank (youth-focused)
                scores.sort(key=lambda x: x[1])
            elif metric in ['median_household_income', 'employment_rate', 'population_density']:
                # Higher = better
                scores.sort(key=lambda x: x[1], reverse=True)
            else:
                # Higher population = better
                scores.sort(key=lambda x: x[1], reverse=True)
            
            comparison["rankings"][metric] = [d[0] for d in scores]
        
        # Calculate overall investment score
        investment_scores = {}
        for district in comparison_districts:
            score = 0
            
            # Population factor (20%)
            pop_score = district.get('total_population', 0) / 1000  # per 1000 people
            score += min(pop_score, 10) * 2
            
            # Income factor (25%)
            income_score = district.get('median_household_income', 0) / 50000  # per $50k
            score += min(income_score, 10) * 2.5
            
            # Employment factor (20%)
            employment_score = district.get('employment_rate', 0) * 10
            score += employment_score * 2
            
            # Density factor (15%)
            density_score = min(district.get('population_density', 0) / 1000, 10)
            score += density_score * 1.5
            
            # Age diversity factor (20%)
            age_groups = district.get('age_groups', {})
            youth_pct = sum(age_groups.get(age, 0) for age in ['0-4', '5-9', '10-14', '15-17', '18']) / district.get('total_population', 1) * 100
            senior_pct = sum(age_groups.get(age, 0) for age in ['55-60', '61-65', '66-70', '71-75', '76-80', '80+']) / district.get('total_population', 1) * 100
            age_diversity = min(youth_pct + senior_pct, 50)  # Max 50 points
            score += age_diversity * 0.4
            
            investment_scores[district['district_id']] = round(score, 2)
        
        # Sort by overall score
        ranked_districts = sorted(investment_scores.items(), key=lambda x: x[1], reverse=True)
        comparison["overall_ranking"] = ranked_districts
        comparison["investment_scores"] = investment_scores
        
        return jsonify({
            "success": True,
            "comparison": comparison,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        log.error(f"Error comparing districts: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
