"""
AI Learning Engine for Vacancy Watch
Machine learning models for pattern recognition, prediction, and adaptive scoring
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import logging

log = logging.getLogger(__name__)

@dataclass
class MLFeatures:
    """Feature set for ML models"""
    parcel_id: str
    address: str
    assessed_value: float
    city_vacant_flag: bool
    violation_count: int
    permit_count: int
    listing_price: Optional[float]
    days_on_market: Optional[int]
    price_to_assessed_ratio: Optional[float]
    neighborhood_vacancy_rate: float
    nearby_permit_activity: int
    historical_violation_trend: float
    time_since_last_permit: int
    property_age_years: Optional[int]
    zip_code: str
    # Zoning-related features
    zone_code: Optional[str] = None
    zone_description: Optional[str] = None
    land_use: Optional[str] = None
    minimum_lot_size: Optional[float] = None
    maximum_building_height: Optional[float] = None
    is_residential_zone: bool = False
    is_commercial_zone: bool = False
    is_mixed_use_zone: bool = False
    zone_density_score: float = 0.0  # R-1=1.0, R-2=2.0, R-3=3.0, B-1=2.5, B-2=3.5
    permitted_use_count: int = 0
    conditional_use_count: int = 0
    
@dataclass
class PredictionResult:
    """ML prediction result"""
    vacancy_probability: float
    risk_score: float
    confidence: float
    key_factors: List[str]
    anomaly_score: float
    predicted_time_to_vacancy: Optional[int]  # days

@dataclass
class SurplusFeatures:
    """Feature set for surplus properties opportunity scoring"""
    parcel_id: str
    address: str
    assessed_value: float
    property_type: str
    zoning: str
    land_area: float
    building_area: float
    year_built: Optional[int]
    status: str
    neighborhood: str
    coordinates: Optional[Dict[str, float]]
    # Location and accessibility features
    distance_to_downtown: float = 0.0  # miles
    distance_to_major_roads: float = 0.0  # miles
    walk_score: float = 0.0
    transit_accessibility: float = 0.0
    # Economic features
    median_income_neighborhood: float = 0.0
    property_value_trend: float = 0.0  # annual change %
    neighborhood_redevelopment_score: float = 0.0
    # Physical characteristics
    lot_coverage_ratio: float = 0.0  # building_area / land_area
    frontage_footage: float = 0.0  # street frontage
    topography_score: float = 0.0  # flat=1.0, steep=0.0
    utility_access_score: float = 0.0  # water, sewer, electric
    # Regulatory features
    zoning_flexibility_score: float = 0.0
    permit_processing_time: float = 0.0  # days
    environmental_constraints: bool = False
    historic_district: bool = False
    # Market features
    days_on_market_surplus: int = 0
    price_reduction_count: int = 0
    competing_properties_count: int = 0
    developer_interest_score: float = 0.0

@dataclass
class OpportunityPrediction:
    """Surplus property opportunity prediction result"""
    opportunity_score: float  # 0-100
    development_potential_score: float  # 0-100
    investment_return_estimate: float  # estimated ROI %
    confidence: float
    key_opportunity_factors: List[str]
    recommended_uses: List[str]
    estimated_development_timeline: int  # months
    risk_factors: List[str]
    market_potential: str  # high, medium, low
    acquisition_eligibility_score: float  # 0-100

class VacancyMLModel:
    """Machine learning model for vacancy prediction"""
    
    def __init__(self, model_path: str = "ml_models"):
        self.model_path = model_path
        self.model_dir = os.path.join(os.getcwd(), model_path)
        os.makedirs(self.model_dir, exist_ok=True)
        
        # ML components
        self.vacancy_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.label_encoders = {}
        
        # Training data storage
        self.training_history = []
        self.feature_importance = {}
        self.model_accuracy = 0.0
        
        # Model files
        self.classifier_file = os.path.join(self.model_dir, "vacancy_classifier.pkl")
        self.anomaly_file = os.path.join(self.model_dir, "anomaly_detector.pkl")
        self.scaler_file = os.path.join(self.model_dir, "scaler.pkl")
        self.metadata_file = os.path.join(self.model_dir, "model_metadata.json")
        
        self._load_models()
    
    def _load_models(self):
        """Load trained models if available"""
        try:
            if os.path.exists(self.classifier_file):
                with open(self.classifier_file, 'rb') as f:
                    self.vacancy_classifier = pickle.load(f)
                log.info("Loaded vacancy classifier model")
            
            if os.path.exists(self.anomaly_file):
                with open(self.anomaly_file, 'rb') as f:
                    self.anomaly_detector = pickle.load(f)
                log.info("Loaded anomaly detector model")
            
            if os.path.exists(scaler_file):
                with open(self.scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                log.info("Loaded feature scaler")
            
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self.model_accuracy = metadata.get('accuracy', 0.0)
                    self.feature_importance = metadata.get('feature_importance', {})
                    self.training_history = metadata.get('training_history', [])
                log.info("Loaded model metadata")
                
        except Exception as e:
            log.warning(f"Could not load models: {e}. Starting with untrained models.")
    
    def _save_models(self):
        """Save trained models"""
        try:
            with open(self.classifier_file, 'wb') as f:
                pickle.dump(self.vacancy_classifier, f)
            
            with open(self.anomaly_file, 'wb') as f:
                pickle.dump(self.anomaly_detector, f)
            
            with open(self.scaler_file, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            metadata = {
                'accuracy': self.model_accuracy,
                'feature_importance': self.feature_importance,
                'training_history': self.training_history,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            log.info("Models saved successfully")
            
        except Exception as e:
            log.error(f"Error saving models: {e}")
    
    def extract_features(self, properties: List[Dict], violations: List[Dict], 
                        permits: List[Dict], historical_data: List[Dict] = None,
                        zoning_data: List[Dict] = None) -> List[MLFeatures]:
        """Extract ML features from raw data"""
        features = []
        
        # Build lookup dictionaries
        violations_by_addr = {}
        for v in violations:
            addr = v.get("address", "").lower()
            violations_by_addr[addr] = violations_by_addr.get(addr, 0) + 1
        
        permits_by_addr = {}
        for p in permits:
            addr = p.get("address", "").lower()
            permits_by_addr[addr] = permits_by_addr.get(addr, 0) + 1
        
        # Build zoning lookup
        zoning_lookup = {}
        if zoning_data:
            for zoning in zoning_data:
                addr = zoning.get("address", "").lower()
                zoning_lookup[addr] = zoning
        
        # Calculate neighborhood statistics
        zip_stats = self._calculate_neighborhood_stats(properties)
        
        for prop in properties:
            addr = prop.get("address", "").lower()
            zip_code = self._extract_zip_code(prop.get("address", ""))
            
            # Historical trend analysis
            hist_trend = self._calculate_historical_trend(
                prop.get("parcel_id", ""), historical_data or []
            )
            
            # Extract zoning features
            zoning_info = zoning_lookup.get(addr, {})
            zoning_features = self._extract_zoning_features(zoning_info)
            
            feature = MLFeatures(
                parcel_id=prop.get("parcel_id", ""),
                address=prop.get("address", ""),
                assessed_value=prop.get("assessed_value", 0.0),
                city_vacant_flag=prop.get("city_vacant_flag", False),
                violation_count=violations_by_addr.get(addr, 0),
                permit_count=permits_by_addr.get(addr, 0),
                listing_price=prop.get("listing_price"),
                days_on_market=prop.get("days_on_market"),
                price_to_assessed_ratio=self._calculate_price_ratio(prop),
                neighborhood_vacancy_rate=zip_stats.get(zip_code, {}).get("vacancy_rate", 0.0),
                nearby_permit_activity=zip_stats.get(zip_code, {}).get("permit_count", 0),
                historical_violation_trend=hist_trend,
                time_since_last_permit=self._days_since_last_permit(prop.get("address", ""), permits),
                property_age_years=self._estimate_property_age(prop),
                zip_code=zip_code,
                **zoning_features
            )
            features.append(feature)
        
        return features
    
    def _calculate_neighborhood_stats(self, properties: List[Dict]) -> Dict[str, Dict]:
        """Calculate neighborhood-level statistics"""
        zip_stats = {}
        
        for prop in properties:
            zip_code = self._extract_zip_code(prop.get("address", ""))
            if zip_code not in zip_stats:
                zip_stats[zip_code] = {
                    "vacancy_rate": 0.0,
                    "permit_count": 0,
                    "total_properties": 0,
                    "vacant_properties": 0
                }
            
            zip_stats[zip_code]["total_properties"] += 1
            if prop.get("city_vacant_flag", False):
                zip_stats[zip_code]["vacant_properties"] += 1
                zip_stats[zip_code]["vacancy_rate"] = (
                    zip_stats[zip_code]["vacant_properties"] / 
                    zip_stats[zip_code]["total_properties"]
                )
        
        return zip_stats
    
    def _extract_zip_code(self, address: str) -> str:
        """Extract zip code from address"""
        import re
        zip_match = re.search(r'\b(\d{5})\b', address)
        return zip_match.group(1) if zip_match else "00000"
    
    def _calculate_price_ratio(self, prop: Dict) -> Optional[float]:
        """Calculate price to assessed value ratio"""
        listing_price = prop.get("listing_price")
        assessed_value = prop.get("assessed_value", 0.0)
        
        if listing_price and assessed_value > 0:
            return listing_price / assessed_value
        return None
    
    def _calculate_historical_trend(self, parcel_id: str, historical_data: List[Dict]) -> float:
        """Calculate historical violation trend for a property"""
        if not historical_data:
            return 0.0
        
        property_history = [
            record for record in historical_data 
            if record.get("parcel_id") == parcel_id
        ]
        
        if len(property_history) < 2:
            return 0.0
        
        # Simple trend calculation (violations over time)
        recent_violations = sum(1 for record in property_history[-5:] 
                              if record.get("has_violation", False))
        older_violations = sum(1 for record in property_history[:-5] 
                             if record.get("has_violation", False))
        
        return recent_violations - older_violations
    
    def _days_since_last_permit(self, address: str, permits: List[Dict]) -> int:
        """Calculate days since last building permit"""
        addr_lower = address.lower()
        property_permits = [
            p for p in permits 
            if p.get("address", "").lower() == addr_lower
        ]
        
        if not property_permits:
            return 999  # No permits found
        
        latest_date = None
        for permit in property_permits:
            permit_date = permit.get("issued_date")
            if permit_date:
                try:
                    date_obj = datetime.fromisoformat(permit_date.replace('Z', '+00:00'))
                    if latest_date is None or date_obj > latest_date:
                        latest_date = date_obj
                except:
                    continue
        
        if latest_date:
            return (datetime.utcnow() - latest_date).days
        
        return 999
    
    def _estimate_property_age(self, prop: Dict) -> Optional[int]:
        """Estimate property age from available data"""
        # This is a simplified estimation - in practice, you'd use construction year
        # For now, return a reasonable default based on assessed value ranges
        assessed_value = prop.get("assessed_value", 0.0)
        
        if assessed_value > 200000:
            return 20  # Newer properties tend to have higher values
        elif assessed_value > 100000:
            return 35
        else:
            return 50  # Older properties tend to have lower values
    
    def prepare_training_data(self, features: List[MLFeatures], 
                            labels: List[int]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and labels for training"""
        if len(features) != len(labels):
            raise ValueError("Features and labels must have same length")
        
        # Convert features to numpy array
        feature_vectors = []
        for feature in features:
            vector = [
                feature.assessed_value,
                int(feature.city_vacant_flag),
                feature.violation_count,
                feature.permit_count,
                feature.listing_price or 0,
                feature.days_on_market or 0,
                feature.price_to_assessed_ratio or 0,
                feature.neighborhood_vacancy_rate,
                feature.nearby_permit_activity,
                feature.historical_violation_trend,
                feature.time_since_last_permit,
                feature.property_age_years or 0,
            ]
            feature_vectors.append(vector)
        
        X = np.array(feature_vectors)
        y = np.array(labels)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled, y
    
    def train(self, features: List[MLFeatures], labels: List[int]) -> Dict[str, Any]:
        """Train the ML models"""
        if len(features) < 10:
            log.warning("Insufficient training data. Need at least 10 samples.")
            return {"status": "insufficient_data", "samples": len(features)}
        
        try:
            # Prepare training data
            X, y = self.prepare_training_data(features, labels)
            
            # Split data for validation
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Train vacancy classifier
            self.vacancy_classifier.fit(X_train, y_train)
            
            # Train anomaly detector
            self.anomaly_detector.fit(X_train)
            
            # Evaluate model
            y_pred = self.vacancy_classifier.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            self.model_accuracy = accuracy
            
            # Store feature importance
            feature_names = [
                'assessed_value', 'city_vacant_flag', 'violation_count',
                'permit_count', 'listing_price', 'days_on_market',
                'price_ratio', 'neighborhood_vacancy', 'nearby_permits',
                'violation_trend', 'days_since_permit', 'property_age'
            ]
            
            importances = self.vacancy_classifier.feature_importances_
            self.feature_importance = dict(zip(feature_names, importances))
            
            # Record training history
            training_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "samples": len(features),
                "accuracy": accuracy,
                "features_used": len(feature_names)
            }
            self.training_history.append(training_record)
            
            # Save models
            self._save_models()
            
            log.info(f"Model trained successfully. Accuracy: {accuracy:.3f}")
            
            return {
                "status": "success",
                "accuracy": accuracy,
                "samples_trained": len(features),
                "feature_importance": self.feature_importance
            }
            
        except Exception as e:
            log.error(f"Training failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def predict(self, features: List[MLFeatures]) -> List[PredictionResult]:
        """Make predictions on new data"""
        if self.model_accuracy == 0.0:
            log.warning("Model not trained yet. Using rule-based predictions.")
            return self._rule_based_predictions(features)
        
        try:
            # Prepare features
            feature_vectors = []
            for feature in features:
                vector = [
                    feature.assessed_value,
                    int(feature.city_vacant_flag),
                    feature.violation_count,
                    feature.permit_count,
                    feature.listing_price or 0,
                    feature.days_on_market or 0,
                    feature.price_to_assessed_ratio or 0,
                    feature.neighborhood_vacancy_rate,
                    feature.nearby_permit_activity,
                    feature.historical_violation_trend,
                    feature.time_since_last_permit,
                    feature.property_age_years or 0,
                ]
                feature_vectors.append(vector)
            
            X = np.array(feature_vectors)
            X_scaled = self.scaler.transform(X)
            
            # Get predictions
            vacancy_probs = self.vacancy_classifier.predict_proba(X_scaled)[:, 1]
            anomaly_scores = self.anomaly_detector.decision_function(X_scaled)
            
            results = []
            for i, feature in enumerate(features):
                # Calculate risk score (0-100)
                risk_score = vacancy_probs[i] * 100
                
                # Determine confidence based on anomaly score
                confidence = max(0, min(1, 1 - abs(anomaly_scores[i])))
                
                # Identify key factors
                key_factors = self._identify_key_factors(feature, vacancy_probs[i])
                
                # Predict time to vacancy (simplified)
                predicted_days = self._predict_time_to_vacancy(feature, vacancy_probs[i])
                
                result = PredictionResult(
                    vacancy_probability=vacancy_probs[i],
                    risk_score=risk_score,
                    confidence=confidence,
                    key_factors=key_factors,
                    anomaly_score=anomaly_scores[i],
                    predicted_time_to_vacancy=predicted_days
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            log.error(f"Prediction failed: {e}")
            return self._rule_based_predictions(features)
    
    def _rule_based_predictions(self, features: List[MLFeatures]) -> List[PredictionResult]:
        """Fallback rule-based predictions"""
        results = []
        
        for feature in features:
            # Simple rule-based scoring
            score = 0.0
            factors = []
            
            if feature.city_vacant_flag:
                score += 40
                factors.append("City vacant registry")
            
            if feature.violation_count > 0:
                score += min(feature.violation_count * 8, 30)
                factors.append(f"Code violations: {feature.violation_count}")
            
            if feature.permit_count == 0 and feature.assessed_value > 0:
                score += 10
                factors.append("No recent permits")
            
            if feature.price_to_assessed_ratio and feature.price_to_assessed_ratio < 0.5:
                score += 15
                factors.append("Price below assessed value")
            
            if feature.days_on_market and feature.days_on_market > 120:
                score += 10
                factors.append(f"Stale listing: {feature.days_on_market} days")
            
            vacancy_prob = min(1.0, score / 100)
            
            result = PredictionResult(
                vacancy_probability=vacancy_prob,
                risk_score=score,
                confidence=0.5,  # Lower confidence for rule-based
                key_factors=factors,
                anomaly_score=0.0,
                predicted_time_to_vacancy=None
            )
            results.append(result)
        
        return results
    
    def _extract_zoning_features(self, zoning_info: Dict) -> Dict[str, Any]:
        """Extract ML features from zoning information"""
        if not zoning_info:
            return {
                'zone_code': None,
                'zone_description': None,
                'land_use': None,
                'minimum_lot_size': None,
                'maximum_building_height': None,
                'is_residential_zone': False,
                'is_commercial_zone': False,
                'is_mixed_use_zone': False,
                'zone_density_score': 0.0,
                'permitted_use_count': 0,
                'conditional_use_count': 0
            }
        
        zone_code = zoning_info.get('zone_code', '')
        land_use = zoning_info.get('land_use', '').lower()
        
        # Zone density scoring
        density_scores = {
            'R-1': 1.0,  # Single-family - lowest density
            'R-2': 2.0,  # Two-family - medium density
            'R-3': 3.0,  # Multi-family - high density
            'B-1': 2.5,  # Neighborhood business - medium-high density
            'B-2': 3.5   # Central business - highest density
        }
        
        zone_density_score = density_scores.get(zone_code, 0.0)
        
        # Zone type flags
        is_residential = zone_code.startswith('R') if zone_code else False
        is_commercial = zone_code.startswith('B') if zone_code else False
        is_mixed_use = 'mixed' in land_use or ('residential' in land_use and 'commercial' in land_use)
        
        # Count permitted and conditional uses
        permitted_uses = zoning_info.get('permitted_uses', [])
        conditional_uses = zoning_info.get('conditional_uses', [])
        
        return {
            'zone_code': zone_code,
            'zone_description': zoning_info.get('zone_description'),
            'land_use': zoning_info.get('land_use'),
            'minimum_lot_size': zoning_info.get('minimum_lot_size'),
            'maximum_building_height': zoning_info.get('maximum_building_height'),
            'is_residential_zone': is_residential,
            'is_commercial_zone': is_commercial,
            'is_mixed_use_zone': is_mixed_use,
            'zone_density_score': zone_density_score,
            'permitted_use_count': len(permitted_uses) if permitted_uses else 0,
            'conditional_use_count': len(conditional_uses) if conditional_uses else 0
        }
    
    def _identify_key_factors(self, feature: MLFeatures, probability: float) -> List[str]:
        """Identify most influential factors for prediction"""
        factors = []
        
        if feature.city_vacant_flag:
            factors.append("City vacant flag")
        
        if feature.violation_count > 2:
            factors.append("High violation count")
        
        if feature.historical_violation_trend > 0:
            factors.append("Worsening violation trend")
        
        if feature.neighborhood_vacancy_rate > 0.1:
            factors.append("High neighborhood vacancy")
        
        if feature.price_to_assessed_ratio and feature.price_to_assessed_ratio < 0.6:
            factors.append("Low price-to-assessed ratio")
        
        # Zoning-related factors
        if feature.is_commercial_zone and feature.zone_density_score > 3.0:
            factors.append("High-density commercial zone")
        
        if feature.is_residential_zone and feature.zone_density_score < 2.0:
            factors.append("Low-density residential zone")
        
        if feature.is_mixed_use_zone:
            factors.append("Mixed-use zoning flexibility")
        
        if feature.minimum_lot_size and feature.minimum_lot_size > 10000:
            factors.append("Large minimum lot size")
        
        return factors[:4]  # Top 4 factors
    
    def _predict_time_to_vacancy(self, feature: MLFeatures, probability: float) -> Optional[int]:
        """Predict days until vacancy (simplified heuristic)"""
        if probability < 0.3:
            return None  # Low risk, no prediction
        
        # Base prediction on risk factors
        base_days = 180  # 6 months baseline
        
        if feature.violation_count > 0:
            base_days -= feature.violation_count * 30
        
        if feature.neighborhood_vacancy_rate > 0.1:
            base_days -= 60
        
        if feature.historical_violation_trend > 0:
            base_days -= 45
        
        return max(30, min(365, int(base_days * (1 - probability))))
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and statistics"""
        return {
            "model_accuracy": self.model_accuracy,
            "feature_importance": self.feature_importance,
            "training_history": self.training_history,
            "models_trained": self.model_accuracy > 0,
            "last_training": self.training_history[-1]["timestamp"] if self.training_history else None
        }
    
    def add_feedback(self, parcel_id: str, actual_outcome: bool, prediction: float):
        """Add feedback for continuous learning"""
        feedback_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "parcel_id": parcel_id,
            "predicted_probability": prediction,
            "actual_vacancy": actual_outcome,
            "prediction_error": abs(prediction - float(actual_outcome))
        }
        
        feedback_file = os.path.join(self.model_dir, "feedback.json")
        
        try:
            if os.path.exists(feedback_file):
                with open(feedback_file, 'r') as f:
                    feedback_data = json.load(f)
            else:
                feedback_data = []
            
            feedback_data.append(feedback_record)
            
            # Keep only last 1000 feedback records
            if len(feedback_data) > 1000:
                feedback_data = feedback_data[-1000:]
            
            with open(feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)
                
            log.info(f"Added feedback for parcel {parcel_id}")
            
        except Exception as e:
            log.error(f"Error saving feedback: {e}")
    
    def retrain_with_feedback(self) -> Dict[str, Any]:
        """Retrain models using accumulated feedback"""
        feedback_file = os.path.join(self.model_dir, "feedback.json")
        
        if not os.path.exists(feedback_file):
            return {"status": "no_feedback_data"}
        
        try:
            with open(feedback_file, 'r') as f:
                feedback_data = json.load(f)
            
            if len(feedback_data) < 50:
                return {"status": "insufficient_feedback", "records": len(feedback_data)}
            
            # This is a simplified retraining - in practice, you'd need to 
            # reconstruct the full feature set for each feedback record
            log.info(f"Retraining with {len(feedback_data)} feedback records")
            
            # For now, just record the retraining attempt
            retraining_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "feedback_records_used": len(feedback_data),
                "status": "scheduled"
            }
            
            self.training_history.append(retraining_record)
            self._save_models()
            
            return {"status": "scheduled", "records": len(feedback_data)}
            
        except Exception as e:
            log.error(f"Error in feedback retraining: {e}")
            return {"status": "error", "message": str(e)}

class SurplusPropertiesMLModel:
    """Machine learning model for surplus properties opportunity scoring"""
    
    def __init__(self, model_path: str = "ml_models"):
        self.model_path = model_path
        self.model_dir = os.path.join(os.getcwd(), model_path)
        os.makedirs(self.model_dir, exist_ok=True)
        
        # ML components for opportunity scoring
        self.opportunity_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.development_potential_regressor = RandomForestClassifier(n_estimators=100, random_state=42)
        self.roi_estimator = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.label_encoders = {}
        
        # Training data storage
        self.training_history = []
        self.feature_importance = {}
        self.model_accuracy = 0.0
        
        # Model files
        self.opportunity_file = os.path.join(self.model_dir, "surplus_opportunity_classifier.pkl")
        self.potential_file = os.path.join(self.model_dir, "surplus_potential_regressor.pkl")
        self.roi_file = os.path.join(self.model_dir, "surplus_roi_estimator.pkl")
        self.scaler_file = os.path.join(self.model_dir, "surplus_scaler.pkl")
        self.metadata_file = os.path.join(self.model_dir, "surplus_model_metadata.json")
        
        self._load_models()
    
    def _load_models(self):
        """Load trained models if available"""
        try:
            if os.path.exists(self.opportunity_file):
                with open(self.opportunity_file, 'rb') as f:
                    self.opportunity_classifier = pickle.load(f)
                log.info("Loaded surplus opportunity classifier model")
            
            if os.path.exists(self.potential_file):
                with open(self.potential_file, 'rb') as f:
                    self.development_potential_regressor = pickle.load(f)
                log.info("Loaded surplus development potential regressor")
            
            if os.path.exists(self.roi_file):
                with open(self.roi_file, 'rb') as f:
                    self.roi_estimator = pickle.load(f)
                log.info("Loaded surplus ROI estimator")
            
            if os.path.exists(self.scaler_file):
                with open(self.scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                log.info("Loaded surplus features scaler")
            
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self.feature_importance = metadata.get('feature_importance', {})
                    self.model_accuracy = metadata.get('accuracy', 0.0)
                    self.training_history = metadata.get('training_history', [])
                log.info("Loaded surplus model metadata")
        
        except Exception as e:
            log.warning(f"Error loading surplus models: {e}")
    
    def prepare_surplus_features(self, features: SurplusFeatures) -> np.ndarray:
        """Convert SurplusFeatures to numpy array for ML"""
        feature_list = [
            features.assessed_value,
            features.land_area,
            features.building_area,
            features.year_built or 0,
            features.distance_to_downtown,
            features.distance_to_major_roads,
            features.walk_score,
            features.transit_accessibility,
            features.median_income_neighborhood,
            features.property_value_trend,
            features.neighborhood_redevelopment_score,
            features.lot_coverage_ratio if features.land_area > 0 else 0,
            features.frontage_footage,
            features.topography_score,
            features.utility_access_score,
            features.zoning_flexibility_score,
            features.permit_processing_time,
            int(features.environmental_constraints),
            int(features.historic_district),
            features.days_on_market_surplus,
            features.price_reduction_count,
            features.competing_properties_count,
            features.developer_interest_score
        ]
        
        # Encode categorical features
        property_type_encoded = self._encode_categorical('property_type', features.property_type)
        zoning_encoded = self._encode_categorical('zoning', features.zoning)
        status_encoded = self._encode_categorical('status', features.status)
        neighborhood_encoded = self._encode_categorical('neighborhood', features.neighborhood)
        
        feature_list.extend([property_type_encoded, zoning_encoded, status_encoded, neighborhood_encoded])
        
        return np.array(feature_list).reshape(1, -1)
    
    def _encode_categorical(self, feature_name: str, value: str) -> float:
        """Encode categorical feature"""
        if feature_name not in self.label_encoders:
            self.label_encoders[feature_name] = LabelEncoder()
            # In a real implementation, you'd fit on all possible values
            self.label_encoders[feature_name].fit([value, 'unknown'])
        
        try:
            return float(self.label_encoders[feature_name].transform([value])[0])
        except ValueError:
            return float(self.label_encoders[feature_name].transform(['unknown'])[0])
    
    def predict_opportunity(self, features: SurplusFeatures) -> OpportunityPrediction:
        """Predict opportunity score for surplus property"""
        try:
            # Prepare features
            X = self.prepare_surplus_features(features)
            X_scaled = self.scaler.transform(X) if hasattr(self.scaler, 'mean_') else X
            
            # Make predictions
            opportunity_score = self.opportunity_classifier.predict_proba(X_scaled)[0]
            development_score = self.development_potential_regressor.predict(X_scaled)[0]
            roi_estimate = self.roi_estimator.predict(X_scaled)[0]
            
            # Calculate confidence based on prediction consistency
            confidence = self._calculate_confidence(opportunity_score, development_score, roi_estimate)
            
            # Determine key factors
            key_factors = self._identify_key_factors(features, opportunity_score)
            risk_factors = self._identify_risk_factors(features)
            recommended_uses = self._recommend_uses(features, development_score)
            
            # Estimate development timeline
            timeline = self._estimate_timeline(features, development_score)
            
            # Determine market potential
            market_potential = self._determine_market_potential(opportunity_score, roi_estimate)
            
            # Calculate acquisition eligibility score
            eligibility_score = self._calculate_eligibility_score(features)
            
            return OpportunityPrediction(
                opportunity_score=float(opportunity_score[1]) * 100,  # Convert to 0-100 scale
                development_potential_score=float(development_score),
                investment_return_estimate=float(roi_estimate),
                confidence=confidence,
                key_opportunity_factors=key_factors,
                recommended_uses=recommended_uses,
                estimated_development_timeline=timeline,
                risk_factors=risk_factors,
                market_potential=market_potential,
                acquisition_eligibility_score=eligibility_score
            )
        
        except Exception as e:
            log.error(f"Error predicting opportunity: {e}")
            # Return fallback prediction
            return self._fallback_prediction(features)
    
    def _calculate_confidence(self, *predictions) -> float:
        """Calculate prediction confidence"""
        # Simple confidence based on prediction variance
        if len(predictions) > 1:
            variance = np.var(predictions)
            confidence = max(0.5, 1.0 - (variance / 4.0))  # Normalize to 0.5-1.0
        else:
            confidence = 0.7  # Default confidence
        
        return confidence
    
    def _identify_key_factors(self, features: SurplusFeatures, opportunity_score: np.ndarray) -> List[str]:
        """Identify key opportunity factors"""
        factors = []
        
        if features.assessed_value < 50000:
            factors.append("low_acquisition_cost")
        
        if features.land_area > 10000:
            factors.append("large_lot_size")
        
        if features.distance_to_downtown < 5:
            factors.append("prime_location")
        
        if features.zoning_flexibility_score > 0.7:
            factors.append("flexible_zoning")
        
        if features.neighborhood_redevelopment_score > 0.6:
            factors.append("area_revitalization")
        
        if features.walk_score > 70:
            factors.append("walkable_location")
        
        if features.transit_accessibility > 0.6:
            factors.append("transit_access")
        
        if features.utility_access_score > 0.8:
            factors.append("excellent_utilities")
        
        return factors
    
    def _identify_risk_factors(self, features: SurplusFeatures) -> List[str]:
        """Identify risk factors"""
        risks = []
        
        if features.environmental_constraints:
            risks.append("environmental_constraints")
        
        if features.historic_district:
            risks.append("historic_district_restrictions")
        
        if features.permit_processing_time > 90:
            risks.append("long_permit_timeline")
        
        if features.topography_score < 0.3:
            risks.append("challenging_topography")
        
        if features.utility_access_score < 0.4:
            risks.append("limited_utility_access")
        
        if features.days_on_market_surplus > 180:
            risks.append("extended_market_time")
        
        if features.competing_properties_count > 5:
            risks.append("high_competition")
        
        return risks
    
    def _recommend_uses(self, features: SurplusFeatures, development_score: float) -> List[str]:
        """Recommend development uses based on features"""
        uses = []
        
        # Residential recommendations
        if 'R' in features.zoning or features.neighborhood_redevelopment_score > 0.5:
            if features.land_area > 5000:
                uses.extend(["single_family_detached", "duplex"])
            if features.land_area > 10000:
                uses.append("multi_family")
        
        # Commercial recommendations
        if 'C' in features.zoning or features.distance_to_major_roads < 1:
            uses.extend(["retail", "office"])
        
        # Mixed use recommendations
        if features.zoning_flexibility_score > 0.7:
            uses.append("mixed_use")
        
        # Special uses based on location
        if features.distance_to_downtown < 2:
            uses.append("urban_infill")
        
        if features.walk_score > 80:
            uses.append("live_work_units")
        
        return uses[:5]  # Limit to top 5 recommendations
    
    def _estimate_timeline(self, features: SurplusFeatures, development_score: float) -> int:
        """Estimate development timeline in months"""
        base_timeline = 12  # Base 12 months
        
        # Adjust based on factors
        if features.building_area > 0:
            base_timeline += 6  # Renovation takes longer
        
        if features.environmental_constraints:
            base_timeline += 4
        
        if features.historic_district:
            base_timeline += 6
        
        if features.permit_processing_time > 60:
            base_timeline += int(features.permit_processing_time / 30)
        
        if features.utility_access_score < 0.5:
            base_timeline += 3
        
        # Adjust based on development potential
        if development_score > 80:
            base_timeline = max(6, base_timeline - 3)
        elif development_score < 40:
            base_timeline += 6
        
        return min(36, base_timeline)  # Cap at 3 years
    
    def _determine_market_potential(self, opportunity_score: np.ndarray, roi_estimate: float) -> str:
        """Determine market potential category"""
        score = float(opportunity_score[1]) * 100
        
        if score > 80 and roi_estimate > 15:
            return "high"
        elif score > 60 and roi_estimate > 8:
            return "medium"
        else:
            return "low"
    
    def _calculate_eligibility_score(self, features: SurplusFeatures) -> float:
        """Calculate acquisition eligibility score"""
        score = 100.0
        
        # Status check
        if features.status.lower() not in ['available', 'for sale']:
            score -= 30
        
        # Value check
        if features.assessed_value > 200000:
            score -= 20
        
        # Zoning check
        if not features.zoning:
            score -= 10
        
        # Location check
        if features.distance_to_downtown > 15:
            score -= 15
        
        # Environmental constraints
        if features.environmental_constraints:
            score -= 25
        
        # Historic district
        if features.historic_district:
            score -= 20
        
        return max(0, score)
    
    def _fallback_prediction(self, features: SurplusFeatures) -> OpportunityPrediction:
        """Fallback prediction when ML models are not available"""
        # Simple rule-based scoring
        opportunity_score = 50.0  # Base score
        
        # Adjust based on key factors
        if features.assessed_value < 50000:
            opportunity_score += 20
        
        if features.land_area > 10000:
            opportunity_score += 15
        
        if features.distance_to_downtown < 5:
            opportunity_score += 10
        
        if features.zoning_flexibility_score > 0.7:
            opportunity_score += 10
        
        development_score = min(100, opportunity_score + np.random.uniform(-10, 10))
        roi_estimate = opportunity_score * 0.15  # Simple ROI estimate
        
        return OpportunityPrediction(
            opportunity_score=opportunity_score,
            development_potential_score=development_score,
            investment_return_estimate=roi_estimate,
            confidence=0.6,  # Lower confidence for fallback
            key_opportunity_factors=["rule_based_analysis"],
            recommended_uses=["residential", "commercial"],
            estimated_development_timeline=12,
            risk_factors=["model_not_trained"],
            market_potential="medium",
            acquisition_eligibility_score=70.0
        )
