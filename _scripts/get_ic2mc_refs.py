#!/usr/bin/env python

import requests
import time
import json
import csv
from pathlib import Path

# =========================
# CONFIG
# =========================
home = Path.home()
GV_KEY = home / ".scopus_api_key"
API_KEY = GV_KEY.read_text().strip()

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"

CROSSREF_URL = "https://api.crossref.org/works/{}"
OPENALEX_URL = "https://api.openalex.org/works/doi:{}"

HEADERS = {
    "X-ELS-APIKey": API_KEY,
    "Accept": "application/json"
}

# folder containing this file
p = Path(__file__).parent
OUTPUT_DIR = p.parent / "_data"

QUERY = """
(
  (
    AFFIL(("iC2MC" OR "Complex Matrices Molecular Characterization") AND (Harfleur OR 76700))
  )
  OR
  (
    (AU-ID(55708480000) AND AU-ID(6602179193))
    OR (AU-ID(55708480000) AND AU-ID(35555917300))
    OR (AU-ID(55708480000) AND AU-ID(55454150300))
    OR (AU-ID(6602179193) AND AU-ID(35555917300))
    OR (AU-ID(6602179193) AND AU-ID(55454150300))
    OR (AU-ID(35555917300) AND AU-ID(55454150300))
  )
)
AND PUBYEAR > 2013
"""


# =========================
# 1. SCOPUS SEARCH
# =========================

def get_scopus_records(count: int = 25):
    """Fetch paginated Scopus search results and normalize core metadata.

    Args:
        count: Number of records requested per API page.

    Returns:
        A list of dictionaries containing Scopus identifiers and basic
        bibliographic fields (title, DOI, year, journal, pages, volume, number).
    """
    records = []
    start = 0

    while True:
        params = {
            "query": QUERY,
            "count": count,
            "start": start,
        }

        r = requests.get(SCOPUS_SEARCH_URL, headers=HEADERS, params=params)
        # r.raise_for_status()
        data = r.json()

        entries = data.get("search-results", {}).get("entry", [])
        if not entries:
            break

        for e in entries:
            records.append({
                "eid": e.get("eid"),
                "title": e.get("dc:title", "Untitled"),
                "doi": e.get("prism:doi", ""),
                "year": (e.get("prism:coverDate") or "0000")[:4],
                "journal": e.get("prism:publicationName", "Unknown Journal"),
                "pages": e.get("prism:pageRange", None),
                "volume": e.get("prism:volume", None),
                "number": e.get("prism:number", None),
            })

        start += count
        time.sleep(0.5)

    return records

def get_scopus_eids(count: int = 25):
    """Fetch paginated Scopus search results and return only EIDs.
    That could be used in combination with SCOPUS ABSTRACT_URL to get 
    metadata for each record separately. But fetch from scopus abstract
    needs specific access rights.

    Args:
        count: Number of records requested per API page.

    Returns:
        A list of Scopus EID strings.
    """
    start = 0

    eids = list()
    while True:
        params = {
            "query": QUERY,
            "count": count,
            "start": start,
        }

        r = requests.get(SCOPUS_SEARCH_URL, headers=HEADERS, params=params)
        data = r.json()

        entries = data.get("search-results", {}).get("entry", [])
        if not entries:
            break

        for e in entries:
            if "eid" in e:
                eids.append(e.get("eid"))

        start += count
        time.sleep(0.5)

    return eids



# =========================
# 3. CROSSREF
# =========================

def enrich_crossref(doi):
    """Enrich a record with metadata from Crossref using its DOI.

    Args:
        doi: DOI string used to query Crossref.

    Returns:
        A dictionary with publisher, journal, publication type, and authors.
        Returns an empty dict when DOI is missing, request fails, or data is
        unavailable.
    """
    if not doi:
        return {}

    try:
        url = f"{CROSSREF_URL}{doi}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {}

        msg = r.json().get("message", {})
        authors = []
        for a in msg.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = {"given": given, "family": family}
            if given or family:
                authors.append(name)

        return {
            "publisher": msg.get("publisher"),
            "journal": (msg.get("container-title") or ["Unknown Journal"])[0],
            "type": msg.get("type"),
            "authors": authors,
        }

    except Exception:
        return {}


# =========================
# 4. OPENALEX
# =========================

def enrich_openalex(doi):
    """Enrich a record with citation and topical data from OpenAlex.

    Args:
        doi: DOI string used to query OpenAlex.

    Returns:
        A dictionary containing citation count, top concepts, open-access flag,
        and top topics. Returns an empty dict when DOI is missing, request
        fails, or data is unavailable.
    """
    if not doi:
        return {}

    try:
        url = f"{OPENALEX_URL}{doi}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {}

        data = r.json()

        return {
            "cited_by_count": data.get("cited_by_count"),
            "concepts": [
                {"name": c["display_name"], "score": c["score"]}
                for c in data.get("concepts", [])[:8]  # top 8
            ],
            "open_access": data.get("open_access", {}).get("is_oa"),
            "topics": [
                t["display_name"]
                for t in data.get("topics", [])[:3]
            ]
        }

    except Exception:
        return {}


# =========================
# 5. PIPELINE
# =========================

def build_database():
    """Build the final publication dataset by merging multiple sources.

    The function starts from Scopus records, enriches each item with Crossref
    and OpenAlex data, and returns a merged list ready for export.

    Returns:
        A list of merged publication dictionaries.
    """
    scopus_records = get_scopus_records()
    # eids = get_scopus_eids()

    enriched = []

    print("Number of Scopus records:", len(scopus_records))
    step = max(1, len(scopus_records) // 10)
    for i, record in enumerate(scopus_records):
        if i % step == 0:
            print(f"{(i + 1 )/ len(scopus_records) * 100:5.1f}% - Processing record {i + 1:4d}/{len(scopus_records)}")

        # item = get_scopus_metadata(eid)
        doi = record.get("doi")

        crossref = enrich_crossref(doi)
        openalex = enrich_openalex(doi)

        merged = {
            **record,
            **crossref,
            **openalex
        }

        enriched.append(merged)

        time.sleep(0.3)

    return enriched


# =========================
# 6. EXPORTS
# =========================

def export_json(data):
    """Write the aggregated dataset to a JSON file.

    Args:
        data: List of merged publication dictionaries.
    """
    with open(OUTPUT_DIR / "database.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def export_csv(data):
    """Write the aggregated dataset to CSV with flattened author values.

    Args:
        data: List of merged publication dictionaries.

    Notes:
        Author lists are converted to a single string using BibTeX-like
        separators (" and ").
    """
    rows = []
    for d in data:
        row = d.copy()
        authors = row.get("authors")

        if isinstance(authors, list):
            names = []
            for a in authors:
                if isinstance(a, dict):
                    family = (a.get("family") or "").strip()
                    given = (a.get("given") or "").strip()
                    name = f"{family}, {given}".strip(", ")
                    if name:
                        names.append(name)
                elif a is not None:
                    name = str(a).strip()
                    if name:
                        names.append(name)
            row["authors"] = " and ".join(names)
        elif authors is None:
            row["authors"] = ""
        elif not isinstance(authors, str):
            row["authors"] = str(authors)

        rows.append(row)

    keys = set().union(*(d.keys() for d in rows))

    with open(OUTPUT_DIR / "database.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(keys))
        writer.writeheader()
        writer.writerows(rows)


def export_bibtex(data):
    """Write the aggregated dataset to a BibTeX file.

    Args:
        data: List of merged publication dictionaries.

    Notes:
        Entries are exported as `@article` records with a generated key derived
        from DOI or title.
    """
    with open(OUTPUT_DIR / "database.bib", "w", encoding="utf-8") as f:
        for i, d in enumerate(data, start=1):
            key = (d.get("doi") or d.get("title") or f"article_{i}")[:20].replace("/", "_")
            authors = [f"{a['family']}, {a['given']}".strip() for a in d.get("authors", [])]
            authors = " and ".join(authors).strip()
            if len(authors) == 0:
                authors = "Unknown Author"

            fields = [
                ("title", d.get("title", "Untitled")),
                ("author", authors),
                ("journal", d.get("journal", "Unknown Journal")),
                ("year", d.get("year", "0000")),
                ("volume", d.get("volume")),
                ("pages", d.get("pages")),
                ("publisher", d.get("publisher")),
                ("number", d.get("number")),
                ("doi", d.get("doi")),
            ]

            lines = [f"@article{{{key},"]
            for name, value in fields:
                if value is None:
                    continue

                lines.append(f"  {name}={{ {value} }},")

            if len(lines) > 1:
                lines[-1] = lines[-1].rstrip(",")

            lines.append("}")
            bib = "\n".join(lines)
            f.write(bib + "\n\n")


# =========================
# MAIN
# =========================

def main():
    """Run the full pipeline: collect, enrich, and export publication data."""
    print("Building database...")

    data = build_database()

    print("Exporting...")
    print("Output directory:", OUTPUT_DIR.resolve())

    export_json(data)
    export_csv(data)
    export_bibtex(data)

    print("Done")
    print("Files: database.json / database.csv / database.bib")


if __name__ == "__main__":
    main()
