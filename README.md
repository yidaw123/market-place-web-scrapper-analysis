# Market Place Web Scrapper Analysis

A multi-platform scraper, work-type & intent classifier, and interactive demand & seasonality dashboard built for a **Handyman & Home Services Marketplace** startup.

**Live Hosted App (GitHub Pages):** https://yidaw123.github.io/market-place-web-scrapper-analysis/

## Key Capabilities

1. **Multi-Platform Live Scrapers (`scrapers/`)**
   - **Kijiji Canada (`scrapers/kijiji_scraper.py`)**: Scrapes Canadian homeowner service requests and wanted ads across Ontario, British Columbia, Alberta, Quebec, Manitoba, Saskatchewan, and Nova Scotia.
   - **Reddit (`scrapers/reddit_scraper.py`)**: Scrapes both local metro subreddits (`r/askTO`, `r/toronto`, `r/vancouver`, `r/Calgary`, `r/montreal`, `r/Austin`, `r/bayarea`, `r/AskNYC`, `r/AskLosAngeles`, etc.) and national home improvement forums (`r/HomeImprovement`, `r/DIY`, `r/fixit`, `r/Plumbing`, `r/landscaping`).
   - **Craigslist (`scrapers/craigslist_scraper.py`)**: Scrapes regional Craigslist boards across **Labor Gigs (`lbg`)**, **Domestic Gigs (`dmg`)**, and **Household Services (`hss`)**.
   - **DIY Stack Exchange (`scrapers/stackexchange_scraper.py`)**: Scrapes homeowner repair & troubleshooting questions from `diy.stackexchange.com`.

2. **Work-Type & Intent Classification Engine (`classifier.py`)**
   - Classifies posts by intent (`customer_hiring`, `diy_help_needed`, `service_provider_ad`, `job_posting`, `irrelevant`), urgency (`high`, `medium`, `low`), and specific **Type of Work**:
     - Plumbing & Drain
     - Electrical & Lighting
     - Yardwork & Landscaping
     - Painting & Drywall
     - Carpentry, Doors & Windows
     - Mounting & Furniture Assembly
     - Roofing, Siding & Gutters
     - Flooring & Tile
     - Appliance & HVAC Repair
     - General Handyman & Odd Jobs

3. **Interactive Web Dashboard & Stock-Market Style Demand Chart (`app.py`, `static/`)**
   - **Stock-Market Style Demand Trend & Seasonality Chart**: Interactive multi-line trend chart across `7D`, `1M`, `3M`, `6M`, `1Y`, `ALL`, and `Seasonality (Jan-Dec)` with clickable work-type toggles and crosshair hover tooltips.
   - **Demand vs. Supply Breakdown** across every work type and geographic region (`Canada` -> Province -> City, `United States` -> State -> City).
   - **Categorized Leads Explorer** with pagination, sorting (`Relevance`, `Newest First`, `Oldest First`, `Urgency`), `Reset Filters`, direct `Link` buttons, and CSV Export.

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
- If you add an LLM key, enrichment runs only on *new* demand posts (max 90 per scrape) to control cost. Use **Reclassify** to re-run classification on everything stored.
