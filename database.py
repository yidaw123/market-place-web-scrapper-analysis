import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_research.db")

DEFAULT_REGIONS = [
    {
        "id": "sfbay",
        "name": "SF Bay Area, CA",
        "craigslist_subdomain": "sfbay",
        "subreddits": ["bayarea", "AskSF", "sanfrancisco", "oakland", "SanJose"],
        "enabled": True,
    },
    {
        "id": "austin",
        "name": "Austin, TX",
        "craigslist_subdomain": "austin",
        "subreddits": ["Austin", "AskAustin"],
        "enabled": True,
    },
    {
        "id": "nyc",
        "name": "New York City, NY",
        "craigslist_subdomain": "newyork",
        "subreddits": ["AskNYC", "nyc", "brooklyn", "queens"],
        "enabled": True,
    },
    {
        "id": "la",
        "name": "Los Angeles, CA",
        "craigslist_subdomain": "losangeles",
        "subreddits": ["AskLosAngeles", "LosAngeles"],
        "enabled": True,
    },
    {
        "id": "chicago",
        "name": "Chicago, IL",
        "craigslist_subdomain": "chicago",
        "subreddits": ["chicago", "AskChicago"],
        "enabled": False,
    },
    {
        "id": "seattle",
        "name": "Seattle, WA",
        "craigslist_subdomain": "seattle",
        "subreddits": ["Seattle", "AskSeattle"],
        "enabled": False,
    },
    {
        "id": "denver",
        "name": "Denver, CO",
        "craigslist_subdomain": "denver",
        "subreddits": ["Denver"],
        "enabled": False,
    },
    {
        "id": "atlanta",
        "name": "Atlanta, GA",
        "craigslist_subdomain": "atlanta",
        "subreddits": ["Atlanta"],
        "enabled": False,
    },
    {
        "id": "dallas",
        "name": "Dallas / Fort Worth, TX",
        "craigslist_subdomain": "dallas",
        "subreddits": ["Dallas", "FortWorth"],
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

    # Seed default settings if not present
    cur.execute("SELECT COUNT(*) as cnt FROM settings WHERE key = 'regions'")
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("regions", json.dumps(DEFAULT_REGIONS)),
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
                external_id, platform, source_detail, city_region, neighborhood,
                title, body, url, author, price_mention, posted_at, scraped_at,
                intent_type, intent_score, primary_category, secondary_categories,
                urgency, diy_difficulty, extracted_pain_point, marketing_angle,
                classified_by, score, num_comments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post["external_id"],
                post["platform"],
                post.get("source_detail", ""),
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


def get_analytics_summary() -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()

    # Total counts by intent
    cur.execute(
        """
        SELECT intent_type, COUNT(*) as count
        FROM posts
        GROUP BY intent_type
        """
    )
    intent_counts = {r["intent_type"]: r["count"] for r in cur.fetchall()}

    # Demand breakdown by service category (customer_hiring + diy_help_needed vs service_provider_ad)
    cur.execute(
        """
        SELECT
            primary_category,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as hiring_count,
            SUM(CASE WHEN intent_type = 'diy_help_needed' THEN 1 ELSE 0 END) as diy_count,
            SUM(CASE WHEN intent_type IN ('customer_hiring', 'diy_help_needed') THEN 1 ELSE 0 END) as total_demand,
            SUM(CASE WHEN intent_type = 'service_provider_ad' THEN 1 ELSE 0 END) as provider_supply,
            ROUND(AVG(CASE WHEN intent_type IN ('customer_hiring', 'diy_help_needed') THEN intent_score ELSE NULL END), 1) as avg_intent_score
        FROM posts
        WHERE intent_type != 'irrelevant'
        GROUP BY primary_category
        ORDER BY total_demand DESC, hiring_count DESC
        """
    )
    category_breakdown = [dict(r) for r in cur.fetchall()]

    # Regional breakdown
    cur.execute(
        """
        SELECT
            city_region,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as hiring_count,
            SUM(CASE WHEN intent_type = 'diy_help_needed' THEN 1 ELSE 0 END) as diy_count,
            SUM(CASE WHEN intent_type IN ('customer_hiring', 'diy_help_needed') THEN 1 ELSE 0 END) as total_demand,
            SUM(CASE WHEN intent_type = 'service_provider_ad' THEN 1 ELSE 0 END) as provider_supply
        FROM posts
        WHERE intent_type != 'irrelevant'
        GROUP BY city_region
        ORDER BY total_demand DESC
        """
    )
    region_breakdown = [dict(r) for r in cur.fetchall()]

    # Platform breakdown
    cur.execute(
        """
        SELECT
            platform,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as hiring_count,
            SUM(CASE WHEN intent_type = 'diy_help_needed' THEN 1 ELSE 0 END) as diy_count,
            SUM(CASE WHEN intent_type = 'service_provider_ad' THEN 1 ELSE 0 END) as provider_supply,
            COUNT(*) as total
        FROM posts
        WHERE intent_type != 'irrelevant'
        GROUP BY platform
        """
    )
    platform_breakdown = [dict(r) for r in cur.fetchall()]

    # Top neighborhoods / subreddits for customer demand
    cur.execute(
        """
        SELECT
            source_detail,
            platform,
            city_region,
            COUNT(*) as demand_count,
            SUM(CASE WHEN intent_type = 'customer_hiring' THEN 1 ELSE 0 END) as direct_hiring
        FROM posts
        WHERE intent_type IN ('customer_hiring', 'diy_help_needed')
        GROUP BY source_detail, platform, city_region
        ORDER BY direct_hiring DESC, demand_count DESC
        LIMIT 12
        """
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
