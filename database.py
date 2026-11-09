import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_research.db")

DEFAULT_REGIONS = [
    # --- Canada: Ontario ---
    {
        "id": "toronto",
        "name": "Toronto / GTA, ON",
        "city": "Toronto / GTA",
        "province": "Ontario",
        "country": "Canada",
        "craigslist_subdomain": "toronto",
        "subreddits": ["askTO", "toronto", "GTA", "mississauga", "Brampton"],
        "enabled": True,
    },
    {
        "id": "ottawa",
        "name": "Ottawa, ON",
        "city": "Ottawa",
        "province": "Ontario",
        "country": "Canada",
        "craigslist_subdomain": "ottawa",
        "subreddits": ["ottawa"],
        "enabled": True,
    },
    {
        "id": "hamilton",
        "name": "Hamilton / Burlington, ON",
        "city": "Hamilton / Burlington",
        "province": "Ontario",
        "country": "Canada",
        "craigslist_subdomain": "hamilton",
        "subreddits": ["Hamilton", "BurlingtonON"],
        "enabled": True,
    },
    {
        "id": "kitchener",
        "name": "Kitchener / Waterloo, ON",
        "city": "Kitchener / Waterloo",
        "province": "Ontario",
        "country": "Canada",
        "craigslist_subdomain": "kitchener",
        "subreddits": ["waterloo", "kitchener"],
        "enabled": False,
    },
    {
        "id": "london_on",
        "name": "London, ON",
        "city": "London",
        "province": "Ontario",
        "country": "Canada",
        "craigslist_subdomain": "londonon",
        "subreddits": ["londonontario"],
        "enabled": False,
    },
    # --- Canada: British Columbia ---
    {
        "id": "vancouver",
        "name": "Vancouver / Lower Mainland, BC",
        "city": "Vancouver / Lower Mainland",
        "province": "British Columbia",
        "country": "Canada",
        "craigslist_subdomain": "vancouver",
        "subreddits": ["vancouver", "AskVan", "burnaby", "SurreyBC"],
        "enabled": True,
    },
    {
        "id": "victoria",
        "name": "Victoria, BC",
        "city": "Victoria",
        "province": "British Columbia",
        "country": "Canada",
        "craigslist_subdomain": "victoria",
        "subreddits": ["VictoriaBC"],
        "enabled": True,
    },
    {
        "id": "kelowna",
        "name": "Kelowna / Okanagan, BC",
        "city": "Kelowna / Okanagan",
        "province": "British Columbia",
        "country": "Canada",
        "craigslist_subdomain": "kelowna",
        "subreddits": ["kelowna"],
        "enabled": False,
    },
    # --- Canada: Alberta ---
    {
        "id": "calgary",
        "name": "Calgary, AB",
        "city": "Calgary",
        "province": "Alberta",
        "country": "Canada",
        "craigslist_subdomain": "calgary",
        "subreddits": ["Calgary"],
        "enabled": True,
    },
    {
        "id": "edmonton",
        "name": "Edmonton, AB",
        "city": "Edmonton",
        "province": "Alberta",
        "country": "Canada",
        "craigslist_subdomain": "edmonton",
        "subreddits": ["Edmonton"],
        "enabled": True,
    },
    # --- Canada: Quebec ---
    {
        "id": "montreal",
        "name": "Montreal, QC",
        "city": "Montreal",
        "province": "Quebec",
        "country": "Canada",
        "craigslist_subdomain": "montreal",
        "subreddits": ["montreal"],
        "enabled": True,
    },
    {
        "id": "quebec_city",
        "name": "Quebec City, QC",
        "city": "Quebec City",
        "province": "Quebec",
        "country": "Canada",
        "craigslist_subdomain": "quebec",
        "subreddits": ["villedequebec"],
        "enabled": False,
    },
    # --- Canada: Manitoba, Saskatchewan, Nova Scotia ---
    {
        "id": "winnipeg",
        "name": "Winnipeg, MB",
        "city": "Winnipeg",
        "province": "Manitoba",
        "country": "Canada",
        "craigslist_subdomain": "winnipeg",
        "subreddits": ["Winnipeg"],
        "enabled": False,
    },
    {
        "id": "saskatoon",
        "name": "Saskatoon, SK",
        "city": "Saskatoon",
        "province": "Saskatchewan",
        "country": "Canada",
        "craigslist_subdomain": "saskatoon",
        "subreddits": ["saskatoon"],
        "enabled": False,
    },
    {
        "id": "halifax",
        "name": "Halifax, NS",
        "city": "Halifax",
        "province": "Nova Scotia",
        "country": "Canada",
        "craigslist_subdomain": "halifax",
        "subreddits": ["halifax"],
        "enabled": False,
    },
    # --- United States ---
    {
        "id": "sfbay",
        "name": "SF Bay Area, CA",
        "city": "SF Bay Area",
        "province": "California",
        "country": "United States",
        "craigslist_subdomain": "sfbay",
        "subreddits": ["bayarea", "AskSF", "sanfrancisco", "oakland", "SanJose"],
        "enabled": True,
    },
    {
        "id": "austin",
        "name": "Austin, TX",
        "city": "Austin",
        "province": "Texas",
        "country": "United States",
        "craigslist_subdomain": "austin",
        "subreddits": ["Austin", "AskAustin"],
        "enabled": True,
    },
    {
        "id": "nyc",
        "name": "New York City, NY",
        "city": "New York City",
        "province": "New York",
        "country": "United States",
        "craigslist_subdomain": "newyork",
        "subreddits": ["AskNYC", "nyc", "brooklyn", "queens"],
        "enabled": True,
    },
    {
        "id": "la",
        "name": "Los Angeles, CA",
        "city": "Los Angeles",
        "province": "California",
        "country": "United States",
        "craigslist_subdomain": "losangeles",
        "subreddits": ["AskLosAngeles", "LosAngeles"],
        "enabled": True,
    },
    {
        "id": "chicago",
        "name": "Chicago, IL",
        "city": "Chicago",
        "province": "Illinois",
        "country": "United States",
        "craigslist_subdomain": "chicago",
        "subreddits": ["chicago", "AskChicago"],
        "enabled": False,
    },
    {
        "id": "seattle",
        "name": "Seattle, WA",
        "city": "Seattle",
        "province": "Washington",
        "country": "United States",
        "craigslist_subdomain": "seattle",
        "subreddits": ["Seattle", "AskSeattle"],
        "enabled": False,
    },
]

DEFAULT_NATIONAL_SUBREDDITS = [
    "HomeImprovement",
    "DIY",
    "handyman",
    "fixit",
    "homeowners",
    "Plumbing",
    "landscaping",
]

DEFAULT_SEARCH_KEYWORDS = [
    "handyman",
    "plumber",
    "electrician",
    "drywall",
    "yard work",
    "landscaping",
    "carpenter",
    "painter",
    "gutter",
    "mount tv",
    "furniture assembly",
    "fence repair",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE NOT NULL,
            platform TEXT NOT NULL,
            source_detail TEXT NOT NULL,
            country TEXT DEFAULT 'National',
            province TEXT DEFAULT '',
            city_region TEXT NOT NULL,
            neighborhood TEXT DEFAULT '',
            title TEXT NOT NULL,
            body TEXT DEFAULT '',
            url TEXT NOT NULL,
            author TEXT DEFAULT '',
            price_mention TEXT DEFAULT '',
            posted_at TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            intent_type TEXT NOT NULL,
            intent_score INTEGER DEFAULT 50,
            primary_category TEXT NOT NULL,
            secondary_categories TEXT DEFAULT '[]',
            urgency TEXT DEFAULT 'medium',
            diy_difficulty TEXT DEFAULT 'moderate',
            extracted_pain_point TEXT DEFAULT '',
            marketing_angle TEXT DEFAULT '',
            classified_by TEXT DEFAULT 'hybrid_rules',
            score INTEGER DEFAULT 0,
            num_comments INTEGER DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            platforms TEXT NOT NULL,
            regions TEXT NOT NULL,
            total_fetched INTEGER DEFAULT 0,
            new_stored INTEGER DEFAULT 0,
            demand_leads_found INTEGER DEFAULT 0,
            status TEXT NOT NULL,
            log_summary TEXT DEFAULT ''
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    # Schema migration for existing DBs: add country and province columns if missing
    cur.execute("PRAGMA table_info(posts)")
    existing_cols = {row["name"] for row in cur.fetchall()}
    if "country" not in existing_cols:
        cur.execute("ALTER TABLE posts ADD COLUMN country TEXT DEFAULT 'National'")
    if "province" not in existing_cols:
        cur.execute("ALTER TABLE posts ADD COLUMN province TEXT DEFAULT ''")

    # Seed or upgrade regions setting so new Canadian provinces/cities are always present
    cur.execute("SELECT value FROM settings WHERE key = 'regions'")
    reg_row = cur.fetchone()
    if not reg_row:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("regions", json.dumps(DEFAULT_REGIONS)),
        )
    else:
        try:
            saved_regions = json.loads(reg_row["value"])
            saved_by_id = {r["id"]: r for r in saved_regions if isinstance(r, dict) and "id" in r}
            merged_regions = []
            for d in DEFAULT_REGIONS:
                if d["id"] in saved_by_id:
                    merged = {**d, "enabled": saved_by_id[d["id"]].get("enabled", d["enabled"])}
                else:
                    merged = dict(d)
                merged_regions.append(merged)
            cur.execute(
                "UPDATE settings SET value = ? WHERE key = 'regions'",
                (json.dumps(merged_regions),),
            )
        except Exception:
            cur.execute(
                "UPDATE settings SET value = ? WHERE key = 'regions'",
                (json.dumps(DEFAULT_REGIONS),),
            )

    # Backfill country/province on any older rows based on city_region
    for reg in DEFAULT_REGIONS:
        cur.execute(
            "UPDATE posts SET country = ?, province = ? WHERE city_region = ? AND (country IS NULL OR country = '' OR country = 'National')",
            (reg["country"], reg["province"], reg["name"]),
        )
    cur.execute("SELECT COUNT(*) as cnt FROM settings WHERE key = 'national_subreddits'")
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("national_subreddits", json.dumps(DEFAULT_NATIONAL_SUBREDDITS)),
        )
    cur.execute("SELECT COUNT(*) as cnt FROM settings WHERE key = 'search_keywords'")
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("search_keywords", json.dumps(DEFAULT_SEARCH_KEYWORDS)),
        )
    cur.execute("SELECT COUNT(*) as cnt FROM settings WHERE key = 'llm_config'")
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            (
                "llm_config",
                json.dumps(
                    {
                        "provider": "gemini",
                        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
                        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
                        "enable_llm_enrichment": True,
                    }
                ),
            ),
        )

    # One-time cleanup: older versions stored a placeholder Craigslist body containing the search
    # keyword (e.g. "matched query: 'handyman'"), which skewed classification. Blank those out.
    cur.execute(
        "UPDATE posts SET body = '' WHERE platform = 'craigslist' AND body LIKE 'Craigslist % listing in %matched query:%'"
    )
    cur.execute(
        "UPDATE posts SET primary_category = 'Yardwork & Landscaping' WHERE primary_category = 'Gardening & Landscaping'"
    )

    conn.commit()
    conn.close()


def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except Exception:
        return row["value"]


def set_setting(key: str, value: Any) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()


def get_existing_ids(external_ids: List[str]) -> set:
    """Return the subset of external_ids already stored (used to avoid re-paying for LLM enrichment)."""
    if not external_ids:
        return set()
    conn = get_connection()
    cur = conn.cursor()
    found: set = set()
    for i in range(0, len(external_ids), 500):
        chunk = external_ids[i:i + 500]
        cur.execute(
            f"SELECT external_id FROM posts WHERE external_id IN ({','.join('?' * len(chunk))})",
            chunk,
        )
        found.update(r["external_id"] for r in cur.fetchall())
    conn.close()
    return found


def upsert_post(post: Dict[str, Any], force: bool = False) -> bool:
    """
    Insert a post or update it if it already exists. Returns True if newly inserted.
    An existing LLM classification is not overwritten by a rules-only classification unless force=True.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, classified_by FROM posts WHERE external_id = ?", (post["external_id"],))
    existing = cur.fetchone()
    now_iso = datetime.now(timezone.utc).isoformat()

    secondary_json = (
        json.dumps(post.get("secondary_categories", []))
        if isinstance(post.get("secondary_categories"), list)
        else str(post.get("secondary_categories", "[]"))
    )

    if existing:
        # Always refresh engagement + content fields (bodies/dates may have been fetched this time)
        if post.get("body"):
            cur.execute("UPDATE posts SET body = ? WHERE external_id = ?", (post["body"], post["external_id"]))
        if post.get("posted_at_exact") and post.get("posted_at"):
            cur.execute("UPDATE posts SET posted_at = ? WHERE external_id = ?", (post["posted_at"], post["external_id"]))
        cur.execute(
            "UPDATE posts SET score = ?, num_comments = ? WHERE external_id = ?",
            (post.get("score", 0), post.get("num_comments", 0), post["external_id"]),
        )
        keep_llm = (
            not force
            and str(existing["classified_by"]).endswith("_llm")
            and not str(post.get("classified_by", "")).endswith("_llm")
        )
        if keep_llm:
            conn.commit()
            conn.close()
            return False
        cur.execute(
            """
            UPDATE posts SET
                country = ?,
                province = ?,
                city_region = ?,
                intent_type = ?,
                intent_score = ?,
                primary_category = ?,
                secondary_categories = ?,
                urgency = ?,
                diy_difficulty = ?,
                extracted_pain_point = ?,
                marketing_angle = ?,
                classified_by = ?,
                price_mention = ?
            WHERE external_id = ?
            """,
            (
                post.get("country", "National"),
                post.get("province", ""),
                post.get("city_region", "National / Online"),
                post.get("intent_type", "diy_help_needed"),
                post.get("intent_score", 50),
                post.get("primary_category", "General Handyman"),
                secondary_json,
                post.get("urgency", "medium"),
                post.get("diy_difficulty", "moderate"),
                post.get("extracted_pain_point", ""),
                post.get("marketing_angle", ""),
                post.get("classified_by", "hybrid_rules"),
                post.get("price_mention", ""),
                post["external_id"],
            ),
        )
        conn.commit()
        conn.close()
        return False
    else:
        cur.execute(
            """
            INSERT INTO posts (
                external_id, platform, source_detail, country, province, city_region, neighborhood,
                title, body, url, author, price_mention, posted_at, scraped_at,
                intent_type, intent_score, primary_category, secondary_categories,
                urgency, diy_difficulty, extracted_pain_point, marketing_angle,
                classified_by, score, num_comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post["external_id"],
                post["platform"],
                post.get("source_detail", ""),
                post.get("country", "National"),
                post.get("province", ""),
                post.get("city_region", "National / Online"),
                post.get("neighborhood", ""),
                post["title"],
                post.get("body", ""),
                post["url"],
                post.get("author", "anonymous"),
                post.get("price_mention", ""),
                post.get("posted_at", now_iso),
                now_iso,
                post.get("intent_type", "diy_help_needed"),
                post.get("intent_score", 50),
                post.get("primary_category", "General Handyman"),
                secondary_json,
                post.get("urgency", "medium"),
                post.get("diy_difficulty", "moderate"),
                post.get("extracted_pain_point", ""),
                post.get("marketing_angle", ""),
                post.get("classified_by", "hybrid_rules"),
                post.get("score", 0),
                post.get("num_comments", 0),
            ),
        )
        conn.commit()
        conn.close()
        return True


def query_posts(
    platform: Optional[str] = None,
    intent_type: Optional[str] = None,
    category: Optional[str] = None,
    country: Optional[str] = None,
    province: Optional[str] = None,
    city_region: Optional[str] = None,
    urgency: Optional[str] = None,
    search: Optional[str] = None,
    min_score: int = 0,
    limit: int = 250,
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    clauses = ["intent_score >= ?"]
    params: List[Any] = [min_score]

    if platform and platform != "all":
        clauses.append("platform = ?")
        params.append(platform)

    if intent_type and intent_type != "all":
        if intent_type == "demand_only":
            clauses.append("intent_type IN ('customer_hiring', 'diy_help_needed')")
        else:
            clauses.append("intent_type = ?")
            params.append(intent_type)

    if category and category != "all":
        clauses.append("primary_category = ?")
        params.append(category)

    if country and country != "all":
        clauses.append("country = ?")
        params.append(country)

    if province and province != "all":
        clauses.append("province = ?")
        params.append(province)

    if city_region and city_region != "all":
        clauses.append("city_region = ?")
        params.append(city_region)

    if urgency and urgency != "all":
        clauses.append("urgency = ?")
        params.append(urgency)

    if search and search.strip():
        q = f"%{search.strip()}%"
        clauses.append("(title LIKE ? OR body LIKE ? OR neighborhood LIKE ? OR source_detail LIKE ?)")
        params.extend([q, q, q, q])

    where_sql = " AND ".join(clauses)
    sql = f"""
        SELECT * FROM posts
        WHERE {where_sql}
        ORDER BY
            CASE WHEN intent_type = 'customer_hiring' THEN 0
                 WHEN intent_type = 'diy_help_needed' THEN 1
                 ELSE 2 END ASC,
            intent_score DESC,
            posted_at DESC
        LIMIT ?
    """
    params.append(limit)
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        try:
            r["secondary_categories"] = json.loads(r.get("secondary_categories") or "[]")
        except Exception:
            r["secondary_categories"] = []
    conn.close()
    return rows


def get_analytics_summary(
    country: Optional[str] = None,
    province: Optional[str] = None,
    city_region: Optional[str] = None,
) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()

    geo_clauses: List[str] = []
    geo_params: List[Any] = []
    if country and country != "all":
        geo_clauses.append("country = ?")
        geo_params.append(country)
    if province and province != "all":
        geo_clauses.append("province = ?")
        geo_params.append(province)
    if city_region and city_region != "all":
        geo_clauses.append("city_region = ?")
        geo_params.append(city_region)

    where_geo_only = ("WHERE " + " AND ".join(geo_clauses)) if geo_clauses else ""
    where_not_irr = "WHERE intent_type != 'irrelevant'" + ((" AND " + " AND ".join(geo_clauses)) if geo_clauses else "")
    where_demand = "WHERE intent_type IN ('customer_hiring', 'diy_help_needed')" + ((" AND " + " AND ".join(geo_clauses)) if geo_clauses else "")

    # Total counts by intent
    cur.execute(
        f"""
        SELECT intent_type, COUNT(*) as count
        FROM posts
        {where_geo_only}
        GROUP BY intent_type
        """,
        geo_params,
    )
    intent_counts = {r["intent_type"]: r["count"] for r in cur.fetchall()}

    # Demand breakdown by service category (customer_hiring + diy_help_needed vs service_provider_ad)
    cur.execute(
        f"""
        SELECT
            primary_category,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as hiring_count,
            SUM(CASE WHEN intent_type = 'diy_help_needed' THEN 1 ELSE 0 END) as diy_count,
            SUM(CASE WHEN intent_type IN ('customer_hiring', 'diy_help_needed') THEN 1 ELSE 0 END) as total_demand,
            SUM(CASE WHEN intent_type = 'service_provider_ad' THEN 1 ELSE 0 END) as provider_supply,
            ROUND(AVG(CASE WHEN intent_type IN ('customer_hiring', 'diy_help_needed') THEN intent_score ELSE NULL END), 1) as avg_intent_score
        FROM posts
        {where_not_irr}
        GROUP BY primary_category
        ORDER BY total_demand DESC, hiring_count DESC
        """,
        geo_params,
    )
    category_breakdown = [dict(r) for r in cur.fetchall()]

    # Regional breakdown
    cur.execute(
        f"""
        SELECT
            city_region,
            province,
            country,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as hiring_count,
            SUM(CASE WHEN intent_type = 'diy_help_needed' THEN 1 ELSE 0 END) as diy_count,
            SUM(CASE WHEN intent_type IN ('customer_hiring', 'diy_help_needed') THEN 1 ELSE 0 END) as total_demand,
            SUM(CASE WHEN intent_type = 'service_provider_ad' THEN 1 ELSE 0 END) as provider_supply
        FROM posts
        {where_not_irr}
        GROUP BY city_region, province, country
        ORDER BY total_demand DESC
        """,
        geo_params,
    )
    region_breakdown = [dict(r) for r in cur.fetchall()]

    # Platform breakdown
    cur.execute(
        f"""
        SELECT
            platform,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as hiring_count,
            SUM(CASE WHEN intent_type = 'diy_help_needed' THEN 1 ELSE 0 END) as diy_count,
            SUM(CASE WHEN intent_type = 'service_provider_ad' THEN 1 ELSE 0 END) as provider_supply,
            COUNT(*) as total
        FROM posts
        {where_not_irr}
        GROUP BY platform
        """,
        geo_params,
    )
    platform_breakdown = [dict(r) for r in cur.fetchall()]

    # Top neighborhoods / subreddits for customer demand
    cur.execute(
        f"""
        SELECT
            source_detail,
            platform,
            city_region,
            COUNT(*) as demand_count,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as direct_hiring
        FROM posts
        {where_demand}
        GROUP BY source_detail, platform, city_region
        ORDER BY direct_hiring DESC, demand_count DESC
        LIMIT 12
        """,
        geo_params,
    )
    top_channels = [dict(r) for r in cur.fetchall()]

    # Recent scrape runs
    cur.execute("SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 5")
    recent_runs = [dict(r) for r in cur.fetchall()]

    conn.close()

    total_hiring = intent_counts.get("customer_hiring", 0)
    total_diy = intent_counts.get("diy_help_needed", 0)
    total_supply = intent_counts.get("service_provider_ad", 0)
    total_jobs = intent_counts.get("job_posting", 0)
    total_demand = total_hiring + total_diy

    return {
        "kpis": {
            "total_posts": sum(intent_counts.values()),
            "total_demand_leads": total_demand,
            "direct_hiring_leads": total_hiring,
            "diy_conversion_leads": total_diy,
            "competitor_supply_ads": total_supply,
            "job_postings": total_jobs,
        },
        "category_breakdown": category_breakdown,
        "region_breakdown": region_breakdown,
        "platform_breakdown": platform_breakdown,
        "top_channels": top_channels,
        "recent_runs": recent_runs,
    }


def get_demand_trends(
    period: str = "1Y",
    country: Optional[str] = None,
    province: Optional[str] = None,
    city_region: Optional[str] = None,
    categories_list: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Returns stock-market style time-series and seasonality demand data broken down
    by work category (customer_hiring + diy_help_needed).
    Supported periods: '7D', '1M', '3M', '6M', '1Y', 'ALL', 'SEASONALITY'
    """
    conn = get_connection()
    cur = conn.cursor()

    clauses = ["intent_type IN ('customer_hiring', 'diy_help_needed')"]
    params: List[Any] = []
    if country and country != "all":
        clauses.append("country = ?")
        params.append(country)
    if province and province != "all":
        clauses.append("province = ?")
        params.append(province)
    if city_region and city_region != "all":
        clauses.append("city_region = ?")
        params.append(city_region)

    where_sql = "WHERE " + " AND ".join(clauses)
    cur.execute(
        f"SELECT posted_at, primary_category, intent_type FROM posts {where_sql}",
        params,
    )
    rows = cur.fetchall()
    conn.close()

    default_cats = categories_list or [
        "Plumbing & Drain",
        "Electrical & Lighting",
        "Yardwork & Landscaping",
        "Painting & Drywall",
        "Carpentry, Doors & Windows",
        "Mounting & Furniture Assembly",
        "Roofing, Siding & Gutters",
        "Flooring & Tile",
        "Appliance & HVAC Repair",
        "General Handyman & Odd Jobs",
    ]
    all_series_keys = ["All Demand"] + default_cats

    # Parse dates safely
    parsed_rows = []
    max_dt: Optional[datetime] = None
    for r in rows:
        raw_dt = str(r["posted_at"] or "")[:19]
        if len(raw_dt) < 10:
            continue
        try:
            dt = datetime.strptime(raw_dt[:10], "%Y-%m-%d")
            parsed_rows.append((dt, r["primary_category"]))
            if max_dt is None or dt > max_dt:
                max_dt = dt
        except ValueError:
            continue

    if max_dt is None:
        max_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    period_norm = (period or "1Y").upper()
    month_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    buckets: List[Dict[str, str]] = []
    if period_norm == "SEASONALITY":
        for m_idx in range(1, 13):
            buckets.append({"key": f"{m_idx:02d}", "label": month_abbr[m_idx - 1]})
        series = {k: [0] * 12 for k in all_series_keys}
        for dt, cat in parsed_rows:
            b_idx = dt.month - 1
            series["All Demand"][b_idx] += 1
            if cat in series:
                series[cat][b_idx] += 1
    elif period_norm in ("7D", "1M"):
        num_days = 7 if period_norm == "7D" else 30
        start_dt = max_dt - timedelta(days=num_days - 1)
        key_to_idx: Dict[str, int] = {}
        for i in range(num_days):
            d = start_dt + timedelta(days=i)
            k = d.strftime("%Y-%m-%d")
            lbl = f"{month_abbr[d.month - 1]} {d.day:02d}"
            key_to_idx[k] = i
            buckets.append({"key": k, "label": lbl})
        series = {k: [0] * num_days for k in all_series_keys}
        for dt, cat in parsed_rows:
            k = dt.strftime("%Y-%m-%d")
            if k in key_to_idx:
                idx = key_to_idx[k]
                series["All Demand"][idx] += 1
                if cat in series:
                    series[cat][idx] += 1
    elif period_norm in ("3M", "6M"):
        num_weeks = 13 if period_norm == "3M" else 26
        # Align end of last 7-day bucket to max_dt
        start_dt = max_dt - timedelta(days=num_weeks * 7 - 1)
        for w in range(num_weeks):
            w_start = start_dt + timedelta(days=w * 7)
            w_end = w_start + timedelta(days=6)
            lbl = f"{month_abbr[w_end.month - 1]} {w_end.day:02d}"
            buckets.append({"key": w_end.strftime("%Y-%m-%d"), "label": lbl})
        series = {k: [0] * num_weeks for k in all_series_keys}
        for dt, cat in parsed_rows:
            delta_days = (dt - start_dt).days
            if 0 <= delta_days < num_weeks * 7:
                w_idx = delta_days // 7
                series["All Demand"][w_idx] += 1
                if cat in series:
                    series[cat][w_idx] += 1
    else:
        # '1Y' (12 months) or 'ALL' (24 months up to max_dt)
        num_months = 12 if period_norm == "1Y" else 24
        end_y, end_m = max_dt.year, max_dt.month
        key_to_idx = {}
        month_list = []
        y, m = end_y, end_m
        for _ in range(num_months):
            month_list.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        month_list.reverse()
        for idx, (yy, mm) in enumerate(month_list):
            k = f"{yy:04d}-{mm:02d}"
            lbl = f"{month_abbr[mm - 1]} '{str(yy)[2:]}"
            key_to_idx[k] = idx
            buckets.append({"key": k, "label": lbl})
        series = {k: [0] * num_months for k in all_series_keys}
        for dt, cat in parsed_rows:
            k = f"{dt.year:04d}-{dt.month:02d}"
            if k in key_to_idx:
                idx = key_to_idx[k]
                series["All Demand"][idx] += 1
                if cat in series:
                    series[cat][idx] += 1

    totals = {k: sum(vals) for k, vals in series.items()}
    return {
        "period": period_norm,
        "buckets": buckets,
        "series": series,
        "totals": totals,
        "categories": default_cats,
    }
