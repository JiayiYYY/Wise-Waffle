# Wise Waffle

Academic literature tracker for researchers. Fetches new papers from Semantic Scholar and OpenAlex, scores them for relevance using Claude, and saves them to Zotero and/or Notion.

---

## Pipeline

**Fetch** → Semantic Scholar (keyword search + scholar tracking) and OpenAlex (journal sweep)  
**Filter** → drops non-English papers, papers without abstracts, and anything already saved  
**Score** → Claude rates each paper 0–10 for relevance to your research focus  
**Save** → sends results to Zotero (sorted by topic collection) and/or Notion

---

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Get API keys**

| Key | Where | Required? |
|-----|-------|-----------|
| Semantic Scholar | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) | Yes |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | For relevance scoring |
| Zotero | [zotero.org/settings/security](https://www.zotero.org/settings/security) — Library ID + API key | Optional |
| Notion | [notion.so/my-integrations](https://notion.so/my-integrations) — Integration token + Database ID | Optional |

**3. Run and configure**

```bash
py -m streamlit run app.py
```

Enter your API keys and research focus in the sidebar. The Anthropic key and research focus are saved to `config.json` automatically when you run the app.

**4. Notion database (optional)**

Create a database with these columns: Title (Title), Authors, Year, Journal, DOI, Abstract (Text), URL (URL), Source (Text), Tier (Select). Then connect your integration via `...` → Connections.

**5. Zotero collections (optional)**

Create a collection per topic and enter the 8-character collection keys from the collection URL in the sidebar. Leave blank to save to root library.

---

## Run

**Web interface**

```bash
py -m streamlit run app.py
```

Fill in your keys, pick a mode, and hit Run. Preview results before saving anything.

**Terminal**

```bash
py paper_fetcher.py --mode all --target both   # full run, save to both
py paper_fetcher.py --mode all --dry-run        # preview without saving
py paper_fetcher.py --mode search               # keywords only
py paper_fetcher.py --mode authors              # scholar tracking only
py paper_fetcher.py --mode journals             # journal sweep only
py paper_fetcher.py --clear-cache               # clear cache after a crashed run
```

---

## Search tiers

| Tier | Source | What it does |
|------|--------|-------------|
| Core (1) | Semantic Scholar | Keyword search by topic |
| Crossover (2) | Semantic Scholar | Interdisciplinary searches, smaller result cap |
| Scholars (3–4) | Semantic Scholar | Recent papers from tracked researchers |
| Journals (5) | OpenAlex | Full sweep of followed journals, no keyword filter |

Results are deduplicated across tiers. Customise keywords and tracked scholars in `topics.json`; journal list is in `journals.json`.

---

## Relevance scoring

Set a **Research Focus** in the sidebar and enter your **Anthropic API key**. Each paper is scored 0–10 by Claude before saving, with a one-sentence reason. Scores are stored in Zotero's Extra field and Notion's Source field. Skip scoring by leaving the research focus blank.

---

## Files

```
app.py               # Streamlit interface
paper_fetcher.py     # Core logic — search, filter, score, save
topics.json          # Keywords and tracked scholars
journals.json        # Journal list with OpenAlex IDs
config.json          # API keys — add to .gitignore
saved_dois.json      # Deduplication history (auto-generated)
cache.json           # Crash recovery (auto-generated)
```

Add to `.gitignore`:

```
config.json
saved_dois.json
cache.json
```
