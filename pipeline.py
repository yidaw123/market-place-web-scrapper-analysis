from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from database import (
    get_connection,
    get_existing_ids,
    get_setting,
    upsert_post,
    DEFAULT_REGIONS,
    DEFAULT_NATIONAL_SUBREDDITS,
    DEFAULT_SEARCH_KEYWORDS,
)
from classifier import classify_post_rules, enrich_posts_with_llm
from scrapers import (
    scrape_craigslist_region,
    scrape_reddit_city_subreddits,
    scrape_reddit_national_subreddits,
    scrape_kijiji_canada,
    scrape_diy_stackexchange,
)


def run_scrape_pipeline(
    platforms: Optional[List[str]] = None,
    region_ids: Optional[List[str]] = None,
    include_national_reddit: bool = True,
    fetch_cl_details: bool = True,
) -> Dict[str, Any]:
    """
    Executes a concurrent multi-platform scrape across Reddit, Craigslist, Kijiji, and DIY StackExchange,
    applies the 2-stage Hybrid Intent & Service Categorization Engine,
    and saves leads to SQLite.
    """
    if not platforms:
        platforms = ["reddit", "craigslist", "kijiji", "stackexchange"]

    all_regions = get_setting("regions", DEFAULT_REGIONS)
    if region_ids:
        active_regions = [r for r in all_regions if r["id"] in region_ids]
    else:
        active_regions = [r for r in all_regions if r.get("enabled", True)]

    national_subs = get_setting("national_subreddits", DEFAULT_NATIONAL_SUBREDDITS)
    keywords = get_setting("search_keywords", DEFAULT_SEARCH_KEYWORDS)
    llm_config = get_setting("llm_config", {})

    started_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scrape_runs (started_at, platforms, regions, status)
        VALUES (?, ?, ?, ?)
        """,
        (
            started_at,
            ", ".join(platforms),
            ", ".join(r["name"] for r in active_regions),
            "running",
        ),
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()

    raw_posts: List[Dict[str, Any]] = []
    logs: List[str] = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        future_map = {}

        if "craigslist" in platforms:
            for reg in active_regions:
                fut = executor.submit(
                    scrape_craigslist_region,
                    reg["craigslist_subdomain"],
                    reg["name"],
                    keywords,
                    15,
                    fetch_cl_details,
                    20,
                    reg.get("country", "Canada"),
                    reg.get("province", ""),
                )
                future_map[fut] = f"Craigslist ({reg['name']})"

        if "reddit" in platforms:
            for reg in active_regions:
                if reg.get("subreddits"):
                    fut = executor.submit(
                        scrape_reddit_city_subreddits,
                        reg["subreddits"],
                        reg["name"],
                        keywords,
                        10,
                        reg.get("country", "Canada"),
                        reg.get("province", ""),
                    )
                    future_map[fut] = f"Reddit Local ({reg['name']})"

            if include_national_reddit and national_subs:
                fut = executor.submit(
                    scrape_reddit_national_subreddits,
                    national_subs,
                    18,
                )
                future_map[fut] = "Reddit National DIY/Home Subreddits"

        if "kijiji" in platforms:
            fut = executor.submit(scrape_kijiji_canada, keywords, 20)
            future_map[fut] = "Kijiji Canada (Wanted & Services)"

        if "stackexchange" in platforms:
            fut = executor.submit(scrape_diy_stackexchange, 35)
            future_map[fut] = "DIY Stack Exchange"

        for fut in as_completed(future_map):
            label = future_map[fut]
            try:
                batch = fut.result()
                raw_posts.extend(batch)
                logs.append(f"{label}: fetched {len(batch)} posts")
            except Exception as exc:
                logs.append(f"{label}: error ({exc})")

    # De-duplicate (the same Reddit post can come back from both local and national searches)
    deduped: Dict[str, Dict[str, Any]] = {}
    for p in raw_posts:
        deduped.setdefault(p["external_id"], p)
    raw_posts = list(deduped.values())
    existing_ids = get_existing_ids(list(deduped.keys()))

    # Stage 1: Hybrid Rule & Keyword Scoring Classification
    classified_posts = [classify_post_rules(p) for p in raw_posts]

    # Stage 2: Optional LLM Enrichment (Gemini / OpenAI) — only for posts we haven't seen before,
    # so repeated scrapes don't re-pay for the same posts.
    new_posts = [p for p in classified_posts if p["external_id"] not in existing_ids]
    seen_posts = [p for p in classified_posts if p["external_id"] in existing_ids]
    new_posts = enrich_posts_with_llm(new_posts, llm_config=llm_config)
    classified_posts = new_posts + seen_posts

    new_stored = 0
    demand_leads = 0
    for p in classified_posts:
        # Don't store brand-new noise, but DO update existing rows so stale labels get corrected
        if p.get("intent_type") == "irrelevant" and p["external_id"] not in existing_ids:
            continue
        is_new = upsert_post(p)
        if is_new:
            new_stored += 1
        if p.get("intent_type") in ("customer_hiring", "diy_help_needed"):
            demand_leads += 1

    finished_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE scrape_runs SET
            finished_at = ?,
            total_fetched = ?,
            new_stored = ?,
            demand_leads_found = ?,
            status = ?,
            log_summary = ?
        WHERE id = ?
        """,
        (
            finished_at,
            len(raw_posts),
            new_stored,
            demand_leads,
            "completed",
            " | ".join(logs),
            run_id,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "run_id": run_id,
        "total_fetched": len(raw_posts),
        "new_stored": new_stored,
        "demand_leads_found": demand_leads,
        "logs": logs,
    }
