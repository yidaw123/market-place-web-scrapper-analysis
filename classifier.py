import json
import re
import urllib.error
import urllib.request
from typing import Dict, Any, List, Tuple

SERVICE_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "Plumbing & Drain": {
        "keywords": [
            ("plumber", 5), ("plumbing", 5), ("leak", 4), ("leaking", 4),
            ("faucet", 4), ("toilet", 4), ("clog", 4), ("clogged", 4),
            ("drain", 4), ("pipe", 3), ("water heater", 5), ("shower valve", 5),
            ("garbage disposal", 5), ("sink", 3), ("sewer", 4), ("bidet", 4),
            ("sump pump", 5), ("hose bib", 4), ("water pressure", 4),
        ],
        "default_difficulty": "pro_required",
        "ad_hook": "Leaking pipe or stubborn clog? Book a vetted local plumber with upfront pricing—no surprise trip fees.",
    },
    "Electrical & Lighting": {
        "keywords": [
            ("electrician", 5), ("electrical", 5), ("outlet", 4), ("breaker", 4),
            ("wiring", 4), ("light fixture", 5), ("ceiling fan", 5), ("chandelier", 4),
            ("dimmer", 4), ("switch", 3), ("gfci", 5), ("panel", 3),
            ("recessed light", 5), ("ev charger", 5), ("thermostat wire", 4),
            ("sparking", 4), ("floodlight", 4), ("sconce", 4),
        ],
        "default_difficulty": "pro_required",
        "ad_hook": "Don't risk DIY shocks. Hire a background-checked electrical & lighting pro in minutes.",
    },
    "Gardening & Landscaping": {
        "keywords": [
            ("garden", 4), ("gardening", 5), ("landscaping", 5), ("landscaper", 5),
            ("yard work", 5), ("yard", 3), ("lawn", 4), ("mowing", 4),
            ("weeding", 5), ("weeds", 4), ("mulch", 4), ("pruning", 4),
            ("tree trimming", 5), ("hedge", 4), ("sprinkler", 4), ("irrigation", 5),
            ("sod", 4), ("patio", 3), ("overgrown", 4), ("leaf removal", 5),
            ("brush clearing", 5), ("digging", 3),
        ],
        "default_difficulty": "easy",
        "ad_hook": "Weekend too short for yard work? Book local gardening & landscaping help on-demand.",
    },
    "Painting & Drywall": {
        "keywords": [
            ("drywall", 5), ("sheetrock", 5), ("spackle", 4), ("plaster", 4),
            ("patch hole", 5), ("wall repair", 5), ("painter", 5), ("painting", 4),
            ("repaint", 4), ("touch up paint", 5), ("popcorn ceiling", 5), ("paint", 3),
            ("wallpaper", 4), ("staining", 3), ("baseboard paint", 4),
            ("ceiling crack", 4), ("mudding", 4), ("texture", 3),
        ],
        "default_difficulty": "moderate",
        "ad_hook": "Seamless drywall patching & interior painting—get matched with a top-rated finisher today.",
    },
    "Carpentry, Doors & Windows": {
        "keywords": [
            ("carpenter", 5), ("carpentry", 5), ("wood", 2), ("rot", 3),
            ("door", 3), ("window", 3), ("trim", 4), ("baseboard", 4),
            ("crown molding", 5), ("cabinet", 4), ("hinge", 4), ("weatherstripping", 4),
            ("deck repair", 5), ("deck", 3), ("fence", 4), ("gate", 3),
            ("framing", 4), ("shelving", 4), ("subfloor", 4), ("caulk", 3),
            ("sliding door", 4), ("screen door", 4),
        ],
        "default_difficulty": "moderate",
        "ad_hook": "Sticking doors, rotten trim, or fence damage? Hire a skilled local carpenter by the job.",
    },
    "Mounting & Furniture Assembly": {
        "keywords": [
            ("mount tv", 6), ("tv mounting", 6), ("hang tv", 6), ("ikea", 5),
            ("furniture assembly", 6), ("assemble", 4), ("assembly", 4),
            ("hang mirror", 5), ("hang art", 5), ("curtain rod", 5), ("blinds", 4),
            ("wall mount", 5), ("bookshelf", 4), ("studs", 3), ("anchor", 3),
            ("gazebo assembly", 5), ("shed assembly", 5), ("trampoline", 4),
        ],
        "default_difficulty": "easy",
        "ad_hook": "Skip the 40-page manual & crooked brackets. Same-day TV mounting & furniture assembly pros.",
    },
    "Roofing, Siding & Gutters": {
        "keywords": [
            ("roof", 4), ("roofer", 5), ("roofing", 5), ("shingle", 5),
            ("gutter", 5), ("gutters", 5), ("downspout", 5), ("siding", 5),
            ("fascia", 5), ("soffit", 5), ("flashing", 5), ("roof vent", 5),
            ("chimney", 4), ("power wash", 4), ("pressure wash", 4), ("moss", 3),
        ],
        "default_difficulty": "pro_required",
        "ad_hook": "Stay off the ladder! Book insured exterior, gutter & roof repair specialists near you.",
    },
    "Flooring & Tile": {
        "keywords": [
            ("tile", 4), ("tiling", 5), ("grout", 5), ("regrout", 5),
            ("backsplash", 5), ("flooring", 5), ("hardwood", 4), ("laminate", 4),
            ("lvp", 5), ("vinyl plank", 5), ("carpet", 3), ("marble", 3),
            ("mosaic", 4), ("cracked tile", 5), ("caulking tub", 5),
        ],
        "default_difficulty": "moderate",
        "ad_hook": "Cracked tile or worn grout? Connect with precision tile & flooring pros with verified portfolios.",
    },
    "Appliance & HVAC Repair": {
        "keywords": [
            ("appliance", 5), ("washer", 4), ("dryer", 4), ("dishwasher", 5),
            ("fridge", 4), ("refrigerator", 4), ("oven", 4), ("stove", 4),
            ("hvac", 5), ("furnace", 5), ("ac unit", 5), ("air conditioner", 5),
            ("mini split", 5), ("dryer vent", 5), ("water filter", 3),
        ],
        "default_difficulty": "pro_required",
        "ad_hook": "Broken appliance or AC acting up? Fast diagnostics & repair from local technicians.",
    },
    "General Handyman & Odd Jobs": {
        "keywords": [
            ("handyman", 5), ("handy man", 5), ("odd jobs", 5), ("punch list", 5),
            ("honey do", 5), ("home repair", 4), ("maintenance", 3),
            ("short-term rental", 4), ("airbnb", 4), ("move out repair", 5),
            ("property maintenance", 4), ("fix", 1), ("repair", 1),
        ],
        "default_difficulty": "moderate",
        "ad_hook": "Got a punch list of home repairs? Book one versatile, vetted handyman to knock it all out.",
    },
}

CUSTOMER_HIRING_PATTERNS = [
    r"\b(looking for|searching for|need|seeking|hire|hiring)\b.{0,35}\b(handyman|plumber|electrician|carpenter|painter|contractor|someone|help|pro|gardener|landscaper)\b",
    r"\b(handyman|plumber|electrician|carpenter|contractor|landscaper)\b.{0,20}\b(needed|wanted|recs|recommendations|recommendation|referral|referrals)\b",
    r"\b(recommend|recs for|anyone know a|who do you use for)\b.{0,35}\b(handyman|plumber|electrician|repair|painter|yard|landscaper|contractor)\b",
    r"\b(quote check|is this quote fair|quoted me|how much to pay|fair price for)\b",
    r"\b(need someone to|pay someone to|looking to hire)\b",
    r"\bon-call handyman\b",
]

DIY_HELP_PATTERNS = [
    r"\b(how do i|how to|can i|should i|help me|need advice|need advise|any advice)\b.{0,40}\b(fix|repair|replace|install|patch|remove|seal|build|mount)\b",
    r"\b(am i in over my head|diy or hire|call a pro|how hard is it to)\b",
    r"\b(what is wrong with|how would you fix|best way to fix|best way to repair)\b",
]

PROVIDER_AD_PATTERNS = [
    r"\b(licensed and insured|licensed & insured|free estimate|free estimates|no job too small)\b",
    r"\b(years of experience|yrs experience|available for hire|handyman for hire|offering.{0,20}services)\b",
    r"\b(call or text|text me for a quote|we specialize in|our services include|affordable rates)\b",
    r"\b(i am a handyman|local handyman available|skilled independent handyman)\b",
    r"\b(handyman services|repair services|we do it all|reasonable rates|best rates|call now|satisfaction guaranteed)\b",
    r"\bcall (?:me|us|\w+ anytime)\b|\b(text|call) (?:me|us) (?:at|for)\b",
    r"\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}",  # phone number in a listing is a strong provider-ad signal
]

# Employers / staffing agencies / gig apps recruiting WORKERS (not homeowners needing a job done).
# These are supply-side signals: labor demand + competitor activity.
JOB_POSTING_PATTERNS = [
    r"\b(our team|grow our team|join our team|we are hiring|now hiring|hiring immediately)\b",
    r"\b(helpers? wanted|workers? needed|technicians? needed|crew members?|positions? available)\b",
    r"\b(helpers?|tradesmen|tradespeople|laborers|independent contractors)\b",
    r"^\W*\$\s?\d+(?:\.\d\d)?\s?(?:/\s?h(?:ou)?r|per hour|an hour)\b",  # title leads with an hourly wage
    r"\$\s?\d+\s?(?:-\s?\$?\d+\s?)?(?:/\s?h(?:r|our)|per hour|an hour|per day|/\s?day)\b.{0,15}\b(start|starting|pay|dop)",
    r"\b(starting pay|pay starts|w-?2|1099 position|full[- ]time|part[- ]time|benefits|apply (?:at|now|online)|resume)\b",
    r"\b(earn on|sign up to earn|become a tasker|earn up to)\b",
    r"\b(porter|maintenance tech|maintenance technician|super(?:intendent)?)\b.{0,20}\b(job|position|wanted|needed)\b",
    r"\b(handyman company hiring|hiring experienced|hiring technicians|experienced .{0,25}wanted|experienced .{0,25}needed)\b",
]

# Homeowner one-off job signals that distinguish a real gig from a recruiting post.
HOMEOWNER_JOB_PATTERNS = [
    r"\b(my|our) (house|home|apartment|apt|condo|garage|yard|backyard|kitchen|bathroom|basement|fence|deck|roof)\b",
    r"\b(one[- ]time|small job|quick job|a few hours|this weekend|need .{0,20} (installed|fixed|repaired|mounted|assembled|replaced))\b",
]

# Posts that mention a pro but aren't a request (scam warnings, rants, pro-community chatter).
NON_REQUEST_PATTERNS = [
    r"\b(scam|scammer|scammed|ripped off|do not hire|don't hire|warning|psa)\b",
    r"\b(mod post|new mod|subreddit rules|weekly thread|megathread)\b",
    r"\b(my clients?|nightmare clients?|for my business|my handyman business|bidding a job|how much should i charge|what do you charge)\b",
]

# Subreddits where posters are mostly tradespeople talking shop (supply-side communities).
PRO_COMMUNITY_SUBS = {"r/handyman", "r/electricians", "r/hvac", "r/contractor", "r/carpentry"}

# National DIY / home subs where homeowners ask for help.
DIY_SUBS = {
    "r/diy", "r/fixit", "r/homeimprovement", "r/plumbing", "r/electrical",
    "r/landscaping", "r/homeowners", "r/homemaintenance", "r/lawncare",
}

QUESTION_SIGNAL = re.compile(
    r"\?|\b(help|advice|advise|how do|how to|should i|can i|what's the best|what is the best|anyone know|ideas|suggestions)\b",
    re.IGNORECASE,
)

URGENCY_HIGH_WORDS = [
    "urgent", "asap", "emergency", "immediately", "today", "tonight",
    "this weekend", "flooding", "burst", "active leak", "no power",
    "sparking", "broken window", "move out tomorrow",
]


def extract_price_mention(text: str) -> str:
    matches = re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?(?:\s?(?:/\s?hr|per hour|flat|obo))?", text, flags=re.IGNORECASE)
    if matches:
        return ", ".join(matches[:2])
    return ""


# Pre-compile whole-word regexes for every keyword so "rot" doesn't match "front",
# "wood" doesn't match "Hollywood", "fix" doesn't match "fixture", etc.
# A trailing optional "s"/"es" lets "outlet" match "outlets" and "leak" match "leaks".
_KEYWORD_REGEX: Dict[str, "re.Pattern[str]"] = {}
for _cat in SERVICE_CATEGORIES.values():
    for _kw, _w in _cat["keywords"]:
        if _kw not in _KEYWORD_REGEX:
            _KEYWORD_REGEX[_kw] = re.compile(r"\b" + re.escape(_kw) + r"(?:s|es)?\b", re.IGNORECASE)


def _kw_in(kw: str, text: str) -> bool:
    return bool(_KEYWORD_REGEX[kw].search(text))


def classify_post_rules(post: Dict[str, Any]) -> Dict[str, Any]:
    title = (post.get("title") or "").strip()
    body = (post.get("body") or "").strip()
    source_detail = (post.get("source_detail") or "").lower()
    platform = (post.get("platform") or "").lower()
    combined = f"{title} {body}".lower()

    # 1. Category scoring
    cat_scores: List[Tuple[str, int]] = []
    for cat_name, cat_info in SERVICE_CATEGORIES.items():
        score = 0
        for kw, weight in cat_info["keywords"]:
            if _kw_in(kw, title):
                score += weight * 2
            elif _kw_in(kw, combined):
                score += weight
        if score > 0:
            cat_scores.append((cat_name, score))

    cat_scores.sort(key=lambda x: x[1], reverse=True)
    if cat_scores:
        primary_category = cat_scores[0][0]
        secondary_categories = [c[0] for c in cat_scores[1:3] if c[1] >= 4]
    else:
        primary_category = "General Handyman & Odd Jobs"
        secondary_categories = []

    # 2. Intent classification
    def _hits(patterns: List[str]) -> int:
        return sum(1 for pat in patterns if re.search(pat, combined))

    provider_hits = _hits(PROVIDER_AD_PATTERNS)
    hiring_hits = _hits(CUSTOMER_HIRING_PATTERNS)
    diy_hits = _hits(DIY_HELP_PATTERNS)
    job_hits = _hits(JOB_POSTING_PATTERNS)
    homeowner_hits = _hits(HOMEOWNER_JOB_PATTERNS)
    non_request_hits = _hits(NON_REQUEST_PATTERNS)
    has_question = bool(QUESTION_SIGNAL.search(combined))
    top_cat_score = cat_scores[0][1] if cat_scores else 0

    # Platform/channel contextual signals
    is_cl_hss = platform == "craigslist" and "/hss" in source_detail
    is_cl_gig = platform == "craigslist" and ("/lbg" in source_detail or "/dmg" in source_detail or "/cwg" in source_detail)
    is_diy_sub = source_detail in DIY_SUBS
    is_pro_sub = source_detail in PRO_COMMUNITY_SUBS

    # Employer recruiting needs a stronger signal on Reddit (homeowners rarely trip these patterns twice)
    is_job_posting = job_hits > 0 and homeowner_hits == 0 and (platform == "craigslist" or job_hits >= 2)

    if non_request_hits > 0 and hiring_hits == 0:
        # Scam warnings, mod posts, tradespeople discussing their own clients/pricing
        intent_type = "irrelevant"
        intent_score = 15
    elif is_job_posting:
        intent_type = "job_posting"
        intent_score = 40
    elif is_cl_hss and (hiring_hits == 0 or provider_hits > 0):
        # Household Services is the "services offered" board; "Looking for a handyman? Call me" is still an ad
        intent_type = "service_provider_ad"
        intent_score = 30
    elif provider_hits > 0 and hiring_hits == 0:
        intent_type = "service_provider_ad"
        intent_score = 25
    elif is_pro_sub and hiring_hits == 0:
        # r/handyman etc. are mostly pros talking shop, not homeowners
        intent_type = "irrelevant"
        intent_score = 20
    elif hiring_hits > 0:
        intent_type = "customer_hiring"
        intent_score = min(98, 75 + hiring_hits * 8 + (5 if homeowner_hits else 0))
    elif is_cl_gig:
        # In Craigslist Labor/Domestic gigs, check if it's someone offering services vs needing help
        if re.search(r"\b(for hire|available|my name is|i have tools|offering|i do)\b", combined) and not re.search(r"\b(need|needed|looking for|help with)\b", combined):
            intent_type = "service_provider_ad"
            intent_score = 30
        elif top_cat_score < 3:
            # No recognizable home-service content (e.g. "Problem Property Finder")
            intent_type = "irrelevant"
            intent_score = 15
        else:
            intent_type = "customer_hiring"
            intent_score = 72 + (8 if homeowner_hits else 0)
    elif top_cat_score >= 3 and (diy_hits > 0 or (is_diy_sub and has_question)):
        # Must be clearly home-service related (filters out "my headphones broke" in r/fixit)
        intent_type = "diy_help_needed"
        intent_score = min(88, 55 + diy_hits * 10 + min(top_cat_score, 15))
    elif top_cat_score >= 6 and has_question:
        intent_type = "diy_help_needed"
        intent_score = 55
    else:
        intent_type = "irrelevant"
        intent_score = 15

    # 3. Urgency detection (whole-word match, so e.g. "asap" doesn't match inside another word)
    if re.search(r"\b(" + "|".join(re.escape(w) for w in URGENCY_HIGH_WORDS) + r")\b", combined):
        urgency = "high"
        if intent_type in ("customer_hiring", "diy_help_needed"):
            intent_score = min(99, intent_score + 6)
    elif "?" in title or hiring_hits > 0 or is_cl_gig:
        urgency = "medium"
    else:
        urgency = "low"

    # 4. DIY Difficulty & Marketing Angle
    cat_meta = SERVICE_CATEGORIES.get(primary_category, SERVICE_CATEGORIES["General Handyman & Odd Jobs"])
    diy_difficulty = cat_meta["default_difficulty"]
    marketing_angle = cat_meta["ad_hook"]

    if intent_type == "customer_hiring":
        pain_point = f"Actively seeking a local pro for {primary_category}"
    elif intent_type == "diy_help_needed":
        pain_point = f"Attempting DIY or troubleshooting {primary_category} issue; prime for pro conversion"
    elif intent_type == "service_provider_ad":
        pain_point = f"Local provider advertising {primary_category} services (supply-side recruitment target)"
        marketing_angle = f"[Supply Acquisition] Recruit this {primary_category} provider onto the marketplace with zero-lead-fee onboarding."
    elif intent_type == "job_posting":
        pain_point = f"Employer/agency recruiting {primary_category} workers (labor demand & competitor signal)"
        marketing_angle = f"[Supply Acquisition] Workers browsing these posts want steady jobs — pitch flexible, self-scheduled {primary_category} gigs on your marketplace."
    else:
        pain_point = "General discussion"

    price_mention = post.get("price_mention") or extract_price_mention(f"{title} {body}")

    return {
        **post,
        "price_mention": price_mention,
        "intent_type": intent_type,
        "intent_score": int(intent_score),
        "primary_category": primary_category,
        "secondary_categories": secondary_categories,
        "urgency": urgency,
        "diy_difficulty": diy_difficulty,
        "extracted_pain_point": pain_point,
        "marketing_angle": marketing_angle,
        "classified_by": "hybrid_rules",
    }


def enrich_posts_with_llm(
    posts: List[Dict[str, Any]],
    llm_config: Dict[str, Any],
    max_batch: int = 15,
    max_total: int = 90,
) -> List[Dict[str, Any]]:
    """
    Optional Stage 2 of Hybrid Pipeline:
    Uses Gemini API or OpenAI API if configured to refine classification, pain points, and ad targeting hooks.
    Falls back seamlessly to Stage 1 rule classifications if no API key is set or on network error.
    """
    if not llm_config or not llm_config.get("enable_llm_enrichment", True):
        return posts

    provider = llm_config.get("provider", "gemini").lower()
    gemini_key = (llm_config.get("gemini_api_key") or "").strip()
    openai_key = (llm_config.get("openai_api_key") or "").strip()

    active_key = gemini_key if provider == "gemini" else openai_key
    if not active_key:
        return posts

    # Select candidate demand posts to enrich (capped to control API cost)
    candidates = [
        (idx, p)
        for idx, p in enumerate(posts)
        if p.get("intent_type") in ("customer_hiring", "diy_help_needed")
    ][:max_total]

    if not candidates:
        return posts

    valid_categories = list(SERVICE_CATEGORIES.keys())
    items_payload = [
        {
            "index": idx,
            "platform": p.get("platform"),
            "source": p.get("source_detail"),
            "title": p.get("title", "")[:160],
            "body": p.get("body", "")[:350],
        }
        for idx, p in candidates
    ]

    prompt = (
        "You are a growth marketing intelligence classifier for a Handyman & Home Services Marketplace startup (like Upwork/Thumbtack for in-person services).\n"
        f"Valid categories: {json.dumps(valid_categories)}\n"
        "Intent definitions:\n"
        "- customer_hiring: a homeowner/renter/landlord wants to hire someone for a specific job\n"
        "- diy_help_needed: a homeowner is trying to fix something themselves and asking for help\n"
        "- service_provider_ad: a tradesperson/company advertising their services\n"
        "- job_posting: an employer, agency or gig app recruiting workers\n"
        "- irrelevant: anything else (rants, scam warnings, pros talking shop, non-home topics)\n"
        'Return ONLY a JSON object of the form {"results": [ ... ]} where each item has keys:\n'
        "- index (int, copied from input)\n"
        "- intent_type (one of the intents above)\n"
        "- intent_score (int 1-100, higher = stronger buyer/hiring intent)\n"
        "- primary_category (one of the valid categories)\n"
        "- urgency ('high' | 'medium' | 'low')\n"
        "- extracted_pain_point (concise 6-12 word summary of what they need fixed)\n"
        "- marketing_angle (1 punchy ad hook tailored to convert this exact person)\n\n"
        "Posts to classify:\n"
    )

    valid_intents = ("customer_hiring", "diy_help_needed", "service_provider_ad", "job_posting", "irrelevant")
    gemini_model = llm_config.get("gemini_model") or "gemini-2.5-flash"
    openai_model = llm_config.get("openai_model") or "gpt-4o-mini"

    # Process in chunks so large scrapes are fully enriched, not just the first batch
    for start in range(0, len(items_payload), max_batch):
        chunk = items_payload[start:start + max_batch]
        chunk_prompt = prompt + json.dumps(chunk)
        try:
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"
                req_body = {
                    "contents": [{"parts": [{"text": chunk_prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(req_body).encode("utf-8"),
                    # Send the key in a header rather than the URL so it never lands in logs/proxies
                    headers={"Content-Type": "application/json", "x-goog-api-key": active_key},
                    method="POST",
                )
                resp = urllib.request.urlopen(req, timeout=45)
                resp_data = json.loads(resp.read().decode("utf-8"))
                raw_json = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                tag = "gemini_llm"
            else:
                url = "https://api.openai.com/v1/chat/completions"
                req_body = {
                    "model": openai_model,
                    "messages": [{"role": "user", "content": chunk_prompt}],
                    "response_format": {"type": "json_object"},
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(req_body).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {active_key}",
                    },
                    method="POST",
                )
                resp = urllib.request.urlopen(req, timeout=45)
                resp_data = json.loads(resp.read().decode("utf-8"))
                raw_json = resp_data["choices"][0]["message"]["content"]
                tag = "openai_llm"

            parsed_obj = json.loads(raw_json)
            if isinstance(parsed_obj, dict):
                # Accept {"results": [...]} or any single list-valued key
                parsed = parsed_obj.get("results")
                if parsed is None:
                    parsed = next((v for v in parsed_obj.values() if isinstance(v, list)), [])
            else:
                parsed = parsed_obj

            if not isinstance(parsed, list):
                continue
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                idx = item.get("index")
                if isinstance(idx, int) and 0 <= idx < len(posts):
                    if item.get("primary_category") in SERVICE_CATEGORIES:
                        posts[idx]["primary_category"] = item["primary_category"]
                    if item.get("intent_type") in valid_intents:
                        posts[idx]["intent_type"] = item["intent_type"]
                    if isinstance(item.get("intent_score"), (int, float)):
                        posts[idx]["intent_score"] = max(1, min(100, int(item["intent_score"])))
                    if item.get("urgency") in ("high", "medium", "low"):
                        posts[idx]["urgency"] = item["urgency"]
                    if item.get("extracted_pain_point"):
                        posts[idx]["extracted_pain_point"] = str(item["extracted_pain_point"])[:200]
                    if item.get("marketing_angle"):
                        posts[idx]["marketing_angle"] = str(item["marketing_angle"])[:300]
                    posts[idx]["classified_by"] = tag
        except Exception as exc:
            # Graceful fallback to Stage 1 rules, but surface the reason so a bad key isn't silent
            print(f"[LLM enrichment] {provider} batch starting at {start} failed: {exc}")
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (400, 401, 403):
                break  # bad key / model name — don't hammer the API with every batch

    return posts
