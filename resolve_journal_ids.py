"""
resolve_journal_ids.py
Fills in openalex_id for each entry in journals_ranked.json by querying the
OpenAlex /sources endpoint. Safe to re-run — already-resolved entries are skipped.
"""

import json
import time
from pathlib import Path

import requests

JOURNALS_PATH = Path(__file__).parent / "journals_ranked.json"
OA_HEADERS    = {"User-Agent": "mailto:jiayi.yan0124@gmail.com"}


def resolve(name):
    url = "https://api.openalex.org/sources"
    params = {"search": name, "per-page": 1, "select": "id,display_name,works_count"}
    try:
        r = requests.get(url, params=params, headers=OA_HEADERS, timeout=10)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                return results[0]["id"].rsplit("/", 1)[-1]
    except requests.RequestException as e:
        print(f"  [network error] {e}")
    return None


def main():
    with open(JOURNALS_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)

    resolved = skipped = failed = 0

    for entry in entries:
        if entry.get("openalex_id"):
            skipped += 1
            continue
        oa_id = resolve(entry["name"])
        if oa_id:
            entry["openalex_id"] = oa_id
            print(f"  ✓  {entry['name'][:55]:<55} → {oa_id}")
            resolved += 1
        else:
            print(f"  ✗  {entry['name'][:55]:<55}   not found")
            failed += 1
        time.sleep(0.3)

    with open(JOURNALS_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Resolved: {resolved}  |  Failed: {failed}  |  Already had ID: {skipped}")


if __name__ == "__main__":
    main()
