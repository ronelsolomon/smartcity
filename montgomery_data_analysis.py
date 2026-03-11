#!/usr/bin/env python3
"""
Montgomery County Open Data Analysis
Analyzes Construction Permits and Code Violations datasets
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

class MontgomeryDataAnalyzer:
    def __init__(self):
        self.permits_url = "https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Construction_Permits/FeatureServer/0/query?where=1%3D1&outFields=*&f=json"
        self.violations_url = "https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Code_Violations/FeatureServer/0/query?where=1%3D1&outFields=*&f=json"
        self.permits_data = None
        self.violations_data = None
        
    def fetch_data(self):
        """Fetch data from Montgomery County open data portal"""
        print("Fetching Construction Permits data...")
        try:
            response = requests.get(self.permits_url)
            self.permits_data = response.json()
            print(f"Retrieved {len(self.permits_data.get('features', []))} permit records")
        except Exception as e:
            print(f"Error fetching permits: {e}")
            
        print("Fetching Code Violations data...")
        try:
            response = requests.get(self.violations_url)
            self.violations_data = response.json()
            print(f"Retrieved {len(self.violations_data.get('features', []))} violation records")
        except Exception as e:
            print(f"Error fetching violations: {e}")
    
    def analyze_permits(self):
        """Analyze construction permits data"""
        if not self.permits_data:
            return None
            
        # Convert to DataFrame
        permits = []
        for feature in self.permits_data.get('features', []):
            attrs = feature.get('attributes', {})
            permits.append(attrs)
        
        df = pd.DataFrame(permits)
        
        # Analysis
        analysis = {
            'total_permits': len(df),
            'date_range': {},
            'project_types': {},
            'cost_analysis': {},
            'status_distribution': {},
            'council_districts': {},
            'recent_trends': {}
        }
        
        # Date analysis
        if 'IssuedDate' in df.columns:
            df['IssuedDate'] = pd.to_datetime(df['IssuedDate'], errors='coerce')
            valid_dates = df['IssuedDate'].dropna()
            if not valid_dates.empty:
                analysis['date_range'] = {
                    'earliest': valid_dates.min().strftime('%Y-%m-%d'),
                    'latest': valid_dates.max().strftime('%Y-%m-%d'),
                    'span_days': (valid_dates.max() - valid_dates.min()).days
                }
        
        # Project types
        if 'ProjectType' in df.columns:
            project_counts = df['ProjectType'].value_counts().head(10)
            analysis['project_types'] = project_counts.to_dict()
        
        # Cost analysis
        if 'EstimatedCost' in df.columns:
            costs = pd.to_numeric(df['EstimatedCost'], errors='coerce').dropna()
            if not costs.empty:
                analysis['cost_analysis'] = {
                    'mean_cost': costs.mean(),
                    'median_cost': costs.median(),
                    'max_cost': costs.max(),
                    'total_value': costs.sum(),
                    'projects_over_100k': (costs > 100000).sum()
                }
        
        # Status distribution
        if 'PermitStatus' in df.columns:
            analysis['status_distribution'] = df['PermitStatus'].value_counts().to_dict()
        
        # Council districts
        if 'CouncilDistrict' in df.columns:
            analysis['council_districts'] = df['CouncilDistrict'].value_counts().to_dict()
        
        return analysis
    
    def analyze_violations(self):
        """Analyze code violations data"""
        if not self.violations_data:
            return None
            
        # Convert to DataFrame
        violations = []
        for feature in self.violations_data.get('features', []):
            attrs = feature.get('attributes', {})
            violations.append(attrs)
        
        df = pd.DataFrame(violations)
        
        analysis = {
            'total_violations': len(df),
            'case_types': {},
            'case_status': {},
            'lien_status': {},
            'council_districts': {},
            'date_analysis': {},
            'common_complaints': {}
        }
        
        # Case types
        if 'CaseType' in df.columns:
            analysis['case_types'] = df['CaseType'].value_counts().to_dict()
        
        # Case status
        if 'CaseStatus' in df.columns:
            analysis['case_status'] = df['CaseStatus'].value_counts().to_dict()
        
        # Lien status
        if 'LienStatus' in df.columns:
            analysis['lien_status'] = df['LienStatus'].value_counts().to_dict()
        
        # Council districts
        if 'CouncilDistrict' in df.columns:
            analysis['council_districts'] = df['CouncilDistrict'].value_counts().to_dict()
        
        # Date analysis
        if 'CaseDate' in df.columns:
            df['CaseDate'] = pd.to_datetime(df['CaseDate'], errors='coerce')
            valid_dates = df['CaseDate'].dropna()
            if not valid_dates.empty:
                analysis['date_analysis'] = {
                    'earliest': valid_dates.min().strftime('%Y-%m-%d'),
                    'latest': valid_dates.max().strftime('%Y-%m-%d'),
                    'span_days': (valid_dates.max() - valid_dates.min()).days
                }
        
        # Common complaints
        if 'ComplaintRem' in df.columns:
            complaints = df['ComplaintRem'].dropna().str.upper()
            # Extract common keywords
            keywords = ['GRASS', 'DEBRIS', 'VEHICLE', 'TREE', 'JUNK', 'TRASH', 'CLEAN', 'CUT']
            keyword_counts = {}
            for keyword in keywords:
                keyword_counts[keyword] = complaints.str.contains(keyword).sum()
            analysis['common_complaints'] = keyword_counts
        
        return analysis
    
    def generate_report(self):
        """Generate comprehensive analysis report"""
        self.fetch_data()
        
        print("\n" + "="*60)
        print("MONTGOMERY COUNTY DATA ANALYSIS REPORT")
        print("="*60)
        
        # Permits analysis
        permits_analysis = self.analyze_permits()
        if permits_analysis:
            print("\n📋 CONSTRUCTION PERMITS ANALYSIS")
            print("-" * 40)
            print(f"Total Permits: {permits_analysis['total_permits']:,}")
            
            if permits_analysis['date_range']:
                dr = permits_analysis['date_range']
                print(f"Date Range: {dr['earliest']} to {dr['latest']} ({dr['span_days']} days)")
            
            if permits_analysis['project_types']:
                print("\nTop Project Types:")
                for ptype, count in list(permits_analysis['project_types'].items())[:5]:
                    print(f"  {ptype}: {count:,}")
            
            if permits_analysis['cost_analysis']:
                ca = permits_analysis['cost_analysis']
                print(f"\nCost Analysis:")
                print(f"  Average Cost: ${ca['mean_cost']:,.0f}")
                print(f"  Median Cost: ${ca['median_cost']:,.0f}")
                print(f"  Total Value: ${ca['total_value']:,.0f}")
                print(f"  Projects >$100K: {ca['projects_over_100k']}")
            
            if permits_analysis['status_distribution']:
                print(f"\nStatus Distribution:")
                for status, count in permits_analysis['status_distribution'].items():
                    print(f"  {status}: {count:,}")
        
        # Violations analysis
        violations_analysis = self.analyze_violations()
        if violations_analysis:
            print("\n⚠️  CODE VIOLATIONS ANALYSIS")
            print("-" * 40)
            print(f"Total Violations: {violations_analysis['total_violations']:,}")
            
            if violations_analysis['date_analysis']:
                dr = violations_analysis['date_analysis']
                print(f"Date Range: {dr['earliest']} to {dr['latest']} ({dr['span_days']} days)")
            
            if violations_analysis['case_types']:
                print("\nViolation Types:")
                for vtype, count in list(violations_analysis['case_types'].items())[:5]:
                    print(f"  {vtype}: {count:,}")
            
            if violations_analysis['case_status']:
                print(f"\nCase Status:")
                for status, count in violations_analysis['case_status'].items():
                    print(f"  {status}: {count:,}")
            
            if violations_analysis['lien_status']:
                print(f"\nLien Status:")
                for status, count in list(violations_analysis['lien_status'].items())[:5]:
                    print(f"  {status}: {count:,}")
            
            if violations_analysis['common_complaints']:
                print(f"\nCommon Complaint Keywords:")
                for keyword, count in sorted(violations_analysis['common_complaints'].items(), 
                                           key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  {keyword}: {count:,}")
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        
        return permits_analysis, violations_analysis

if __name__ == "__main__":
    analyzer = MontgomeryDataAnalyzer()
    permits_analysis, violations_analysis = analyzer.generate_report()
