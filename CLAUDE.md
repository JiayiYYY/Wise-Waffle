# Wise Waffle — CLAUDE.md

Academic literature tracker. Fetches papers from Semantic Scholar and OpenAlex, scores them with Claude, saves to Zotero and/or Notion.

Run with: `py -m streamlit run app.py`

---

## Files

```
app.py               Streamlit UI — landing page, Mode 1, Mode 2, paper cards, citation panel
paper_fetcher.py     All backend logic — fetch, filter, score, save
topics.json          Keywords and tracked scholars (tier1–tier4)
journals.json        Journal list with OpenAlex source IDs (tier5)
config.json          API keys — not in git
saved_dois.json      Deduplication history — auto-generated
cache.json           Crash recovery — auto-generated
```

---

## Architecture

### Pipeline (paper_fetcher.py)

| Function | What it does |
|---|---|
| `run_search(topics, since)` | Tier 1+2: keyword search via S2 bulk search |
| `run_authors(topics, since)` | Tier 3+4: fetch recent papers from tracked scholars |
| `run_journals(since)` | Tier 5: sweep journals via OpenAlex by source ID |
| `run_keywords_flexible` | Mode 2: keyword search, arbitrary terms |
| `run_authors_flexible` | Mode 2: scholar lookup — accepts numeric S2 Author IDs or names |
| `run_journals_flexible` | Mode 2: journal sweep — accepts OpenAlex Source IDs (S\d+) or names |
| `normalize(paper, tag)` | Normalises S2 or OpenAlex paper dicts to a common schema |
| `score_papers(...)` | Claude relevance scoring in batches of 10 |
| `fetch_openalex_network(doi)` | Citation panel data — references + citing works via OpenAlex |
| `save_to_zotero` / `save_to_notion` | Save normalised papers to Zotero or Notion |

### Normalized paper schema

```python
{
  "title", "authors", "year", "pub_date", "abstract",
  "journal", "doi", "url", "tag",
  # tag format: "tier1:group", "tier2:group", "tier3:ascor", "tier5:group", "flex:keyword", etc.
}
```

### Abstract fallback

`normalize()` checks if abstract is empty. If so, and DOI is present, it calls:
`https://api.openalex.org/works/https://doi.org/{doi}?select=abstract_inverted_index`
and reconstructs the abstract via `_openalex_rebuild_abstract()`. Adds 0.5s delay.
Note: Taylor & Francis and other restrictive publishers often have null abstract in OpenAlex too.

### Flexible author input (Mode 2)

`run_authors_flexible` accepts either:
- Numeric string → treated as S2 Author ID, used directly
- Name string → resolved via S2 author search

### Flexible journal input (Mode 2)

`run_journals_flexible` accepts either:
- `S\d+` pattern → OpenAlex Source ID, skip name lookup
- Anything else → name-based lookup via OpenAlex `/sources`

---

## UI (app.py)

### Views
- **Landing page** (`render_landing`) — "What is this?" expander + Mode 1 / Mode 2 cards
- **Mode 1** (`render_mode1`) — preset pipeline with sidebar config
- **Mode 2** (`render_mode2`) — freeform search inputs

### Key components
- `render_paper_card(p)` — paper card HTML + Abstract expander (abstract first, relevance reason below)
- `render_results(...)` — filter/sort UI, paginated paper list, save buttons
- `_render_network(p)` — citation panel: References and Cited By tables from OpenAlex

### Citation panel (`_render_network`)

Uses OpenAlex, not Semantic Scholar. Called per-paper when user clicks "🔗 Citation Network".
- Fetches via `pf.fetch_openalex_network(doi)`
- References: batch-fetched in groups of 20 using `filter=openalex:W1|W2|...`
- Cited by: from `cited_by_api_url` field (may be None for recent papers)
- Results shown as `st.dataframe` with `LinkColumn` DOI links
- Cached in `st.session_state["network_cache"]` keyed by paper DOI/title

### Secrets (Streamlit Cloud)

Mode 1 "Fill my credentials" button reads from `st.secrets["host"]`:
```toml
[host]
s2_key = "..."
zotero_id = "..."
zotero_key = "..."
notion_tok = "..."
notion_db = "..."
anthropic_key = "..."

[host_collections]
"tier1:ai_fairness_decolonial" = "XXXXXXXX"
# etc.
```
Mode 2 has the same fill button reading from `[host]` (no collection keys).

---

## API keys

| Key | Used for | Required |
|---|---|---|
| Semantic Scholar | All paper search | Yes |
| Anthropic | Claude relevance scoring | Optional |
| Zotero library ID + API key | Save to Zotero | Optional |
| Notion token + database ID | Save to Notion | Optional |

Scoring uses `claude-opus-4-7`. System prompt is cached (`cache_control: ephemeral`).

---

## Search tiers

| Tier | Source | Notes |
|---|---|---|
| 1 | S2 bulk search | Core keywords, 10 results/keyword |
| 2 | S2 bulk search | Crossover keywords, 5 results/keyword |
| 3+4 | S2 author papers | Tracked scholars; resolves names to IDs first |
| 5 | OpenAlex | Full journal sweep by source ID, no keyword filter |

Results are deduplicated across tiers by DOI (fallback: title).

---

## Known limitations

- Taylor & Francis and some other publishers don't expose abstracts via S2, OpenAlex, or Crossref for recent papers. The OpenAlex fallback in `normalize()` handles some cases but not all.
- `cited_by_api_url` is `None` for papers too new to have been cited yet (normal for 2025–2026 papers).
- S2 recommendations endpoint returns 404 for papers without enough citation graph data — Related Papers section was removed for this reason.
