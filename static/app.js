let currentSettings = null;
let summaryData = null;
let trendData = null;
let currentTrendPeriod = "1Y";
let currentTrendMode = "count"; // 'count' or 'share'
let selectedPricingTrade = "all";
const WORK_TYPE_COLORS = {
  "All Demand": "#60a5fa",
  "Plumbing & Drain": "#38bdf8",
  "Electrical & Lighting": "#fbbf24",
  "Yardwork & Landscaping": "#34d399",
  "Carpentry, Doors & Windows": "#f97316",
  "Painting & Drywall": "#a855f7",
  "Mounting & Furniture Assembly": "#ec4899",
  "Roofing, Siding & Gutters": "#14b8a6",
  "Flooring & Tile": "#818cf8",
  "Appliance & HVAC Repair": "#fb7185",
  "General Handyman & Odd Jobs": "#94a3b8",
};

let activeWorkTypes = new Set(Object.keys(WORK_TYPE_COLORS));
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

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : "#";
}

let searchDebounce = null;
function debouncedLoadPosts() {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadPosts, 250);
}

function switchTab(tabName) {
  const leadsEl = document.getElementById("view-leads");
  if (leadsEl) leadsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function syncActiveKpiCard(intentVal) {
  const types = ["demand_only", "customer_hiring", "diy_help_needed", "service_provider_ad", "job_posting"];
  types.forEach(t => {
    const el = document.getElementById(`kpi-card-${t}`);
    if (el) el.classList.toggle("active", t === intentVal);
  });
}

function quickSelectIntent(intentVal) {
  document.getElementById("filter-intent").value = intentVal;
  if (intentVal === "demand_only") {
    document.getElementById("filter-category").value = "all";
    const subSel = document.getElementById("filter-sub-service");
    if (subSel) subSel.value = "all";
  }
  syncActiveKpiCard(intentVal);
  loadTrends();
  loadPosts();
}

function onIntentDropdownChange() {
  const val = document.getElementById("filter-intent").value;
  syncActiveKpiCard(val);
  loadTrends();
  loadPosts();
}

let staticSnapshot = null;

async function ensureStaticSnapshot() {
  if (staticSnapshot) return staticSnapshot;
  const resp = await fetch("./static/snapshot.json");
  staticSnapshot = await resp.json();
  return staticSnapshot;
}

function computeStaticSummary(snap, country, province, city_region) {
  const posts = (snap.posts || []).filter(p => {
    if (country && country !== "all" && p.country !== country) return false;
    if (province && province !== "all" && p.province !== province) return false;
    if (city_region && city_region !== "all" && p.city_region !== city_region) return false;
    return true;
  });
  let hiring = 0, diy = 0, supply = 0, jobs = 0;
  const catMap = {};
  const subMap = {};
  const priceCatMap = {};
  const regMap = {};
  const chMap = {};

  const addPrice = (bucket, p) => {
    const pv = Number(p.price_value || 0);
    if (pv <= 0) return;
    if (p.price_type === "hourly") bucket.hrVals.push(pv);
    else if (p.price_type === "flat") bucket.flatVals.push(pv);
  };
  const finalizePrice = b => {
    const hr = b.hrVals;
    const fl = b.flatVals;
    b.hourly_count = hr.length;
    b.avg_hourly = hr.length ? Math.round(hr.reduce((a, x) => a + x, 0) / hr.length) : null;
    b.min_hourly = hr.length ? Math.round(Math.min(...hr)) : null;
    b.max_hourly = hr.length ? Math.round(Math.max(...hr)) : null;
    b.flat_count = fl.length;
    b.avg_flat = fl.length ? Math.round(fl.reduce((a, x) => a + x, 0) / fl.length) : null;
    b.min_flat = fl.length ? Math.round(Math.min(...fl)) : null;
    b.max_flat = fl.length ? Math.round(Math.max(...fl)) : null;
    delete b.hrVals;
    delete b.flatVals;
    return b;
  };

  posts.forEach(p => {
    if (p.intent_type === "customer_hiring") hiring++;
    else if (p.intent_type === "diy_help_needed") diy++;
    else if (p.intent_type === "service_provider_ad") supply++;
    else if (p.intent_type === "job_posting") jobs++;
    if (p.intent_type === "irrelevant") return;

    const c = p.primary_category || "General Handyman & Odd Jobs";
    const sub = p.sub_service || "General Service";
    if (!catMap[c]) catMap[c] = { primary_category: c, hiring_count: 0, diy_count: 0, total_demand: 0, provider_supply: 0 };
    if (p.intent_type === "customer_hiring") { catMap[c].hiring_count++; catMap[c].total_demand++; }
    else if (p.intent_type === "diy_help_needed") { catMap[c].diy_count++; catMap[c].total_demand++; }
    else if (p.intent_type === "service_provider_ad") catMap[c].provider_supply++;

    if (!priceCatMap[c]) priceCatMap[c] = { primary_category: c, hrVals: [], flatVals: [] };
    addPrice(priceCatMap[c], p);

    const sk = `${c}|||${sub}`;
    if (!subMap[sk]) subMap[sk] = { primary_category: c, sub_service: sub, hiring_count: 0, diy_count: 0, total_demand: 0, provider_supply: 0, hrVals: [], flatVals: [] };
    if (p.intent_type === "customer_hiring") { subMap[sk].hiring_count++; subMap[sk].total_demand++; }
    else if (p.intent_type === "diy_help_needed") { subMap[sk].diy_count++; subMap[sk].total_demand++; }
    else if (p.intent_type === "service_provider_ad") subMap[sk].provider_supply++;
    addPrice(subMap[sk], p);

    const r = p.city_region || "National / DIY Forums";
    if (!regMap[r]) regMap[r] = { city_region: r, province: p.province, country: p.country, hiring_count: 0, diy_count: 0, total_demand: 0, provider_supply: 0 };
    if (p.intent_type === "customer_hiring") { regMap[r].hiring_count++; regMap[r].total_demand++; }
    else if (p.intent_type === "diy_help_needed") { regMap[r].diy_count++; regMap[r].total_demand++; }
    else if (p.intent_type === "service_provider_ad") regMap[r].provider_supply++;

    if (p.intent_type === "customer_hiring" || p.intent_type === "diy_help_needed") {
      const ch = p.source_detail || p.platform;
      if (!chMap[ch]) chMap[ch] = { source_detail: ch, platform: p.platform, city_region: r, demand_count: 0, direct_hiring: 0 };
      chMap[ch].demand_count++;
      if (p.intent_type === "customer_hiring") chMap[ch].direct_hiring++;
    }
  });
  return {
    kpis: {
      total_posts: posts.length,
      total_demand_leads: hiring + diy,
      direct_hiring_leads: hiring,
      diy_conversion_leads: diy,
      competitor_supply_ads: supply,
      job_postings: jobs,
    },
    categories_list: snap.categories_list || Object.keys(WORK_TYPE_COLORS).filter(k => k !== "All Demand"),
    sub_services_map: snap.sub_services_map || {},
    category_breakdown: Object.values(catMap).sort((a, b) => b.total_demand - a.total_demand),
    sub_service_breakdown: Object.values(subMap).map(finalizePrice).sort((a, b) => b.total_demand - a.total_demand),
    pricing_by_category: Object.values(priceCatMap).map(finalizePrice),
    region_breakdown: Object.values(regMap).sort((a, b) => b.total_demand - a.total_demand),
    top_channels: Object.values(chMap).sort((a, b) => b.direct_hiring - a.direct_hiring || b.demand_count - a.demand_count).slice(0, 12),
  };
}

function computeStaticTrends(snap, period, country, province, city_region, intent_type) {
  const cats = snap.categories_list || Object.keys(WORK_TYPE_COLORS).filter(k => k !== "All Demand");
  const allKeys = ["All Demand", ...cats];
  const demandPosts = (snap.posts || []).filter(p => {
    if (!intent_type || intent_type === "demand_only") {
      if (p.intent_type !== "customer_hiring" && p.intent_type !== "diy_help_needed") return false;
    } else if (intent_type === "all") {
      if (p.intent_type === "irrelevant") return false;
    } else if (p.intent_type !== intent_type) {
      return false;
    }
    if (country && country !== "all" && p.country !== country) return false;
    if (province && province !== "all" && p.province !== province) return false;
    if (city_region && city_region !== "all" && p.city_region !== city_region) return false;
    return true;
  });

  const monthAbbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  let maxDateStr = "2026-11-09";
  demandPosts.forEach(p => {
    const d = String(p.posted_at || "").slice(0, 10);
    if (d.length === 10 && d > maxDateStr) maxDateStr = d;
  });
  const maxDt = new Date(maxDateStr + "T00:00:00Z");
  const pNorm = (period || "1Y").toUpperCase();
  const buckets = [];
  const series = {};

  if (pNorm === "SEASONALITY") {
    for (let m = 1; m <= 12; m++) buckets.push({ key: String(m).padStart(2, "0"), label: monthAbbr[m - 1] });
    allKeys.forEach(k => { series[k] = new Array(12).fill(0); });
    demandPosts.forEach(p => {
      const m = parseInt(String(p.posted_at || "").slice(5, 7), 10);
      if (m >= 1 && m <= 12) {
        series["All Demand"][m - 1]++;
        if (series[p.primary_category]) series[p.primary_category][m - 1]++;
      }
    });
  } else if (pNorm === "7D" || pNorm === "1M") {
    const nDays = pNorm === "7D" ? 7 : 30;
    const keyIdx = {};
    for (let i = 0; i < nDays; i++) {
      const d = new Date(maxDt.getTime() - (nDays - 1 - i) * 86400000);
      const k = d.toISOString().slice(0, 10);
      keyIdx[k] = i;
      buckets.push({ key: k, label: `${monthAbbr[d.getUTCMonth()]} ${String(d.getUTCDate()).padStart(2, "0")}` });
    }
    allKeys.forEach(k => { series[k] = new Array(nDays).fill(0); });
    demandPosts.forEach(p => {
      const k = String(p.posted_at || "").slice(0, 10);
      if (keyIdx[k] !== undefined) {
        series["All Demand"][keyIdx[k]]++;
        if (series[p.primary_category]) series[p.primary_category][keyIdx[k]]++;
      }
    });
  } else if (pNorm === "3M" || pNorm === "6M") {
    const nWeeks = pNorm === "3M" ? 13 : 26;
    const startMs = maxDt.getTime() - (nWeeks * 7 - 1) * 86400000;
    for (let w = 0; w < nWeeks; w++) {
      const wEnd = new Date(startMs + (w * 7 + 6) * 86400000);
      buckets.push({ key: wEnd.toISOString().slice(0, 10), label: `${monthAbbr[wEnd.getUTCMonth()]} ${String(wEnd.getUTCDate()).padStart(2, "0")}` });
    }
    allKeys.forEach(k => { series[k] = new Array(nWeeks).fill(0); });
    demandPosts.forEach(p => {
      const dStr = String(p.posted_at || "").slice(0, 10);
      if (dStr.length === 10) {
        const dtMs = new Date(dStr + "T00:00:00Z").getTime();
        const deltaDays = Math.floor((dtMs - startMs) / 86400000);
        if (deltaDays >= 0 && deltaDays < nWeeks * 7) {
          const wIdx = Math.floor(deltaDays / 7);
          series["All Demand"][wIdx]++;
          if (series[p.primary_category]) series[p.primary_category][wIdx]++;
        }
      }
    });
  } else {
    const nMonths = pNorm === "1Y" ? 12 : 24;
    let y = maxDt.getUTCFullYear(), m = maxDt.getUTCMonth() + 1;
    const mList = [];
    for (let i = 0; i < nMonths; i++) {
      mList.push([y, m]);
      m--;
      if (m === 0) { m = 12; y--; }
    }
    mList.reverse();
    const keyIdx = {};
    mList.forEach(([yy, mm], idx) => {
      const k = `${yy}-${String(mm).padStart(2, "0")}`;
      keyIdx[k] = idx;
      buckets.push({ key: k, label: `${monthAbbr[mm - 1]} '${String(yy).slice(2)}` });
    });
    allKeys.forEach(k => { series[k] = new Array(nMonths).fill(0); });
    demandPosts.forEach(p => {
      const k = String(p.posted_at || "").slice(0, 7);
      if (keyIdx[k] !== undefined) {
        series["All Demand"][keyIdx[k]]++;
        if (series[p.primary_category]) series[p.primary_category][keyIdx[k]]++;
      }
    });
  }

  const totals = {};
  allKeys.forEach(k => { totals[k] = (series[k] || []).reduce((a, b) => a + b, 0); });
  return { period: pNorm, buckets, series, totals, categories: cats };
}

async function fetchJsonWithFallback(url, fallbackFn) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (_e) {
    const snap = await ensureStaticSnapshot();
    return fallbackFn(snap);
  }
}

async function refreshSummaryForGeo() {
  const country = document.getElementById("filter-country").value || "all";
  const province = document.getElementById("filter-province").value || "all";
  const city = document.getElementById("filter-region").value || "all";
  const qs = new URLSearchParams({ country, province, city_region: city }).toString();
  const [sumRes] = await Promise.all([
    fetchJsonWithFallback(`/api/summary?${qs}`, snap => computeStaticSummary(snap, country, province, city)),
    loadTrends(),
  ]);
  summaryData = sumRes;
  renderKPIs(sumRes.kpis);
  renderPricingAndTaskBreakdown();
  renderCategoryBars(sumRes.category_breakdown || []);
  renderRegionBars(sumRes.region_breakdown || [], sumRes.top_channels || []);
}

async function loadTrends() {
  const country = document.getElementById("filter-country").value || "all";
  const province = document.getElementById("filter-province").value || "all";
  const city = document.getElementById("filter-region").value || "all";
  const intentEl = document.getElementById("filter-intent");
  const intent_type = intentEl ? intentEl.value : "demand_only";
  const qs = new URLSearchParams({
    period: currentTrendPeriod,
    country,
    province,
    city_region: city,
    intent_type,
  }).toString();
  trendData = await fetchJsonWithFallback(`/api/trends?${qs}`, snap =>
    computeStaticTrends(snap, currentTrendPeriod, country, province, city, intent_type)
  );
  renderTrendPills();
  renderTrendChart();
}

function setTrendMode(mode) {
  currentTrendMode = mode;
  document.querySelectorAll("#trend-mode-tabs .period-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-mode") === mode);
  });
  renderTrendChart();
}

function setTrendPeriod(period) {
  currentTrendPeriod = period;
  document.querySelectorAll("#trend-period-tabs .period-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-period") === period);
  });
  loadTrends();
}

function getAllWorkCategories() {
  return (trendData && trendData.categories && trendData.categories.length)
    ? trendData.categories
    : Object.keys(WORK_TYPE_COLORS).filter(k => k !== "All Demand");
}

function toggleWorkTypePill(workType) {
  const allCats = getAllWorkCategories();
  if (workType === "All Demand") {
    const allSelected = allCats.every(c => activeWorkTypes.has(c));
    if (allSelected) {
      // Turn OFF everything
      activeWorkTypes.clear();
    } else {
      // Turn ON all job types
      activeWorkTypes.add("All Demand");
      allCats.forEach(c => activeWorkTypes.add(c));
    }
  } else {
    if (activeWorkTypes.has(workType)) {
      activeWorkTypes.delete(workType);
      activeWorkTypes.delete("All Demand");
    } else {
      activeWorkTypes.add(workType);
      if (allCats.every(c => activeWorkTypes.has(c))) {
        activeWorkTypes.add("All Demand");
      }
    }
  }
  renderTrendPills();
  renderTrendChart();
}

function soloWorkType(workType, evt) {
  if (evt) evt.stopPropagation();
  const allCats = getAllWorkCategories();
  activeWorkTypes.clear();
  if (workType === "All Demand") {
    activeWorkTypes.add("All Demand");
    allCats.forEach(c => activeWorkTypes.add(c));
  } else {
    activeWorkTypes.add(workType);
  }
  renderTrendPills();
  renderTrendChart();
}

function renderTrendPills() {
  const container = document.getElementById("trend-work-pills");
  if (!container || !trendData) return;
  const totals = trendData.totals || {};
  const allCats = getAllWorkCategories();
  const allSelected = allCats.every(c => activeWorkTypes.has(c));
  const keys = ["All Demand", ...allCats];

  container.innerHTML = keys.map(k => {
    const isActive = k === "All Demand" ? allSelected : activeWorkTypes.has(k);
    const color = WORK_TYPE_COLORS[k] || "#60a5fa";
    const count = totals[k] || 0;
    const borderStyle = isActive ? `border-color:${color};box-shadow:0 0 0 1px ${color}40;` : "";
    const tip = k === "All Demand"
      ? "Click to toggle ALL job types on or off"
      : "Click to toggle this job type on/off (double-click to solo)";
    return `
      <div class="work-pill ${isActive ? 'active' : ''}" style="${borderStyle}" data-wt="${esc(k)}" onclick="toggleWorkTypePill(this.dataset.wt)" ondblclick="soloWorkType(this.dataset.wt, event)" title="${tip}">
        <span class="work-pill-dot" style="background:${color};opacity:${isActive ? 1 : 0.35}"></span>
        <span>${esc(k)}</span>
        <span class="work-pill-count">${count}</span>
      </div>
    `;
  }).join("");
}

function renderTrendChart() {
  const svgWrap = document.getElementById("trend-svg-container");
  const statsEl = document.getElementById("trend-stats-summary");
  if (!svgWrap || !trendData) return;

  const buckets = trendData.buckets || [];
  const series = trendData.series || {};
  const activeKeys = [...activeWorkTypes].filter(k => k !== "All Demand" && Array.isArray(series[k]));

  if (!buckets.length || !activeKeys.length) {
    if (statsEl) {
      statsEl.innerHTML = `<span style="color:var(--muted);">All job types toggled off &mdash; click <strong>All Demand</strong> to turn all on, or click individual job types to compare</span>`;
    }
    svgWrap.innerHTML = `<div style="color:var(--muted);padding:64px 20px;text-align:center;border:1px dashed var(--border);border-radius:8px;">All job types are currently toggled off. Click <strong>All Demand</strong> to select all, or click any specific job type pill above to plot its demand trend.</div>`;
    return;
  }

  // Helper to get plotted value at bucket idx (either raw count or % share of bucket total)
  const allDemandVals = series["All Demand"] || [];
  const isShare = currentTrendMode === "share";
  const valAt = (k, idx) => {
    const raw = (series[k] || [])[idx] || 0;
    if (!isShare) return raw;
    const tot = allDemandVals[idx] || 0;
    return tot > 0 ? Math.round((raw / tot) * 1000) / 10 : 0;
  };

  // Compute period summary & peak bucket for the top active series
  const leadKey = activeKeys[0];
  const leadVals = series[leadKey] || [];
  const leadTotal = leadVals.reduce((a, b) => a + b, 0);
  let peakVal = -1;
  let peakLbl = "-";
  leadVals.forEach((_v, idx) => {
    const pv = valAt(leadKey, idx);
    if (pv > peakVal && buckets[idx]) {
      peakVal = pv;
      peakLbl = buckets[idx].label;
    }
  });

  if (statsEl) {
    const modeLabel = currentTrendPeriod === "SEASONALITY"
      ? "Seasonal Monthly Aggregation (Jan - Dec)"
      : `Timeframe: ${currentTrendPeriod}`;
    const peakUnit = isShare ? `${peakVal}% share` : `${peakVal} posts`;
    statsEl.innerHTML = `
      <span style="color:var(--text);font-weight:600;">${esc(modeLabel)}</span>
      &nbsp;&middot;&nbsp;
      <span>Showing <strong>${activeKeys.length}</strong> trade${activeKeys.length > 1 ? "s" : ""} (${isShare ? "% Share of Month" : "Post Count"})</span>
      &nbsp;&middot;&nbsp;
      <span>Peak for <strong style="color:${WORK_TYPE_COLORS[leadKey] || '#60a5fa'}">${esc(leadKey)}</strong>: <strong>${esc(peakLbl)}</strong> (${peakUnit}, ${leadTotal} total posts)</span>
    `;
  }

  const width = Math.max(640, svgWrap.clientWidth || 920);
  const height = 260;
  const padL = 46;
  const padR = 18;
  const padT = 16;
  const padB = 32;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  let maxY = isShare ? 20 : 4;
  activeKeys.forEach(k => {
    buckets.forEach((_b, idx) => {
      const v = valAt(k, idx);
      if (v > maxY) maxY = v;
    });
  });
  const ySteps = 4;
  const stepVal = Math.max(1, Math.ceil(maxY / ySteps));
  const yCeil = stepVal * ySteps;

  const xAt = idx => buckets.length <= 1 ? padL + plotW / 2 : padL + (idx / (buckets.length - 1)) * plotW;
  const yAt = val => padT + plotH - (val / yCeil) * plotH;

  // Grid lines & Y-axis labels
  let gridHtml = "";
  for (let i = 0; i <= ySteps; i++) {
    const v = i * stepVal;
    const y = yAt(v).toFixed(1);
    const yLbl = isShare ? `${v}%` : `${v}`;
    gridHtml += `
      <line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="rgba(148,163,184,0.14)" stroke-dasharray="${i === 0 ? 'none' : '3,3'}" />
      <text x="${padL - 8}" y="${Number(y) + 4}" text-anchor="end" fill="#94a3b8" font-size="11">${yLbl}</text>
    `;
  }

  // X-axis labels (avoid crowding on 30-day / 26-week charts)
  const labelStride = Math.max(1, Math.ceil(buckets.length / 12));
  let xLabelsHtml = "";
  buckets.forEach((b, idx) => {
    if (idx % labelStride === 0 || idx === buckets.length - 1) {
      const x = xAt(idx).toFixed(1);
      xLabelsHtml += `<text x="${x}" y="${height - 8}" text-anchor="middle" fill="#94a3b8" font-size="11">${esc(b.label)}</text>`;
    }
  });

  // Defs & lines for each active work type
  let defsHtml = "";
  let pathsHtml = "";
  activeKeys.forEach((k, sIdx) => {
    const vals = buckets.map((_b, idx) => valAt(k, idx));
    const color = WORK_TYPE_COLORS[k] || "#60a5fa";
    const pts = vals.map((v, idx) => `${xAt(idx).toFixed(1)},${yAt(v).toFixed(1)}`);
    const gradId = `trendGrad_${sIdx}`;

    if (activeKeys.length <= 2) {
      defsHtml += `
        <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.26" />
          <stop offset="100%" stop-color="${color}" stop-opacity="0.0" />
        </linearGradient>
      `;
      const areaPts = `${xAt(0).toFixed(1)},${(padT + plotH).toFixed(1)} ` + pts.join(" ") + ` ${xAt(vals.length - 1).toFixed(1)},${(padT + plotH).toFixed(1)}`;
      pathsHtml += `<polygon points="${areaPts}" fill="url(#${gradId})" />`;
    }

    pathsHtml += `<polyline fill="none" stroke="${color}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" points="${pts.join(" ")}" />`;
    vals.forEach((v, idx) => {
      const cx = xAt(idx).toFixed(1);
      const cy = yAt(v).toFixed(1);
      pathsHtml += `<circle cx="${cx}" cy="${cy}" r="3.2" fill="${color}" stroke="#0f172a" stroke-width="1.4" />`;
    });
  });

  svgWrap.innerHTML = `
    <svg id="trend-svg" viewBox="0 0 ${width} ${height}" width="100%" height="${height}" style="overflow:visible;cursor:crosshair;"
         onmousemove="onTrendChartHover(event)" onmouseleave="hideTrendTooltip()">
      <defs>${defsHtml}</defs>
      ${gridHtml}
      ${xLabelsHtml}
      ${pathsHtml}
      <line id="trend-crosshair" x1="0" y1="${padT}" x2="0" y2="${padT + plotH}" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="3,3" style="display:none;" />
    </svg>
  `;
}

function onTrendChartHover(evt) {
  if (!trendData || !trendData.buckets || !trendData.buckets.length) return;
  const svg = document.getElementById("trend-svg");
  const tooltip = document.getElementById("trend-tooltip");
  const cross = document.getElementById("trend-crosshair");
  const wrap = document.getElementById("trend-chart-wrap");
  if (!svg || !tooltip || !wrap) return;

  const rect = svg.getBoundingClientRect();
  const relX = evt.clientX - rect.left;
  const padL = 42;
  const padR = 18;
  const plotW = rect.width - padL - padR;
  const buckets = trendData.buckets;
  const ratio = Math.max(0, Math.min(1, (relX - padL) / Math.max(1, plotW)));
  const idx = Math.round(ratio * (buckets.length - 1));
  const bucket = buckets[idx];
  if (!bucket) return;

  const xPos = buckets.length <= 1 ? padL + plotW / 2 : padL + (idx / (buckets.length - 1)) * plotW;
  if (cross) {
    cross.setAttribute("x1", xPos.toFixed(1));
    cross.setAttribute("x2", xPos.toFixed(1));
    cross.style.display = "block";
  }

  const activeKeys = [...activeWorkTypes].filter(k => k !== "All Demand" && Array.isArray(trendData.series[k]));
  const allDemandAtIdx = ((trendData.series["All Demand"] || [])[idx]) || 0;
  const isShare = currentTrendMode === "share";
  const rows = activeKeys
    .map(k => {
      const raw = (trendData.series[k] || [])[idx] || 0;
      const pct = allDemandAtIdx > 0 ? Math.round((raw / allDemandAtIdx) * 1000) / 10 : 0;
      return { key: k, raw, pct, sortVal: isShare ? pct : raw, color: WORK_TYPE_COLORS[k] || "#60a5fa" };
    })
    .sort((a, b) => b.sortVal - a.sortVal);
  const bucketTotal = rows.reduce((s, r) => s + r.raw, 0);

  tooltip.innerHTML = `
    <div class="trend-tooltip-title">${esc(bucket.label)} &middot; ${bucketTotal} posts</div>
    ${rows.map(r => `
      <div class="trend-tooltip-row">
        <span style="display:inline-flex;align-items:center;gap:6px;">
          <span class="work-pill-dot" style="background:${r.color}"></span>
          <span>${esc(r.key)}</span>
        </span>
        <strong>${isShare ? `${r.pct}% (${r.raw})` : r.raw}</strong>
      </div>
    `).join("")}
  `;
  tooltip.style.display = "block";

  const wrapRect = wrap.getBoundingClientRect();
  let left = evt.clientX - wrapRect.left + 14;
  if (left + 210 > wrapRect.width) {
    left = evt.clientX - wrapRect.left - 210;
  }
  tooltip.style.left = `${Math.max(8, left)}px`;
  tooltip.style.top = `42px`;
}

function hideTrendTooltip() {
  const tooltip = document.getElementById("trend-tooltip");
  const cross = document.getElementById("trend-crosshair");
  if (tooltip) tooltip.style.display = "none";
  if (cross) cross.style.display = "none";
}

async function loadDashboard() {
  const [sumRes, setRes] = await Promise.all([
    fetchJsonWithFallback("/api/summary", snap => computeStaticSummary(snap, "all", "all", "all")),
    fetchJsonWithFallback("/api/settings", snap => snap.settings || {}),
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

function onPricingTradeSelect(trade) {
  selectedPricingTrade = trade || "all";
  const sel = document.getElementById("pricing-trade-select");
  if (sel && sel.value !== selectedPricingTrade) sel.value = selectedPricingTrade;
  renderPricingAndTaskBreakdown();
}

function renderPricingAndTaskBreakdown() {
  const container = document.getElementById("pricing-task-chart");
  if (!container || !summaryData) return;

  const subList = summaryData.sub_service_breakdown || [];
  const priceByCat = summaryData.pricing_by_category || [];
  const catList = summaryData.category_breakdown || [];

  const fmtHr = r => {
    if (!r || !r.avg_hourly) return `<span style="color:var(--muted);">—</span>`;
    const range = r.min_hourly && r.max_hourly && r.min_hourly !== r.max_hourly
      ? `<span class="price-range-sub">($${r.min_hourly}–$${r.max_hourly}/hr · ${r.hourly_count})</span>`
      : `<span class="price-range-sub">(${r.hourly_count} post${r.hourly_count > 1 ? "s" : ""})</span>`;
    return `<span class="price-pill">$${r.avg_hourly}/hr avg</span>${range}`;
  };

  const fmtFlat = r => {
    if (!r || !r.avg_flat) return `<span style="color:var(--muted);">—</span>`;
    const range = r.min_flat && r.max_flat && r.min_flat !== r.max_flat
      ? `<span class="price-range-sub">($${r.min_flat}–$${r.max_flat} · ${r.flat_count})</span>`
      : `<span class="price-range-sub">(${r.flat_count} post${r.flat_count > 1 ? "s" : ""})</span>`;
    return `<span class="price-pill price-pill-flat">$${r.avg_flat} avg</span>${range}`;
  };

  if (selectedPricingTrade === "all") {
    const priceLookup = {};
    priceByCat.forEach(p => { priceLookup[p.primary_category] = p; });
    const tasksByCat = {};
    subList.forEach(s => {
      if (!tasksByCat[s.primary_category]) tasksByCat[s.primary_category] = [];
      tasksByCat[s.primary_category].push(s);
    });

    const rowsHtml = catList.map(c => {
      const cat = c.primary_category;
      const pr = priceLookup[cat] || {};
      const topTasks = (tasksByCat[cat] || []).slice(0, 3).map(t => `${esc(t.sub_service)} (${t.total_demand})`).join(" · ");
      return `
        <tr data-cat="${esc(cat)}" onclick="onPricingTradeSelect(this.dataset.cat)" title="Click to drill into Specific Tasks for ${esc(cat)}">
          <td>
            <div style="font-weight:600;color:var(--text);">${esc(cat)}</div>
            <div style="font-size:0.75rem;color:var(--muted);margin-top:2px;">Top Tasks: ${topTasks || "General"}</div>
          </td>
          <td>
            <span style="color:#34d399;font-weight:600;">${c.hiring_count || 0} Hiring</span> &middot;
            <span style="color:#fbbf24;">${c.diy_count || 0} DIY</span> &middot;
            <span style="color:#c084fc;">${c.provider_supply || 0} Supply</span>
          </td>
          <td>${fmtHr(pr)}</td>
          <td>${fmtFlat(pr)}</td>
          <td style="text-align:right;">
            <button class="secondary" style="padding:4px 10px;font-size:0.76rem;">View Tasks</button>
          </td>
        </tr>
      `;
    }).join("");

    container.innerHTML = `
      <div class="table-wrap">
        <table class="pricing-table">
          <thead>
            <tr>
              <th>Trade Category &amp; Top Specific Tasks</th>
              <th>Demand &amp; Supply Volume</th>
              <th>Hourly Rate Benchmark ($/hr)</th>
              <th>Flat Job Budget Benchmark ($)</th>
              <th style="text-align:right;">Drill-Down</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
  } else {
    const tasks = subList.filter(s => s.primary_category === selectedPricingTrade);
    const rowsHtml = tasks.map(t => `
      <tr data-cat="${esc(t.primary_category)}" data-sub="${esc(t.sub_service)}" onclick="filterBySubService(this.dataset.cat, this.dataset.sub)" title="Click to filter leads table to this Specific Task">
        <td>
          <div style="font-weight:600;color:#93c5fd;">${esc(t.sub_service)}</div>
          <div style="font-size:0.74rem;color:var(--muted);">${esc(t.primary_category)}</div>
        </td>
        <td>
          <span style="color:#34d399;font-weight:600;">${t.hiring_count || 0} Hiring</span> &middot;
          <span style="color:#fbbf24;">${t.diy_count || 0} DIY</span> &middot;
          <span style="color:#c084fc;">${t.provider_supply || 0} Supply</span>
        </td>
        <td>${fmtHr(t)}</td>
        <td>${fmtFlat(t)}</td>
        <td style="text-align:right;">
          <button class="secondary" style="padding:4px 10px;font-size:0.76rem;">Filter Posts</button>
        </td>
      </tr>
    `).join("");

    container.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-size:0.84rem;color:var(--text-secondary);">
          Showing Specific Tasks within <strong>${esc(selectedPricingTrade)}</strong> (click any task row to filter posts below)
        </div>
        <button class="secondary" style="padding:5px 11px;font-size:0.78rem;" onclick="onPricingTradeSelect('all')">Back to All Trade Categories</button>
      </div>
      <div class="table-wrap">
        <table class="pricing-table">
          <thead>
            <tr>
              <th>Specific Task (Service)</th>
              <th>Demand &amp; Supply Volume</th>
              <th>Hourly Rate ($/hr)</th>
              <th>Flat Job Price ($)</th>
              <th style="text-align:right;">Action</th>
            </tr>
          </thead>
          <tbody>${rowsHtml || `<tr><td colspan="5" style="text-align:center;color:var(--muted);">No tasks found for this trade.</td></tr>`}</tbody>
        </table>
      </div>
    `;
  }
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
            <span style="color:#fbbf24">${c.diy_count} DIY</span> ·
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
  chEl.innerHTML = channels.slice(0, 8).map(ch => `
    <span class="badge b-cat" style="margin:3px 4px 3px 0; padding:5px 10px;">
      ${esc(ch.source_detail)}: ${ch.demand_count}
    </span>
  `).join("");
}

function populateFilterDropdowns(sumRes) {
  const catSel = document.getElementById("filter-category");
  const currentCat = catSel.value || "all";
  const cats = sumRes.categories_list || [];
  catSel.innerHTML = `<option value="all">All Trade Categories</option>` +
    cats.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  catSel.value = currentCat;

  const pSel = document.getElementById("pricing-trade-select");
  if (pSel) {
    pSel.innerHTML = `<option value="all">All Trade Categories (Overview)</option>` +
      cats.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    pSel.value = selectedPricingTrade;
  }

  updateSubServiceOptions();
  updateProvinceAndCityOptions();
}

function updateSubServiceOptions() {
  const subSel = document.getElementById("filter-sub-service");
  if (!subSel) return;
  const cat = document.getElementById("filter-category").value || "all";
  const prevSub = subSel.value || "all";
  const subMap = (summaryData && summaryData.sub_services_map) ? summaryData.sub_services_map : {};

  let tasks = [];
  if (cat !== "all" && Array.isArray(subMap[cat])) {
    tasks = subMap[cat];
  } else {
    Object.values(subMap).forEach(arr => {
      (arr || []).forEach(t => {
        if (!tasks.includes(t)) tasks.push(t);
      });
    });
  }

  const label = cat !== "all" ? `All Tasks in ${cat}` : "All Specific Tasks";
  subSel.innerHTML = `<option value="all">${esc(label)}</option>` +
    tasks.map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join("");
  subSel.value = tasks.includes(prevSub) ? prevSub : "all";
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
    ? "All Provinces"
    : country === "United States"
    ? "All States"
    : "All Provinces / States";

  provSel.innerHTML = `<option value="all">${provLabel}</option>` +
    provinces.map(p => `<option value="${esc(p)}">${esc(p)}</option>`).join("");
  provSel.value = provinces.includes(prevProv) ? prevProv : "all";

  const activeProv = provSel.value;
  const matchingCityRegs = matchingCountryRegs.filter(r => activeProv === "all" || r.province === activeProv);
  const cities = [...new Set(matchingCityRegs.map(r => r.name))];

  const cityLabel = activeProv !== "all"
    ? `All in ${activeProv}`
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

function onCategoryDropdownChange() {
  const cat = document.getElementById("filter-category").value;
  const subSel = document.getElementById("filter-sub-service");
  if (subSel) subSel.value = "all";
  updateSubServiceOptions();
  if (cat && cat !== "all") {
    activeWorkTypes.add(cat);
    renderTrendPills();
    renderTrendChart();
    onPricingTradeSelect(cat);
  } else {
    onPricingTradeSelect("all");
  }
  loadPosts();
}

function filterByCategory(cat) {
  document.getElementById("filter-category").value = cat;
  const subSel = document.getElementById("filter-sub-service");
  if (subSel) subSel.value = "all";
  updateSubServiceOptions();
  if (cat && cat !== "all") {
    activeWorkTypes.add(cat);
    renderTrendPills();
    renderTrendChart();
    onPricingTradeSelect(cat);
  }
  switchTab("leads");
  loadPosts();
}

function filterBySubService(cat, sub) {
  document.getElementById("filter-category").value = cat;
  updateSubServiceOptions();
  const subSel = document.getElementById("filter-sub-service");
  if (subSel) subSel.value = sub;
  switchTab("leads");
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
  switchTab("leads");
  await refreshSummaryForGeo();
  await loadPosts();
}

function getFilterQueryString() {
  const subSel = document.getElementById("filter-sub-service");
  const params = new URLSearchParams({
    platform: document.getElementById("filter-platform").value,
    intent_type: document.getElementById("filter-intent").value,
    category: document.getElementById("filter-category").value,
    sub_service: subSel ? subSel.value : "all",
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

  const res = await fetchJsonWithFallback(`/api/posts?${qs}`, snap => {
    const plat = document.getElementById("filter-platform").value;
    const intent = document.getElementById("filter-intent").value;
    const cat = document.getElementById("filter-category").value;
    const subSel = document.getElementById("filter-sub-service");
    const sub = subSel ? subSel.value : "all";
    const country = document.getElementById("filter-country").value;
    const prov = document.getElementById("filter-province").value;
    const city = document.getElementById("filter-region").value;
    const urg = document.getElementById("filter-urgency").value;
    const q = (document.getElementById("filter-search").value || "").trim().toLowerCase();

    const filtered = (snap.posts || []).filter(p => {
      if (plat !== "all" && p.platform !== plat) return false;
      if (intent === "demand_only") {
        if (p.intent_type !== "customer_hiring" && p.intent_type !== "diy_help_needed") return false;
      } else if (intent !== "all" && p.intent_type !== intent) return false;
      if (cat !== "all" && p.primary_category !== cat) return false;
      if (sub !== "all" && p.sub_service !== sub) return false;
      if (country !== "all" && p.country !== country) return false;
      if (prov !== "all" && p.province !== prov) return false;
      if (city !== "all" && p.city_region !== city) return false;
      if (urg !== "all" && p.urgency !== urg) return false;
      if (q) {
        const hay = `${p.title || ""} ${p.body || ""} ${p.neighborhood || ""} ${p.source_detail || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    return { posts: filtered, count: filtered.length };
  });
  allFilteredPosts = res.posts || [];
  applySortAndRender();
}

function applySortAndRender() {
  const sortEl = document.getElementById("filter-sort");
  const sortBy = sortEl ? sortEl.value : "relevance";
  const urgRank = { high: 3, medium: 2, low: 1 };
  const intentRank = { customer_hiring: 3, diy_help_needed: 2, job_posting: 1, service_provider_ad: 1, irrelevant: 0 };

  allFilteredPosts.sort((a, b) => {
    if (sortBy === "date_desc") {
      return String(b.posted_at || "").localeCompare(String(a.posted_at || ""));
    }
    if (sortBy === "date_asc") {
      return String(a.posted_at || "").localeCompare(String(b.posted_at || ""));
    }
    if (sortBy === "urgency") {
      const uDiff = (urgRank[b.urgency] || 0) - (urgRank[a.urgency] || 0);
      if (uDiff !== 0) return uDiff;
      return (b.intent_score || 0) - (a.intent_score || 0);
    }
    const iDiff = (intentRank[b.intent_type] || 0) - (intentRank[a.intent_type] || 0);
    if (iDiff !== 0) return iDiff;
    const sDiff = (b.intent_score || 0) - (a.intent_score || 0);
    if (sDiff !== 0) return sDiff;
    return String(b.posted_at || "").localeCompare(String(a.posted_at || ""));
  });

  currentPage = 1;
  renderPostsPage();
}

async function resetFilters() {
  document.getElementById("filter-intent").value = "demand_only";
  document.getElementById("filter-platform").value = "all";
  document.getElementById("filter-category").value = "all";
  const subSel = document.getElementById("filter-sub-service");
  if (subSel) subSel.value = "all";
  document.getElementById("filter-country").value = "all";
  document.getElementById("filter-province").value = "all";
  document.getElementById("filter-region").value = "all";
  document.getElementById("filter-urgency").value = "all";
  document.getElementById("filter-sort").value = "relevance";
  document.getElementById("filter-search").value = "";
  selectedPricingTrade = "all";
  const pSel = document.getElementById("pricing-trade-select");
  if (pSel) pSel.value = "all";
  syncActiveKpiCard("demand_only");
  updateSubServiceOptions();
  updateProvinceAndCityOptions();
  await refreshSummaryForGeo();
  await loadPosts();
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
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:32px;">No posts match your current filters.</td></tr>`;
    if (pagBar) pagBar.innerHTML = "";
    return;
  }

  tbody.innerHTML = posts.map(p => {
    const intentBadge = p.intent_type === "customer_hiring"
      ? `<span class="badge b-hiring">Hiring Pro</span>`
      : p.intent_type === "diy_help_needed"
      ? `<span class="badge b-diy">DIY Help</span>`
      : p.intent_type === "job_posting"
      ? `<span class="badge b-job">Job Posting</span>`
      : p.intent_type === "irrelevant"
      ? `<span class="badge b-cat">Irrelevant</span>`
      : `<span class="badge b-supply">Provider Ad</span>`;

    const platBadge = p.platform === "reddit"
      ? `<span class="badge b-reddit">Reddit</span>`
      : p.platform === "kijiji"
      ? `<span class="badge b-kijiji">Kijiji</span>`
      : p.platform === "stackexchange"
      ? `<span class="badge b-stackexchange">StackExchange</span>`
      : `<span class="badge b-craigslist">Craigslist</span>`;

    const urgBadge = p.urgency === "high"
      ? `<div style="margin-top:5px;"><span class="badge b-high">Urgent</span></div>`
      : "";

    const bodySnippet = (p.body || "").trim();
    const dateStr = (p.posted_at || "").slice(0, 10);

    return `
      <tr>
        <td>
          <a class="post-title" href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener noreferrer">${esc(p.title)}</a>
          ${bodySnippet ? `<div class="post-body">${esc(bodySnippet)}</div>` : ""}
        </td>
        <td>
          <div><span class="badge b-cat">${esc(p.primary_category)}</span></div>
          ${p.sub_service ? `<div><span class="badge b-subtask">${esc(p.sub_service)}</span></div>` : ""}
          ${p.price_mention ? `<div style="color:#34d399;font-size:0.78rem;margin-top:6px;font-weight:600;">${esc(p.price_mention)}</div>` : ""}
        </td>
        <td>
          ${intentBadge}
          ${urgBadge}
        </td>
        <td>
          <div style="font-weight:600;font-size:0.83rem;color:var(--text-secondary);">${esc(p.city_region)}</div>
          <div style="display:flex;align-items:center;gap:6px;margin-top:5px;flex-wrap:wrap;">
            ${platBadge}
            <span style="font-size:0.75rem;color:var(--muted);">${esc(dateStr)}</span>
          </div>
        </td>
        <td style="text-align:right;">
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
        Showing <strong>${startIdx + 1}-${endIdx}</strong> of <strong>${total}</strong>
        &nbsp;·&nbsp;
        Rows:
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
  btn.textContent = "Scraping...";
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
