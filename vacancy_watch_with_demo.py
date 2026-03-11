"""
Vacancy Watch - Smart Cities Intelligence System (Demo Version)
Uses demo data when Montgomery Open Data APIs are unavailable
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urlencode
from free_scraper import FreeWebScraper, ScrapingConfig, quick_scrape

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

# Montgomery AL Open Data (Demo Files)
DEMO_FILES = {
    "properties": "demo_properties.json",
    "violations": "demo_violations.json", 
    "permits": "demo_permits.json",
    "traffic": "demo_traffic.json"
}

# Real-estate listing sites to crawl for vacancy/listing signals
REAL_ESTATE_URLS = [
    "https://www.zillow.com/montgomery-al/",
    "https://www.realtor.com/realestateandhomes-search/Montgomery_AL",
    "https://www.trulia.com/AL/Montgomery/",
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Property:
    parcel_id: str
    address: str
    owner: str = ""
    assessed_value: float = 0.0
    city_vacant_flag: bool = False
    open_violations: int = 0
    recent_permits: int = 0
    listing_price: Optional[float] = None
    listing_source: str = ""
    days_on_market: Optional[int] = None
    vacancy_score: float = 0.0
    signals: list = field(default_factory=list)

@dataclass
class TrafficIncident:
    incident_id: str
    location: str
    type: str
    date: str
    severity: str = "unknown"

@dataclass
class ConstructionPermit:
    permit_id: str
    address: str
    type: str
    issued_date: str
    value: float = 0.0

@dataclass
class VacancyWatchReport:
    generated_at: str
    total_properties: int
    high_risk_vacancies: list
    construction_hotspots: list
    traffic_alerts: list
    real_estate_trends: dict
    summary: dict

# ---------------------------------------------------------------------------
# Demo Data Client
# ---------------------------------------------------------------------------

class DemoDataClient:
    """Load demo data from local JSON files"""

    def __init__(self):
        self.data_dir = "."

    def _load_demo_data(self, filename: str) -> list:
        """Load demo data from JSON file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            log.warning(f"Demo file {filename} not found. Run 'python demo_data.py' first.")
            return []
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON in {filename}: {e}")
            return []

    def get_vacant_properties(self, limit: int = 500) -> list[Property]:
        rows = self._load_demo_data(DEMO_FILES["properties"])
        props = []
        for r in rows[:limit]:
            props.append(Property(
                parcel_id=r.get("parcel_id", f"PROP-{len(props)}"),
                address=r.get("address", "Unknown"),
                owner=r.get("owner_name", ""),
                city_vacant_flag=r.get("city_vacant_flag", False),
                signals=r.get("signals", ["demo_data"]),
            ))
        log.info("Loaded %d demo vacant properties.", len(props))
        return props

    def get_property_assessments(self, limit: int = 1000) -> list[dict]:
        return self._load_demo_data(DEMO_FILES["properties"])[:limit]

    def get_code_violations(self, limit: int = 500) -> list[dict]:
        return self._load_demo_data(DEMO_FILES["violations"])[:limit]

    def get_building_permits(self, days_back: int = 90, limit: int = 500) -> list[ConstructionPermit]:
        rows = self._load_demo_data(DEMO_FILES["permits"])
        permits = []
        for r in rows[:limit]:
            permits.append(ConstructionPermit(
                permit_id=r.get("permit_number", f"PERM-{len(permits)}"),
                address=r.get("address", "Unknown"),
                type=r.get("permit_type", "General"),
                issued_date=r.get("issued_date", ""),
                value=float(r.get("job_value", r.get("estimated_cost", 0)) or 0),
            ))
        log.info("Loaded %d demo building permits.", len(permits))
        return permits

    def get_traffic_incidents(self, days_back: int = 30, limit: int = 200) -> list[TrafficIncident]:
        rows = self._load_demo_data(DEMO_FILES["traffic"])
        incidents = []
        for r in rows[:limit]:
            incidents.append(TrafficIncident(
                incident_id=r.get("incident_id", f"INC-{len(incidents)}"),
                location=r.get("location", "Unknown"),
                type=r.get("incident_type", r.get("type", "General")),
                date=r.get("incident_date", ""),
                severity=r.get("severity", "unknown"),
            ))
        log.info("Loaded %d demo traffic incidents.", len(incidents))
        return incidents

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
# Real-estate trend parser
# ---------------------------------------------------------------------------

def parse_real_estate_signals(crawl_results: list[dict]) -> dict:
    """Extract vacancy and pricing signals from crawled real-estate pages."""
    trends = {
        "sources_crawled": len(crawl_results),
        "listing_keywords": {},
        "price_range": {"min": None, "max": None},
        "vacancy_mentions": 0,
        "raw_snippets": [],
    }

    vacancy_keywords = [
        "vacant", "foreclosure", "bank owned", "REO",
        "abandoned", "distressed", "price reduced", "days on market",
    ]

    for result in crawl_results:
        url = result.get("url", "")
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

        # Naive price extraction
        import re
        prices = [int(p.replace(",", "")) for p in re.findall(r"\$(\d{2,3},\d{3})", content)]
        if prices:
            cur_min = trends["price_range"]["min"]
            cur_max = trends["price_range"]["max"]
            trends["price_range"]["min"] = min(prices) if cur_min is None else min(cur_min, min(prices))
            trends["price_range"]["max"] = max(prices) if cur_max is None else max(cur_max, max(prices))

    return trends

# ---------------------------------------------------------------------------
# Vacancy scoring engine
# ---------------------------------------------------------------------------

def score_property(prop: Property, violations_by_address: dict, permits_by_address: dict) -> Property:
    """Compute a 0-100 vacancy/blight risk score."""
    score = 0.0
    signals = list(prop.signals)

    if prop.city_vacant_flag:
        score += 40
        signals.append("city_vacant_registry")

    viol_count = violations_by_address.get(prop.address.lower(), 0)
    if viol_count > 0:
        score += min(viol_count * 8, 30)
        signals.append(f"code_violations:{viol_count}")

    permit_count = permits_by_address.get(prop.address.lower(), 0)
    if permit_count == 0 and prop.assessed_value > 0:
        score += 10
        signals.append("no_recent_permits")
    elif permit_count > 0:
        score -= 10
        signals.append(f"active_permits:{permit_count}")

    if prop.listing_price and prop.assessed_value:
        ratio = prop.listing_price / max(prop.assessed_value, 1)
        if ratio < 0.5:
            score += 15
            signals.append("price_below_assessed")

    if prop.days_on_market and prop.days_on_market > 120:
        score += 10
        signals.append(f"stale_listing:{prop.days_on_market}d")

    prop.vacancy_score = max(0.0, min(100.0, score))
    prop.open_violations = viol_count
    prop.recent_permits = permit_count
    prop.signals = signals
    return prop

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class VacancyWatch:
    def __init__(self, scraper_config: ScrapingConfig = None,
                 socrata_token: str = ""):
        self.scraper = FreeScraperClient(scraper_config or SCRAPER_CONFIG)
        self.city_data = DemoDataClient()  # Use demo data client
        self._demo_mode = False  # Demo data is always available

    # ------------------------------------------------------------------
    def run(self) -> VacancyWatchReport:
        log.info("=== Vacancy Watch starting (Demo Mode) ===")

        # 1. Pull demo data signals
        vacant_props = self.city_data.get_vacant_properties(limit=200)
        violations = self.city_data.get_code_violations(limit=500)
        permits = self.city_data.get_building_permits(days_back=90)
        traffic = self.city_data.get_traffic_incidents(days_back=30)

        # 2. Build lookup dicts (address → count)
        violations_by_addr = {}
        for v in violations:
            addr = v.get("address", v.get("street_address", "")).lower()
            violations_by_addr[addr] = violations_by_addr.get(addr, 0) + 1

        permits_by_addr = {}
        for p in permits:
            addr = p.address.lower()
            permits_by_addr[addr] = permits_by_addr.get(addr, 0) + 1

        # 3. Crawl real-estate sites
        log.info("Crawling %d real-estate URLs with free scraper...", len(REAL_ESTATE_URLS))
        try:
            crawl_results = self.scraper.crawl(REAL_ESTATE_URLS)
            real_estate_trends = parse_real_estate_signals(crawl_results)
        except Exception as exc:
            log.error("Crawl failed: %s. Using demo trends.", exc)
            real_estate_trends = self._demo_real_estate_trends()

        # 4. Score each property
        scored = [score_property(p, violations_by_addr, permits_by_addr) for p in vacant_props]
        scored.sort(key=lambda p: p.vacancy_score, reverse=True)
        high_risk = [p for p in scored if p.vacancy_score >= 50]

        # 5. Construction hotspots
        hotspot_addr = sorted(permits_by_addr.items(), key=lambda x: x[1], reverse=True)[:10]
        construction_hotspots = [
            {"address": a, "permit_count": c} for a, c in hotspot_addr
        ]

        # 6. Traffic alerts summary
        traffic_alerts = [
            {"location": t.location, "type": t.type, "date": t.date, "severity": t.severity}
            for t in traffic[:20]
        ]

        # 7. Summary statistics
        summary = {
            "total_city_vacant_properties": len(vacant_props),
            "high_risk_count": len(high_risk),
            "total_violations_indexed": len(violations),
            "permits_last_90_days": len(permits),
            "traffic_incidents_last_30d": len(traffic),
            "avg_vacancy_score": round(
                sum(p.vacancy_score for p in scored) / max(len(scored), 1), 1),
        }

        report = VacancyWatchReport(
            generated_at=datetime.utcnow().isoformat() + "Z",
            total_properties=len(scored),
            high_risk_vacancies=[asdict(p) for p in high_risk[:50]],
            construction_hotspots=construction_hotspots,
            traffic_alerts=traffic_alerts,
            real_estate_trends=real_estate_trends,
            summary=summary,
        )
        return report

    # ------------------------------------------------------------------
    @staticmethod
    def _demo_real_estate_trends() -> dict:
        return {
            "sources_crawled": 3,
            "listing_keywords": {
                "foreclosure": 12,
                "price reduced": 27,
                "vacant": 8,
                "days on market": 45,
            },
            "price_range": {"min": 45000, "max": 389000},
            "vacancy_mentions": 20,
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

    parser = argparse.ArgumentParser(description="Vacancy Watch – Montgomery AL Smart Cities Signal (Demo)")
    parser.add_argument("--output", default="vacancy_watch_demo_report.json",
                        help="Output JSON report path")
    parser.add_argument("--use-selenium", action="store_true",
                        help="Use Selenium for JavaScript-heavy sites")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run browser in headless mode")
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

    watch = VacancyWatch(scraper_config=config)
    try:
        report = watch.run()
        
        out_path = pathlib.Path(args.output)
        out_path.write_text(json.dumps(asdict(report), indent=2))
        log.info("Demo report written → %s", out_path.resolve())

        # Print summary to stdout
        s = report.summary
        print("\n" + "═" * 55)
        print("  VACANCY WATCH — MONTGOMERY AL (DEMO)")
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
        print("  🎉 This is DEMO data showing system capabilities!")
        print("  📊 Real Montgomery data APIs are currently unavailable")
        print("  🔧 To use real APIs, fix Montgomery Open Data endpoints")
    finally:
        watch.scraper.close()

if __name__ == "__main__":
    main()
