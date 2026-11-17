// Newswire Frontend Application Logic - Category-First & Compliance Monitor
const API_BASE = ""; // Relative path works seamlessly via Nginx reverse proxy (/api/v1) and FastAPI direct

let currentTab = "articles";
let currentCategory = ""; // Empty string denotes 'All Topics'
let sentimentChartInstance = null;
let complianceChartInstance = null;
let currentArticlesData = [];

// DOM Ready initialization
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    checkBackendConnection();
    loadDashboard();

    // Auto refresh telemetry & counts every 20 seconds
    setInterval(() => {
        checkBackendConnection();
        loadKPIs();
        loadCategoryCounts();
    }, 20000);
});

// Toast notification helper
function showToast(message, duration = 3500) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.style.display = "block";
    setTimeout(() => {
        toast.style.display = "none";
    }, duration);
}

// Check Backend Connectivity & Health
async function checkBackendConnection() {
    const indicator = document.getElementById("connection-status");
    const pingText = document.getElementById("ping-text");
    const startTime = performance.now();

    try {
        const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
        const latency = Math.round(performance.now() - startTime);
        if (res.ok) {
            indicator.className = "connection-indicator";
            pingText.textContent = `Backend Live (${latency}ms)`;
        } else {
            throw new Error(`HTTP ${res.status}`);
        }
    } catch (err) {
        indicator.className = "connection-indicator disconnected";
        pingText.textContent = "Backend Disconnected";
    }
}

// Load all dashboard components
async function loadDashboard() {
    await loadCategoryCounts();
    await loadArticles();
    await loadKPIs();
    await loadMetricsCharts();
}

// Category Selector Handler
function selectCategory(categoryName, pillElement) {
    currentCategory = categoryName;

    // Update active visual pill
    document.querySelectorAll(".category-pill").forEach(p => p.classList.remove("active"));
    if (pillElement) {
        pillElement.classList.add("active");
    }

    // Update active label display
    const activeLabel = document.getElementById("active-category-display");
    if (activeLabel) {
        activeLabel.textContent = categoryName || "All Topics";
    }

    // Reload articles feed for selected category
    loadArticles();
}

// Fetch Real-Time Category Article Counts
async function loadCategoryCounts() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/categories`);
        if (!res.ok) return;
        const data = await res.json();

        // Update All Topics count
        const countAllEl = document.getElementById("count-all");
        if (countAllEl) {
            countAllEl.textContent = (data.total_articles || 0).toLocaleString();
        }

        // Map category counts
        const map = {};
        (data.categories || []).forEach(c => {
            map[c.name] = c.count;
        });

        const mapping = {
            "count-business": "Business & Finance",
            "count-tech": "Technology & AI",
            "count-compliance": "Compliance & Sanctions",
            "count-world": "World & Geopolitics",
            "count-beauty": "Beauty",
            "count-entertainment": "Entertainment",
            "count-sports": "Sports"
        };

        for (const [elemId, catName] of Object.entries(mapping)) {
            const el = document.getElementById(elemId);
            if (el) {
                el.textContent = (map[catName] || 0).toLocaleString();
            }
        }
    } catch (e) {
        console.warn("Could not fetch category counts:", e);
    }
}

// Fetch Status & Update KPI Counters
async function loadKPIs() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/status`);
        if (!res.ok) return;
        const data = await res.json();

        const kpiArticles = document.getElementById("kpi-total-articles");
        const kpiAlerts = document.getElementById("kpi-flagged-alerts");
        const kpiSources = document.getElementById("kpi-active-sources");
        const kpiSentiment = document.getElementById("kpi-sentiment-summary");

        if (kpiArticles) kpiArticles.textContent = (data.total_articles_count || 0).toLocaleString();
        if (kpiAlerts) kpiAlerts.textContent = (data.flagged_articles_count || 0).toLocaleString();
        if (kpiSources) kpiSources.textContent = (data.active_sources_count || 0).toLocaleString();

        const pos = data.sentiment_ratio?.positive || 0;
        const neu = data.sentiment_ratio?.neutral || 0;
        const neg = data.sentiment_ratio?.negative || 0;
        if (kpiSentiment) kpiSentiment.textContent = `${pos} / ${neu} / ${neg}`;

        updateSentimentChart(pos, neu, neg);
    } catch (e) {
        console.error("Error fetching KPIs:", e);
    }
}

// Initialize Charts using Chart.js
function initCharts() {
    const sentimentCtx = document.getElementById("sentimentChart")?.getContext("2d");
    if (sentimentCtx) {
        sentimentChartInstance = new Chart(sentimentCtx, {
            type: "doughnut",
            data: {
                labels: ["Positive", "Neutral", "Negative"],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ["#10b981", "#64748b", "#ef4444"],
                    borderColor: "#1f293d",
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "right",
                        labels: { color: "#9ca3af", font: { size: 12, family: "Inter" } }
                    }
                }
            }
        });
    }

    const complianceCtx = document.getElementById("complianceChart")?.getContext("2d");
    if (complianceCtx) {
        complianceChartInstance = new Chart(complianceCtx, {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Violations Triggered",
                    data: [],
                    backgroundColor: "#f87171",
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: "#9ca3af", precision: 0 },
                        grid: { color: "rgba(255,255,255,0.06)" }
                    },
                    x: {
                        ticks: { color: "#9ca3af", font: { size: 10 } },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

function updateSentimentChart(pos, neu, neg) {
    if (sentimentChartInstance) {
        sentimentChartInstance.data.datasets[0].data = [pos, neu, neg];
        sentimentChartInstance.update();
    }
}

async function loadMetricsCharts() {
    try {
        const res = await fetch(`${API_BASE}/api/v1/metrics`);
        if (!res.ok) return;
        const data = await res.json();

        if (complianceChartInstance && data.top_compliance_categories) {
            const categories = data.top_compliance_categories.map(c => c.category);
            const hits = data.top_compliance_categories.map(c => c.hits);
            complianceChartInstance.data.labels = categories;
            complianceChartInstance.data.datasets[0].data = hits;
            complianceChartInstance.update();
        }
    } catch (e) {
        console.error("Error loading metrics:", e);
    }
}

function getCategoryClass(cat) {
    if (!cat) return "cat-business-finance";
    const lower = cat.toLowerCase();
    if (lower.includes("beauty")) return "cat-beauty";
    if (lower.includes("sport")) return "cat-sports";
    if (lower.includes("entertain")) return "cat-entertainment";
    if (lower.includes("tech") || lower.includes("ai")) return "cat-technology-ai";
    if (lower.includes("world") || lower.includes("geopolitic")) return "cat-world-geopolitics";
    if (lower.includes("compliance") || lower.includes("sanction")) return "cat-compliance-sanctions";
    return "cat-business-finance";
}

// Fetch & Render Articles Feed
async function loadArticles() {
    const sentiment = document.getElementById("filter-sentiment").value;
    const isFlagged = document.getElementById("filter-flagged").value;
    const search = document.getElementById("filter-search").value.trim();
    const minRisk = document.getElementById("filter-risk").value;

    let url = `${API_BASE}/api/v1/articles?limit=50`;
    if (currentCategory) url += `&category=${encodeURIComponent(currentCategory)}`;
    if (sentiment) url += `&sentiment=${encodeURIComponent(sentiment)}`;
    if (isFlagged !== "") url += `&is_flagged=${isFlagged}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (minRisk) url += `&min_risk_score=${encodeURIComponent(minRisk)}`;

    const tbody = document.getElementById("articles-tbody");
    tbody.innerHTML = `<tr><td colspan="4" class="empty-cell">Scanning intelligence database...</td></tr>`;

    try {
        const res = await fetch(url);
        const articles = await res.json();
        currentArticlesData = articles;

        const countText = currentCategory
            ? `${articles.length} records in ${currentCategory}`
            : `${articles.length} total records`;
        document.getElementById("items-count").textContent = countText;

        if (!articles || articles.length === 0) {
            const catMsg = currentCategory ? ` for "${currentCategory}"` : "";
            tbody.innerHTML = `<tr><td colspan="4" class="empty-cell">No articles found${catMsg}. Click "Run Ingestion Now" to poll live feeds.</td></tr>`;
            return;
        }

        tbody.innerHTML = articles.map(a => {
            const dateStr = a.publish_date ? new Date(a.publish_date).toLocaleDateString() : "Recent";
            const sentimentBadge = a.sentiment_label === "positive"
                ? `<span class="badge badge-pos">▲ Pos (${a.sentiment_score})</span>`
                : a.sentiment_label === "negative"
                ? `<span class="badge badge-neg">▼ Neg (${a.sentiment_score})</span>`
                : `<span class="badge badge-neu">● Neu (${a.sentiment_score})</span>`;

            const riskBadge = a.is_compliance_flagged
                ? `<span class="risk-pill risk-critical">⚠️ RISK ${a.compliance_risk_score}</span>`
                : `<span class="risk-pill risk-clean">✓ CLEAN (${a.compliance_risk_score})</span>`;

            const categoriesTags = (a.compliance_categories || []).map(c =>
                `<span class="flag-category-tag">${c}</span>`
            ).join(" ");

            const keywordsPills = (a.keywords || []).slice(0, 4).map(k =>
                `<span class="tag-pill">#${k}</span>`
            ).join(" ");

            const catClass = getCategoryClass(a.category);
            const catBadge = `<span class="category-tag-inline ${catClass}">${escapeHtml(a.category || "Business & Finance")}</span>`;

            return `
                <tr>
                    <td>
                        <div style="margin-bottom: 4px;">${catBadge}</div>
                        <a href="javascript:void(0)" onclick="inspectArticle(${a.id})" class="article-headline">${escapeHtml(a.title)}</a>
                        <div class="article-snippet">${escapeHtml(a.summary || "Extractive NLP summary pending.")}</div>
                        <div class="keywords-wrap">${keywordsPills}</div>
                    </td>
                    <td>
                        <div style="font-weight: 600; color: #e2e8f0;">${escapeHtml(a.source_name || "Unknown")}</div>
                        <div class="article-meta-row">${dateStr}</div>
                    </td>
                    <td>${sentimentBadge}</td>
                    <td>
                        <div style="margin-bottom: 6px;">${riskBadge}</div>
                        <div>${categoriesTags || '<span style="color: var(--text-muted); font-size: 11px;">No triggers</span>'}</div>
                    </td>
                </tr>
            `;
        }).join("");

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-cell">Failed to load articles: ${e.message}</td></tr>`;
    }
}

// Fetch & Render Sources View
async function loadSources() {
    const tbody = document.getElementById("sources-tbody");
    tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">Loading configured news sources...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/api/v1/sources`);
        const sources = await res.json();

        if (!sources || sources.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">No sources configured yet. Add one using the button above.</td></tr>`;
            return;
        }

        tbody.innerHTML = sources.map(s => {
            const lastFetched = s.last_fetched_at ? new Date(s.last_fetched_at).toLocaleTimeString() : "Never";
            return `
                <tr>
                    <td><strong>${escapeHtml(s.name)}</strong></td>
                    <td style="font-family: monospace; font-size: 11px; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="${s.url}" target="_blank" style="color: var(--text-secondary);">${escapeHtml(s.url)}</a>
                    </td>
                    <td><span class="badge badge-neu">${s.source_type}</span></td>
                    <td><span class="category-tag-inline ${getCategoryClass(s.category)}">${escapeHtml(s.category)}</span></td>
                    <td>${s.fetch_interval_minutes}m (Last: ${lastFetched})</td>
                    <td>
                        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="triggerSingleSource(${s.id})">⚡ Ingest</button>
                        <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="deleteSource(${s.id})">Delete</button>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">Failed to load sources.</td></tr>`;
    }
}

// Fetch & Render Compliance Taxonomies
async function loadRules() {
    const container = document.getElementById("rules-container");
    container.innerHTML = `<div class="empty-cell">Loading active compliance taxonomies...</div>`;

    try {
        const res = await fetch(`${API_BASE}/api/v1/compliance/rules`);
        const data = await res.json();
        const rules = data.compliance_rules || {};

        container.innerHTML = Object.entries(rules).map(([category, details]) => {
            const severityBadge = details.severity === "CRITICAL"
                ? `<span class="badge badge-neg">CRITICAL</span>`
                : `<span class="badge badge-neu">${details.severity}</span>`;

            const kws = (details.keywords || []).map(k => `<span class="tag-pill">${k}</span>`).join(" ");

            return `
                <div style="background: rgba(10, 15, 29, 0.4); border: 1px solid var(--border-light); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h4 style="font-size: 14px; font-weight: 600;">${escapeHtml(category)}</h4>
                        ${severityBadge}
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">${kws}</div>
                </div>
            `;
        }).join("");
    } catch (e) {
        container.innerHTML = `<div class="empty-cell">Failed to load rules.</div>`;
    }
}

// Fetch & Render Ingestion Logs
async function loadLogs() {
    const tbody = document.getElementById("logs-tbody");
    try {
        const res = await fetch(`${API_BASE}/api/v1/metrics`);
        const data = await res.json();
        const logs = data.recent_fetch_logs || [];

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">No ingestion audit records yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => {
            const statusBadge = l.status === "SUCCESS"
                ? `<span class="badge badge-pos">SUCCESS</span>`
                : `<span class="badge badge-neg">ERROR</span>`;
            return `
                <tr>
                    <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
                    <td><strong>${escapeHtml(l.source_name)}</strong></td>
                    <td>${statusBadge}</td>
                    <td>${l.discovered} found / ${l.ingested} ingested</td>
                    <td><span style="color: #60a5fa; font-family: monospace;">${l.skipped_duplicates} skipped</span></td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">Failed to load logs.</td></tr>`;
    }
}

// Trigger Manual Batch Ingestion
async function triggerIngestion() {
    const btn = document.getElementById("btn-run-ingestion");
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Ingesting Feeds...`;

    try {
        const res = await fetch(`${API_BASE}/api/v1/fetch/trigger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ background: false, limit_per_source: 15 })
        });
        const data = await res.json();
        showToast(data.message || "Ingestion cycle completed successfully!");
        await loadCategoryCounts();
        await loadKPIs();
        await loadArticles();
        await loadMetricsCharts();
    } catch (e) {
        showToast("Ingestion request failed: " + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡</span> Run Ingestion Now`;
    }
}

// Trigger Single Source Ingestion
async function triggerSingleSource(sourceId) {
    showToast(`Polling source ${sourceId}...`);
    try {
        const res = await fetch(`${API_BASE}/api/v1/fetch/trigger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_id: sourceId, background: false, limit_per_source: 15 })
        });
        const data = await res.json();
        showToast(data.message || "Source ingested!");
        await loadCategoryCounts();
        await loadKPIs();
        await loadArticles();
        await loadSources();
    } catch (e) {
        showToast("Error ingesting source: " + e.message);
    }
}

// Inspect Full Article Details & Compliance Flags Modal
async function inspectArticle(articleId) {
    const modal = document.getElementById("modal-article-detail");
    modal.classList.add("active");
    const container = document.getElementById("article-modal-body");
    container.innerHTML = `<div class="empty-cell">Loading full article text and compliance hit snippets...</div>`;

    try {
        const res = await fetch(`${API_BASE}/api/v1/articles/${articleId}`);
        const article = await res.json();

        const flagsHtml = (article.compliance_flags && article.compliance_flags.length > 0)
            ? article.compliance_flags.map(f => `
                <div style="background: rgba(220, 38, 38, 0.1); border-left: 3px solid #ef4444; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: 700; color: #fca5a5;">${escapeHtml(f.category)}: [${escapeHtml(f.term)}]</span>
                        <span class="badge badge-neg">${escapeHtml(f.severity)}</span>
                    </div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #cbd5e1;">${escapeHtml(f.context_snippet || "")}</div>
                </div>
            `).join("")
            : `<div style="color: #6ee7b7; font-size: 13px;">✓ No regulatory or compliance risk flags triggered for this article.</div>`;

        const catClass = getCategoryClass(article.category);
        const catBadge = `<span class="category-tag-inline ${catClass}">${escapeHtml(article.category || "Business & Finance")}</span>`;

        container.innerHTML = `
            <div style="margin-bottom: 16px;">
                <div style="margin-bottom: 6px;">${catBadge}</div>
                <h2 style="font-size: 18px; margin-bottom: 8px;">${escapeHtml(article.title)}</h2>
                <div style="font-size: 12px; color: var(--text-muted); display: flex; gap: 16px; margin-bottom: 12px; flex-wrap: wrap;">
                    <span><strong>Source:</strong> ${escapeHtml(article.source_name || "Unknown")}</span>
                    <span><strong>Category:</strong> ${escapeHtml(article.category || "Business & Finance")}</span>
                    <span><strong>Published:</strong> ${article.publish_date ? new Date(article.publish_date).toLocaleString() : "Recent"}</span>
                    <span><strong>Risk Score:</strong> ${article.compliance_risk_score} / 100</span>
                </div>
                <a href="${article.url}" target="_blank" class="btn btn-secondary" style="font-size: 11px; padding: 4px 10px;">Open Original Article ↗</a>
            </div>

            <div style="margin-bottom: 20px;">
                <h4 style="font-size: 13px; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 8px;">Compliance Violations & Context Snippets</h4>
                ${flagsHtml}
            </div>

            <div style="margin-bottom: 20px;">
                <h4 style="font-size: 13px; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 8px;">NLP Extractive Summary</h4>
                <div style="background: rgba(10, 15, 29, 0.5); padding: 12px; border-radius: 6px; font-size: 13px; line-height: 1.6; border: 1px solid var(--border-light);">
                    ${escapeHtml(article.summary || "No summary available.")}
                </div>
            </div>

            <div>
                <h4 style="font-size: 13px; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 8px;">Clean Body Text (Parsed via Newspaper4k)</h4>
                <div style="background: rgba(10, 15, 29, 0.5); padding: 14px; border-radius: 6px; font-size: 12px; line-height: 1.7; max-height: 250px; overflow-y: auto; white-space: pre-wrap; color: #cbd5e1; border: 1px solid var(--border-light);">
                    ${escapeHtml(article.content || "Empty content.")}
                </div>
            </div>
        `;
    } catch (e) {
        container.innerHTML = `<div class="empty-cell">Error loading article details: ${e.message}</div>`;
    }
}

// Modal and Tab Switchers
function closeModal(id) {
    document.getElementById(id).classList.remove("active");
}

function openAddSourceModal() {
    document.getElementById("modal-add-source").classList.add("active");
}

function openAddRuleModal() {
    document.getElementById("modal-add-rule").classList.add("active");
}

function switchTab(tabName, btn) {
    currentTab = tabName;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    document.getElementById("view-articles").style.display = tabName === "articles" ? "block" : "none";
    document.getElementById("view-sources").style.display = tabName === "sources" ? "block" : "none";
    document.getElementById("view-rules").style.display = tabName === "rules" ? "block" : "none";
    document.getElementById("view-logs").style.display = tabName === "logs" ? "block" : "none";

    if (tabName === "articles") loadArticles();
    if (tabName === "sources") loadSources();
    if (tabName === "rules") loadRules();
    if (tabName === "logs") loadLogs();
}

// Form Handlers
async function handleAddSource(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("src-name").value,
        url: document.getElementById("src-url").value,
        source_type: document.getElementById("src-type").value,
        category: document.getElementById("src-category").value,
        fetch_interval_minutes: parseInt(document.getElementById("src-interval").value, 10),
        is_active: true
    };

    try {
        const res = await fetch(`${API_BASE}/api/v1/sources`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast("Source registered successfully!");
            closeModal("modal-add-source");
            document.getElementById("form-add-source").reset();
            loadSources();
            loadCategoryCounts();
            loadKPIs();
        } else {
            const err = await res.json();
            showToast(err.detail || "Error adding source.");
        }
    } catch (e) {
        showToast("Network error creating source.");
    }
}

async function handleAddRule(e) {
    e.preventDefault();
    const rawKeywords = document.getElementById("rule-keywords").value;
    const keywords = rawKeywords.split(",").map(k => k.trim()).filter(k => k.length > 0);

    const payload = {
        category: document.getElementById("rule-category").value,
        keywords: keywords,
        severity: document.getElementById("rule-severity").value,
        is_active: true
    };

    try {
        const res = await fetch(`${API_BASE}/api/v1/compliance/rules`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast("Compliance rule added successfully!");
            closeModal("modal-add-rule");
            document.getElementById("form-add-rule").reset();
            loadRules();
        } else {
            showToast("Error saving rule.");
        }
    } catch (e) {
        showToast("Network error creating rule.");
    }
}

async function deleteSource(sourceId) {
    if (!confirm(`Are you sure you want to remove Source #${sourceId}?`)) return;
    try {
        const res = await fetch(`${API_BASE}/api/v1/sources/${sourceId}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Source removed successfully.");
            loadSources();
            loadCategoryCounts();
            loadKPIs();
        }
    } catch (e) {
        showToast("Error deleting source.");
    }
}

function applyPreset(name, url, category) {
    document.getElementById("src-name").value = name;
    document.getElementById("src-url").value = url;
    const catSelect = document.getElementById("src-category");
    if (catSelect) {
        catSelect.value = category;
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}