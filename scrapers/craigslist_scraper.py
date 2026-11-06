import hashlib
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Dict, Any
from bs4 import BeautifulSoup

CL_SECTIONS = [
    ("lbg", "Labor Gigs"),
    ("dmg", "Domestic Gigs"),
    ("hss", "Household Services"),
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def fetch_craigslist_post_details(url: str, timeout: int = 6) -> Dict[str, str]:
    """Fetch the full description body and real posting date of a specific Craigslist post."""
    details = {"body": "", "posted_at": ""}
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        html = resp.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        body_el = soup.select_one("#postingbody")
        if body_el:
            # Remove "QR Code Link to This Post" boilerplate
            for qr in body_el.select(".print-information"):
                qr.decompose()
            text = body_el.get_text(" ", strip=True)
            details["body"] = text.replace("QR Code Link to This Post", "").strip()[:1200]
        time_el = soup.select_one(".postinginfos time[datetime]") or soup.select_one("time[datetime]")
        if time_el:
            raw_dt = time_el.get("datetime", "")
            try:
                details["posted_at"] = datetime.fromisoformat(raw_dt).astimezone(timezone.utc).isoformat()
            except ValueError:
                pass
    except Exception:
        pass
    return details


def scrape_craigslist_region(
    subdomain: str,
    region_name: str,
    queries: List[str],
    max_per_section: int = 18,
    fetch_details_for_gigs: bool = True,
    max_detail_fetches: int = 20,
) -> List[Dict[str, Any]]:
    """
    Scrape Craigslist Labor Gigs (lbg), Domestic Gigs (dmg), and Household Services (hss)
    for a given city subdomain (e.g. 'sfbay', 'austin', 'newyork').
    """
    results: Dict[str, Dict[str, Any]] = {}
    now_iso = datetime.now(timezone.utc).isoformat()

    # Combine queries into efficient search terms so we don't make excessive HTTP calls
    search_terms = queries[:2] if queries else ["handyman", "repair"]

    for section_code, section_label in CL_SECTIONS:
        # For gigs (lbg, dmg), search top 2 keywords; for hss (services), search top 1 keyword
        active_queries = search_terms if section_code in ("lbg", "dmg") else search_terms[:1]

        for q in active_queries:
            encoded_q = urllib.parse.quote_plus(q)
            url = f"https://{subdomain}.craigslist.org/search/{section_code}?query={encoded_q}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            try:
                resp = urllib.request.urlopen(req, timeout=10)
                html = resp.read().decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select("li.cl-static-search-result")

                count_for_query = 0
                for item in items:
                    if count_for_query >= max_per_section:
                        break

                    a_el = item.select_one("a")
                    title_el = item.select_one(".title")
                    price_el = item.select_one(".price")
                    loc_el = item.select_one(".location")

                    if not a_el or not title_el:
                        continue

                    post_url = a_el.get("href", "").strip()
                    title = title_el.get_text(" ", strip=True)
                    if not post_url or not title:
                        continue

                    # Deduplicate by URL hash
                    ext_id = "cl_" + hashlib.md5(post_url.encode("utf-8")).hexdigest()[:16]
                    if ext_id in results:
                        continue

                    price = price_el.get_text(strip=True) if price_el else ""
                    neighborhood = loc_el.get_text(strip=True) if loc_el else ""

                    results[ext_id] = {
                        "external_id": ext_id,
                        "platform": "craigslist",
                        "source_detail": f"{subdomain}/{section_code} ({section_label})",
                        "city_region": region_name,
                        "neighborhood": neighborhood,
                        "title": title,
                        # Leave body empty until we fetch the real description. (Previously a placeholder
                        # containing the search keyword was used, which biased the classifier.)
                        "body": "",
                        "url": post_url,
                        "author": "craigslist_poster",
                        "price_mention": price,
                        "posted_at": now_iso,
                        "score": 1 if section_code in ("lbg", "dmg") else 0,
                        "num_comments": 0,
                        "_is_gig": section_code in ("lbg", "dmg"),
                    }
                    count_for_query += 1
            except Exception:
                continue

    post_list = list(results.values())

    # Enrich gig posts with the real Craigslist body text + posting date. Gigs are where homeowner
    # demand lives, so they get priority; a small thread pool keeps this fast but polite.
    if fetch_details_for_gigs:
        to_fetch = [p for p in post_list if p.get("_is_gig")][:max_detail_fetches]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for p, details in zip(to_fetch, pool.map(lambda x: fetch_craigslist_post_details(x["url"], timeout=6), to_fetch)):
                if details["body"]:
                    p["body"] = details["body"]
                if details["posted_at"]:
                    p["posted_at"] = details["posted_at"]
                    p["posted_at_exact"] = True
    for p in post_list:
        p.pop("_is_gig", None)

    return post_list
