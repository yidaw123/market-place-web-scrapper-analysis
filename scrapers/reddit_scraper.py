import json
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

ARCTIC_SHIFT_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"
_REDDIT_LOCK = threading.Lock()
_LAST_CALL_TS = 0.0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

CITY_MENTION_MAP = [
    # Canadian cities & provinces
    (r"\b(toronto|gta|mississauga|brampton|scarborough|etobicoke|north york|markham|vaughan|oakville)\b", ("Toronto / GTA, ON", "Ontario", "Canada")),
    (r"\b(ottawa|kanata|nepean|orleans)\b", ("Ottawa, ON", "Ontario", "Canada")),
    (r"\b(hamilton|burlington|stoney creek|ancaster)\b", ("Hamilton / Burlington, ON", "Ontario", "Canada")),
    (r"\b(kitchener|waterloo|cambridge|guelph)\b", ("Kitchener / Waterloo, ON", "Ontario", "Canada")),
    (r"\b(london ontario|london, on)\b", ("London, ON", "Ontario", "Canada")),
    (r"\b(vancouver|burnaby|surrey|richmond bc|coquitlam|new westminster|north van|lower mainland)\b", ("Vancouver / Lower Mainland, BC", "British Columbia", "Canada")),
    (r"\b(victoria bc|saanich|langford)\b", ("Victoria, BC", "British Columbia", "Canada")),
    (r"\b(kelowna|okanagan|kamloops)\b", ("Kelowna / Okanagan, BC", "British Columbia", "Canada")),
    (r"\b(calgary|airdrie|okotoks|yyc)\b", ("Calgary, AB", "Alberta", "Canada")),
    (r"\b(edmonton|st\.? albert|sherwood park|yeg)\b", ("Edmonton, AB", "Alberta", "Canada")),
    (r"\b(montreal|laval|longueuil)\b", ("Montreal, QC", "Quebec", "Canada")),
    (r"\b(quebec city|ville de quebec)\b", ("Quebec City, QC", "Quebec", "Canada")),
    (r"\b(winnipeg|manitoba)\b", ("Winnipeg, MB", "Manitoba", "Canada")),
    (r"\b(saskatoon|regina|saskatchewan)\b", ("Saskatoon, SK", "Saskatchewan", "Canada")),
    (r"\b(halifax|dartmouth|nova scotia)\b", ("Halifax, NS", "Nova Scotia", "Canada")),
    # US cities
    (r"\b(san francisco|sf bay|bay area|oakland|san jose|berkeley|peninsula|east bay)\b", ("SF Bay Area, CA", "California", "United States")),
    (r"\b(austin|round rock|cedar park|pflugerville|atx)\b", ("Austin, TX", "Texas", "United States")),
    (r"\b(nyc|brooklyn|queens|manhattan|bronx|staten island|new york city)\b", ("New York City, NY", "New York", "United States")),
    (r"\b(los angeles|santa monica|pasadena|burbank|socal|hollywood|long beach)\b", ("Los Angeles, CA", "California", "United States")),
    (r"\b(chicago|chicagoland|evanston|naperville)\b", ("Chicago, IL", "Illinois", "United States")),
    (r"\b(seattle|bellevue|tacoma|redmond|kirkland)\b", ("Seattle, WA", "Washington", "United States")),
]


def detect_city_from_text(
    text: str,
    default_region: str = "National / DIY Forums",
    default_province: str = "",
    default_country: str = "National",
):
    lower = text.lower()
    for pattern, (region_label, prov, country) in CITY_MENTION_MAP:
        if re.search(pattern, lower):
            return region_label, prov, country
    return default_region, default_province, default_country


def _fetch_arctic_shift(subreddit: str, query: Optional[str] = None, limit: int = 25) -> Optional[List[Dict[str, Any]]]:
    """Returns a list of raw posts, or None if the request failed (so callers can fall back)."""
    global _LAST_CALL_TS
    params: Dict[str, Any] = {
        "subreddit": subreddit,
        "limit": limit,
        "sort": "desc",
    }
    if query:
        params["title"] = query

    url = f"{ARCTIC_SHIFT_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    # Serialize calls with a small gap; the free API returns 422 "slow down" when hammered
    with _REDDIT_LOCK:
        elapsed = time.time() - _LAST_CALL_TS
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
            return payload.get("data") or []
        except Exception:
            return None
        finally:
            _LAST_CALL_TS = time.time()


# Used to filter "latest posts" locally when the API's title search times out on big subreddits
_HOME_SERVICE_FILTER = re.compile(
    r"\b(handy ?man|handymen|plumb(?:er|ing)|electrician|contractor|carpenter|painter|landscap\w*|"
    r"gardener|roofer|drywall|leak\w*|repair\w*|install\w*|mount\w*|fence|gutter\w*|hvac|"
    r"water heater|toilet|faucet|appliance|yard work|tile|flooring|furniture assembly)\b",
    re.IGNORECASE,
)


def _normalize_reddit_post(
    raw: Dict[str, Any],
    default_region: str,
    default_province: str = "",
    default_country: str = "National",
) -> Optional[Dict[str, Any]]:
    post_id = raw.get("id")
    title = (raw.get("title") or "").strip()
    if not post_id or not title:
        return None

    selftext = (raw.get("selftext") or "").strip()
    if selftext in ("[removed]", "[deleted]"):
        selftext = ""

    subreddit = raw.get("subreddit") or "reddit"
    permalink = raw.get("permalink") or f"/r/{subreddit}/comments/{post_id}/"
    full_url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink

    created_utc = raw.get("created_utc")
    if isinstance(created_utc, (int, float)) and created_utc > 0:
        posted_at = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
    else:
        posted_at = datetime.now(timezone.utc).isoformat()

    city_region = default_region
    province = default_province
    country = default_country
    if default_region == "National / DIY Forums":
        city_region, province, country = detect_city_from_text(
            f"{title} {selftext}", default_region, default_province, default_country
        )

    return {
        "external_id": f"rd_{post_id}",
        "platform": "reddit",
        "source_detail": f"r/{subreddit}",
        "country": country,
        "province": province,
        "city_region": city_region,
        # Post flair (e.g. "Question") isn't a neighborhood; leave blank rather than mislabel location
        "neighborhood": "",
        "title": title,
        "body": selftext[:1500],
        "url": full_url,
        "author": f"u/{raw.get('author', 'redditor')}",
        "price_mention": "",
        "posted_at": posted_at,
        "posted_at_exact": True,
        "score": int(raw.get("score") or 0),
        "num_comments": int(raw.get("num_comments") or 0),
    }


def scrape_reddit_city_subreddits(
    subreddits: List[str],
    region_name: str,
    queries: List[str],
    limit_per_query: int = 12,
    country: str = "Canada",
    province: str = "",
) -> List[Dict[str, Any]]:
    """
    Search local city subreddits (e.g., r/Austin, r/AskSF, r/AskNYC) for handyman/home service inquiries.
    """
    results: Dict[str, Dict[str, Any]] = {}
    # Title search terms with the best signal-to-noise for local "who do I hire" posts
    search_terms = ["handyman", "plumber"]

    def _add(raw_posts: List[Dict[str, Any]], local_filter: bool = False) -> None:
        for raw in raw_posts:
            if local_filter and not _HOME_SERVICE_FILTER.search(f"{raw.get('title', '')} {raw.get('selftext', '')}"):
                continue
            norm = _normalize_reddit_post(
                raw,
                default_region=region_name,
                default_province=province,
                default_country=country,
            )
            if norm and norm["external_id"] not in results:
                results[norm["external_id"]] = norm

    for sub in subreddits[:2]:
        sub_before = len(results)
        for q in search_terms:
            raw_posts = _fetch_arctic_shift(subreddit=sub, query=q, limit=limit_per_query)
            if raw_posts is None:
                break
            _add(raw_posts)
        if len(results) - sub_before < 4:
            # Also scan the latest 100 posts with broad home-service keyword matching
            _add(_fetch_arctic_shift(subreddit=sub, query=None, limit=100) or [], local_filter=True)

    return list(results.values())


def scrape_reddit_national_subreddits(
    subreddits: List[str],
    limit_per_sub: int = 25,
) -> List[Dict[str, Any]]:
    """
    Scrape national home improvement & DIY subreddits (r/HomeImprovement, r/DIY, r/handyman, r/fixit, r/Plumbing).
    """
    results: Dict[str, Dict[str, Any]] = {}

    for sub in subreddits[:10]:
        raw_posts = _fetch_arctic_shift(subreddit=sub, query=None, limit=limit_per_sub) or []
        for raw in raw_posts:
            norm = _normalize_reddit_post(raw, default_region="National / DIY Forums")
            if norm and norm["external_id"] not in results:
                results[norm["external_id"]] = norm

    return list(results.values())
