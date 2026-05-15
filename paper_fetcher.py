"""
paper_fetcher.py — Wise Waffle backend
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import requests

BASE_DIR      = Path(__file__).parent
CONFIG_PATH   = BASE_DIR / "config.json"
TOPICS_PATH   = BASE_DIR / "topics.json"
JOURNALS_PATH = BASE_DIR / "journals.json"
CACHE_PATH    = BASE_DIR / "cache.json"
SAVED_PATH    = BASE_DIR / "saved_dois.json"

S2_HEADERS: dict = {}
S2_BASE          = "https://api.semanticscholar.org/graph/v1"
S2_BULK_SEARCH   = f"{S2_BASE}/paper/search/bulk"
S2_AUTHOR_SEARCH = f"{S2_BASE}/author/search"
PAPER_FIELDS     = "title,authors,year,abstract,externalIds,venue,publicationDate,url,openAccessPdf,publicationTypes"

# ── Config ────────────────────────────────────────────────────────────────────

def load_json(path):
    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ── Cache ─────────────────────────────────────────────────────────────────────

def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clear_cache():
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()
        print("[cache] cleared")

# ── Saved history ─────────────────────────────────────────────────────────────

def load_saved():
    if SAVED_PATH.exists():
        with open(SAVED_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def record_saved(papers):
    existing = load_saved()
    for p in papers:
        key = p["doi"].strip().lower() if p.get("doi") else p.get("title", "").strip().lower()
        if key:
            existing.add(key)
    with open(SAVED_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(existing), f, ensure_ascii=False, indent=2)
    print(f"[saved] {len(existing)} records in saved_dois.json")

def filter_new(papers):
    saved = load_saved()
    new, skipped = [], 0
    for p in papers:
        key = p["doi"].strip().lower() if p.get("doi") else p.get("title", "").strip().lower()
        if key and key in saved:
            skipped += 1
        else:
            new.append(p)
    if skipped:
        print(f"[dedup] skipped {skipped} already-saved papers, {len(new)} new")
    return new

# ── HTTP ──────────────────────────────────────────────────────────────────────

def _request(method, url, retries=5, **kwargs):
    kwargs.setdefault("headers", S2_HEADERS)
    kwargs.setdefault("timeout", 20)
    for attempt in range(retries):
        try:
            r = requests.get(url, **kwargs) if method == "GET" else requests.post(url, **kwargs)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = (2 ** attempt) * 5
                print(f"  [rate limit 429] waiting {wait}s (attempt {attempt+1}/{retries})...")
                time.sleep(wait)
                continue
            if r.status_code in (500, 502, 503, 504):
                wait = (2 ** attempt) * 3
                print(f"  [server error {r.status_code}] waiting {wait}s (attempt {attempt+1}/{retries})...")
                time.sleep(wait)
                continue
            print(f"  [warning] HTTP {r.status_code}: {url}")
            return None
        except requests.RequestException as e:
            wait = (2 ** attempt) * 3
            print(f"  [network error] {e}, retrying in {wait}s...")
            time.sleep(wait)
    print(f"  [failed] max retries reached: {url}")
    return None

# ── Filters ───────────────────────────────────────────────────────────────────

def _is_english(paper):
    text = (paper.get("title") or "") + " " + (paper.get("abstract") or "")
    if not text.strip():
        return True
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / len(text)
    return ascii_ratio > 0.85

def _has_abstract(paper):
    abstract = paper.get("abstract") or ""
    return len(abstract.strip()) > 100

def _is_recent(paper, since):
    pub = paper.get("publicationDate") or paper.get("pub_date", "")
    if pub:
        return pub >= since
    year = paper.get("year") or paper.get("publication_year", "")
    return str(year) >= since[:4] if year else False

def _log_step(n, label, count=None, detail=""):
    count_str  = f": {count} papers" if count is not None else ""
    detail_str = f" ({detail})" if detail else ""
    print(f"\n── Step {n}: {label}{count_str}{detail_str}")

# ── Normalize ─────────────────────────────────────────────────────────────────

def normalize(paper, tag=""):
    """Normalize a paper dict from S2 or OpenAlex into a standard format."""
    raw_authors = paper.get("authors", [])
    if raw_authors and isinstance(raw_authors[0], dict):
        authors = [a.get("name", "") or a.get("display_name", "") for a in raw_authors]
    else:
        authors = [str(a) for a in raw_authors]
    authors = [a for a in authors if a]

    doi = (paper.get("externalIds") or {}).get("DOI", "") or paper.get("doi", "") or ""
    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]

    pdf_url = ""
    if paper.get("openAccessPdf"):
        pdf_url = paper["openAccessPdf"].get("url", "") or ""

    pub_date = paper.get("publicationDate") or paper.get("publication_date") or ""
    abstract = paper.get("abstract", "") or ""

    if not abstract and doi:
        try:
            r = requests.get(
                f"https://api.openalex.org/works/https://doi.org/{doi}",
                params={"select": "abstract_inverted_index"},
                timeout=10,
            )
            if r.status_code == 200:
                abstract = _openalex_rebuild_abstract(
                    r.json().get("abstract_inverted_index")
                )
                if abstract:
                    print(f"    [abstract] fetched from OpenAlex for {doi[:50]}")
        except requests.RequestException:
            pass
        time.sleep(0.5)

    return {
        "title":    paper.get("title", "Untitled") or "Untitled",
        "authors":  authors,
        "year":     str(paper.get("year") or paper.get("publication_year") or ""),
        "pub_date": pub_date,
        "abstract": abstract,
        "journal":  paper.get("venue") or paper.get("journal", "") or "",
        "doi":      doi,
        "url":      paper.get("url", "") or pdf_url,
        "tag":      tag,
    }

def deduplicate(papers):
    seen, result = set(), []
    for p in papers:
        key = p["doi"].strip().lower() if p.get("doi") else p.get("title", "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(p)
    return result

# ── S2 bulk search ────────────────────────────────────────────────────────────

def search_bulk(query, since, max_results=100):
    params = {
        "query":                 query,
        "fields":                PAPER_FIELDS,
        "publicationTypes":      "JournalArticle",
        "publicationDateOrYear": f"{since}:",
        "sort":                  "publicationDate:desc",
        "fieldsOfStudy": "Sociology,Psychology,Political Science,Education,Linguistics,Communication",
    }
    results = []
    while len(results) < max_results:
        data = _request("GET", S2_BULK_SEARCH, params=params)
        if not data:
            break
        raw     = data.get("data", [])
        no_lang = sum(1 for p in raw if not _is_english(p))
        no_abs  = sum(1 for p in raw if _is_english(p) and not _has_abstract(p))
        batch   = [p for p in raw if _is_english(p) and _has_abstract(p)]
        if no_lang or no_abs:
            print(f"    [filter] -{no_lang} non-English, -{no_abs} no abstract, +{len(batch)} kept")
        results.extend(batch)
        token = data.get("token")
        if not token or len(results) >= max_results:
            break
        params = {**params, "token": token}
        time.sleep(1.2)
    return results[:max_results]

# ── Authors ───────────────────────────────────────────────────────────────────

def resolve_author_ids(names):
    name_to_id = {}
    for name in names:
        data = _request("GET", S2_AUTHOR_SEARCH,
                        params={"query": name, "limit": 1, "fields": "name,authorId"})
        if data:
            hits = data.get("data", [])
            if hits:
                name_to_id[name] = hits[0]["authorId"]
                print(f"    ✓ {name} → {hits[0]['authorId']}")
            else:
                print(f"    ✗ {name}: not found")
        time.sleep(1.2)
    return name_to_id

def get_papers_for_authors(author_ids, since, papers_per_author=15):
    all_papers = []
    for author_id in author_ids:
        url  = f"{S2_BASE}/author/{author_id}/papers"
        data = _request("GET", url, params={"fields": PAPER_FIELDS, "limit": 50})
        if not data:
            time.sleep(1.2)
            continue
        papers  = data.get("data", [])
        total   = len(papers)
        recent  = [p for p in papers if _is_recent(p, since) and _is_english(p) and _has_abstract(p)]
        recent  = sorted(recent, key=lambda p: p.get("publicationDate") or "", reverse=True)
        kept    = recent[:papers_per_author]
        dropped = total - len(recent)
        if dropped:
            print(f"    [filter] author {author_id}: -{dropped} (old/non-English/no abstract), +{len(kept)} kept")
        all_papers.extend(kept)
        time.sleep(1.2)
    return all_papers

# ── Run search (Tier 1 + 2) ───────────────────────────────────────────────────

def run_search(topics, since):
    collected = []

    print("\n[Tier 1] Core topic search")
    for group, keywords in topics["tier1_core"].items():
        if group.startswith("_"):
            continue
        print(f"  {group}")
        for kw in keywords:
            papers = search_bulk(kw, since=since, max_results=10)
            collected.extend(normalize(p, tag=f"tier1:{group}") for p in papers)
            time.sleep(1.2)

    print("\n[Tier 2] Interdisciplinary crossover")
    for group, keywords in topics["tier2_interdisciplinary"].items():
        if group.startswith("_"):
            continue
        print(f"  {group}")
        for kw in keywords:
            papers = search_bulk(kw, since=since, max_results=5)
            collected.extend(normalize(p, tag=f"tier2:{group}") for p in papers)
            time.sleep(1.2)

    deduped = deduplicate(collected)
    print(f"\n[search] {len(collected)} raw → {len(deduped)} after dedup")
    return deduped

# ── Run authors (Tier 3 + 4) ──────────────────────────────────────────────────

def run_authors(topics, since):
    scholar_names = list(topics["tier3_ascor_scholars"]["scholars"])
    for group, names in topics.get("tier4_global_scholars", {}).items():
        if not group.startswith("_"):
            scholar_names.extend(names)
    scholar_names = list(dict.fromkeys(scholar_names))

    print(f"\n[Tier 3+4] Resolving {len(scholar_names)} scholar IDs...")
    name_to_id = resolve_author_ids(scholar_names)
    if not name_to_id:
        return []

    print(f"\n[Tier 3] Fetching recent papers for {len(name_to_id)} scholars...")
    raw_papers = get_papers_for_authors(list(name_to_id.values()), since=since)

    id_to_name = {v: k for k, v in name_to_id.items()}
    collected, journal_log = [], []
    for p in raw_papers:
        author_tag = "ascor"
        for a in p.get("authors", []):
            aid = a.get("authorId", "")
            if aid in id_to_name:
                author_tag = f"ascor:{id_to_name[aid]}"
                break
        norm = normalize(p, tag=author_tag)
        collected.append(norm)
        if norm["journal"]:
            journal_log.append(norm["journal"])

    deduped = deduplicate(collected)
    print(f"\n[scholars] {len(deduped)} papers after dedup")

    if journal_log:
        print("\n" + "=" * 52)
        print("Top 10 journals in scholar results")
        print("=" * 52)
        for j, n in Counter(journal_log).most_common(10):
            print(f"  {n:3d}  {j}")
        print("=" * 52)

    return deduped

# ── Run journals (Tier 5) via OpenAlex ───────────────────────────────────────

def _openalex_rebuild_abstract(inv):
    if not inv:
        return ""
    words = []
    for word, positions in inv.items():
        for pos in positions:
            words.append((pos, word))
    words.sort(key=lambda x: x[0])
    return " ".join(w for _, w in words)

def run_journals(since):
    journal_cfg = load_json(JOURNALS_PATH)
    collected = []
    print("\n[Tier 5] OpenAlex journal sweep")

    for group, journals in journal_cfg.items():
        if group.startswith("_"):
            continue
        print(f"  {group}")

        for item in journals:
            journal   = item["name"]
            source_id = item["id"]
            if not source_id:
                print(f"    {journal[:50]}: skipped (no id)")
                continue

            all_results, page = [], 1
            while True:
                params = {
                    "filter":   f"primary_location.source.id:{source_id},from_publication_date:{since},type:article",
                    "per-page": 100,
                    "page":     page,
                    "select":   "title,authorships,publication_date,publication_year,doi,abstract_inverted_index,primary_location,open_access,id",
                }
                try:
                    r = requests.get("https://api.openalex.org/works", params=params, timeout=20)
                except requests.RequestException as e:
                    print(f"    {journal[:50]}: network error {e}")
                    break
                if r.status_code != 200:
                    print(f"    {journal[:50]}: HTTP {r.status_code}")
                    break

                data    = r.json()
                results = data.get("results", [])
                if not results:
                    break

                for p in results:
                    authors = []
                    for a in p.get("authorships", []):
                        name = (a.get("author") or {}).get("display_name", "")
                        if name:
                            authors.append({"name": name})

                    doi = p.get("doi", "") or ""
                    if doi.startswith("https://doi.org/"):
                        doi = doi[len("https://doi.org/"):]

                    loc     = p.get("primary_location") or {}
                    src     = loc.get("source") or {}
                    landing = loc.get("landing_page_url", "") or ""
                    oa      = p.get("open_access") or {}
                    pdf     = oa.get("oa_url", "") or ""
                    pub_date = p.get("publication_date", "") or ""

                    if pub_date and pub_date < since:
                        continue

                    paper = {
                        "title":           p.get("title", "") or "Untitled",
                        "authors":         authors,
                        "year":            str(p.get("publication_year", "") or ""),
                        "publicationDate": pub_date,
                        "abstract":        _openalex_rebuild_abstract(p.get("abstract_inverted_index")),
                        "venue":           src.get("display_name", "") or journal,
                        "externalIds":     {"DOI": doi},
                        "doi":             doi,
                        "url":             landing or pdf or p.get("id", ""),
                        "openAccessPdf":   {"url": pdf} if pdf else None,
                    }
                    all_results.append(paper)

                print(f"    {journal[:50]}: page {page}, kept={len(all_results)}")
                if len(results) < 100:
                    break
                page += 1
                time.sleep(0.8)

            print(f"    {journal[:50]}: {len(all_results)} total")
            collected.extend(normalize(p, tag=f"tier5:{group}") for p in all_results)
            time.sleep(0.5)

    deduped = deduplicate(collected)
    print(f"\n[journals] {len(deduped)} papers after dedup")
    return deduped

# ── Flexible mode pipeline ───────────────────────────────────────────────────

def run_keywords_flexible(keywords, since, max_per_keyword=20):
    """Search each keyword independently and return deduplicated normalized papers."""
    collected = []
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        print(f"  keyword: {kw}")
        papers = search_bulk(kw, since=since, max_results=max_per_keyword)
        collected.extend(normalize(p, tag="flex:keyword") for p in papers)
        time.sleep(1.2)
    deduped = deduplicate(collected)
    print(f"\n[flex:keywords] {len(deduped)} papers after dedup")
    return deduped


def run_authors_flexible(author_names, since, papers_per_author=15):
    """Resolve author names/IDs to S2 IDs and fetch their recent papers.

    Numeric entries are treated as Semantic Scholar Author IDs and used directly;
    non-numeric entries are resolved by name search first.
    """
    entries = [n.strip() for n in author_names if n.strip()]
    if not entries:
        return []

    direct_ids, names_to_resolve = [], []
    for entry in entries:
        if entry.isdigit():
            direct_ids.append(entry)
            print(f"    [ID] {entry} (direct)")
        else:
            names_to_resolve.append(entry)

    resolved_ids = list(direct_ids)
    if names_to_resolve:
        print(f"\n[flex:scholars] Resolving {len(names_to_resolve)} scholar name(s)…")
        name_to_id = resolve_author_ids(names_to_resolve)
        resolved_ids.extend(name_to_id.values())

    if not resolved_ids:
        return []
    print(f"\n[flex:scholars] Fetching papers for {len(resolved_ids)} scholar(s)…")
    raw = get_papers_for_authors(resolved_ids, since=since,
                                  papers_per_author=papers_per_author)
    deduped = deduplicate([normalize(p, tag="flex:scholar") for p in raw])
    print(f"\n[flex:scholars] {len(deduped)} papers after dedup")
    return deduped


def _openalex_source_id_by_name(journal_name):
    """Return the short OpenAlex source ID (e.g. 'S123456789') for a journal name.

    Fetches up to 5 candidates and picks the one with the highest works_count so
    that common abbreviations or variant names resolve to the canonical source.
    """
    url    = "https://api.openalex.org/sources"
    params = {"search": journal_name, "select": "id,display_name,works_count", "per-page": 5}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            hits = r.json().get("results", [])
            if hits:
                best = max(hits, key=lambda h: h.get("works_count") or 0)
                return best["id"].split("/")[-1]
    except Exception as e:
        print(f"    [openalex] error resolving '{journal_name}': {e}")
    return None


def _fetch_openalex_by_source_id(journal_name, source_id, since, tag="flex:journal", keyword=None):
    """Paginate OpenAlex works for a given source ID and return normalized papers."""
    all_results, page = [], 1
    while True:
        params = {
            "filter":   f"primary_location.source.id:{source_id},from_publication_date:{since},type:article",
            "per-page": 100,
            "page":     page,
            "select":   "title,authorships,publication_date,publication_year,doi,"
                        "abstract_inverted_index,primary_location,open_access,id",
        }
        if keyword:
            params["search"] = keyword
        try:
            r = requests.get("https://api.openalex.org/works", params=params, timeout=20)
        except requests.RequestException as e:
            print(f"    [openalex] network error: {e}")
            break
        if r.status_code == 429:
            print("    [rate limit] pausing...")
            time.sleep(10)
            try:
                r = requests.get("https://api.openalex.org/works", params=params, timeout=20)
            except requests.RequestException as e:
                print(f"    [openalex] network error: {e}")
                break
            if r.status_code != 200:
                break
        elif r.status_code != 200:
            break
        data    = r.json()
        results = data.get("results", [])
        if not results:
            break
        for p in results:
            authors  = [{"name": (a.get("author") or {}).get("display_name", "")}
                        for a in p.get("authorships", [])
                        if (a.get("author") or {}).get("display_name")]
            doi      = (p.get("doi", "") or "")
            if doi.startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/"):]
            loc      = p.get("primary_location") or {}
            src      = loc.get("source") or {}
            landing  = loc.get("landing_page_url", "") or ""
            oa       = p.get("open_access") or {}
            pdf      = oa.get("oa_url", "") or ""
            pub_date = p.get("publication_date", "") or ""
            if pub_date and pub_date < since:
                continue
            all_results.append({
                "title":           p.get("title", "") or "Untitled",
                "authors":         authors,
                "year":            str(p.get("publication_year", "") or ""),
                "publicationDate": pub_date,
                "abstract":        _openalex_rebuild_abstract(p.get("abstract_inverted_index")),
                "venue":           src.get("display_name", "") or journal_name,
                "externalIds":     {"DOI": doi},
                "doi":             doi,
                "url":             landing or pdf or p.get("id", ""),
                "openAccessPdf":   {"url": pdf} if pdf else None,
            })
        if len(results) < 100:
            break
        page += 1
        time.sleep(0.8)
    return [normalize(p, tag=tag) for p in all_results]


def run_journals_flexible(journal_names, since, keywords=None):
    """Sweep journals supplied by name or OpenAlex Source ID (e.g. S12345678).

    Entries matching the pattern S\\d+ are used as Source IDs directly, skipping
    the name-lookup step.  All other entries are resolved by name.

    If keywords are provided, one API call is made per journal × keyword combination
    and results are deduplicated.  Without keywords, all recent articles are fetched.
    """
    collected = []
    kw_list   = keywords if keywords else [None]
    print("\n[flex:journals] OpenAlex sweep")
    for entry in journal_names:
        entry = entry.strip()
        if not entry:
            continue
        if re.match(r'^S\d+$', entry):
            source_id = entry
            label     = entry
        else:
            label     = entry
            source_id = _openalex_source_id_by_name(entry)
            if not source_id:
                print(f"    {entry[:50]}: not found in OpenAlex — skipping")
                continue

        journal_papers = []
        for kw in kw_list:
            papers = _fetch_openalex_by_source_id(label, source_id, since, tag="flex:journal", keyword=kw)
            journal_papers.extend(papers)
            time.sleep(1)

        journal_papers = deduplicate(journal_papers)
        kw_note = f" across {len(kw_list)} keyword{'s' if len(kw_list) != 1 else ''}" if keywords else ""
        print(f"    {label[:50]}: {len(journal_papers)} papers found{kw_note}")
        collected.extend(journal_papers)

    deduped = deduplicate(collected)
    print(f"\n[flex:journals] {len(deduped)} papers after dedup")
    return deduped


# ── Tier helpers ──────────────────────────────────────────────────────────────

def _get_tier(tag):
    if tag.startswith("tier1"): return "tier1"
    if tag.startswith("tier2"): return "tier2"
    if tag.startswith("ascor"): return "tier3"
    if tag.startswith("tier5"): return "tier5"
    return "tier1"

def _get_topic_key(tag):
    if tag.startswith("ascor"): return "tier3:ascor"
    return ":".join(tag.split(":")[:2]) if ":" in tag else tag

# ── Claude relevance scoring ──────────────────────────────────────────────────

def score_papers(papers, research_focus, min_score=0, api_key="", batch_size=10):
    """Score papers for relevance using Claude API; filter to >= min_score if min_score > 0.

    Papers are scored in tiered priority order: tier1 → scholars → journals → crossover.
    Each tier is capped at 100 papers; total hard cap is 400.
    """
    try:
        import anthropic
    except ImportError:
        print("[relevance] 'anthropic' not installed — pip install anthropic")
        return papers

    GROUP_CAP = 100
    TOTAL_CAP = 400

    def _tag_in(p, *fragments):
        tag = p.get("tag", "")
        return any(f in tag for f in fragments)

    # "keyword" covers flex:keyword (Mode 2 direct keyword search → same priority as tier1)
    g_tier1     = [p for p in papers if _tag_in(p, "tier1", "core", "keyword")][:GROUP_CAP]
    g_scholars  = [p for p in papers if _tag_in(p, "scholar", "ascor")
                   and not _tag_in(p, "tier1", "core", "keyword")][:GROUP_CAP]
    g_journals  = [p for p in papers if _tag_in(p, "journal", "tier5")
                   and not _tag_in(p, "tier1", "core", "keyword")
                   and not _tag_in(p, "scholar", "ascor")][:GROUP_CAP]
    g_crossover = [p for p in papers if _tag_in(p, "crossover", "tier2")
                   and not _tag_in(p, "tier1", "core", "keyword")
                   and not _tag_in(p, "scholar", "ascor")
                   and not _tag_in(p, "journal", "tier5")][:GROUP_CAP]

    matched   = set(id(p) for p in g_tier1 + g_scholars + g_journals + g_crossover)
    g_other   = [p for p in papers if id(p) not in matched][:GROUP_CAP]

    selected = (g_tier1 + g_scholars + g_journals + g_crossover + g_other)[:TOTAL_CAP]
    n1, n2, n3, n4, n5 = (len(g_tier1), len(g_scholars), len(g_journals),
                           len(g_crossover), len(g_other))

    print(f"\n[relevance] {len(selected)} papers queued for scoring "
          f"(tier1: {n1}, scholars: {n2}, journals: {n3}, crossover: {n4}, other: {n5})")

    client    = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    n_batches = (len(selected) + batch_size - 1) // batch_size
    print(f"[relevance] scoring in {n_batches} batch(es)...")

    system_block = {
        "type": "text",
        "text": (
            "You are a research assistant scoring academic papers for relevance.\n\n"
            f"Research focus: {research_focus}\n\n"
            "For each paper in the JSON array provided, return a JSON array where each element has:\n"
            '  "index": integer (0-based, matching input)\n'
            '  "score": integer 0-10 (0=irrelevant, 10=highly relevant)\n'
            '  "reason": one sentence explaining the score\n\n'
            "Respond with only the JSON array, no other text."
        ),
        "cache_control": {"type": "ephemeral"},
    }

    scored = []
    for i in range(0, len(selected), batch_size):
        batch   = selected[i : i + batch_size]
        payload = [
            {"index": j, "title": p["title"], "abstract": (p["abstract"] or "")[:800]}
            for j, p in enumerate(batch)
        ]
        try:
            resp    = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=[system_block],
                messages=[{"role": "user", "content": json.dumps(payload)}],
            )
            entries = json.loads(resp.content[0].text)
        except Exception as e:
            print(f"  [relevance] batch {i // batch_size + 1} error: {e} — defaulting to score 5")
            entries = [{"index": j, "score": 5, "reason": "scoring error"} for j in range(len(batch))]

        for entry in entries:
            idx = entry.get("index", 0)
            if 0 <= idx < len(batch):
                batch[idx]["relevance_score"]  = entry.get("score", 5)
                batch[idx]["relevance_reason"] = entry.get("reason", "")

        for p in batch:
            if "relevance_score" not in p:
                p["relevance_score"]  = 5
                p["relevance_reason"] = "not scored"

        above = sum(1 for p in batch if p.get("relevance_score", 0) >= min_score)
        print(f"  batch {i // batch_size + 1}/{n_batches}: {len(batch)} scored, {above} >= {min_score}")
        scored.extend(batch)
        time.sleep(0.3)

    if min_score > 0:
        before = len(scored)
        scored = [p for p in scored if p.get("relevance_score", 0) >= min_score]
        print(f"[relevance] {before} → {len(scored)} after min_score={min_score} filter")

    print(f"[scoring] {len(scored)} papers scored "
          f"(tier1: {n1}, scholars: {n2}, journals: {n3}, crossover: {n4}, other: {n5})")

    return scored

# ── Citation network (OpenAlex) ───────────────────────────────────────────────

def _oa_normalize_work(w):
    """Extract {title, doi, year, authors} from an OpenAlex work object."""
    doi = (w.get("doi") or "")
    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]
    authors = [
        (a.get("author") or {}).get("display_name", "")
        for a in (w.get("authorships") or [])[:3]
        if (a.get("author") or {}).get("display_name")
    ]
    return {
        "title":   w.get("title") or "Unknown",
        "doi":     doi,
        "year":    str(w.get("publication_year", "") or ""),
        "authors": authors,
    }


def fetch_openalex_network(doi, ref_limit=40, cit_limit=20):
    """Return citation network for a DOI via OpenAlex.

    Returns a dict with keys:
        center      – {title, doi, year}
        references  – list of {title, doi, year, authors}
        citations   – list of {title, doi, year, authors}
    Returns None if the DOI is missing or OpenAlex returns no data.
    """
    if not doi:
        return None

    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    print(f"[openalex network] GET {url}")
    try:
        r = requests.get(url, timeout=15)
    except requests.RequestException as e:
        print(f"[openalex network] request error: {e}")
        return None

    print(f"[openalex network] status: {r.status_code}")
    if r.status_code != 200:
        return None

    work = r.json()
    if not work.get("id"):
        return None

    center       = _oa_normalize_work(work)
    ref_ids_full = work.get("referenced_works") or []
    cited_by_url = work.get("cited_by_api_url")  # may be None

    def _resolve_ids(ids_full, limit, label):
        """Batch-fetch OpenAlex works by ID in groups of 20."""
        results = []
        short_ids = [rid.rsplit("/", 1)[-1] for rid in ids_full[:limit]]
        for i in range(0, len(short_ids), 20):
            batch = short_ids[i:i + 20]
            try:
                rr = requests.get(
                    "https://api.openalex.org/works",
                    params={
                        "filter":   f"openalex:{'|'.join(batch)}",
                        "per-page": 20,
                        "select":   "id,title,doi,publication_year,authorships",
                    },
                    timeout=20,
                )
                if rr.status_code == 200:
                    results.extend(_oa_normalize_work(w) for w in rr.json().get("results", []))
                else:
                    print(f"[openalex network] {label} batch HTTP {rr.status_code}")
            except requests.RequestException as e:
                print(f"[openalex network] {label} batch error: {e}")
        return results

    references = _resolve_ids(ref_ids_full, ref_limit, "refs")

    # ── Citing works ──────────────────────────────────────────────────────────
    citations = []
    if cited_by_url:
        try:
            cr = requests.get(
                cited_by_url,
                params={
                    "per-page": cit_limit,
                    "select":   "id,title,doi,publication_year,authorships",
                },
                timeout=20,
            )
            if cr.status_code == 200:
                citations = [_oa_normalize_work(w) for w in cr.json().get("results", [])]
            else:
                print(f"[openalex network] citations HTTP {cr.status_code}")
        except requests.RequestException as e:
            print(f"[openalex network] citations error: {e}")
    else:
        print("[openalex network] cited_by_api_url is None — skipping citations")

    return {"center": center, "references": references, "citations": citations}


# ── Save to Zotero ────────────────────────────────────────────────────────────

def save_to_zotero(papers, config, dry_run=False):
    if dry_run:
        print(f"\n[dry-run] Zotero: {len(papers)} papers (not saved)")
        return
    try:
        from pyzotero import zotero
    except ImportError:
        print("[ERROR] pip install pyzotero")
        return

    cfg       = config.get("zotero", {})
    zot       = zotero.Zotero(cfg["library_id"], cfg.get("library_type", "user"), cfg["api_key"])
    coll_keys = cfg.get("collection_keys", {})

    topic_groups: dict = {}
    for p in papers:
        topic_groups.setdefault(_get_topic_key(p["tag"]), []).append(p)

    total = 0
    for topic, ps in sorted(topic_groups.items()):
        coll  = coll_keys.get(topic, "")
        items = []
        for p in ps:
            item = zot.item_template("journalArticle")
            item["title"]            = p["title"]
            item["abstractNote"]     = p["abstract"]
            item["publicationTitle"] = p["journal"]
            item["date"]             = p["pub_date"] or p["year"]
            item["DOI"]              = p["doi"]
            item["url"]              = p["url"]
            score_note = (
                f"\nrelevance: {p['relevance_score']}/10 — {p.get('relevance_reason', '')}"
                if p.get("relevance_score") is not None else ""
            )
            item["extra"]            = f"source_tag: {p['tag']}{score_note}"
            item["creators"]         = [
                {"creatorType": "author", "firstName": "", "lastName": n}
                for n in p["authors"]
            ]
            if coll:
                item["collections"] = [coll]
            items.append(item)
        for i in range(0, len(items), 50):
            zot.create_items(items[i:i+50])
        total += len(items)
        print(f"[Zotero] {topic}: {len(items)} papers → {'collection ' + coll if coll else 'root library'}")
    print(f"[Zotero] saved {total} papers total")

# ── Save to Notion ────────────────────────────────────────────────────────────

def save_to_notion(papers, config, dry_run=False):
    if dry_run:
        print(f"\n[dry-run] Notion: {len(papers)} papers (not saved)")
        return
    try:
        from notion_client import Client
    except ImportError:
        print("[ERROR] pip install notion-client")
        return

    cfg    = config.get("notion", {})
    notion = Client(auth=cfg["token"])
    db_id  = cfg["database_id"]
    print(f"[Notion] saving to db: {db_id}")
    saved = skipped = 0

    for p in papers:
        authors_str = "; ".join(str(a) for a in p.get("authors", []))[:2000]
        tier      = _get_tier(p["tag"])
        score_tag = f" | relevance:{p['relevance_score']}/10" if p.get("relevance_score") is not None else ""
        props = {
            "Title":    {"title":     [{"text": {"content": (p.get("title") or "")[:2000]}}]},
            "Authors":  {"rich_text": [{"text": {"content": authors_str}}]},
            "Year":     {"rich_text": [{"text": {"content": str(p.get("year") or "")}}]},
            "Journal":  {"rich_text": [{"text": {"content": (p.get("journal") or "")[:500]}}]},
            "DOI":      {"rich_text": [{"text": {"content": (p.get("doi") or "")[:500]}}]},
            "Abstract": {"rich_text": [{"text": {"content": (p.get("abstract") or "")[:2000]}}]},
            "Source":   {"rich_text": [{"text": {"content": (p.get("tag", "") + score_tag)[:500]}}]},
            "Tier":     {"select":    {"name": tier}},
        }
        url = p.get("url", "")
        if url:
            props["URL"] = {"url": url}
        try:
            result = notion.pages.create(parent={"database_id": db_id}, properties=props)
            saved += 1
            print(f"  [✓] {p['title'][:60]} → {result.get('id', '')}")
            time.sleep(0.35)
        except Exception as e:
            print(f"  [✗] {type(e).__name__}: {e}")
            skipped += 1

    print(f"[Notion] saved {saved}, skipped {skipped}")

# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Wise Waffle — academic literature tracker")
    p.add_argument("--mode",        "-m", choices=["search", "authors", "journals", "all"], default="all")
    p.add_argument("--target",      "-t", choices=["zotero", "notion", "both"], default="both")
    p.add_argument("--dry-run",     action="store_true", help="preview only, don't save")
    p.add_argument("--clear-cache", action="store_true", help="clear cache and re-fetch everything")
    p.add_argument("--min-score",   type=int, default=0, metavar="N",
                   help="only save papers with Claude relevance score >= N (0-10, default: 0 = no filter)")
    return p.parse_args()

def main():
    global S2_HEADERS
    args   = parse_args()
    config = load_json(CONFIG_PATH)
    topics = load_json(TOPICS_PATH)

    if args.clear_cache:
        clear_cache()

    s2_key = config.get("semantic_scholar", {}).get("api_key", "")
    if s2_key:
        S2_HEADERS = {"x-api-key": s2_key}
        print("[API] Semantic Scholar key loaded ✓")
    else:
        print("[API] no key found, using anonymous access (stricter rate limits)")

    research_focus = config.get("research_focus", "").strip()
    anthropic_key  = config.get("anthropic", {}).get("api_key", "")
    if research_focus:
        preview = research_focus[:80] + ("..." if len(research_focus) > 80 else "")
        print(f"[API] research_focus: {preview}")

    since = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    print(f"[config] search range: {since} → today")
    print("━" * 60)

    step       = 0
    cache      = load_cache()
    all_papers = []

    # ── Fetch ─────────────────────────────────────────────────────────────────

    if args.mode in ("search", "all"):
        step += 1
        _log_step(step, "Keyword search (Tier 1 + 2)")
        if "search" in cache:
            print(f"  [cache] {len(cache['search'])} results loaded")
            all_papers.extend(cache["search"])
        else:
            papers = run_search(topics, since)
            cache["search"] = papers
            save_cache(cache)
            all_papers.extend(papers)
        print(f"  → {len(all_papers)} papers total so far")

    if args.mode in ("authors", "all"):
        step += 1
        _log_step(step, "Scholar tracking (Tier 3 + 4)")
        if "authors" in cache:
            print(f"  [cache] {len(cache['authors'])} results loaded")
            all_papers.extend(cache["authors"])
        else:
            papers = run_authors(topics, since)
            cache["authors"] = papers
            save_cache(cache)
            all_papers.extend(papers)
        print(f"  → {len(all_papers)} papers total so far")

    if args.mode in ("journals", "all"):
        step += 1
        _log_step(step, "Journal sweep (Tier 5 — OpenAlex)")
        if "journals" in cache:
            print(f"  [cache] {len(cache['journals'])} results loaded")
            all_papers.extend(cache["journals"])
        else:
            papers = run_journals(since)
            cache["journals"] = papers
            save_cache(cache)
            all_papers.extend(papers)
        print(f"  → {len(all_papers)} papers total so far")

    # ── Filter ────────────────────────────────────────────────────────────────

    if args.mode == "all":
        step += 1
        before     = len(all_papers)
        all_papers = deduplicate(all_papers)
        _log_step(step, "Cross-tier deduplication", len(all_papers),
                  f"removed {before - len(all_papers)} duplicates")

    step += 1
    before     = len(all_papers)
    all_papers = filter_new(all_papers)
    _log_step(step, "Filter already-saved papers", len(all_papers),
              f"removed {before - len(all_papers)}")

    if not all_papers:
        print("\nNothing new. Done.")
        return

    if research_focus:
        step += 1
        _log_step(step, f"Relevance scoring with Claude (min_score={args.min_score})")
        all_papers = score_papers(
            all_papers, research_focus,
            min_score=args.min_score,
            api_key=anthropic_key,
        )
        print(f"  → {len(all_papers)} papers after scoring")
        if not all_papers:
            print("\nAll papers filtered by relevance threshold. Done.")
            return
    elif args.min_score > 0:
        print(f"\n[relevance] --min-score={args.min_score} ignored — no research_focus configured")

    # ── Save ──────────────────────────────────────────────────────────────────

    step += 1
    _log_step(step, f"Save to {args.target}", len(all_papers))
    print("━" * 60)

    if args.target in ("zotero", "both"):
        save_to_zotero(all_papers, config, dry_run=args.dry_run)
    if args.target in ("notion", "both"):
        save_to_notion(all_papers, config, dry_run=args.dry_run)
    if not args.dry_run:
        record_saved(all_papers)
        clear_cache()
    print("\nDone.")

if __name__ == "__main__":
    main()
