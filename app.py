import csv
import io
import json
import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any, List

from database import (
    init_db,
    query_posts,
    get_analytics_summary,
    get_demand_trends,
    get_setting,
    set_setting,
    upsert_post,
    DEFAULT_REGIONS,
    DEFAULT_NATIONAL_SUBREDDITS,
    DEFAULT_SEARCH_KEYWORDS,
)
from classifier import SERVICE_CATEGORIES, classify_post_rules, enrich_posts_with_llm
from pipeline import run_scrape_pipeline

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SCRAPE_LOCK = threading.Lock()


def _qs_int(qs: Dict[str, List[str]], key: str, default: int, lo: int = 0, hi: int = 5000) -> int:
    """Parse an int query param safely (bad input falls back to default instead of crashing)."""
    try:
        return max(lo, min(hi, int(qs.get(key, [str(default)])[0])))
    except (ValueError, TypeError):
        return default


def _csv_safe(value: Any) -> Any:
    """
    Neutralize spreadsheet formula injection: scraped titles like "=HYPERLINK(...)" or "+1..."
    would otherwise execute as formulas when the CSV is opened in Excel/Sheets.
    """
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def build_marketing_recommendations(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Synthesizes actionable Marketing Campaign & Ad Targeting recommendations
    from the scraped Reddit & Craigslist demand vs. supply data.
    """
    recommendations: List[Dict[str, Any]] = []
    cats = summary.get("category_breakdown", [])
    regions = summary.get("region_breakdown", [])
    channels = summary.get("top_channels", [])

    # 1. Highest Demand / Underserved Category Opportunity
    if cats:
        top_cat = cats[0]
        cat_name = top_cat["primary_category"]
        cat_meta = SERVICE_CATEGORIES.get(cat_name, {})
        recommendations.append(
            {
                "type": "Top Service Vertical",
                "badge": "High Buyer Intent",
                "title": f"Prioritize '{cat_name}' in Paid Search & Local Social Ads",
                "metrics": f"{top_cat['total_demand']} demand signals ({top_cat['hiring_count']} direct hiring, {top_cat['diy_count']} DIY struggle)",
                "action": cat_meta.get(
                    "ad_hook",
                    f"Launch targeted ad sets for {cat_name} with instant quote booking.",
                ),
            }
        )

        # Find category with high DIY struggle ratio (prime for "Stop struggling with DIY" video/carousel ads)
        diy_heavy = sorted(cats, key=lambda x: x.get("diy_count", 0), reverse=True)
        if diy_heavy and diy_heavy[0].get("diy_count", 0) > 0:
            dc = diy_heavy[0]
            recommendations.append(
                {
                    "type": "DIY-to-Pro Conversion",
                    "badge": "Reddit Ad Target",
                    "title": f"Target DIY Frustration in '{dc['primary_category']}'",
                    "metrics": f"{dc['diy_count']} homeowners asking how to fix/troubleshoot {dc['primary_category']}",
                    "action": f"Run Reddit & Instagram before/after ads targeting DIYers: 'Halfway through a {dc['primary_category']} project? Book a vetted pro to finish it today.'",
                }
            )

        # Find highest Demand-to-Supply ratio (underserved market gap)
        underserved = sorted(
            [c for c in cats if c.get("total_demand", 0) >= 2],
            key=lambda x: (x.get("total_demand", 0) / max(1, x.get("provider_supply", 0))),
            reverse=True,
        )
        if underserved:
            u = underserved[0]
            recommendations.append(
                {
                    "type": "Marketplace Supply Gap",
                    "badge": "High Margin Opportunity",
                    "title": f"Demand Outpaces Supply in '{u['primary_category']}'",
                    "metrics": f"{u['total_demand']} buyer leads vs. {u['provider_supply']} provider ads",
                    "action": f"Recruit independent {u['primary_category']} specialists from Craigslist Household Services first so your marketplace has instant liquidity.",
                }
            )

    # 2. Top Geographic Hotspot
    local_regions = [r for r in regions if r["city_region"] != "National / DIY Forums"]
    if local_regions:
        top_reg = local_regions[0]
        recommendations.append(
            {
                "type": "Geographic Launch Market",
                "badge": "Geo-Targeting",
                "title": f"Focus Hyper-Local Launch Spend in {top_reg['city_region']}",
                "metrics": f"{top_reg['total_demand']} local demand leads ({top_reg['hiring_count']} actively hiring) & {top_reg['provider_supply']} local providers",
                "action": f"Concentrate initial zip-code ad spend and Craigslist provider outreach in {top_reg['city_region']}.",
            }
        )

    # 3. Top Community Channel
    if channels:
        top_ch = channels[0]
        recommendations.append(
            {
                "type": "Top Organic Channel",
                "badge": top_ch["platform"].capitalize(),
                "title": f"High-Converting Community: {top_ch['source_detail']}",
                "metrics": f"{top_ch['demand_count']} active leads ({top_ch['direct_hiring']} direct hiring requests)",
                "action": f"Monitor {top_ch['source_detail']} daily for high-urgency requests and engage with helpful cost breakdowns + marketplace booking links.",
            }
        )

    return recommendations


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        # Keep console output clean
        pass

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", errors="ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Clear-Site-Data", '"cache", "storage"')
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"error": "Dashboard UI not found"}, 404)
            return

        if path.startswith("/static/"):
            rel_name = os.path.basename(path)
            file_path = os.path.join(STATIC_DIR, rel_name)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    content = f.read()
                ctype = "text/css" if rel_name.endswith(".css") else "application/javascript" if rel_name.endswith(".js") else "text/plain"
                self.send_response(200)
                self.send_header("Content-Type", f"{ctype}; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.end_headers()
                self.wfile.write(content)
                return

        if path == "/api/summary":
            summary = get_analytics_summary(
                country=qs.get("country", ["all"])[0],
                province=qs.get("province", ["all"])[0],
                city_region=qs.get("city_region", ["all"])[0],
            )
            summary["recommendations"] = build_marketing_recommendations(summary)
            summary["categories_list"] = list(SERVICE_CATEGORIES.keys())
            self._send_json(summary)
            return

        if path == "/api/trends":
            trends = get_demand_trends(
                period=qs.get("period", ["1Y"])[0],
                country=qs.get("country", ["all"])[0],
                province=qs.get("province", ["all"])[0],
                city_region=qs.get("city_region", ["all"])[0],
                categories_list=list(SERVICE_CATEGORIES.keys()),
            )
            self._send_json(trends)
            return

        if path == "/api/posts":
            posts = query_posts(
                platform=qs.get("platform", ["all"])[0],
                intent_type=qs.get("intent_type", ["demand_only"])[0],
                category=qs.get("category", ["all"])[0],
                country=qs.get("country", ["all"])[0],
                province=qs.get("province", ["all"])[0],
                city_region=qs.get("city_region", ["all"])[0],
                urgency=qs.get("urgency", ["all"])[0],
                search=qs.get("search", [""])[0],
                min_score=_qs_int(qs, "min_score", 0, 0, 100),
                limit=_qs_int(qs, "limit", 300, 1, 2000),
            )
            self._send_json({"posts": posts, "count": len(posts)})
            return

        if path == "/api/export.csv":
            posts = query_posts(
                platform=qs.get("platform", ["all"])[0],
                intent_type=qs.get("intent_type", ["all"])[0],
                category=qs.get("category", ["all"])[0],
                country=qs.get("country", ["all"])[0],
                province=qs.get("province", ["all"])[0],
                city_region=qs.get("city_region", ["all"])[0],
                urgency=qs.get("urgency", ["all"])[0],
                search=qs.get("search", [""])[0],
                min_score=_qs_int(qs, "min_score", 0, 0, 100),
                limit=5000,
            )
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "ID",
                    "Platform",
                    "Source / Channel",
                    "Country",
                    "Province / State",
                    "City / Region",
                    "Neighborhood",
                    "Intent Type",
                    "Intent Score",
                    "Primary Service Category",
                    "Secondary Categories",
                    "Urgency",
                    "DIY Difficulty",
                    "Price Mention",
                    "Title",
                    "Extracted Pain Point",
                    "Recommended Ad Hook",
                    "Author",
                    "URL",
                    "Posted At",
                ]
            )
            for p in posts:
                writer.writerow(
                    [_csv_safe(v) for v in [
                        p.get("external_id"),
                        p.get("platform"),
                        p.get("source_detail"),
                        p.get("country"),
                        p.get("province"),
                        p.get("city_region"),
                        p.get("neighborhood"),
                        p.get("intent_type"),
                        p.get("intent_score"),
                        p.get("primary_category"),
                        ", ".join(p.get("secondary_categories", [])),
                        p.get("urgency"),
                        p.get("diy_difficulty"),
                        p.get("price_mention"),
                        p.get("title"),
                        p.get("extracted_pain_point"),
                        p.get("marketing_angle"),
                        p.get("author"),
                        p.get("url"),
                        p.get("posted_at"),
                    ]]
                )
            csv_bytes = output.getvalue().encode("utf-8-sig")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                'attachment; filename="handyman_market_research_leads.csv"',
            )
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        if path == "/api/settings":
            llm_cfg = get_setting("llm_config", {})
            self._send_json(
                {
                    "regions": get_setting("regions", DEFAULT_REGIONS),
                    "national_subreddits": get_setting("national_subreddits", DEFAULT_NATIONAL_SUBREDDITS),
                    "search_keywords": get_setting("search_keywords", DEFAULT_SEARCH_KEYWORDS),
                    "llm_config": {
                        "provider": llm_cfg.get("provider", "gemini"),
                        "has_gemini_key": bool(llm_cfg.get("gemini_api_key")),
                        "has_openai_key": bool(llm_cfg.get("openai_api_key")),
                        "enable_llm_enrichment": llm_cfg.get("enable_llm_enrichment", True),
                    },
                }
            )
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        if path == "/api/scrape":
            if not SCRAPE_LOCK.acquire(blocking=False):
                self._send_json({"error": "A scrape is already running — please wait for it to finish."}, 409)
                return
            try:
                platforms = body.get("platforms", ["reddit", "craigslist", "kijiji", "stackexchange"])
                region_ids = body.get("region_ids")
                include_national = body.get("include_national_reddit", True)
                result = run_scrape_pipeline(
                    platforms=platforms,
                    region_ids=region_ids,
                    include_national_reddit=include_national,
                    fetch_cl_details=True,
                )
            finally:
                SCRAPE_LOCK.release()
            self._send_json(result)
            return

        if path == "/api/settings":
            if "regions" in body and isinstance(body["regions"], list):
                set_setting("regions", body["regions"])
            if "national_subreddits" in body and isinstance(body["national_subreddits"], list):
                set_setting("national_subreddits", body["national_subreddits"])
            if "search_keywords" in body and isinstance(body["search_keywords"], list):
                set_setting("search_keywords", body["search_keywords"])
            if "llm_config" in body and isinstance(body["llm_config"], dict):
                current_llm = get_setting("llm_config", {})
                incoming = body["llm_config"]
                if "provider" in incoming:
                    current_llm["provider"] = incoming["provider"]
                if "enable_llm_enrichment" in incoming:
                    current_llm["enable_llm_enrichment"] = bool(incoming["enable_llm_enrichment"])
                if incoming.get("gemini_api_key"):
                    current_llm["gemini_api_key"] = incoming["gemini_api_key"].strip()
                if incoming.get("openai_api_key"):
                    current_llm["openai_api_key"] = incoming["openai_api_key"].strip()
                set_setting("llm_config", current_llm)

            self._send_json({"status": "saved"})
            return

        if path == "/api/reclassify":
            # Re-run the current rules over everything stored (force=True so rule improvements apply).
            # LLM enrichment is re-run too if a key is configured.
            posts = query_posts(intent_type="all", limit=5000)
            reclassified = [classify_post_rules(p) for p in posts]
            llm_cfg = get_setting("llm_config", {})
            reclassified = enrich_posts_with_llm(reclassified, llm_config=llm_cfg, max_batch=20)
            for p in reclassified:
                upsert_post(p, force=True)
            self._send_json({"status": "reclassified", "count": len(reclassified)})
            return

        self._send_json({"error": "Not found"}, 404)


def run_server(port: int = 8765) -> None:
    init_db()
    # Check if DB is empty; if so, run an initial live scrape automatically on startup!
    summary = get_analytics_summary()
    if summary["kpis"]["total_posts"] == 0:
        print("Database is empty — running initial live scrape of Reddit & Craigslist...")
        res = run_scrape_pipeline(
            platforms=["reddit", "craigslist"],
            include_national_reddit=True,
            fetch_cl_details=True,
        )
        print(
            f"Initial scrape finished: fetched {res['total_fetched']} posts, "
            f"identified {res['demand_leads_found']} homeowner demand leads!"
        )

    # On Windows, SO_REUSEADDR lets a second server silently bind the same port and split requests
    # with a stale instance. Disable it there so a duplicate launch fails loudly instead.
    ThreadingHTTPServer.allow_reuse_address = os.name != "nt"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    except OSError as exc:
        print(f"Could not start on port {port} ({exc}). Is the dashboard already running? Try --port 8081.")
        return
    print(f"Handyman Market Intelligence Dashboard running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Handyman Startup Market Research Scraper & Dashboard")
    parser.add_argument("--port", type=int, default=8765, help="Port to run the web dashboard on")
    parser.add_argument("--scrape-only", action="store_true", help="Run a live scrape and exit without starting the web server")
    args = parser.parse_args()

    init_db()
    if args.scrape_only:
        res = run_scrape_pipeline()
        print(json.dumps(res, indent=2))
    else:
        run_server(port=args.port)
