let currentSettings = null;
let summaryData = null;
let allFilteredPosts = [];
let currentPage = 1;
let pageSize = 15;

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Only allow http(s) links from scraped data (blocks javascript: URLs)
function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : "#";
}

let searchDebounce = null;
function debouncedLoadPosts() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadPosts, 300);
}

async function refreshSummaryForGeo() {
  const country = document.getElementById("filter-country").value || "all";
  const province = document.getElementById("filter-province").value || "all";
  const city = document.getElementById("filter-region").value || "all";
  const qs = new URLSearchParams({ country, province, city_region: city }).toString();
  const sumRes = await fetch(`/api/summary?${qs}`).then(r => r.json());
  summaryData = sumRes;
  renderKPIs(sumRes.kpis);
  renderRecommendations(sumRes.recommendations || []);
  renderCategoryBars(sumRes.category_breakdown || []);
  renderRegionBars(sumRes.region_breakdown || [], sumRes.top_channels || []);
}

async function loadDashboard() {
  const [sumRes, setRes] = await Promise.all([
    fetch("/api/summary").then(r => r.json()),
    fetch("/api/settings").then(r => r.json()),
  ]);
  summaryData = sumRes;
  currentSettings = setRes;

  populateFilterDropdowns(sumRes);
  await refreshSummaryForGeo();
  await loadPosts();
}

function renderKPIs(kpis) {
  document.getElementById("kpi-total-demand").textContent = kpis.total_demand_leads || 0;
  document.getElementById("kpi-hiring").textContent = kpis.direct_hiring_leads || 0;
  document.getElementById("kpi-diy").textContent = kpis.diy_conversion_leads || 0;
  document.getElementById("kpi-supply").textContent = kpis.competitor_supply_ads || 0;
  document.getElementById("kpi-jobs").textContent = kpis.job_postings || 0;
}

function renderRecommendations(recs) {
  const el = document.getElementById("recommendations-grid");
  if (!recs.length) {
    el.innerHTML = `<div class="card">Run a scrape to generate marketing & ad targeting insights.</div>`;
    return;
  }
  el.innerHTML = recs.map(r => `
    <div class="rec-card">
      <div class="rec-header">
        <span>${esc(r.type)}</span>
        <span class="badge b-hiring">${esc(r.badge)}</span>
      </div>
      <div class="rec-title">${esc(r.title)}</div>
      <div class="rec-metrics">${esc(r.metrics)}</div>
      <div class="rec-action">${esc(r.action)}</div>
    </div>
  `).join("");
}

function renderCategoryBars(cats) {
  const container = document.getElementById("category-chart");
  if (!cats.length) {
    container.innerHTML = `<p style="color:var(--muted)">No categorized posts yet.</p>`;
    return;
  }
  const maxVal = Math.max(1, ...cats.map(c => (c.total_demand || 0) + (c.provider_supply || 0)));

  container.innerHTML = cats.map(c => {
    const hiringPct = ((c.hiring_count || 0) / maxVal) * 100;
    const diyPct = ((c.diy_count || 0) / maxVal) * 100;
    const supPct = ((c.provider_supply || 0) / maxVal) * 100;
    return `
      <div class="bar-row" style="cursor:pointer" data-cat="${esc(c.primary_category)}" onclick="filterByCategory(this.dataset.cat)">
        <div class="bar-label">
          <strong>${esc(c.primary_category)}</strong>
          <span style="color:var(--muted)">
            <span style="color:#34d399">${c.hiring_count} Hiring</span> ·
            <span style="color:#fbbf24">${c.diy_count} DIY Help</span> ·
            <span style="color:#c084fc">${c.provider_supply} Supply</span>
          </span>
        </div>
        <div class="bar-track">
          <div class="bar-fill-hiring" style="width:${hiringPct}%"></div>
          <div class="bar-fill-diy" style="width:${diyPct}%"></div>
          <div class="bar-fill-supply" style="width:${supPct}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

function renderRegionBars(regions, channels) {
  const regEl = document.getElementById("region-chart");
  const maxReg = Math.max(1, ...regions.map(r => (r.total_demand || 0) + (r.provider_supply || 0)));

  regEl.innerHTML = regions.map(r => {
    const hiringPct = ((r.hiring_count || 0) / maxReg) * 100;
    const diyPct = ((r.diy_count || 0) / maxReg) * 100;
    const supPct = ((r.provider_supply || 0) / maxReg) * 100;
    return `
      <div class="bar-row" style="cursor:pointer" data-reg="${esc(r.city_region)}" onclick="filterByRegion(this.dataset.reg)">
        <div class="bar-label">
          <strong>${esc(r.city_region)}</strong>
          <span style="color:var(--muted)">
            <span style="color:#34d399">${r.hiring_count} Hiring</span> ·
            <span style="color:#fbbf24">${r.diy_count} DIY</span> ·
            <span style="color:#c084fc">${r.provider_supply} Supply</span>
          </span>
        </div>
        <div class="bar-track">
          <div class="bar-fill-hiring" style="width:${hiringPct}%"></div>
          <div class="bar-fill-diy" style="width:${diyPct}%"></div>
          <div class="bar-fill-supply" style="width:${supPct}%"></div>
        </div>
      </div>
    `;
  }).join("");

  const chEl = document.getElementById("top-channels-list");
  chEl.innerHTML = channels.slice(0, 6).map(ch => `
    <span class="badge ${ch.platform === 'reddit' ? 'b-reddit' : 'b-craigslist'}" style="margin:3px 4px 3px 0; padding:5px 10px;">
      ${esc(ch.source_detail)}: ${ch.demand_count} leads
    </span>
  `).join("");
}

function populateFilterDropdowns(sumRes) {
  const catSel = document.getElementById("filter-category");
  const currentCat = catSel.value || "all";
  catSel.innerHTML = `<option value="all">All Service Categories</option>` +
    (sumRes.categories_list || []).map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  catSel.value = currentCat;

  updateProvinceAndCityOptions();
}

function updateProvinceAndCityOptions() {
  const country = document.getElementById("filter-country").value || "all";
  const provSel = document.getElementById("filter-province");
  const regSel = document.getElementById("filter-region");
  const prevProv = provSel.value || "all";
  const prevCity = regSel.value || "all";

  const allRegions = (currentSettings && currentSettings.regions) ? currentSettings.regions : [];
  const matchingCountryRegs = allRegions.filter(r => country === "all" || r.country === country);

  const provinces = [...new Set(matchingCountryRegs.map(r => r.province).filter(Boolean))];
  const provLabel = country === "Canada"
    ? "All Canadian Provinces"
    : country === "United States"
    ? "All US States"
    : "All Provinces / States";

  provSel.innerHTML = `<option value="all">${provLabel}</option>` +
    provinces.map(p => `<option value="${esc(p)}">${esc(p)}</option>`).join("");
  provSel.value = provinces.includes(prevProv) ? prevProv : "all";

  const activeProv = provSel.value;
  const matchingCityRegs = matchingCountryRegs.filter(r => activeProv === "all" || r.province === activeProv);
  const cities = [...new Set(matchingCityRegs.map(r => r.name))];

  const cityLabel = activeProv !== "all"
    ? `All Cities in ${activeProv}`
    : country === "Canada"
    ? "All Canadian Cities"
    : "All Cities";

  regSel.innerHTML = `<option value="all">${esc(cityLabel)}</option>` +
    cities.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  regSel.value = cities.includes(prevCity) ? prevCity : "all";
}

async function onCountryChange() {
  document.getElementById("filter-province").value = "all";
  document.getElementById("filter-region").value = "all";
  updateProvinceAndCityOptions();
  await refreshSummaryForGeo();
  await loadPosts();
}

async function onProvinceChange() {
  document.getElementById("filter-region").value = "all";
  updateProvinceAndCityOptions();
  await refreshSummaryForGeo();
  await loadPosts();
}

async function onCityChange() {
  await refreshSummaryForGeo();
  await loadPosts();
}

function filterByCategory(cat) {
  document.getElementById("filter-category").value = cat;
  loadPosts();
}

async function filterByRegion(reg) {
  const allRegions = (currentSettings && currentSettings.regions) ? currentSettings.regions : [];
  const match = allRegions.find(r => r.name === reg);
  if (match) {
    document.getElementById("filter-country").value = match.country || "all";
    updateProvinceAndCityOptions();
    document.getElementById("filter-province").value = match.province || "all";
    updateProvinceAndCityOptions();
  }
  document.getElementById("filter-region").value = reg;
  await refreshSummaryForGeo();
  await loadPosts();
}

function getFilterQueryString() {
  const params = new URLSearchParams({
    platform: document.getElementById("filter-platform").value,
    intent_type: document.getElementById("filter-intent").value,
    category: document.getElementById("filter-category").value,
    country: document.getElementById("filter-country").value,
    province: document.getElementById("filter-province").value,
    city_region: document.getElementById("filter-region").value,
    urgency: document.getElementById("filter-urgency").value,
    search: document.getElementById("filter-search").value,
  });
  return params.toString();
}

async function loadPosts() {
  const qs = getFilterQueryString();
  document.getElementById("export-btn").href = `/api/export.csv?${qs}`;

  const res = await fetch(`/api/posts?${qs}`).then(r => r.json());
  allFilteredPosts = res.posts || [];
  currentPage = 1;
  renderPostsPage();
}

function goToPage(page) {
  const totalPages = Math.max(1, Math.ceil(allFilteredPosts.length / pageSize));
  currentPage = Math.max(1, Math.min(totalPages, page));
  renderPostsPage();
  document.getElementById("posts-tbody").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function changePageSize(newSize) {
  pageSize = Number(newSize) || 15;
  currentPage = 1;
  renderPostsPage();
}

function renderPostsPage() {
  const total = allFilteredPosts.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;

  const startIdx = (currentPage - 1) * pageSize;
  const endIdx = Math.min(startIdx + pageSize, total);
  const posts = allFilteredPosts.slice(startIdx, endIdx);

  document.getElementById("results-count").textContent =
    total > 0 ? `Showing ${startIdx + 1}-${endIdx} of ${total} matching posts` : "0 matching posts";

  const tbody = document.getElementById("posts-tbody");
  const pagBar = document.getElementById("pagination-bar");
  if (!posts.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:28px;">No posts match the current filters.</td></tr>`;
    if (pagBar) pagBar.innerHTML = "";
    return;
  }

  tbody.innerHTML = posts.map(p => {
    const intentBadge = p.intent_type === "customer_hiring"
      ? `<span class="badge b-hiring">Hiring Pro (${p.intent_score})</span>`
      : p.intent_type === "diy_help_needed"
      ? `<span class="badge b-diy">DIY Help (${p.intent_score})</span>`
      : p.intent_type === "job_posting"
      ? `<span class="badge b-job">Job Posting / Recruiting</span>`
      : p.intent_type === "irrelevant"
      ? `<span class="badge">Irrelevant</span>`
      : `<span class="badge b-supply">Provider Ad</span>`;

    const platBadge = p.platform === "reddit"
      ? `<span class="badge b-reddit">Reddit</span>`
      : p.platform === "kijiji"
      ? `<span class="badge b-kijiji">Kijiji</span>`
      : p.platform === "stackexchange"
      ? `<span class="badge b-stackexchange">StackExchange</span>`
      : `<span class="badge b-craigslist">Craigslist</span>`;

    const urgBadge = p.urgency === "high"
      ? `<span class="badge b-high" style="margin-left:4px;">Urgent</span>`
      : "";

    const bodySnippet = (p.body || "").slice(0, 220) + ((p.body || "").length > 220 ? "..." : "");
    const locText = p.neighborhood ? `${p.city_region} (${p.neighborhood})` : p.city_region;

    return `
      <tr>
        <td>
          ${intentBadge}
          ${urgBadge}
          <div style="font-size:0.73rem;color:var(--muted);margin-top:4px;">${esc(p.classified_by)}</div>
        </td>
        <td>
          <strong>${esc(p.primary_category)}</strong>
          ${p.price_mention ? `<div style="color:#34d399;font-size:0.78rem;margin-top:2px;">Budget/Price: ${esc(p.price_mention)}</div>` : ""}
        </td>
        <td>
          ${platBadge}
          <div style="font-size:0.78rem;margin-top:4px;font-weight:600;">${esc(p.source_detail)}</div>
          <div style="font-size:0.75rem;color:var(--muted);">${esc(locText)}</div>
          ${p.province ? `<div style="font-size:0.72rem;color:#93c5fd;">${esc(p.province)}, ${esc(p.country)}</div>` : ""}
        </td>
        <td>
          <a class="post-title" href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener noreferrer">${esc(p.title)}</a>
          <div class="post-body">${esc(bodySnippet)}</div>
          <div class="ad-hook"><strong>Ad Hook:</strong> ${esc(p.marketing_angle)}</div>
        </td>
        <td style="font-size:0.78rem;color:var(--muted);">
          <div>${esc(p.author)}</div>
          <div style="margin-top:4px;">${esc((p.posted_at || "").slice(0, 10))}</div>
        </td>
        <td>
          <a class="btn" style="padding:6px 14px;font-size:0.8rem;" href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener noreferrer">Link</a>
        </td>
      </tr>
    `;
  }).join("");

  if (pagBar) {
    const pages = [];
    const windowStart = Math.max(1, currentPage - 2);
    const windowEnd = Math.min(totalPages, currentPage + 2);
    if (windowStart > 1) pages.push(1);
    if (windowStart > 2) pages.push("...");
    for (let i = windowStart; i <= windowEnd; i++) pages.push(i);
    if (windowEnd < totalPages - 1) pages.push("...");
    if (windowEnd < totalPages) pages.push(totalPages);

    const pageBtnsHtml = pages.map(pg =>
      pg === "..."
        ? `<span style="padding:0 4px;">...</span>`
        : `<button class="page-btn ${pg === currentPage ? 'active' : ''}" onclick="goToPage(${pg})">${pg}</button>`
    ).join("");

    pagBar.innerHTML = `
      <div>
        Showing <strong>${startIdx + 1}-${endIdx}</strong> of <strong>${total}</strong> posts
        &nbsp;·&nbsp;
        Per page:
        <select class="page-size-select" onchange="changePageSize(this.value)">
          ${[10, 15, 25, 50].map(sz => `<option value="${sz}" ${sz === pageSize ? 'selected' : ''}>${sz}</option>`).join("")}
        </select>
      </div>
      <div class="page-controls">
        <button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage <= 1 ? "disabled" : ""}>Previous</button>
        ${pageBtnsHtml}
        <button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? "disabled" : ""}>Next</button>
      </div>
    `;
  }
}

async function triggerScrape() {
  const btn = document.getElementById("scrape-btn");
  btn.disabled = true;
  btn.textContent = "Scraping Kijiji, Reddit & Craigslist...";
  try {
    const resp = await fetch("/api/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platforms: ["reddit", "craigslist", "kijiji", "stackexchange"], include_national_reddit: true }),
    });
    const res = await resp.json();
    if (!resp.ok) throw new Error(res.error || `HTTP ${resp.status}`);
    await loadDashboard();
    alert(`Scrape complete! Fetched ${res.total_fetched} posts (${res.new_stored} new stored, ${res.demand_leads_found} demand leads).`);
  } catch (e) {
    alert("Error running scrape: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run Live Scrape";
  }
}

async function triggerReclassify() {
  if (!confirm("Re-run classification on all stored posts with the latest rules (and LLM, if configured)?")) return;
  const res = await fetch("/api/reclassify", { method: "POST" }).then(r => r.json());
  await loadDashboard();
  alert(`Reclassified ${res.count} posts.`);
}

function openSettingsModal() {
  if (!currentSettings) return;
  const regContainer = document.getElementById("settings-regions");
  regContainer.innerHTML = (currentSettings.regions || []).map((r, i) => `
    <label class="region-item">
      <input type="checkbox" data-reg-idx="${i}" ${r.enabled ? "checked" : ""} />
      <span>${esc(r.name)}</span>
    </label>
  `).join("");

  document.getElementById("settings-keywords").value = (currentSettings.search_keywords || []).join(", ");
  document.getElementById("settings-subs").value = (currentSettings.national_subreddits || []).join(", ");
  document.getElementById("settings-llm-provider").value = (currentSettings.llm_config || {}).provider || "gemini";
  document.getElementById("settings-modal").classList.add("open");
}

function closeSettingsModal() {
  document.getElementById("settings-modal").classList.remove("open");
}

async function saveSettings() {
  const checkboxes = document.querySelectorAll("[data-reg-idx]");
  checkboxes.forEach(cb => {
    const idx = Number(cb.getAttribute("data-reg-idx"));
    if (currentSettings.regions[idx]) {
      currentSettings.regions[idx].enabled = cb.checked;
    }
  });

  const keywords = document.getElementById("settings-keywords").value.split(",").map(s => s.trim()).filter(Boolean);
  const subs = document.getElementById("settings-subs").value.split(",").map(s => s.trim()).filter(Boolean);
  const provider = document.getElementById("settings-llm-provider").value;
  const geminiKey = document.getElementById("settings-gemini-key").value.trim();
  const openaiKey = document.getElementById("settings-openai-key").value.trim();

  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      regions: currentSettings.regions,
      search_keywords: keywords,
      national_subreddits: subs,
      llm_config: {
        provider,
        gemini_api_key: geminiKey,
        openai_api_key: openaiKey,
        enable_llm_enrichment: true,
      },
    }),
  });
  closeSettingsModal();
  await loadDashboard();
}

window.addEventListener("DOMContentLoaded", loadDashboard);
