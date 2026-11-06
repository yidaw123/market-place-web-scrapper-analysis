import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Map Canadian postal/address mentions to (city_region, province)
KIJIJI_LOCATION_MAP: List[Tuple[str, str, str]] = [
    (r"\b(toronto|scarborough|etobicoke|north york|mississauga|brampton|markham|vaughan|richmond hill|oakville|pickering|ajax|oshawa|gta)\b", "Toronto / GTA, ON", "Ontario"),
    (r"\b(ottawa|kanata|nepean|orleans|gatineau)\b", "Ottawa, ON", "Ontario"),
    (r"\b(hamilton|burlington|stoney creek|ancaster|dundas|grimsby|brantford|st\.?\s*catharines|niagara)\b", "Hamilton / Burlington, ON", "Ontario"),
    (r"\b(kitchener|waterloo|cambridge|guelph)\b", "Kitchener / Waterloo, ON", "Ontario"),
    (r"\b(london|st\.?\s*thomas|woodstock|sarnia|windsor)\b", "London, ON", "Ontario"),
    (r"\b(vancouver|burnaby|surrey|richmond|coquitlam|new westminster|langley|delta|abbotsford|north vancouver|west vancouver)\b", "Vancouver / Lower Mainland, BC", "British Columbia"),
    (r"\b(victoria|saanich|langford|nanaimo|sidney)\b", "Victoria, BC", "British Columbia"),
    (r"\b(kelowna|vernon|penticton|kamloops|okanagan)\b", "Kelowna / Okanagan, BC", "British Columbia"),
    (r"\b(calgary|airdrie|cochrane|okotoks|red deer|lethbridge)\b", "Calgary, AB", "Alberta"),
    (r"\b(edmonton|st\.?\s*albert|sherwood park|spruce grove|leduc|fort saskatchewan)\b", "Edmonton, AB", "Alberta"),
    (r"\b(montreal|laval|longueuil|brossard|pointe-claire|dorval)\b", "Montreal, QC", "Quebec"),
    (r"\b(quebec city|quebec, qc|levis)\b", "Quebec City, QC", "Quebec"),
    (r"\b(winnipeg|brandon|steinbach)\b", "Winnipeg, MB", "Manitoba"),
    (r"\b(saskatoon|regina|prince albert|moose jaw)\b", "Saskatoon, SK", "Saskatchewan"),
    (r"\b(halifax|dartmouth|bedford|truro|sydney)\b", "Halifax, NS", "Nova Scotia"),
]

PROVINCE_CODE_FALLBACK = [
    (r"\b(ON|Ontario)\b", ("Toronto / GTA, ON", "Ontario")),
    (r"\b(BC|British Columbia)\b", ("Vancouver / Lower Mainland, BC", "British Columbia")),
    (r"\b(AB|Alberta)\b", ("Calgary, AB", "Alberta")),
    (r"\b(QC|Quebec)\b", ("Montreal, QC", "Quebec")),
    (r"\b(MB|Manitoba)\b", ("Winnipeg, MB", "Manitoba")),
    (r"\b(SK|Saskatchewan)\b", ("Saskatoon, SK", "Saskatchewan")),
    (r"\b(NS|Nova Scotia)\b", ("Halifax, NS", "Nova Scotia")),
]


def _resolve_canadian_location(address_str: str, title_str: str) -> Tuple[str, str]:
    combined = f"{address_str} {title_str}"
    lower = combined.lower()
    for pat, city_reg, prov in KIJIJI_LOCATION_MAP:
        if re.search(pat, lower):
            return city_reg, prov
    for pat, (city_reg, prov) in PROVINCE_CODE_FALLBACK:
        if re.search(pat, combined):
            return city_reg, prov
    return "Toronto / GTA, ON", "Ontario"


def _fetch_kijiji_listings(url: str) -> List[Dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        nxt_el = soup.select_one("script#__NEXT_DATA__")
        if not nxt_el or not nxt_el.string:
            return []
        nxt = json.loads(nxt_el.string)
        apollo = nxt.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
        return [v for k, v in apollo.items() if "Listing:" in k and isinstance(v, dict)]
    except Exception:
        return []


def scrape_kijiji_canada(queries: List[str], max_per_query: int = 20) -> List[Dict[str, Any]]:
    """
    Scrapes Kijiji Canada (kijiji.ca) across:
    1) Wanted Services (?ad=wanted) — Homeowners across Canadian provinces actively looking to hire a pro
    2) Skilled Trades & Home Services — Local demand & supply across Canadian cities
    """
    results: Dict[str, Dict[str, Any]] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    wanted_terms = [
        "handyman",
        "plumber",
        "carpenter",
        "electrician",
        "painter",
        "drywall",
        "fence repair",
        "yard work",
        "roof repair",
    ]

    # 1. Scrape Kijiji "Wanted" ads across Canada (high-intent homeowner requests)
    for term in wanted_terms:
        slug = urllib.parse.quote_plus(term.replace(" ", "-"))
        url = f"https://www.kijiji.ca/b-services/canada/{slug}/k0c72l0?ad=wanted"
        listings = _fetch_kijiji_listings(url)
        for item in listings[:max_per_query]:
            lid = item.get("id")
            title = (item.get("title") or "").strip()
            if not lid or not title:
                continue
            ext_id = f"kj_{lid}"
            if ext_id in results:
                continue

            desc = (item.get("description") or "").strip()
            loc_obj = item.get("location") or {}
            address = loc_obj.get("address") or loc_obj.get("name") or "Canada"
            city_region, province = _resolve_canadian_location(address, f"{title} {desc}")

            item_url = item.get("url") or ""
            if item_url.startswith("/"):
                item_url = f"https://www.kijiji.ca{item_url}"

            posted_at = item.get("sortingDate") or item.get("activationDate") or now_iso

            results[ext_id] = {
                "external_id": ext_id,
                "platform": "kijiji",
                "source_detail": "kijiji.ca (Wanted Services)",
                "country": "Canada",
                "province": province,
                "city_region": city_region,
                "neighborhood": address[:60],
                "title": title,
                "body": desc[:1200],
                "url": item_url,
                "author": "kijiji_homeowner",
                "price_mention": "",
                "posted_at": posted_at,
                "posted_at_exact": True,
                "score": 2,
                "num_comments": 0,
            }

    # 2. Scrape general Kijiji "handyman needed" / "plumber needed" across Canada
    for direct_q in ["handyman-needed", "plumber-needed", "carpenter-needed"]:
        url = f"https://www.kijiji.ca/b-canada/{direct_q}/k0l0"
        listings = _fetch_kijiji_listings(url)
        for item in listings[:15]:
            lid = item.get("id")
            title = (item.get("title") or "").strip()
            if not lid or not title:
                continue
            ext_id = f"kj_{lid}"
            if ext_id in results:
                continue

            desc = (item.get("description") or "").strip()
            loc_obj = item.get("location") or {}
            address = loc_obj.get("address") or loc_obj.get("name") or "Canada"
            city_region, province = _resolve_canadian_location(address, f"{title} {desc}")

            item_url = item.get("url") or ""
            if item_url.startswith("/"):
                item_url = f"https://www.kijiji.ca{item_url}"

            posted_at = item.get("sortingDate") or item.get("activationDate") or now_iso

            results[ext_id] = {
                "external_id": ext_id,
                "platform": "kijiji",
                "source_detail": f"kijiji.ca ({direct_q})",
                "country": "Canada",
                "province": province,
                "city_region": city_region,
                "neighborhood": address[:60],
                "title": title,
                "body": desc[:1200],
                "url": item_url,
                "author": "kijiji_user",
                "price_mention": "",
                "posted_at": posted_at,
                "posted_at_exact": True,
                "score": 1,
                "num_comments": 0,
            }

    return list(results.values())
