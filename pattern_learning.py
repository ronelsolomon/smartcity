"""
Pattern Learning Module for Real Estate Trend Analysis
Advanced pattern recognition and trend forecasting
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import re
import logging

log = logging.getLogger(__name__)

@dataclass
class TrendPattern:
    """Detected trend pattern"""
    pattern_type: str  # seasonal, cyclical,突发性, gradual
    confidence: float
    start_date: str
    end_date: str
    description: str
    keywords: List[str]
    price_impact: float
    volume_impact: float

@dataclass
class MarketSignal:
    """Market signal extracted from data"""
    signal_type: str  # price_drop, volume_spike, keyword_trend
    strength: float
    timestamp: str
    source: str
    details: Dict[str, Any]

class PatternLearner:
    """Advanced pattern learning for real estate trends"""
    
    def __init__(self, history_size: int = 365):
        self.history_size = history_size  # days of history to maintain
        self.patterns = []
        self.signals = deque(maxlen=1000)
        self.keyword_trends = defaultdict(lambda: deque(maxlen=100))
        self.price_history = defaultdict(lambda: deque(maxlen=50))
        self.volume_history = defaultdict(lambda: deque(maxlen=50))
        
        # Pattern detection parameters
        self.seasonal_patterns = {}
        self.cyclical_patterns = {}
        self.baseline_metrics = {}
        
        # Storage
        self.patterns_file = "ml_models/learned_patterns.json"
        self.signals_file = "ml_models/market_signals.json"
        
        self._load_historical_data()
    
    def _load_historical_data(self):
        """Load previously learned patterns and signals"""
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r') as f:
                    data = json.load(f)
                    self.patterns = [TrendPattern(**p) for p in data.get('patterns', [])]
                    self.seasonal_patterns = data.get('seasonal_patterns', {})
                    self.cyclical_patterns = data.get('cyclical_patterns', {})
                    self.baseline_metrics = data.get('baseline_metrics', {})
                log.info(f"Loaded {len(self.patterns)} historical patterns")
            
            if os.path.exists(self.signals_file):
                with open(self.signals_file, 'r') as f:
                    signals_data = json.load(f)
                    self.signals = deque(
                        [MarketSignal(**s) for s in signals_data.get('signals', [])],
                        maxlen=1000
                    )
                log.info(f"Loaded {len(self.signals)} historical signals")
                
        except Exception as e:
            log.warning(f"Could not load historical data: {e}")
    
    def _save_patterns(self):
        """Save learned patterns and signals"""
        try:
            os.makedirs(os.path.dirname(self.patterns_file), exist_ok=True)
            
            patterns_data = {
                'patterns': [asdict(p) for p in self.patterns],
                'seasonal_patterns': self.seasonal_patterns,
                'cyclical_patterns': self.cyclical_patterns,
                'baseline_metrics': self.baseline_metrics,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            with open(self.patterns_file, 'w') as f:
                json.dump(patterns_data, f, indent=2)
            
            signals_data = {
                'signals': [asdict(s) for s in self.signals],
                'last_updated': datetime.utcnow().isoformat()
            }
            
            with open(self.signals_file, 'w') as f:
                json.dump(signals_data, f, indent=2)
                
        except Exception as e:
            log.error(f"Error saving patterns: {e}")
    
    def analyze_crawl_results(self, crawl_results: List[Dict], timestamp: str = None) -> List[MarketSignal]:
        """Analyze new crawl results for patterns and signals"""
        if not timestamp:
            timestamp = datetime.utcnow().isoformat()
        
        signals = []
        
        for result in crawl_results:
            url = result.get("url", "")
            content = result.get("markdown", result.get("content", ""))
            
            if not content:
                continue
            
            # Extract price information
            price_signals = self._extract_price_signals(content, url, timestamp)
            signals.extend(price_signals)
            
            # Extract keyword trends
            keyword_signals = self._extract_keyword_signals(content, url, timestamp)
            signals.extend(keyword_signals)
            
            # Extract volume indicators
            volume_signals = self._extract_volume_signals(content, url, timestamp)
            signals.extend(volume_signals)
        
        # Add to signal history
        self.signals.extend(signals)
        
        # Detect new patterns
        new_patterns = self._detect_patterns()
        self.patterns.extend(new_patterns)
        
        # Save updated data
        self._save_patterns()
        
        return signals
    
    def _extract_price_signals(self, content: str, source: str, timestamp: str) -> List[MarketSignal]:
        """Extract price-related signals from content"""
        signals = []
        
        # Find price mentions
        price_pattern = r'\$(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        prices = [float(p.replace(',', '')) for p in re.findall(price_pattern, content)]
        
        if prices:
            avg_price = np.mean(prices)
            median_price = np.median(prices)
            
            # Store price history
            domain = self._extract_domain(source)
            self.price_history[domain].append({
                'timestamp': timestamp,
                'avg_price': avg_price,
                'median_price': median_price,
                'count': len(prices)
            })
            
            # Detect price drops
            if len(self.price_history[domain]) >= 2:
                recent = self.price_history[domain][-1]
                previous = self.price_history[domain][-2]
                
                price_change = (recent['avg_price'] - previous['avg_price']) / previous['avg_price']
                
                if price_change < -0.1:  # 10%+ drop
                    signals.append(MarketSignal(
                        signal_type="price_drop",
                        strength=abs(price_change),
                        timestamp=timestamp,
                        source=source,
                        details={
                            "percentage_change": price_change,
                            "previous_avg": previous['avg_price'],
                            "current_avg": recent['avg_price'],
                            "domain": domain
                        }
                    ))
        
        return signals
    
    def _extract_keyword_signals(self, content: str, source: str, timestamp: str) -> List[MarketSignal]:
        """Extract keyword trend signals"""
        signals = []
        
        # Vacancy and distress keywords
        vacancy_keywords = [
            "vacant", "foreclosure", "bank owned", "reo", "abandoned",
            "distressed", "price reduced", "days on market", "motivated seller",
            "short sale", "auction", "fixer upper", "as-is", "cash only"
        ]
        
        content_lower = content.lower()
        domain = self._extract_domain(source)
        
        for keyword in vacancy_keywords:
            count = content_lower.count(keyword)
            if count > 0:
                # Track keyword frequency over time
                self.keyword_trends[(domain, keyword)].append({
                    'timestamp': timestamp,
                    'count': count,
                    'content_length': len(content)
                })
                
                # Detect keyword spikes
                if len(self.keyword_trends[(domain, keyword)]) >= 2:
                    recent = self.keyword_trends[(domain, keyword)][-1]
                    previous = self.keyword_trends[(domain, keyword)][-2]
                    
                    # Normalize by content length
                    recent_freq = recent['count'] / recent['content_length'] * 1000
                    previous_freq = previous['count'] / previous['content_length'] * 1000
                    
                    if recent_freq > previous_freq * 2:  # 2x increase
                        signals.append(MarketSignal(
                            signal_type="keyword_spike",
                            strength=recent_freq / previous_freq,
                            timestamp=timestamp,
                            source=source,
                            details={
                                "keyword": keyword,
                                "recent_frequency": recent_freq,
                                "previous_frequency": previous_freq,
                                "domain": domain
                            }
                        ))
        
        return signals
    
    def _extract_volume_signals(self, content: str, source: str, timestamp: str) -> List[MarketSignal]:
        """Extract listing volume signals"""
        signals = []
        
        # Look for listing count indicators
        volume_patterns = [
            r'(\d+)\s*(?:homes?|houses?|properties?)\s*(?:for sale|available)',
            r'(\d+)\s*(?:listings?|results?)',
            r'(\d+)\s*(?:units?|condos?|apartments?)'
        ]
        
        domain = self._extract_domain(source)
        total_volume = 0
        
        for pattern in volume_patterns:
            matches = re.findall(pattern, content.lower())
            total_volume += sum(int(m) for m in matches)
        
        if total_volume > 0:
            # Store volume history
            self.volume_history[domain].append({
                'timestamp': timestamp,
                'volume': total_volume
            })
            
            # Detect volume spikes
            if len(self.volume_history[domain]) >= 2:
                recent = self.volume_history[domain][-1]
                previous = self.volume_history[domain][-2]
                
                volume_change = (recent['volume'] - previous['volume']) / previous['volume']
                
                if volume_change > 0.5:  # 50%+ increase
                    signals.append(MarketSignal(
                        signal_type="volume_spike",
                        strength=volume_change,
                        timestamp=timestamp,
                        source=source,
                        details={
                            "percentage_change": volume_change,
                            "previous_volume": previous['volume'],
                            "current_volume": recent['volume'],
                            "domain": domain
                        }
                    ))
        
        return signals
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return "unknown"
    
    def _detect_patterns(self) -> List[TrendPattern]:
        """Detect patterns from accumulated signals"""
        new_patterns = []
        
        # Detect seasonal patterns
        seasonal_patterns = self._detect_seasonal_patterns()
        new_patterns.extend(seasonal_patterns)
        
        # Detect cyclical patterns
        cyclical_patterns = self._detect_cyclical_patterns()
        new_patterns.extend(cyclical_patterns)
        
        # Detect突发性 patterns (sudden changes)
        sudden_patterns = self._detect_sudden_patterns()
        new_patterns.extend(sudden_patterns)
        
        return new_patterns
    
    def _detect_seasonal_patterns(self) -> List[TrendPattern]:
        """Detect seasonal patterns in data"""
        patterns = []
        
        # Group signals by month
        monthly_signals = defaultdict(list)
        for signal in self.signals:
            try:
                date = datetime.fromisoformat(signal.timestamp.replace('Z', '+00:00'))
                month = date.month
                monthly_signals[month].append(signal)
            except:
                continue
        
        # Look for consistent monthly patterns
        for month, signals in monthly_signals.items():
            if len(signals) >= 3:  # Need at least 3 occurrences
                # Check if this month consistently shows certain patterns
                price_drops = [s for s in signals if s.signal_type == "price_drop"]
                volume_spikes = [s for s in signals if s.signal_type == "volume_spike"]
                
                if len(price_drops) >= 2:
                    patterns.append(TrendPattern(
                        pattern_type="seasonal_price_drop",
                        confidence=len(price_drops) / len(signals),
                        start_date=f"{month}-01",
                        end_date=f"{month}-31",
                        description=f"Seasonal price drop pattern in month {month}",
                        keywords=["price_drop", "seasonal"],
                        price_impact=-0.15,  # Typical 15% drop
                        volume_impact=0.1
                    ))
        
        return patterns
    
    def _detect_cyclical_patterns(self) -> List[TrendPattern]:
        """Detect cyclical patterns (weekly, bi-weekly, etc.)"""
        patterns = []
        
        # Group by day of week
        weekly_signals = defaultdict(list)
        for signal in self.signals:
            try:
                date = datetime.fromisoformat(signal.timestamp.replace('Z', '+00:00'))
                day_of_week = date.weekday()  # 0 = Monday, 6 = Sunday
                weekly_signals[day_of_week].append(signal)
            except:
                continue
        
        # Look for consistent weekly patterns
        for day, signals in weekly_signals.items():
            if len(signals) >= 4:  # Need at least 4 occurrences
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                
                # Check for specific signal types on this day
                keyword_spikes = [s for s in signals if s.signal_type == "keyword_spike"]
                
                if len(keyword_spikes) >= 3:
                    patterns.append(TrendPattern(
                        pattern_type="weekly_keyword_spike",
                        confidence=len(keyword_spikes) / len(signals),
                        start_date=day_names[day],
                        end_date=day_names[day],
                        description=f"Weekly keyword spike pattern on {day_names[day]}",
                        keywords=["keyword_spike", "weekly"],
                        price_impact=0.0,
                        volume_impact=0.05
                    ))
        
        return patterns
    
    def _detect_sudden_patterns(self) -> List[TrendPattern]:
        """Detect sudden, unexpected patterns"""
        patterns = []
        
        # Look for clusters of strong signals in short time periods
        if len(self.signals) < 10:
            return patterns
        
        # Sort signals by timestamp
        sorted_signals = sorted(self.signals, key=lambda s: s.timestamp)
        
        # Look for signal clusters
        window_size = timedelta(days=7)
        cluster_threshold = 5  # Minimum signals for a cluster
        
        for i in range(len(sorted_signals) - cluster_threshold + 1):
            window_start = datetime.fromisoformat(sorted_signals[i].timestamp.replace('Z', '+00:00'))
            window_end = window_start + window_size
            
            # Count signals in window
            window_signals = []
            for j in range(i, min(i + 20, len(sorted_signals))):  # Check next 20 signals
                try:
                    signal_time = datetime.fromisoformat(sorted_signals[j].timestamp.replace('Z', '+00:00'))
                    if window_start <= signal_time <= window_end:
                        window_signals.append(sorted_signals[j])
                    elif signal_time > window_end:
                        break
                except:
                    continue
            
            if len(window_signals) >= cluster_threshold:
                # Calculate cluster strength
                avg_strength = np.mean([s.strength for s in window_signals])
                
                if avg_strength > 0.5:  # Strong cluster
                    patterns.append(TrendPattern(
                        pattern_type="sudden_signal_cluster",
                        confidence=avg_strength,
                        start_date=window_start.isoformat(),
                        end_date=window_end.isoformat(),
                        description=f"Sudden cluster of {len(window_signals)} strong signals",
                        keywords=[s.signal_type for s in window_signals],
                        price_impact=-0.2 if any(s.signal_type == "price_drop" for s in window_signals) else 0.0,
                        volume_impact=0.3 if any(s.signal_type == "volume_spike" for s in window_signals) else 0.0
                    ))
        
        return patterns
    
    def predict_trends(self, days_ahead: int = 30) -> Dict[str, Any]:
        """Predict future trends based on learned patterns"""
        predictions = {
            "time_horizon_days": days_ahead,
            "price_trend": "stable",
            "volume_trend": "stable",
            "risk_factors": [],
            "opportunities": [],
            "confidence": 0.5,
            "supporting_patterns": []
        }
        
        # Analyze recent signals
        recent_signals = [s for s in self.signals 
                         if datetime.fromisoformat(s.timestamp.replace('Z', '+00:00')) > 
                         datetime.utcnow() - timedelta(days=7)]
        
        if not recent_signals:
            return predictions
        
        # Count signal types in recent data
        price_drops = len([s for s in recent_signals if s.signal_type == "price_drop"])
        volume_spikes = len([s for s in recent_signals if s.signal_type == "volume_spike"])
        keyword_spikes = len([s for s in recent_signals if s.signal_type == "keyword_spike"])
        
        # Determine trends based on signal patterns
        if price_drops >= 3:
            predictions["price_trend"] = "declining"
            predictions["risk_factors"].append("Multiple price drop signals detected")
        
        if volume_spikes >= 2:
            predictions["volume_trend"] = "increasing"
            predictions["opportunities"].append("Higher listing volume expected")
        
        if keyword_spikes >= 4:
            predictions["risk_factors"].append("High distress keyword activity")
        
        # Check for supporting historical patterns
        current_month = datetime.utcnow().month
        supporting_patterns = [p for p in self.patterns 
                             if p.pattern_type.startswith("seasonal") and 
                             int(p.start_date.split('-')[0]) == current_month]
        
        predictions["supporting_patterns"] = [asdict(p) for p in supporting_patterns[:5]]
        
        # Calculate confidence based on data consistency
        total_signals = len(recent_signals)
        if total_signals >= 10:
            predictions["confidence"] = 0.8
        elif total_signals >= 5:
            predictions["confidence"] = 0.6
        else:
            predictions["confidence"] = 0.4
        
        return predictions
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of learned patterns"""
        return {
            "total_patterns": len(self.patterns),
            "pattern_types": {
                ptype: len([p for p in self.patterns if p.pattern_type == ptype])
                for ptype in set(p.pattern_type for p in self.patterns)
            },
            "recent_signals": len([s for s in self.signals 
                                 if datetime.fromisoformat(s.timestamp.replace('Z', '+00:00')) > 
                                 datetime.utcnow() - timedelta(days=7)]),
            "total_signals": len(self.signals),
            "active_keywords": list(set([s.details.get("keyword", "") for s in self.signals 
                                       if s.signal_type == "keyword_spike"])),
            "monitored_domains": list(set([s.details.get("domain", "") for s in self.signals 
                                         if "domain" in s.details]))
        }
