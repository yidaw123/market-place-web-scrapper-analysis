# Handyman Marketplace — Market Research & Lead Intelligence Tool

A multi-platform scraper, service categorizer, and interactive market research dashboard built for a **Handyman & Home Services Marketplace** startup.

## Key Capabilities

1. **Multi-Platform Live Scrapers (`scrapers/`)**
   - **Reddit (`scrapers/reddit_scraper.py`)**: Scrapes both local metro subreddits (`r/Austin`, `r/bayarea`, `r/AskSF`, `r/AskNYC`, `r/AskLosAngeles`, etc.) for local handyman hiring requests and national home improvement forums (`r/HomeImprovement`, `r/DIY`, `r/handyman`, `r/fixit`, `r/Plumbing`, `r/landscaping`) for DIY struggle & pricing questions.
   - **Craigslist (`scrapers/craigslist_scraper.py`)**: Scrapes regional Craigslist boards across **Labor Gigs (`lbg`)**, **Domestic Gigs (`dmg`)**, and **Household Services (`hss`)** to capture high-intent customer gigs as well as local handyman supply benchmarks.

2. **Hybrid Intent & Service Categorization Engine (`classifier.py`)**
   - **Stage 1 (Rule & Weighted Keyword Scoring)**: Instantly classifies posts by intent (`customer_hiring`, `diy_help_needed`, `service_provider_ad`, `irrelevant`), scores buyer urgency (`high`, `medium`, `low`), extracts budget/price mentions, and maps each post to 10 core service verticals:
     - Plumbing & Drain
     - Electrical & Lighting
     - Gardening & Landscaping
     - Painting & Drywall
     - Carpentry, Doors & Windows
     - Mounting & Furniture Assembly
     - Roofing, Siding & Gutters
     - Flooring & Tile
     - Appliance & HVAC Repair
     - General Handyman & Odd Jobs
   - **Stage 2 (Optional LLM Enrichment)**: Add a **Google Gemini** (`gemini-2.5-flash`) or **OpenAI** (`gpt-4o-mini`) API key in the dashboard settings modal to refine pain points and generate tailored ad copy hooks.

3. **Interactive Web Dashboard (`app.py`, `static/`)**
   - Visualizes **Demand vs. Supply** across every service category and target metro area.
   - Generates an **Ad Campaign & Targeting Playbook** highlighting underserved service categories, DIY-to-Pro conversion opportunities, and top-converting local channels.
   - One-click **CSV Export** for Meta/Google/Reddit ad campaign planning or direct lead outreach.

## Quick Start

```powershell
pip install -r requirements.txt

# Start the Web Dashboard on http://localhost:8765
python app.py
```

Or run a standalone CLI scrape:

```powershell
python app.py --scrape-only
```

Run the classifier regression tests:

```powershell
python -m unittest test_classifier.py
```

## Intent Types

| Intent | Meaning | Use it for |
|---|---|---|
| `customer_hiring` | Homeowner/renter/landlord wants to hire for a specific job | Demand ads, geo targeting |
| `diy_help_needed` | Homeowner trying to fix it themselves | "Stop struggling, book a pro" campaigns |
| `service_provider_ad` | Tradesperson advertising services | Supply-side recruiting onto the marketplace |
| `job_posting` | Employer, staffing agency or gig app recruiting workers | Labor-market & competitor signal |
| `irrelevant` | Scam warnings, pros talking shop, off-topic | Filtered out of demand metrics |

## Notes & Limitations

- **Reddit data** comes from the free [Arctic Shift](https://arctic-shift.photon-reddit.com) archive API (reddit.com blocks unauthenticated JSON). It's rate-limited; large subreddits fall back to scanning the latest 100 posts with local keyword filtering. For production volume, consider the official Reddit API (OAuth app).
- **Craigslist** results come from the public search pages; full descriptions + real posting dates are fetched for up to 20 gig posts per region per scrape.
- **Data use:** this is built for aggregate market research (which services, where, how urgent). Craigslist's terms restrict automated access, and both platforms restrict using personal data for unsolicited outreach — keep scrape volume modest, and use the insights for ad targeting rather than cold-messaging individual posters.
- If you add an LLM key, enrichment runs only on *new* demand posts (max 90 per scrape) to control cost. Use **⟳ Reclassify** to re-run classification on everything stored.
