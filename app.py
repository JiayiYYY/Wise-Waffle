"""
app.py — Wise Waffle: Academic Literature Tracker
Run with: py -m streamlit run app.py
"""

import builtins
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

import streamlit as st
import paper_fetcher as pf

st.set_page_config(page_title="Wise Waffle", page_icon="🧇", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --ink:    #1a1a1a;
    --paper:  #fdf8f2;
    --accent: #d63d6e;
    --teal:   #2aaa8a;
    --yellow: #f5a623;
    --blush:  #f7c5d5;
    --soft:   #ede8e0;
    --muted:  #9a9490;
}

html, body, [class*="css"] { font-family: Cambria, Georgia, serif; background-color:var(--paper); color:var(--ink); }

section[data-testid="stSidebar"] { background-color:#3d2c1e !important; }
section[data-testid="stSidebar"] * { color:#fdf0e4 !important; }
section[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
    background: #fff !important;
    padding: 0.8rem !important;
    border-radius: 6px !important;
}
section[data-testid="stSidebar"] [data-testid="stExpanderDetails"] * {
    color: #1a1a1a !important;
}
section[data-testid="stSidebar"] input    { color:var(--ink) !important; background:#fff !important; }
section[data-testid="stSidebar"] textarea { color:var(--ink) !important; background:#fff !important; }
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * { color:var(--ink) !important; }
section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] * { color:var(--ink) !important; }

h1, h2, h3 { font-family: Cambria, Georgia, serif; }
h1 { font-size:2.8rem; letter-spacing:-0.02em; }
h3 { font-weight:500; font-size:1rem; }

.paper-card {
    background:white; border:1px solid var(--soft); border-left:3px solid var(--accent);
    border-radius:6px; padding:1.1rem 1.3rem; margin-bottom:0.75rem;
    transition: box-shadow 0.15s;
}
.paper-card:hover { box-shadow: 0 2px 12px rgba(214,61,110,0.1); }
.paper-title { font-family:Cambria,Georgia,serif; font-size:1.05rem; margin-bottom:0.2rem; }
.paper-meta  { font-family:'DM Mono',monospace; font-size:0.72rem; color:var(--muted); margin-bottom:0.4rem; }
.paper-tag {
    display:inline-block; font-family:'DM Mono',monospace; font-size:0.65rem;
    padding:2px 7px; border-radius:20px; background:var(--soft); color:var(--ink); margin-right:4px;
}
.tag-tier1 { background:#fde0ea; color:#d63d6e; }
.tag-tier2 { background:#d4f0e8; color:#1e8a6e; }
.tag-tier3 { background:#fef3d6; color:#b87c0a; }
.tag-tier5 { background:#e8e0f5; color:#6b3a8f; }

.stat-box   { background:white; border:1px solid var(--soft); border-radius:8px; padding:1rem; text-align:center; }
.stat-num   { font-family:Cambria,Georgia,serif; font-size:2.2rem; color:var(--accent); }
.stat-label { font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.08em; }

.stButton > button {
    background:var(--accent) !important; color:white !important; border:none !important;
    border-radius:20px !important; font-family:Cambria,Georgia,serif !important;
    font-weight:500 !important; padding:0.5rem 1.8rem !important;
}
.stButton > button:hover { opacity:0.88; }

.intro-box {
    background: linear-gradient(135deg, #fff5f8 0%, #f0faf6 100%);
    border: 1px solid var(--blush); border-radius: 12px;
    padding: 1.8rem 2rem; margin-bottom: 1rem;
}
.tier-pill {
    display:inline-block; font-family:'DM Mono',monospace; font-size:0.7rem;
    padding:3px 10px; border-radius:20px; margin:2px;
}
.abstract-text { font-size:0.85rem; color:#444; line-height:1.6; margin-top:0.5rem; }
hr { border-color:var(--soft); }

@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50%       { transform: translateY(-8px); }
}
</style>
""", unsafe_allow_html=True)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
TOPICS_PATH = BASE_DIR / "topics.json"
SAVED_PATH   = BASE_DIR / "saved_dois.json"
SEARCHES_PATH = BASE_DIR / "saved_searches.json"

TOPIC_LABELS = {
    "tier1:ai_fairness_decolonial":          "AI Fairness & Decolonial",
    "tier1:sexual_behavior_youth":           "Sexual Behavior & Youth",
    "tier1:social_media_wellbeing":          "Social Media & Wellbeing",
    "tier1:gender_studies":                  "Gender Studies",
    "tier1:entertainment_youth_media":       "Entertainment & Youth Media",
    "tier2:biology_crossover":               "× Biology",
    "tier2:anthropology_crossover":          "× Anthropology",
    "tier2:sociology_crossover":             "× Sociology",
    "tier2:public_health_crossover":         "× Public Health",
    "tier2:political_psychology_crossover":  "× Political Psychology",
    "tier3:ascor":                           "ASCoR & Global Scholars",
    "tier5:your_watchlist":                  "📰 Watchlist Journals",
    "tier5:high_impact_comm":                "📰 High Impact Comm",
    "tier5:psychology_adjacent":             "📰 Psychology Adjacent",
    "tier5:gender_feminist":                 "📰 Gender & Feminist",
    "tier5:interdisciplinary_high_impact":   "📰 Interdisciplinary",
}

JOURNAL_GROUPS = {
    "your_watchlist":                "📌 Watchlist",
    "high_impact_comm":              "📡 High Impact Communication",
    "psychology_adjacent":           "🧠 Psychology Adjacent",
    "gender_feminist":               "♀ Gender & Feminist",
    "interdisciplinary_high_impact": "🔬 Interdisciplinary",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_json_safe(path):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return None

def saved_count():
    data = load_json_safe(SAVED_PATH)
    return len(data) if data else 0

def load_searches():
    data = load_json_safe(SEARCHES_PATH)
    if not data or not isinstance(data, dict):
        return {"profiles": {}, "snapshots": {}}
    data.setdefault("profiles", {})
    data.setdefault("snapshots", {})
    return data

def save_searches(data):
    with open(SEARCHES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

_SNAP_PAPER_FIELDS = ("title", "doi", "year", "pub_date", "journal", "authors",
                      "tag", "search_term", "relevance_score", "relevance_reason",
                      "url", "citation_count", "impact_score")

def _trim_papers(papers):
    return [{k: p.get(k) for k in _SNAP_PAPER_FIELDS} for p in papers]

def _capture_m1_config(date_from, date_to):
    return {
        "date_from":      str(date_from),
        "date_to":        str(date_to),
        "run_keywords":   st.session_state.get("m1_run_keywords", True),
        "run_scholars":   st.session_state.get("m1_run_scholars", True),
        "run_journals":   st.session_state.get("m1_run_journals", True),
        "research_focus": st.session_state.get("research_focus_input", ""),
        "extra_keywords": st.session_state.get("m1_extra_keywords", ""),
        "extra_scholars": st.session_state.get("m1_extra_scholars", ""),
        "extra_journals": st.session_state.get("m1_extra_journals", ""),
    }

def _restore_m1_config(cfg):
    for sk, ck in [
        ("m1_run_keywords",    "run_keywords"),
        ("m1_run_scholars",    "run_scholars"),
        ("m1_run_journals",    "run_journals"),
        ("research_focus_input", "research_focus"),
        ("m1_extra_keywords",  "extra_keywords"),
        ("m1_extra_scholars",  "extra_scholars"),
        ("m1_extra_journals",  "extra_journals"),
    ]:
        if ck in cfg:
            st.session_state[sk] = cfg[ck]
    from datetime import date
    for dk in ("m1_date_from", "m1_date_to"):
        ck = dk[3:]  # "date_from" / "date_to"
        if ck in cfg:
            try:
                st.session_state[dk] = date.fromisoformat(cfg[ck])
            except ValueError:
                pass

def _capture_m2_config(date_from, date_to):
    return {
        "date_from":        str(date_from),
        "date_to":          str(date_to),
        "keywords":         st.session_state.get("m2_keywords", ""),
        "crossover":        st.session_state.get("m2_crossover", ""),
        "scholars":         st.session_state.get("m2_scholars", ""),
        "journals":         st.session_state.get("m2_journals", ""),
        "journal_keywords": st.session_state.get("m2_journal_keywords", ""),
        "research_focus":   st.session_state.get("m2_research_focus", ""),
        "search_mode":      st.session_state.get("m2_search_mode", "recent"),
        "impact_threshold": st.session_state.get("m2_impact_threshold", 0.3),
        "scholar_lookback": st.session_state.get("m2_scholar_lookback", 10),
    }

def _restore_m2_config(cfg):
    for sk, ck in [
        ("m2_keywords",         "keywords"),
        ("m2_crossover",        "crossover"),
        ("m2_scholars",         "scholars"),
        ("m2_journals",         "journals"),
        ("m2_journal_keywords", "journal_keywords"),
        ("m2_research_focus",   "research_focus"),
        ("m2_search_mode",      "search_mode"),
        ("m2_impact_threshold", "impact_threshold"),
        ("m2_scholar_lookback", "scholar_lookback"),
    ]:
        if ck in cfg:
            st.session_state[sk] = cfg[ck]
    from datetime import date
    for dk in ("m2_date_from", "m2_date_to"):
        ck = dk[3:]
        if ck in cfg:
            try:
                st.session_state[dk] = date.fromisoformat(cfg[ck])
            except ValueError:
                pass

def get_topic_key(tag):
    if tag.startswith("ascor"): return "tier3:ascor"
    parts = tag.split(":")
    return f"{parts[0]}:{parts[1]}" if len(parts) >= 2 else tag

def tag_color(tag):
    if tag.startswith("tier1"): return "tag-tier1"
    if tag.startswith("tier2"): return "tag-tier2"
    if tag.startswith("tier5"): return "tag-tier5"
    if tag.startswith("flex"):  return "paper-tag"
    return "tag-tier3"

def tier_label(tag):
    if tag.startswith("tier1"):          return "Core"
    if tag.startswith("tier2"):          return "Crossover"
    if tag.startswith("tier5"):          return "Journal"
    if tag.startswith("flex:keyword"):   return "Keyword"
    if tag.startswith("flex:crossover"): return "Crossover"
    if tag.startswith("flex:scholar"):   return "Scholar"
    if tag.startswith("flex:journal"):   return "Journal"
    return "Scholar"

def topic_display(tag):
    if tag.startswith("flex:"):
        parts = tag.split(":")
        return parts[1].capitalize() if len(parts) >= 2 else tag
    key = get_topic_key(tag)
    if key in TOPIC_LABELS: return TOPIC_LABELS[key]
    parts = tag.split(":")
    return parts[1] if len(parts) >= 2 else tag

def paper_key(p):
    return (p.get("doi") or p.get("title", "")).strip().lower()

def render_paper_card(p):
    tag         = p.get("tag", "")
    doi         = p.get("doi", "")
    url         = p.get("url", "") or (f"https://doi.org/{doi}" if doi else "")
    title       = p.get("title", "Untitled")
    title_html  = f'<a href="{url}" target="_blank" style="text-decoration:none;color:inherit;">{title}</a>' if url else title
    authors     = p.get("authors", [])
    authors_str = ", ".join(authors[:4]) + (" et al." if len(authors) > 4 else "")
    journal     = p.get("journal", "")
    pub_date    = p.get("pub_date", "") or p.get("year", "")
    cls         = tag_color(tag)
    score       = p.get("relevance_score")
    score_html  = f'<span class="paper-tag" style="background:#e0f2e9;color:#1a7a3a">★ {score}/10</span>' if score is not None else ""
    impact      = p.get("impact_score")
    impact_html = (f'<span class="paper-tag" style="background:#fff3cd;color:#7a5700">'
                   f'⚡ {impact:.2f}</span>') if impact is not None else ""

    st.markdown(f"""
    <div class="paper-card">
        <div class="paper-title">{title_html}</div>
        <div class="paper-meta">{authors_str} &nbsp;·&nbsp; {journal} &nbsp;·&nbsp; {pub_date}</div>
        <span class="paper-tag {cls}">{tier_label(tag)}</span>
        <span class="paper-tag">{topic_display(tag)}</span>
        {score_html}
        {impact_html}
        {"<span class='paper-tag'>" + doi + "</span>" if doi else ""}
    </div>
    """, unsafe_allow_html=True)
    abstract = p.get("abstract", "")
    reason   = p.get("relevance_reason", "")
    if abstract or reason:
        with st.expander("Abstract", expanded=False):
            st.write("DEBUG abstract:", p.get("abstract", "MISSING"))
            if abstract:
                st.markdown(f'<p class="abstract-text">{abstract[:800]}{"…" if len(abstract) > 800 else ""}</p>',
                            unsafe_allow_html=True)
            if reason:
                st.markdown(f'<p style="font-size:0.78rem;color:#666;margin-top:0.5rem;margin-bottom:0"><em>Relevance: {reason}</em></p>', unsafe_allow_html=True)

def _render_network(p, s2_key=""):
    _NO_DATA = "No citation data available — this paper may not be indexed in OpenAlex yet."

    doi = p.get("doi", "")

    if not doi:
        st.info(_NO_DATA)
        return

    pk    = paper_key(p)
    cache = st.session_state["network_cache"]

    if pk not in cache:
        with st.spinner("Fetching citation data from OpenAlex…"):
            cache[pk] = pf.fetch_openalex_network(doi)

    data = cache[pk]
    if not data:
        st.info(_NO_DATA)
        return

    refs = data.get("references") or []
    cits = data.get("citations")  or []

    def _to_rows(items):
        rows = []
        for item in items:
            d = item.get("doi", "")
            rows.append({
                "Title":   item.get("title") or "Unknown",
                "Authors": ", ".join(item.get("authors") or []),
                "Year":    item.get("year") or "",
                "DOI":     f"https://doi.org/{d}" if d else "",
            })
        return rows

    def _show_table(items):
        st.dataframe(
            _to_rows(items),
            use_container_width=True,
            hide_index=True,
            column_config={"DOI": st.column_config.LinkColumn("DOI", display_text="↗ open")},
        )

    st.markdown(f"**References ({len(refs)}) — papers this article cites**")
    if refs:
        _show_table(refs)
    else:
        st.caption("No references indexed.")

    st.markdown(f"**Cited by ({len(cits)}) — papers citing this article**")
    if cits:
        _show_table(cits)
    else:
        st.caption("No citing papers indexed yet — this paper may be too recent.")

COLLECTION_KEY_LABELS = {
    "tier1:ai_fairness_decolonial":          "Core — AI Fairness & Decolonial",
    "tier1:sexual_behavior_youth":           "Core — Sexual Behavior & Youth",
    "tier1:social_media_wellbeing":          "Core — Social Media & Wellbeing",
    "tier1:gender_studies":                  "Core — Gender Studies",
    "tier1:entertainment_youth_media":       "Core — Entertainment & Youth",
    "tier2:biology_crossover":               "Cross — Biology",
    "tier2:anthropology_crossover":          "Cross — Anthropology",
    "tier2:sociology_crossover":             "Cross — Sociology",
    "tier2:public_health_crossover":         "Cross — Public Health",
    "tier2:political_psychology_crossover":  "Cross — Political Psychology",
    "tier3:ascor":                           "Scholars — ASCoR & Global",
    "tier5:your_watchlist":                  "Journal — Watchlist",
    "tier5:high_impact_comm":                "Journal — High Impact Comm",
    "tier5:psychology_adjacent":             "Journal — Psychology Adjacent",
    "tier5:gender_feminist":                 "Journal — Gender & Feminist",
    "tier5:interdisciplinary_high_impact":   "Journal — Interdisciplinary",
}

def build_config(s2_key, zotero_id, zotero_key, notion_tok, notion_db, collection_keys=None, anthropic_key="", library_type="user"):
    cfg = load_json_safe(CONFIG_PATH) or {}
    if s2_key: cfg["semantic_scholar"] = {"api_key": s2_key}
    if anthropic_key: cfg["anthropic"] = {"api_key": anthropic_key}
    if zotero_id and zotero_key:
        z = cfg.get("zotero", {})
        z.update({"library_id": zotero_id, "api_key": zotero_key, "library_type": library_type})
        if collection_keys:
            z["collection_keys"] = {k: v for k, v in collection_keys.items() if v.strip()}
        cfg["zotero"] = z
    if notion_tok and notion_db:
        cfg["notion"] = {"token": notion_tok, "database_id": notion_db}
    return cfg

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"results": [], "saved_this": 0, "selected_keys": set(), "results_page": 1,
             "last_filtered_count": 0, "prefill": False, "log_lines": [],
             "network_paper_key": None, "network_cache": {}, "view": "landing",
             "m2_all_scored": [], "m2_score_threshold": 6,
             "m1_save_name": "", "m2_save_name": "",
             "m2_search_mode": "recent", "m2_impact_threshold": 0.3,
             "m2_all_deep": [], "m2_scholar_lookback": 10}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Landing page ──────────────────────────────────────────────────────────────
def render_landing():
    with st.sidebar:
        st.markdown("## 🧇 Wise Waffle")
        st.caption("Choose a mode to begin.")

    st.markdown("""
<div style="text-align:center; padding: 3rem 0 1.5rem 0;">
    <div style="font-size:3.5rem; animation: bounce 2s ease infinite; display:inline-block;">🧇</div>
    <h1 style="font-family:Cambria,Georgia,serif; font-size:3.2rem; letter-spacing:-0.02em;
               background: linear-gradient(135deg, #d63d6e, #f5a623, #2aaa8a);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               background-clip: text; margin: 0.3rem 0 0.5rem 0;">
        Wise Waffle
    </h1>
    <p style="color:#9a9490; font-family:'DM Mono',monospace; font-size:0.85rem; letter-spacing:0.12em; text-transform:uppercase;">
        Academic literature tracker &nbsp;·&nbsp; Semantic Scholar → Zotero & Notion
    </p>
</div>
""", unsafe_allow_html=True)

    with st.expander("👋 What is this?", expanded=True):
        st.markdown("""
<div class="intro-box">

<p>Welcome, hot nerds. This is an academic research helper that pulls peer-reviewed articles into one place based on your keywords, scholars, and journals.</p>

<p><strong>Highlights:</strong></p>
<ul>
  <li>Time range: pick any date range up to 5 years back</li>
  <li>Connected papers: visualise citing and cited relationships</li>
  <li>Optional save to Zotero and/or Notion</li>
  <li>Relevance scoring by Claude against your written research focus</li>
</ul>

<p><strong>To run any search, you need:</strong></p>
<ol>
  <li>Semantic Scholar API key — free for academic use, request at <a href="https://www.semanticscholar.org/product/api" target="_blank">semanticscholar.org/product/api</a></li>
  <li>(optional) Anthropic API key — for Claude relevance scoring, get it at <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>. Cost is roughly $0.01–0.05 per run depending on paper count.</li>
  <li>(optional) Zotero API key — free, find it at <a href="https://www.zotero.org/settings/keys" target="_blank">zotero.org/settings/keys</a></li>
  <li>(optional) Notion integration token — free, set it up at <a href="https://www.notion.so/my-integrations" target="_blank">notion.so/my-integrations</a></li>
</ol>

<p>In short: Semantic Scholar API is the only mandatory key. Everything else is optional. Use dry run mode to preview results without saving.</p>

<p>For a transparent look at the code and a vibe coding manual, see the GitHub repository: <a href="https://github.com/JiayiYYY/Wise-Waffle" target="_blank">github.com/JiayiYYY/Wise-Waffle</a></p>

</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
<div style="background:white; border:1px solid var(--blush); border-radius:12px; padding:2rem;">
    <h2 style="color:var(--accent); margin-top:0; font-size:1.4rem;">Mode 1 — Preset Pipeline (my personal setup)</h2>
    <p style="color:#555; font-size:0.92rem; line-height:1.7; margin-bottom:1rem;">
        Runs a fixed five-tier search tailored to communication science research on media, youth, gender, and AI fairness:
    </p>
    <ul style="color:#555; font-size:0.85rem; line-height:1.9; padding-left:1.2rem; margin:0 0 1rem 0;">
        <li>Tier 1: core topic keywords (AI fairness, social media wellbeing, gender studies, sexual behaviour and youth, entertainment and youth media)</li>
        <li>Tier 2: interdisciplinary crossover keywords (biology, anthropology, sociology, public health, political psychology)</li>
        <li>Tier 3 &amp; 4: tracked scholars in these fields</li>
        <li>Tier 5: journal sweep across communication, psychology, and gender studies journals via OpenAlex</li>
    </ul>
    <p style="color:#555; font-size:0.85rem; margin:0;">Good if you want to see how the tool works or share the research interests above.</p>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        if st.button("Enter Mode 1 →", key="go_mode1", use_container_width=True):
            st.session_state["view"]     = "mode1"
            st.session_state["results"]  = []
            st.session_state["log_lines"] = []
            st.rerun()

    with col2:
        st.markdown("""
<div style="background:white; border:1px solid #c8e8de; border-radius:12px; padding:2rem;">
    <h2 style="color:var(--teal); margin-top:0; font-size:1.4rem;">Mode 2 — Custom Search</h2>
    <p style="color:#555; font-size:0.92rem; line-height:1.7; margin:0 0 0.75rem 0;">
        Enter your own keywords, scholars, journals, and research focus. All input categories are independent — use any combination or just one.
    </p>
    <p style="color:#555; font-size:0.85rem; line-height:1.7; margin:0;">
        Choose <strong>Recent papers</strong> (date-filtered, last days to months) for a quick sweep of new publications, or <strong>Deep search</strong> (no date filter, ranked by citation impact) for building a literature review.
    </p>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        if st.button("Enter Mode 2 →", key="go_mode2", use_container_width=True):
            st.session_state["view"]     = "mode2"
            st.session_state["results"]  = []
            st.session_state["log_lines"] = []
            st.rerun()

def _reset_results_page():
    st.session_state["results_page"] = 1
    st.query_params["page"] = "1"

# ── Shared results renderer ───────────────────────────────────────────────────
def render_results(results, s2_key="", zotero_id="", zotero_key="",
                   notion_tok="", notion_db="", collection_keys=None, anthropic_key="", library_type="user"):
    if not results:
        return

    st.divider()

    is_flex = any(p.get("tag", "").startswith("flex:") for p in results)

    if is_flex:
        flex_counts = Counter(p.get("tag", "") for p in results)
        r1, r2, r3, r4 = st.columns(4)
        with r1: st.markdown(f'<div class="stat-box"><div class="stat-num">{len(results)}</div><div class="stat-label">Papers found</div></div>', unsafe_allow_html=True)
        with r2: st.markdown(f'<div class="stat-box"><div class="stat-num">{flex_counts.get("flex:keyword", 0) + flex_counts.get("flex:crossover", 0)}</div><div class="stat-label">From keywords</div></div>', unsafe_allow_html=True)
        with r3: st.markdown(f'<div class="stat-box"><div class="stat-num">{flex_counts.get("flex:scholar", 0)}</div><div class="stat-label">From scholars</div></div>', unsafe_allow_html=True)
        with r4: st.markdown(f'<div class="stat-box"><div class="stat-num">{flex_counts.get("flex:journal", 0)}</div><div class="stat-label">From journals</div></div>', unsafe_allow_html=True)
    else:
        tier_counts = Counter(pf._get_tier(p["tag"]) for p in results)
        r1, r2, r3, r4, r5 = st.columns(5)
        with r1: st.markdown(f'<div class="stat-box"><div class="stat-num">{len(results)}</div><div class="stat-label">Papers found</div></div>', unsafe_allow_html=True)
        with r2: st.markdown(f'<div class="stat-box"><div class="stat-num">{tier_counts.get("tier1",0)}</div><div class="stat-label">Core</div></div>', unsafe_allow_html=True)
        with r3: st.markdown(f'<div class="stat-box"><div class="stat-num">{tier_counts.get("tier2",0)}</div><div class="stat-label">Crossover</div></div>', unsafe_allow_html=True)
        with r4: st.markdown(f'<div class="stat-box"><div class="stat-num">{tier_counts.get("tier3",0)}</div><div class="stat-label">Scholars</div></div>', unsafe_allow_html=True)
        with r5: st.markdown(f'<div class="stat-box"><div class="stat-num">{tier_counts.get("tier5",0)}</div><div class="stat-label">Journals</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    all_keywords = sorted(set(p.get("search_term", "") for p in results if p.get("search_term")))
    all_journals = sorted(set(p["journal"] for p in results if p.get("journal")))

    fc1, fc2, fc3 = st.columns([1.2, 1.5, 2])
    with fc1:
        kw_filter = st.multiselect("Filter by keyword", all_keywords, default=all_keywords,
                                   placeholder="All keywords…",
                                   key="rr_kw_filter", on_change=_reset_results_page)
    with fc2:
        journal_filter = st.multiselect("Filter by journal", all_journals, default=[],
                                        placeholder="All journals…",
                                        key="rr_journal_filter", on_change=_reset_results_page)
    with fc3:
        search_filter = st.text_input("Search", placeholder="Filter by title, author, journal…",
                                      key="rr_search_filter", on_change=_reset_results_page)
    sc1, _ = st.columns([1, 4])
    with sc1:
        sort_by = st.selectbox("Sort by", ["date_desc", "date_asc", "journal", "score_desc"],
            format_func=lambda x: {"date_desc": "Newest first", "date_asc": "Oldest first",
                                    "journal": "Journal A–Z", "score_desc": "Score (high → low)"}[x],
            key="rr_sort_by", on_change=_reset_results_page)

    filtered = [p for p in results
                if not kw_filter
                or not p.get("search_term")
                or p.get("search_term") in kw_filter]

    if journal_filter:
        filtered = [p for p in filtered if p.get("journal") in journal_filter]
    if search_filter:
        q = search_filter.lower()
        filtered = [p for p in filtered
                    if q in p.get("title", "").lower()
                    or q in " ".join(p.get("authors", [])).lower()
                    or q in p.get("journal", "").lower()]
    if sort_by == "date_desc":
        filtered = sorted(filtered, key=lambda p: p.get("pub_date", "") or p.get("year", ""), reverse=True)
    elif sort_by == "date_asc":
        filtered = sorted(filtered, key=lambda p: p.get("pub_date", "") or p.get("year", ""))
    elif sort_by == "score_desc":
        filtered = sorted(filtered, key=lambda p: p.get("relevance_score") if p.get("relevance_score") is not None else -1, reverse=True)
    else:
        filtered = sorted(filtered, key=lambda p: p.get("journal", "").lower())

    with st.expander("📊 Results breakdown", expanded=True):
        col_chart, col_journals_chart = st.columns(2)
        with col_chart:
            st.markdown("**Papers per topic** *(filtered)*")
            ftc = Counter(get_topic_key(p["tag"]) for p in filtered)
            sorted_t = sorted(ftc.items(), key=lambda x: -x[1])
            max_n = sorted_t[0][1] if sorted_t else 1
            for tk, n in sorted_t:
                label = TOPIC_LABELS.get(tk, tk)
                bar_w = int((n / max_n) * 100)
                if tk.startswith("tier1"):   color = "#d63d6e"
                elif tk.startswith("tier2"): color = "#2aaa8a"
                elif tk.startswith("tier5"): color = "#6b3a8f"
                elif tk.startswith("flex"):  color = "#4a90d9"
                else:                        color = "#b87c0a"
                st.markdown(f"""<div style="margin-bottom:8px">
                  <div style="display:flex;justify-content:space-between;margin-bottom:2px">
                    <span style="font-size:0.78rem;color:#444">{label}</span>
                    <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:#8a8480">{n}</span>
                  </div>
                  <div style="background:#ede8e0;border-radius:2px;height:5px">
                    <div style="background:{color};width:{bar_w}%;height:5px;border-radius:2px"></div>
                  </div></div>""", unsafe_allow_html=True)
        with col_journals_chart:
            st.markdown("**Top journals** *(filtered)*")
            jlist = [p["journal"] for p in filtered if p.get("journal")]
            if jlist:
                top_j = Counter(jlist).most_common(8)
                max_j = top_j[0][1]
                for j, n in top_j:
                    bar_w = int((n / max_j) * 100)
                    st.markdown(f"""<div style="margin-bottom:8px">
                      <div style="display:flex;justify-content:space-between;margin-bottom:2px">
                        <span style="font-size:0.78rem;color:#444">{j[:40]}</span>
                        <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:#8a8480">{n}</span>
                      </div>
                      <div style="background:#ede8e0;border-radius:2px;height:5px">
                        <div style="background:#d63d6e;width:{bar_w}%;height:5px;border-radius:2px"></div>
                      </div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    PAGE_SIZE   = 20
    total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)

    # Sync page from URL query params so browser back/forward works
    _qp = st.query_params.get("page", "")
    if _qp:
        try:
            _want = max(1, min(int(_qp), total_pages))
        except (ValueError, TypeError):
            _want = 1
        _cur = st.session_state.get("results_page", 1)
        if _cur != _want:
            st.session_state["results_page"] = _want
            if str(_want) != _qp:
                st.query_params["page"] = str(_want)
            st.rerun()

    page        = max(1, min(st.session_state.get("results_page", 1), total_pages))
    start       = (page - 1) * PAGE_SIZE
    page_papers = filtered[start:start + PAGE_SIZE]

    st.markdown(
        f"### Results &nbsp;<small style='color:#9a9490;font-size:0.8rem;font-family:DM Mono,monospace'>"
        f"{len(filtered)} papers · page {page}/{total_pages}</small>",
        unsafe_allow_html=True)

    sel1, sel2, sel3 = st.columns([1, 1, 5])
    with sel1:
        if st.button("☑ Select page"):
            for p in page_papers:
                pk = paper_key(p)
                st.session_state["selected_keys"].add(pk)
                st.session_state[f"chk_{pk[:60]}"] = True
            st.rerun()
    with sel2:
        if st.button("☐ Clear all"):
            st.session_state["selected_keys"] = set()
            for _k in list(st.session_state.keys()):
                if _k.startswith("chk_"):
                    st.session_state[_k] = False
            st.rerun()

    n_selected = len(st.session_state["selected_keys"])
    if n_selected:
        st.markdown(f"**{n_selected} paper{'s' if n_selected > 1 else ''} selected**")

    for p in page_papers:
        pk      = paper_key(p)
        checked = pk in st.session_state["selected_keys"]
        col_chk, col_card = st.columns([0.04, 0.96])
        with col_chk:
            new_val = st.checkbox("select", value=checked, key=f"chk_{pk[:60]}", label_visibility="hidden")
            if new_val:
                st.session_state["selected_keys"].add(pk)
            else:
                st.session_state["selected_keys"].discard(pk)
        with col_card:
            render_paper_card(p)
        if p.get("doi"):
            is_active = st.session_state.get("network_paper_key") == pk
            if st.button("▲ Hide Network" if is_active else "🔗 Citation Network",
                         key=f"net_btn_{pk[:50]}"):
                st.session_state["network_paper_key"] = None if is_active else pk
            if st.session_state.get("network_paper_key") == pk:
                _render_network(p, s2_key)

    if total_pages > 1:
        pc1, pc2, pc3, pc4, pc5 = st.columns([1, 1, 2, 1, 1])
        with pc1:
            if st.button("⟪ First") and page > 1:
                st.session_state["results_page"] = 1
                st.query_params["page"] = "1"
                st.rerun()
        with pc2:
            if st.button("← Prev") and page > 1:
                st.session_state["results_page"] = page - 1
                st.query_params["page"] = str(page - 1)
                st.rerun()
        with pc3:
            st.markdown(f'<div style="text-align:center;font-family:DM Mono,monospace;font-size:0.8rem;'
                        f'color:#9a9490;padding-top:0.5rem">Page {page} of {total_pages}</div>',
                        unsafe_allow_html=True)
        with pc4:
            if st.button("Next →") and page < total_pages:
                st.session_state["results_page"] = page + 1
                st.query_params["page"] = str(page + 1)
                st.rerun()
        with pc5:
            if st.button("Last ⟫") and page < total_pages:
                st.session_state["results_page"] = total_pages
                st.query_params["page"] = str(total_pages)
                st.rerun()

    st.markdown("---")
    selected_papers = [p for p in filtered if paper_key(p) in st.session_state["selected_keys"]]

    if selected_papers:
        st.markdown(f"### Save {len(selected_papers)} selected paper{'s' if len(selected_papers) > 1 else ''}")
        config_now = build_config(s2_key, zotero_id, zotero_key, notion_tok, notion_db, collection_keys, anthropic_key, library_type)
        sv1, sv2, sv3 = st.columns([1, 1, 4])
        with sv1:
            if st.button("💾 Save to Zotero", disabled=not (zotero_id and zotero_key)):
                try:
                    pf.S2_HEADERS = {"x-api-key": s2_key} if s2_key else {}
                    pf.save_to_zotero(selected_papers, config_now)
                    pf.record_saved(selected_papers)
                    st.session_state["selected_keys"] = set()
                    st.success(f"✓ {len(selected_papers)} papers saved to Zotero.")
                except Exception as e:
                    st.error(f"Zotero save failed: {e}")
        with sv2:
            if st.button("📝 Save to Notion", disabled=not (notion_tok and notion_db)):
                try:
                    pf.S2_HEADERS = {"x-api-key": s2_key} if s2_key else {}
                    pf.save_to_notion(selected_papers, config_now)
                    pf.record_saved(selected_papers)
                    st.session_state["selected_keys"] = set()
                    st.success(f"✓ {len(selected_papers)} papers saved to Notion.")
                except Exception as e:
                    st.error(f"Notion save failed: {e}")
    elif st.session_state["saved_this"] > 0:
        st.success(f"✓ {st.session_state['saved_this']} papers auto-saved.")

# ── Mode 1 ────────────────────────────────────────────────────────────────────
def render_mode1():
    with st.sidebar:
        if st.button("← Home", key="m1_back"):
            st.session_state["view"]      = "landing"
            st.session_state["results"]   = []
            st.session_state["log_lines"] = []
            st.rerun()
        st.markdown("## 🧇")
        st.divider()

        try:
            host_secrets = dict(st.secrets["host"]) if "host" in st.secrets else {}
        except Exception:
            host_secrets = {}
        try:
            host_colls = dict(st.secrets["host_collections"]) if "host_collections" in st.secrets else {}
        except Exception:
            host_colls = {}
        is_host = bool(host_secrets)

        st.markdown("### API Keys")
        if is_host:
            if st.button("⚡ Fill my credentials"):
                st.session_state["s2_key_input"]        = host_secrets.get("s2_key", "")
                st.session_state["zotero_id_input"]     = host_secrets.get("zotero_id", "")
                st.session_state["zotero_key_input"]    = host_secrets.get("zotero_key", "")
                st.session_state["notion_tok_input"]    = host_secrets.get("notion_tok", "")
                st.session_state["notion_db_input"]     = host_secrets.get("notion_db", "")
                st.session_state["anthropic_key_input"] = host_secrets.get("anthropic_key", "")
                for k in COLLECTION_KEY_LABELS:
                    st.session_state[f"coll_{k}"] = host_colls.get(k, "")

        st.text_input("Semantic Scholar API Key", type="password", key="s2_key_input",     placeholder="Enter key…")
        _zid_col, _ztype_col = st.columns([2, 1])
        with _zid_col:
            st.text_input("Zotero Library ID", key="zotero_id_input", placeholder="e.g. 10541129")
        with _ztype_col:
            st.selectbox("Library type", ["user", "group"], key="zotero_lib_type")
        st.text_input("Zotero API Key",           type="password", key="zotero_key_input")
        st.text_input("Notion Token",             type="password", key="notion_tok_input", placeholder="secret_…")
        st.text_input("Notion Database ID",                        key="notion_db_input",  placeholder="32-char ID")
        st.text_input("Anthropic API Key",        type="password", key="anthropic_key_input", placeholder="sk-ant-…")

        s2_key        = st.session_state.get("s2_key_input", "")
        zotero_id     = st.session_state.get("zotero_id_input", "")
        zotero_key    = st.session_state.get("zotero_key_input", "")
        notion_tok    = st.session_state.get("notion_tok_input", "")
        notion_db     = st.session_state.get("notion_db_input", "")
        anthropic_key = st.session_state.get("anthropic_key_input", "")
        zotero_lib_type = st.session_state.get("zotero_lib_type", "user")

        with st.expander("📁 Zotero Collection Keys (optional)"):
            st.markdown('<p style="font-size:0.75rem;color:#aaa;margin-bottom:0.5rem">8-char key from each collection URL. Leave blank to save to root library.</p>', unsafe_allow_html=True)
            collection_keys = {}
            for key, label in COLLECTION_KEY_LABELS.items():
                collection_keys[key] = st.text_input(label, placeholder="e.g. ABC12345", key=f"coll_{key}")
        with st.expander("ℹ️ Setup guide"):
            st.markdown("""
**Semantic Scholar**
Get a free API key at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api). Required to run any search.

---

**Zotero**
1. Find your **Library ID** at [zotero.org/settings/security](https://www.zotero.org/settings/security) — shown as "Your userID for use in API calls"
2. On the same page, click **Create new private key** to get your API key
3. Collection keys are optional — leave blank to save everything to your root library. To use collections, go to a collection on zotero.org and copy the 8-character key from the URL

---
**Notion**
1. Go to [notion.so/my-integrations](https://notion.so/my-integrations) → **New integration** → copy the token
2. Open your database in Notion → `...` → **Connections** → add your integration
3. Copy the **Database ID** from the URL: `notion.so/`**`your-database-id`**`?v=...`
4. Your database needs these columns: Title (Title), Authors, Year, Journal, DOI, Abstract (all Text), URL (URL), Source (Text), Tier (Select)

""")

        st.divider()
        _searches_m1 = load_searches()
        _profiles_m1 = _searches_m1.get("profiles", {})
        _snaps_m1    = _searches_m1.get("snapshots", {})
        if _profiles_m1:
            with st.expander("📂 Load saved search config"):
                _chosen_profile_m1 = st.selectbox(
                    "Profile", [""] + list(_profiles_m1.keys()),
                    format_func=lambda x: "— select —" if x == "" else x,
                    key="m1_load_profile",
                )
                lp1, lp2 = st.columns(2)
                with lp1:
                    if st.button("Load", key="m1_load_btn", disabled=not _chosen_profile_m1):
                        _restore_m1_config(_profiles_m1[_chosen_profile_m1]["config"])
                        st.success(f'Loaded "{_chosen_profile_m1}"')
                        st.rerun()
                with lp2:
                    if st.button("Delete", key="m1_del_profile", disabled=not _chosen_profile_m1):
                        del _searches_m1["profiles"][_chosen_profile_m1]
                        save_searches(_searches_m1)
                        st.success("Deleted.")
                        st.rerun()
        if _snaps_m1:
            with st.expander("📚 Saved snapshots"):
                _chosen_snap_m1 = st.selectbox(
                    "Snapshot", [""] + list(reversed(list(_snaps_m1.keys()))),
                    format_func=lambda x: "— select —" if x == "" else x,
                    key="m1_load_snap",
                )
                if _chosen_snap_m1:
                    _s = _snaps_m1[_chosen_snap_m1]
                    st.caption(f'{_s["paper_count"]} papers · {_s["timestamp"][:10]}')
                    sv1, sv2 = st.columns(2)
                    with sv1:
                        if st.button("View", key="m1_view_snap"):
                            st.session_state["results"]       = _s["papers"]
                            st.session_state["results_page"]  = 1
                            st.session_state["selected_keys"] = set()
                            st.rerun()
                    with sv2:
                        if st.button("Delete", key="m1_del_snap"):
                            del _searches_m1["snapshots"][_chosen_snap_m1]
                            save_searches(_searches_m1)
                            st.success("Deleted.")
                            st.rerun()

        st.divider()
        st.markdown("### Search Settings")
        st.caption("Tiers to run")
        run_keywords     = st.checkbox("Keywords (Tier 1+2)",  value=True, key="m1_run_keywords")
        run_scholars     = st.checkbox("Scholars (Tier 3+4)",  value=True, key="m1_run_scholars")
        run_journals_chk = st.checkbox("Journals (Tier 5)",    value=True, key="m1_run_journals")
        target = st.selectbox("Save to", ["view", "both", "zotero", "notion"],
            format_func=lambda x: {"view": "View only (no save)", "both": "Zotero + Notion",
                                    "zotero": "Zotero only", "notion": "Notion only"}[x])
        _today    = datetime.today().date()
        date_from = st.date_input("From", value=_today - timedelta(days=30),
                                  min_value=_today - timedelta(days=5*365), max_value=_today,
                                  key="m1_date_from")
        date_to   = st.date_input("To",   value=_today,
                                  min_value=_today - timedelta(days=5*365), max_value=_today,
                                  key="m1_date_to")
        if date_from > date_to:
            st.error("'From' date must not be after 'To'.")
        dry_run   = st.checkbox("Dry run (preview, don't save)", value=True)

        st.markdown("### Research Focus")
        _cfg_rf = load_json_safe(CONFIG_PATH) or {}
        research_focus_input = st.text_area(
            "Describe your research interests — used by Claude to score paper relevance",
            value=_cfg_rf.get("research_focus", ""),
            height=110,
            placeholder="e.g. political communication, misinformation, social media and democracy",
            key="research_focus_input",
        )
        if st.button("Save focus"):
            _cfg_save = load_json_safe(CONFIG_PATH) or {}
            _cfg_save["research_focus"] = research_focus_input.strip()
            with open(CONFIG_PATH, "w", encoding="utf-8") as _f:
                json.dump(_cfg_save, _f, ensure_ascii=False, indent=2)
            st.success("Research focus saved.")

        st.divider()
        st.markdown("### Stats")
        st.markdown(f'<div class="stat-box"><div class="stat-num">{saved_count()}</div>'
                    f'<div class="stat-label">Saved all-time</div></div>', unsafe_allow_html=True)
        if st.button("🗑 Reset history"):
            if SAVED_PATH.exists(): SAVED_PATH.unlink()
            st.success("History cleared.")

    # ── Header ──
    st.markdown("""
<div style="text-align:center; padding: 2.5rem 0 1rem 0;">
    <div style="font-size:3.5rem; animation: bounce 2s ease infinite; display:inline-block;">🧇</div>
    <h1 style="font-family:Cambria,Georgia,serif; font-size:3.2rem; letter-spacing:-0.02em;
               background: linear-gradient(135deg, #d63d6e, #f5a623, #2aaa8a);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               background-clip: text; margin: 0.3rem 0 0.5rem 0;">
        Wise Waffle
    </h1>
    <p style="color:#9a9490; font-family:'DM Mono',monospace; font-size:0.85rem; letter-spacing:0.12em; text-transform:uppercase;">
        Weekly academic literature tracker &nbsp;·&nbsp; Semantic Scholar → Zotero & Notion
    </p>
</div>
""", unsafe_allow_html=True)

    st.divider()

    config_ok = bool(s2_key)
    col_a, col_b, col_c = st.columns(3)
    with col_a: st.markdown(f'<div class="stat-box"><div class="stat-num">{"✓" if s2_key else "✗"}</div><div class="stat-label">S2 API Key</div></div>', unsafe_allow_html=True)
    with col_b: st.markdown(f'<div class="stat-box"><div class="stat-num">{"✓" if zotero_id and zotero_key else "–"}</div><div class="stat-label">Zotero</div></div>', unsafe_allow_html=True)
    with col_c: st.markdown(f'<div class="stat-box"><div class="stat-num">{"✓" if notion_tok and notion_db else "–"}</div><div class="stat-label">Notion</div></div>', unsafe_allow_html=True)

    st.divider()

    col_run, col_info = st.columns([1, 3])
    with col_run:
        run_btn = st.button("▶ Run", disabled=not config_ok or date_from > date_to)
    with col_info:
        if not config_ok:
            st.warning("Enter your Semantic Scholar API key in the sidebar to start.")
        elif dry_run:
            st.info("Dry run — results shown but nothing saved.")
        if research_focus_input.strip() and anthropic_key and (date_to - date_from).days > 90:
            st.warning("Scoring is enabled for a large date range. This may take a long time and incur API costs. Consider reducing the date range or disabling scoring.")

    with st.expander("Add to this run (optional)"):
        st.caption("Extra inputs for this run only — not saved to topics.json.")
        xc1, xc2, xc3 = st.columns(3)
        with xc1:
            st.markdown("**Extra keywords**")
            st.caption("One per line")
            extra_keywords_raw = st.text_area("Extra keywords", height=120, key="m1_extra_keywords",
                label_visibility="collapsed",
                placeholder="social media wellbeing\nalgorithmic fairness")
        with xc2:
            st.markdown("**Extra scholars**")
            st.caption("Name or S2 Author ID, one per line")
            extra_scholars_raw = st.text_area("Extra scholars", height=120, key="m1_extra_scholars",
                label_visibility="collapsed",
                placeholder="Amy Orben\n1234567890")
        with xc3:
            st.markdown("**Extra journals**")
            st.caption("Name or OpenAlex Source ID, one per line")
            extra_journals_raw = st.text_area("Extra journals", height=120, key="m1_extra_journals",
                label_visibility="collapsed",
                placeholder="Journal of Communication\nS12345678")

    if run_btn:
        st.session_state["results"]       = []
        st.session_state["saved_this"]    = 0
        st.session_state["selected_keys"] = set()
        st.session_state["results_page"]  = 1
        st.session_state["log_lines"]     = []
        for _k in ("rr_kw_filter", "rr_journal_filter", "rr_search_filter", "rr_sort_by"):
            st.session_state.pop(_k, None)
        st.query_params["page"] = "1"

        config = build_config(s2_key, zotero_id, zotero_key, notion_tok, notion_db, collection_keys, anthropic_key, zotero_lib_type)
        topics = load_json_safe(TOPICS_PATH) or {}
        since  = date_from.strftime("%Y-%m-%d")
        pf.S2_HEADERS = {"x-api-key": s2_key} if s2_key else {}

        st.markdown("### Progress")
        log_container = st.empty()
        log_lines = st.session_state["log_lines"]
        log_lines.append(f"Search range: {since} → {date_to.strftime('%Y-%m-%d')}")

        def update_log():
            log_text = "\n".join(log_lines[-80:])
            log_container.markdown(
                f'<div style="background:#0f0e0d;color:#a8d5a2;font-family:DM Mono,monospace;'
                f'font-size:0.75rem;padding:1rem;border-radius:4px;height:220px;overflow-y:auto;">'
                f'<pre>{log_text}</pre></div>', unsafe_allow_html=True)

        def _log_step(msg):
            log_lines.append(msg); update_log()

        original_print = builtins.print
        def patched_print(*args, **kwargs):
            log_lines.append(" ".join(str(a) for a in args))
            update_log()
            original_print(*args, **kwargs)
        builtins.print = patched_print

        extra_keywords   = [l.strip() for l in extra_keywords_raw.splitlines() if l.strip()]
        extra_scholars   = [l.strip() for l in extra_scholars_raw.splitlines() if l.strip()]
        extra_journals_l = [l.strip() for l in extra_journals_raw.splitlines() if l.strip()]

        until = date_to.strftime("%Y-%m-%d")
        try:
            with st.spinner("Fetching papers…"):
                all_papers = []
                if run_keywords:
                    _log_step("\n── Tier 1 & 2: Keyword search ──")
                    all_papers.extend(pf.run_search(topics, since, until=until))
                else:
                    _log_step("── Tier 1 & 2: skipped ──")
                if run_scholars:
                    _log_step("\n── Tier 3 & 4: Scholar tracking ──")
                    all_papers.extend(pf.run_authors(topics, since, until=until))
                else:
                    _log_step("── Tier 3 & 4: skipped ──")
                if run_journals_chk:
                    _log_step("\n── Tier 5: Journal sweep ──")
                    all_papers.extend(pf.run_journals(since, until=until))
                else:
                    _log_step("── Tier 5: skipped ──")
                if sum([run_keywords, run_scholars, run_journals_chk]) > 1:
                    all_papers = pf.deduplicate(all_papers)

                if extra_keywords:
                    _log_step(f"\n── Extra keywords: {len(extra_keywords)} term(s) ──")
                    xk = pf.run_keywords_flexible(extra_keywords, since, until=until)
                    all_papers.extend(xk)
                if extra_scholars:
                    _log_step(f"\n── Extra scholars: {len(extra_scholars)} ──")
                    all_papers.extend(pf.run_authors_flexible(extra_scholars, since, until=until))
                if extra_journals_l:
                    _log_step(f"\n── Extra journals: {len(extra_journals_l)} ──")
                    all_papers.extend(pf.run_journals_flexible(extra_journals_l, since, until=until))
                if extra_keywords or extra_scholars or extra_journals_l:
                    all_papers = pf.deduplicate(all_papers)

                if research_focus_input.strip():
                    if anthropic_key:
                        log_lines.append(f"\n── Scoring {len(all_papers)} papers with Claude ──"); update_log()
                        all_papers = pf.score_papers(all_papers, research_focus_input.strip(), api_key=anthropic_key)
                        log_lines.append(f"{len(all_papers)} papers after scoring"); update_log()
                        st.session_state["results"] = all_papers
                    else:
                        log_lines.append("[relevance] Anthropic API key not set — skipping scoring"); update_log()

                if not dry_run and target != "view":
                    all_papers = pf.filter_new(all_papers)
                    log_lines.append(f"\n{len(all_papers)} new papers (after dedup with history)")
                else:
                    log_lines.append(f"\n{len(all_papers)} papers found (dry run / view mode)")
                update_log()

                st.session_state["results"] = all_papers

                if all_papers and not dry_run and target != "view":
                    if target in ("zotero", "both") and config.get("zotero"):
                        log_lines.append("\n── Saving to Zotero ──"); update_log()
                        pf.save_to_zotero(all_papers, config)
                    if target in ("notion", "both") and config.get("notion"):
                        log_lines.append("\n── Saving to Notion ──"); update_log()
                        pf.save_to_notion(all_papers, config)
                    pf.record_saved(all_papers)
                    pf.clear_cache()
                    st.session_state["saved_this"] = len(all_papers)
                else:
                    log_lines.append("Results ready — select papers below to save manually.")

                log_lines.append("\n✓ Done."); update_log()

        except Exception as e:
            log_lines.append(f"\n[ERROR] {type(e).__name__}: {e}"); update_log()
        finally:
            builtins.print = original_print

    if st.session_state.get("log_lines"):
        with st.expander("📋 Last run log", expanded=False):
            log_text = "\n".join(st.session_state["log_lines"])
            st.markdown(
                f'<div style="background:#0f0e0d;color:#a8d5a2;font-family:DM Mono,monospace;'
                f'font-size:0.75rem;padding:1rem;border-radius:4px;max-height:400px;overflow-y:auto;">'
                f'<pre>{log_text}</pre></div>', unsafe_allow_html=True)

    render_results(
        st.session_state.get("results", []),
        s2_key=s2_key,
        zotero_id=zotero_id,
        zotero_key=zotero_key,
        notion_tok=notion_tok,
        notion_db=notion_db,
        collection_keys=collection_keys,
        anthropic_key=anthropic_key,
        library_type=zotero_lib_type,
    )

    if st.session_state.get("results"):
        with st.expander("💾 Save this search", expanded=False):
            sn_col, sb_col = st.columns([3, 2])
            with sn_col:
                _m1_save_name = st.text_input(
                    "Profile name", placeholder="e.g. weekly comm, gender studies 2026",
                    key="m1_save_name_input",
                )
            with sb_col:
                st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.button("Save config", key="m1_save_cfg_btn", disabled=not _m1_save_name):
                        _sd = load_searches()
                        _sd["profiles"][_m1_save_name] = {
                            "name":    _m1_save_name,
                            "mode":    "mode1",
                            "created": datetime.now().isoformat(),
                            "config":  _capture_m1_config(date_from, date_to),
                        }
                        save_searches(_sd)
                        st.success(f'Profile "{_m1_save_name}" saved.')
                with sc2:
                    if st.button("Save snapshot", key="m1_save_snap_btn", disabled=not _m1_save_name):
                        _sd = load_searches()
                        _snap_key = f"{_m1_save_name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        _papers_now = st.session_state["results"]
                        _sd["snapshots"][_snap_key] = {
                            "name":         _snap_key,
                            "profile_name": _m1_save_name,
                            "mode":         "mode1",
                            "timestamp":    datetime.now().isoformat(),
                            "paper_count":  len(_papers_now),
                            "papers":       _trim_papers(_papers_now),
                        }
                        # keep only 20 most recent snapshots
                        if len(_sd["snapshots"]) > 20:
                            oldest = list(_sd["snapshots"].keys())[0]
                            del _sd["snapshots"][oldest]
                        save_searches(_sd)
                        st.success(f'Snapshot "{_snap_key}" saved ({len(_papers_now)} papers).')

# ── Mode 2 ────────────────────────────────────────────────────────────────────
def render_mode2():
    with st.sidebar:
        if st.button("← Home", key="m2_back"):
            st.session_state["view"]      = "landing"
            st.session_state["results"]   = []
            st.session_state["log_lines"] = []
            st.rerun()
        st.markdown("## 🧇")
        st.divider()

        st.markdown("### API Keys")
        try:
            host_secrets_m2 = dict(st.secrets["host"]) if "host" in st.secrets else {}
        except Exception:
            host_secrets_m2 = {}
        if host_secrets_m2:
            if st.button("⚡ Fill my credentials", key="m2_fill"):
                st.session_state["m2_s2_key"]        = host_secrets_m2.get("s2_key", "")
                st.session_state["m2_zotero_id"]     = host_secrets_m2.get("zotero_id", "")
                st.session_state["m2_zotero_key"]    = host_secrets_m2.get("zotero_key", "")
                st.session_state["m2_notion_tok"]    = host_secrets_m2.get("notion_tok", "")
                st.session_state["m2_notion_db"]     = host_secrets_m2.get("notion_db", "")
                st.session_state["m2_anthropic_key"] = host_secrets_m2.get("anthropic_key", "")

        st.text_input("Semantic Scholar API Key *", type="password", key="m2_s2_key",       placeholder="Required")
        _m2_zid_col, _m2_ztype_col = st.columns([2, 1])
        with _m2_zid_col:
            st.text_input("Zotero Library ID", key="m2_zotero_id", placeholder="e.g. 10541129")
        with _m2_ztype_col:
            st.selectbox("Library type", ["user", "group"], key="m2_zotero_lib_type")
        st.text_input("Zotero API Key",              type="password", key="m2_zotero_key")
        st.text_input("Notion Token",                type="password", key="m2_notion_tok",  placeholder="secret_…")
        st.text_input("Notion Database ID",                           key="m2_notion_db",   placeholder="32-char ID")
        st.text_input("Anthropic API Key",           type="password", key="m2_anthropic_key", placeholder="sk-ant-… (for scoring)")
        st.text_input("Zotero Collection Key (optional)", key="m2_zotero_coll",
                      placeholder="8-char key, blank = root library")

        s2_key        = st.session_state.get("m2_s2_key", "")
        zotero_id     = st.session_state.get("m2_zotero_id", "")
        zotero_key    = st.session_state.get("m2_zotero_key", "")
        notion_tok    = st.session_state.get("m2_notion_tok", "")
        notion_db     = st.session_state.get("m2_notion_db", "")
        anthropic_key = st.session_state.get("m2_anthropic_key", "")
        zotero_lib_type = st.session_state.get("m2_zotero_lib_type", "user")
        zotero_coll   = st.session_state.get("m2_zotero_coll", "")

        st.divider()
        _searches_m2 = load_searches()
        _profiles_m2 = _searches_m2.get("profiles", {})
        _snaps_m2    = _searches_m2.get("snapshots", {})
        if _profiles_m2:
            with st.expander("📂 Load saved search config"):
                _chosen_profile_m2 = st.selectbox(
                    "Profile", [""] + list(_profiles_m2.keys()),
                    format_func=lambda x: "— select —" if x == "" else x,
                    key="m2_load_profile",
                )
                lp1, lp2 = st.columns(2)
                with lp1:
                    if st.button("Load", key="m2_load_btn", disabled=not _chosen_profile_m2):
                        _restore_m2_config(_profiles_m2[_chosen_profile_m2]["config"])
                        st.success(f'Loaded "{_chosen_profile_m2}"')
                        st.rerun()
                with lp2:
                    if st.button("Delete", key="m2_del_profile", disabled=not _chosen_profile_m2):
                        del _searches_m2["profiles"][_chosen_profile_m2]
                        save_searches(_searches_m2)
                        st.success("Deleted.")
                        st.rerun()
        if _snaps_m2:
            with st.expander("📚 Saved snapshots"):
                _chosen_snap_m2 = st.selectbox(
                    "Snapshot", [""] + list(reversed(list(_snaps_m2.keys()))),
                    format_func=lambda x: "— select —" if x == "" else x,
                    key="m2_load_snap",
                )
                if _chosen_snap_m2:
                    _s2 = _snaps_m2[_chosen_snap_m2]
                    st.caption(f'{_s2["paper_count"]} papers · {_s2["timestamp"][:10]}')
                    sv1, sv2 = st.columns(2)
                    with sv1:
                        if st.button("View", key="m2_view_snap"):
                            st.session_state["results"]       = _s2["papers"]
                            st.session_state["results_page"]  = 1
                            st.session_state["selected_keys"] = set()
                            st.rerun()
                    with sv2:
                        if st.button("Delete", key="m2_del_snap"):
                            del _searches_m2["snapshots"][_chosen_snap_m2]
                            save_searches(_searches_m2)
                            st.success("Deleted.")
                            st.rerun()

        st.divider()
        st.markdown("### Settings")
        target    = st.selectbox("Save to", ["view", "both", "zotero", "notion"],
            format_func=lambda x: {"view": "View only (no save)", "both": "Zotero + Notion",
                                    "zotero": "Zotero only", "notion": "Notion only"}[x],
            key="m2_target")
        _today_m2       = datetime.today().date()
        _search_mode_sb = st.session_state.get("m2_search_mode", "recent")
        if _search_mode_sb == "recent":
            date_from = st.date_input("From", value=_today_m2 - timedelta(days=30),
                                      min_value=_today_m2 - timedelta(days=5*365), max_value=_today_m2,
                                      key="m2_date_from")
            date_to   = st.date_input("To",   value=_today_m2,
                                      min_value=_today_m2 - timedelta(days=5*365), max_value=_today_m2,
                                      key="m2_date_to")
            if date_from > date_to:
                st.error("'From' date must not be after 'To'.")
        else:
            st.slider(
                "Impact score threshold", 0.0, 1.0, 0.3, 0.05,
                key="m2_impact_threshold",
                on_change=_reset_results_page,
                help="Papers below this score are hidden. 0 = show all, higher = more selective.",
            )
            date_from = _today_m2 - timedelta(days=10 * 365)
            date_to   = _today_m2
        dry_run   = st.checkbox("Dry run (preview, don't save)", value=True, key="m2_dry_run")

        st.divider()
        st.markdown("### Stats")
        st.markdown(f'<div class="stat-box"><div class="stat-num">{saved_count()}</div>'
                    f'<div class="stat-label">Saved all-time</div></div>', unsafe_allow_html=True)
        if st.button("🗑 Reset history", key="m2_reset"):
            if SAVED_PATH.exists(): SAVED_PATH.unlink()
            st.success("History cleared.")

    flex_coll_keys = {
        "flex:keyword":   zotero_coll,
        "flex:crossover": zotero_coll,
        "flex:scholar":   zotero_coll,
        "flex:journal":   zotero_coll,
    } if zotero_coll else {}

    # ── Header ──
    st.markdown("""
<div style="text-align:center; padding: 2rem 0 0.5rem 0;">
    <div style="font-size:3rem; animation: bounce 2s ease infinite; display:inline-block;">🧇</div>
    <h1 style="font-family:Cambria,Georgia,serif; font-size:2.6rem; letter-spacing:-0.02em;
               background: linear-gradient(135deg, #2aaa8a, #4a90d9);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               background-clip: text; margin: 0.3rem 0 0.4rem 0;">
        Custom Search
    </h1>
    <p style="color:#9a9490; font-family:'DM Mono',monospace; font-size:0.82rem; letter-spacing:0.1em; text-transform:uppercase;">
        Mode 2 &nbsp;·&nbsp; Enter your own keywords, scholars, and journals
    </p>
</div>
""", unsafe_allow_html=True)

    config_ok = bool(s2_key)
    col_a, col_b, col_c = st.columns(3)
    with col_a: st.markdown(f'<div class="stat-box"><div class="stat-num">{"✓" if s2_key else "✗"}</div><div class="stat-label">S2 API Key</div></div>', unsafe_allow_html=True)
    with col_b: st.markdown(f'<div class="stat-box"><div class="stat-num">{"✓" if zotero_id and zotero_key else "–"}</div><div class="stat-label">Zotero</div></div>', unsafe_allow_html=True)
    with col_c: st.markdown(f'<div class="stat-box"><div class="stat-num">{"✓" if notion_tok and notion_db else "–"}</div><div class="stat-label">Notion</div></div>', unsafe_allow_html=True)

    st.divider()

    # ── Search mode toggle ──
    st.radio(
        "Search mode",
        ["recent", "deep"],
        format_func=lambda x: {
            "recent": "🗓 Recent papers — date-filtered",
            "deep":   "🔭 Deep search — no date filter, ranked by citation impact",
        }[x],
        horizontal=True,
        key="m2_search_mode",
    )
    _active_mode = st.session_state.get("m2_search_mode", "recent")

    # ── Inputs ──
    st.markdown("### Search Inputs")
    st.caption("All categories are independent — search with any one or combine them freely.")
    col_left, col_right = st.columns(2)

    with col_left:
        if _active_mode == "recent":
            st.markdown("**Keywords** — Semantic Scholar keyword search, up to 20 results per term")
        else:
            st.markdown("**Keywords** — Semantic Scholar keyword search, up to 100 results per term (no date filter)")
        st.caption("One per line.")
        keywords_raw = st.text_area("Keywords", height=130, key="m2_keywords",
            placeholder="social media wellbeing\ngender norms youth\nalgorithmic fairness",
            label_visibility="collapsed")

        if _active_mode == "recent":
            st.markdown("**Crossover keywords** *(optional)* — same search, 8 results per term")
        else:
            st.markdown("**Crossover keywords** *(optional)* — same search, 50 results per term (no date filter)")
        st.caption("Good for adjacent fields where you want signal without floods. One per line.")
        crossover_raw = st.text_area("Crossover keywords", height=110, key="m2_crossover",
            placeholder="evolutionary psychology\nbioethics\npolitical polarization",
            label_visibility="collapsed")

    with col_right:
        st.markdown("**Scholars** — fetches their papers from Semantic Scholar")
        if _active_mode == "recent":
            st.caption("Enter full names or Semantic Scholar Author IDs (numeric). IDs are more reliable — find them at semanticscholar.org. One per line.")
        else:
            st.caption("Enter full names or Semantic Scholar Author IDs. Lookback period set below. One per line.")
        scholars_raw = st.text_area("Scholars", height=110, key="m2_scholars",
            placeholder="Amy Orben\nAndrew Przybylski\nPhilipp Masur",
            label_visibility="collapsed")

        if _active_mode == "deep":
            st.selectbox(
                "Scholar lookback period",
                [5, 10, 20],
                index=1,
                format_func=lambda x: f"{x} years",
                key="m2_scholar_lookback",
            )

        st.markdown("**Journals** — sweeps articles via OpenAlex")
        if _active_mode == "recent":
            st.caption("Enter exact journal names or OpenAlex Source IDs (format: S12345678). IDs avoid name-matching errors — find them at openalex.org. One per line.")
        else:
            st.caption("Deep search uses a 10-year lookback per journal. Enter names or OpenAlex Source IDs. One per line.")
        journals_raw = st.text_area("Journals", height=90, key="m2_journals",
            placeholder="Journal of Communication\nNew Media & Society\nComputers in Human Behavior",
            label_visibility="collapsed")
        st.markdown("**Journal search terms** *(optional, 3–5 terms recommended)*")
        st.caption("Filters results within the journals above. Leave blank to fetch all articles (slower).")
        journal_keywords_raw = st.text_area("Journal search terms (optional, 3-5 terms recommended)", height=80, key="m2_journal_keywords",
            placeholder="social media\nalgorithmic curation\nmisinformation",
            label_visibility="collapsed")

    st.markdown("### Research Focus *(optional)*")
    st.caption("Claude scores each paper 0–10 for relevance. Requires an Anthropic key in the sidebar.")
    research_focus_input = st.text_area(
        "Research Focus",
        height=90,
        placeholder="e.g. political communication, misinformation, social media and democracy",
        key="m2_research_focus",
        label_visibility="collapsed",
    )

    st.divider()

    col_run, col_info = st.columns([1, 3])
    with col_run:
        _date_ok = (_active_mode == "deep") or (date_from <= date_to)
        run_btn = st.button("▶ Run", disabled=not config_ok or not _date_ok, key="m2_run")
    with col_info:
        if not config_ok:
            st.warning("Enter your Semantic Scholar API key in the sidebar to start.")
        elif _active_mode == "deep":
            st.info("Deep search fetches without a date limit and ranks results by citation impact score. This may take longer than recent mode.")
        elif dry_run:
            st.info("Dry run — results shown but nothing saved.")
        if _active_mode == "recent" and research_focus_input.strip() and anthropic_key and (date_to - date_from).days > 90:
            st.warning("Scoring is enabled for a large date range. This may take a long time and incur API costs. Consider reducing the date range or disabling scoring.")

    if run_btn:
        keywords         = [l.strip() for l in keywords_raw.splitlines()         if l.strip()]
        crossovers       = [l.strip() for l in crossover_raw.splitlines()       if l.strip()]
        scholars         = [l.strip() for l in scholars_raw.splitlines()        if l.strip()]
        journals         = [l.strip() for l in journals_raw.splitlines()        if l.strip()]
        journal_keywords = [l.strip() for l in journal_keywords_raw.splitlines() if l.strip()]

        if not any([keywords, crossovers, scholars, journals]):
            st.warning("Enter at least one keyword, scholar, or journal to search.")
        else:
            st.session_state["results"]       = []
            st.session_state["saved_this"]    = 0
            st.session_state["selected_keys"] = set()
            st.session_state["results_page"]  = 1
            st.session_state["log_lines"]     = []
            st.session_state["m2_all_scored"] = []
            st.session_state["m2_all_deep"]   = []
            for _k in ("rr_kw_filter", "rr_journal_filter", "rr_search_filter", "rr_sort_by"):
                st.session_state.pop(_k, None)
            st.query_params["page"] = "1"

            pf.S2_HEADERS = {"x-api-key": s2_key} if s2_key else {}

            st.markdown("### Progress")
            log_container = st.empty()
            log_lines = st.session_state["log_lines"]

            def update_log():
                log_text = "\n".join(log_lines[-80:])
                log_container.markdown(
                    f'<div style="background:#0f0e0d;color:#a8d5a2;font-family:DM Mono,monospace;'
                    f'font-size:0.75rem;padding:1rem;border-radius:4px;height:220px;overflow-y:auto;">'
                    f'<pre>{log_text}</pre></div>', unsafe_allow_html=True)

            original_print = builtins.print
            def patched_print(*args, **kwargs):
                log_lines.append(" ".join(str(a) for a in args))
                update_log()
                original_print(*args, **kwargs)
            builtins.print = patched_print

            run_mode = st.session_state.get("m2_search_mode", "recent")

            try:
                with st.spinner("Fetching papers…"):
                    all_papers = []

                    if run_mode == "recent":
                        # ── Recent papers pipeline ───────────────────────────────────
                        since = date_from.strftime("%Y-%m-%d")
                        until = date_to.strftime("%Y-%m-%d")
                        log_lines.append(f"Search range: {since} → {until}"); update_log()

                        if keywords:
                            log_lines.append(f"\n── Keywords: {len(keywords)} term(s) ──"); update_log()
                            all_papers.extend(pf.run_keywords_flexible(keywords, since, until=until, max_per_keyword=20))

                        if crossovers:
                            log_lines.append(f"\n── Crossover keywords: {len(crossovers)} term(s) ──"); update_log()
                            cx = pf.run_keywords_flexible(crossovers, since, until=until, max_per_keyword=8)
                            for p in cx:
                                p["tag"] = "flex:crossover"
                            all_papers.extend(cx)

                        if scholars:
                            log_lines.append(f"\n── Scholars: {len(scholars)} name(s) ──"); update_log()
                            all_papers.extend(pf.run_authors_flexible(scholars, since, until=until))

                        if journals:
                            log_lines.append(f"\n── Journals: {len(journals)} name(s) ──"); update_log()
                            all_papers.extend(pf.run_journals_flexible(journals, since, until=until, keywords=journal_keywords or None))

                        all_papers = pf.deduplicate(all_papers)
                        log_lines.append(f"\n{len(all_papers)} papers after cross-source dedup"); update_log()

                        if research_focus_input.strip():
                            if anthropic_key:
                                log_lines.append(f"\n── Scoring {len(all_papers)} papers with Claude ──"); update_log()
                                all_papers = pf.score_papers(all_papers, research_focus_input.strip(), api_key=anthropic_key)
                                log_lines.append(f"{len(all_papers)} papers after scoring"); update_log()
                                st.session_state["m2_all_scored"] = list(all_papers)
                                threshold_now = st.session_state.get("m2_score_threshold", 6)
                                before_filter = len(all_papers)
                                all_papers = [p for p in all_papers
                                              if p.get("relevance_score") is None or p.get("relevance_score", 0) >= threshold_now]
                                log_lines.append(f"{len(all_papers)} papers kept (score ≥ {threshold_now}, was {before_filter})"); update_log()
                            else:
                                log_lines.append("[relevance] Anthropic API key not set — skipping scoring"); update_log()

                    else:
                        # ── Deep search pipeline ─────────────────────────────────────
                        log_lines.append("Mode: Deep search (no date filter, citation-impact scoring)"); update_log()

                        if keywords:
                            log_lines.append(f"\n── Deep keywords: {len(keywords)} term(s), up to 100 each ──"); update_log()
                            all_papers.extend(pf.deep_search_s2(keywords, max_per_keyword=100))

                        if crossovers:
                            log_lines.append(f"\n── Deep crossover: {len(crossovers)} term(s), up to 50 each ──"); update_log()
                            cx = pf.deep_search_s2(crossovers, max_per_keyword=50)
                            for p in cx:
                                p["tag"] = "flex:crossover"
                            all_papers.extend(cx)

                        if scholars:
                            lookback_yrs = st.session_state.get("m2_scholar_lookback", 10)
                            since_scholars = (_today_m2 - timedelta(days=lookback_yrs * 365)).strftime("%Y-%m-%d")
                            log_lines.append(f"\n── Deep scholars: {len(scholars)} name(s), {lookback_yrs}-year lookback ──"); update_log()
                            all_papers.extend(pf.run_authors_flexible(scholars, since_scholars))

                        if journals:
                            log_lines.append(f"\n── Deep journals: {len(journals)} name(s), 10-year lookback ──"); update_log()
                            all_papers.extend(pf.deep_search_openalex(journals, keywords=journal_keywords or None))

                        all_papers = pf.deduplicate(all_papers)
                        log_lines.append(f"\n{len(all_papers)} papers after dedup"); update_log()

                        log_lines.append("\n── Computing citation impact scores ──"); update_log()
                        all_papers = pf.compute_impact_score(all_papers)
                        st.session_state["m2_all_deep"] = list(all_papers)

                        impact_thr = st.session_state.get("m2_impact_threshold", 0.3)
                        all_papers = [p for p in all_papers if p.get("impact_score", 0) >= impact_thr]
                        log_lines.append(f"{len(all_papers)} papers above impact threshold {impact_thr}"); update_log()

                        if research_focus_input.strip():
                            if anthropic_key:
                                log_lines.append(f"\n── Scoring {len(all_papers)} papers with Claude ──"); update_log()
                                all_papers = pf.deep_score_papers(all_papers, research_focus_input.strip(), api_key=anthropic_key)
                                log_lines.append(f"{len(all_papers)} papers after scoring"); update_log()
                                st.session_state["m2_all_scored"] = list(all_papers)
                                threshold_now = st.session_state.get("m2_score_threshold", 6)
                                before_filter = len(all_papers)
                                all_papers = [p for p in all_papers
                                              if p.get("relevance_score") is None or p.get("relevance_score", 0) >= threshold_now]
                                log_lines.append(f"{len(all_papers)} papers kept (score ≥ {threshold_now}, was {before_filter})"); update_log()
                            else:
                                log_lines.append("[relevance] Anthropic API key not set — skipping scoring"); update_log()

                    # ── Save / dry-run (shared) ──────────────────────────────────
                    if not dry_run and target != "view":
                        all_papers = pf.filter_new(all_papers)
                        log_lines.append(f"\n{len(all_papers)} new papers (after dedup with history)")
                    else:
                        log_lines.append(f"\n{len(all_papers)} papers found (dry run / view mode)")
                    update_log()

                    st.session_state["results"] = all_papers

                    if all_papers and not dry_run and target != "view":
                        config = build_config(s2_key, zotero_id, zotero_key, notion_tok, notion_db,
                                              flex_coll_keys, anthropic_key, zotero_lib_type)
                        if target in ("zotero", "both") and config.get("zotero"):
                            log_lines.append("\n── Saving to Zotero ──"); update_log()
                            pf.save_to_zotero(all_papers, config)
                        if target in ("notion", "both") and config.get("notion"):
                            log_lines.append("\n── Saving to Notion ──"); update_log()
                            pf.save_to_notion(all_papers, config)
                        pf.record_saved(all_papers)
                        pf.clear_cache()
                        st.session_state["saved_this"] = len(all_papers)
                    else:
                        log_lines.append("Results ready — select papers below to save manually.")

                    log_lines.append("\n✓ Done."); update_log()

            except Exception as e:
                log_lines.append(f"\n[ERROR] {type(e).__name__}: {e}"); update_log()
            finally:
                builtins.print = original_print

    if st.session_state.get("log_lines"):
        with st.expander("📋 Last run log", expanded=False):
            log_text = "\n".join(st.session_state["log_lines"])
            st.markdown(
                f'<div style="background:#0f0e0d;color:#a8d5a2;font-family:DM Mono,monospace;'
                f'font-size:0.75rem;padding:1rem;border-radius:4px;max-height:400px;overflow-y:auto;">'
                f'<pre>{log_text}</pre></div>', unsafe_allow_html=True)

    _m2_all_scored  = st.session_state.get("m2_all_scored", [])
    _m2_all_deep    = st.session_state.get("m2_all_deep", [])
    _current_mode   = st.session_state.get("m2_search_mode", "recent")

    if _m2_all_scored:
        _threshold = st.session_state.get("m2_score_threshold", 6)
        _display_results = [p for p in _m2_all_scored
                            if p.get("relevance_score") is None or p.get("relevance_score", 0) >= _threshold]
    elif _current_mode == "deep" and _m2_all_deep:
        _impact_thr = st.session_state.get("m2_impact_threshold", 0.3)
        _display_results = [p for p in _m2_all_deep if p.get("impact_score", 0) >= _impact_thr]
    else:
        _display_results = st.session_state.get("results", [])

    render_results(
        _display_results,
        s2_key=s2_key,
        zotero_id=zotero_id,
        zotero_key=zotero_key,
        notion_tok=notion_tok,
        notion_db=notion_db,
        collection_keys=flex_coll_keys,
        anthropic_key=anthropic_key,
        library_type=zotero_lib_type,
    )

    if _current_mode == "deep" and _m2_all_deep and not _m2_all_scored:
        _thr_d = st.session_state.get("m2_impact_threshold", 0.3)
        _shown_d = sum(1 for p in _m2_all_deep if p.get("impact_score", 0) >= _thr_d)
        st.caption(f"{_shown_d} of {len(_m2_all_deep)} papers shown (impact score ≥ {_thr_d}) · adjust threshold in sidebar")

    if _m2_all_scored:
        st.divider()
        thr_col, info_col = st.columns([1, 3])
        with thr_col:
            st.number_input(
                "Minimum relevance score", min_value=0, max_value=10, step=1,
                key="m2_score_threshold",
                on_change=_reset_results_page,
                help="Re-filters scored papers instantly — no need to re-run the search.",
            )
        with info_col:
            _thr = st.session_state.get("m2_score_threshold", 6)
            _kept = sum(1 for p in _m2_all_scored
                        if p.get("relevance_score") is None or p.get("relevance_score", 0) >= _thr)
            st.markdown(
                f'<div style="padding-top:1.75rem; color:#666; font-size:0.85rem">'
                f'{_kept} of {len(_m2_all_scored)} papers shown at score ≥ {_thr}</div>',
                unsafe_allow_html=True,
            )

    if st.session_state.get("results"):
        with st.expander("💾 Save this search", expanded=False):
            sn_col, sb_col = st.columns([3, 2])
            with sn_col:
                _m2_save_name = st.text_input(
                    "Profile name", placeholder="e.g. misinformation sweep, orben scholars",
                    key="m2_save_name_input",
                )
            with sb_col:
                st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.button("Save config", key="m2_save_cfg_btn", disabled=not _m2_save_name):
                        _sd = load_searches()
                        _sd["profiles"][_m2_save_name] = {
                            "name":    _m2_save_name,
                            "mode":    "mode2",
                            "created": datetime.now().isoformat(),
                            "config":  _capture_m2_config(date_from, date_to),
                        }
                        save_searches(_sd)
                        st.success(f'Profile "{_m2_save_name}" saved.')
                with sc2:
                    if st.button("Save snapshot", key="m2_save_snap_btn", disabled=not _m2_save_name):
                        _sd = load_searches()
                        _snap_key = f"{_m2_save_name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        _papers_now = st.session_state["results"]
                        _sd["snapshots"][_snap_key] = {
                            "name":         _snap_key,
                            "profile_name": _m2_save_name,
                            "mode":         "mode2",
                            "timestamp":    datetime.now().isoformat(),
                            "paper_count":  len(_papers_now),
                            "papers":       _trim_papers(_papers_now),
                        }
                        if len(_sd["snapshots"]) > 20:
                            oldest = list(_sd["snapshots"].keys())[0]
                            del _sd["snapshots"][oldest]
                        save_searches(_sd)
                        st.success(f'Snapshot "{_snap_key}" saved ({len(_papers_now)} papers).')

# ── Router ────────────────────────────────────────────────────────────────────
view = st.session_state.get("view", "landing")
if view == "mode1":
    render_mode1()
elif view == "mode2":
    render_mode2()
else:
    render_landing()
