# 🧇 Wise Waffle

An academic literature tracker built for (communication science) researchers. It pulls new papers from Semantic Scholar and OpenAlex, tracks what your favourite scholars are publishing, goes through journals you follow, and saves everything to Zotero and/or Notion automatically. You can also choose to manually select the articles you want to save - or just view, no save.

There's a [Streamlit web interface](http://wise-waffle.streamlit.app/) for easier use, or you can run it straight from the terminal.

---

## What you can do with this

Every time you run it, Wise Waffle:

1. Searches _Semantic Scholar_ using your keywords, organised by research topic
2. Checks what your tracked scholars have published recently
3. Sweeps through specific journals via _OpenAlex_ and pulls all recent articles
4. Filters out non-English papers and papers without abstracts
5. Skips anything you've already saved before
6. Saves new papers to Zotero (sorted into collections by topic) and/or Notion

---

## Setup

**1. Install dependencies**

```bash
pip install requests pyzotero notion-client streamlit langdetect
```

**2. Set up your config**

The app reads API keys directly from the Streamlit sidebar — you don't need to edit any files. If you're running from the terminal, create a `config.json`:

```json
{
  "semantic_scholar": { "api_key": "your_key_here" },
  "zotero": {
    "library_id": "your_library_id",
    "api_key": "your_api_key",
    "library_type": "user"
  },
  "notion": {
    "token": "your_token",
    "database_id": "your_database_id"
  }
}
```

Get your keys here:
- **Semantic Scholar** — [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)
- **Zotero** — [zotero.org/settings/security](https://www.zotero.org/settings/security)
- **Notion** — [notion.so/my-integrations](https://notion.so/my-integrations)
  A Semantic Scholar key is mandatory to get it running, Zotero &/ Notion is optional.

**3. Set up your Notion database (optional)**

Create a database with these columns:

| Column | Type |
|--------|------|
| Title | Title |
| Authors | Text |
| Year | Text |
| Journal | Text |
| DOI | Text |
| Abstract | Text |
| URL | URL |
| Source | Text |
| Tier | Select |

Then open the database, click `...` → Connections → add your integration.

**4. Zotero collections (optional)**

Create a collection in Zotero for each topic, then enter the 8-character collection keys in the Streamlit sidebar under "Zotero Collection Keys". You can find the key in the collection's URL on zotero.org. If you leave them blank, everything goes to your *root* library.

---

## Running it

**Web interface (recommended)**

```bash
py -m streamlit run app.py
```

Fill in your API keys in the sidebar, pick a mode, hit Run. You can preview results before saving anything.

**Terminal**

```bash
# Full run — keywords + scholars + journals, save to both
py paper_fetcher.py --mode all --target both

# Preview without saving
py paper_fetcher.py --mode all --dry-run

# Keywords only
py paper_fetcher.py --mode search

# Scholar tracking only
py paper_fetcher.py --mode authors

# Journal sweep only
py paper_fetcher.py --mode journals

# Clear the cache if a run crashed halfway
py paper_fetcher.py --clear-cache
```

---

## How the search tiers work

| Tier | What it does |
|------|-------------|
| **Tier 1 — Core** | Keyword search across your main research topics. Uses Semantic Scholar's full query syntax including phrases, OR, wildcards. |
| **Tier 2 — Crossover** | Interdisciplinary searches with a smaller result cap per keyword, to avoid flooding. |
| **Tier 3 & 4 — Scholars** | Tracks recent publications from specific researchers you follow. Looks them up by name on Semantic Scholar. |
| **Tier 5 — Journals** | Full table-of-contents sweep via OpenAlex. No keyword filter — every recent article from journals you care about. |

Results are deduplicated across tiers, and anything you've already saved is filtered out automatically.

---

## Customising your search

Everything lives in `topics.json`. The structure is:

- **`tier1_core`** — keyword lists per topic. Supports `"phrases"`, `|` for OR, `*` for prefix matching, `(grouping)`.
- **`tier2_interdisciplinary`** — same format, smaller result limit per keyword.
- **`tier3_ascor_scholars`** — list of scholar names to track.
- **`tier4_global_scholars`** — same, grouped by research area.
- **`tier5_journals`** — not used for search (journals are defined in `journals.json`). You can still reference them here for display purposes.

Journal sources for Tier 5 are in `journals.json`, each with an OpenAlex source ID. The app uses these IDs to pull directly from each journal.

---

## Files

```
wise-waffle/
├── app.py               # Streamlit web interface
├── paper_fetcher.py     # Core logic — search, filter, save
├── topics.json          # Keywords and scholars
├── journals.json        # Journal list with OpenAlex IDs
├── requirements.txt     # Python dependencies
├── config.json          # Your API keys — don't commit this
├── saved_dois.json      # Auto-generated: deduplication history
└── cache.json           # Auto-generated: crash recovery cache
```

Add these to your `.gitignore`:

```
config.json
saved_dois.json
cache.json
```

---

## A few things to know

- A full run across all tiers takes 20–40 minutes depending on your Semantic Scholar API rate limit.
- If a run crashes halfway, just run again — `cache.json` saves progress so it picks up where it left off.
- `saved_dois.json` is your deduplication history. Reset it from the sidebar if you want to re-fetch everything.
- Tier 5 uses OpenAlex, which has better journal coverage and doesn't require an API key.
- On Streamlit Cloud, `saved_dois.json` is read-only between sessions. Use the "Reset history" button in the sidebar to clear it.

---

## Built with

- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [OpenAlex API](https://openalex.org)
- [pyzotero](https://github.com/urschrei/pyzotero)
- [notion-client](https://github.com/ramnes/notion-sdk-py)
- [Streamlit](https://streamlit.io)
