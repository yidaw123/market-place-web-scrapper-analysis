import html
import json
import urllib.request
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .reddit_scraper import detect_city_from_text

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def scrape_diy_stackexchange(limit: int = 35) -> List[Dict[str, Any]]:
    """
    Scrapes live homeowner repair & troubleshooting questions from
    Home Improvement Stack Exchange (diy.stackexchange.com).
    """
    url = (
        f"https://api.stackexchange.com/2.3/questions?"
        f"order=desc&sort=creation&site=diy&pagesize={min(50, limit)}&filter=withbody"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    results: List[Dict[str, Any]] = []
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        items = payload.get("items", [])
        for item in items:
            qid = item.get("question_id")
            raw_title = html.unescape(item.get("title") or "").strip()
            if not qid or not raw_title:
                continue

            raw_body_html = item.get("body") or ""
            body_text = BeautifulSoup(raw_body_html, "html.parser").get_text(" ", strip=True)
            tags = item.get("tags") or []
            tags_str = ", ".join(tags[:4])

            created_ts = item.get("creation_date")
            if isinstance(created_ts, (int, float)) and created_ts > 0:
                posted_at = datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat()
            else:
                posted_at = datetime.now(timezone.utc).isoformat()

            city_region, province, country = detect_city_from_text(
                f"{raw_title} {body_text}",
                default_region="National / DIY Forums",
                default_province="",
                default_country="National",
            )

            owner = item.get("owner") or {}
            author = html.unescape(owner.get("display_name") or "homeowner")

            results.append(
                {
                    "external_id": f"se_{qid}",
                    "platform": "stackexchange",
                    "source_detail": f"diy.stackexchange ({tags_str})" if tags_str else "diy.stackexchange.com",
                    "country": country,
                    "province": province,
                    "city_region": city_region,
                    "neighborhood": "",
                    "title": raw_title,
                    "body": body_text[:1200],
                    "url": item.get("link") or f"https://diy.stackexchange.com/questions/{qid}",
                    "author": author,
                    "price_mention": "",
                    "posted_at": posted_at,
                    "posted_at_exact": True,
                    "score": int(item.get("score") or 0),
                    "num_comments": int(item.get("answer_count") or 0),
                }
            )
    except Exception:
        pass
    return results
