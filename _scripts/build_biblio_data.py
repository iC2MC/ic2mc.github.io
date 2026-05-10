#!/usr/bin/env python

import json
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations


ROOT_DIR = Path(__file__).parent.parent


NAME_ALIASES = {
    ("G.", "Salvato Vallverdu"):   ("Germain", "Salvato Vallverdu"),
    ("G.", "Vallverdu"):           ("Germain", "Salvato Vallverdu"),
    ("Germain", "Salvato Vallverdu"): ("Germain", "Salvato Vallverdu"),
    ("Germain", "Salvato-Vallverdu"): ("Germain", "Salvato Vallverdu"),
    ("Germain", "Vallverdu"):      ("Germain", "Salvato Vallverdu"),
    ("Germain Salvato", "Vallverdu"): ("Germain", "Salvato Vallverdu"),

    # Ruiz Encinar
    ("J", "Ruiz Encinar"):             ("Jorge", "Ruiz Encinar"),
    ("J.", "Ruiz Encinar"):            ("Jorge", "Ruiz Encinar"),
    ("J.", "Ruiz\u2005Encinar"):       ("Jorge", "Ruiz Encinar"),
    ("J. R.", "Encinar"):              ("Jorge", "Ruiz Encinar"),
    ("J. Ruiz", "Encinar"):            ("Jorge", "Ruiz Encinar"),
    ("J.R.", "Encinar"):               ("Jorge", "Ruiz Encinar"),
    ("Jorge", "Encinar"):              ("Jorge", "Ruiz Encinar"),
    ("Jorge", "Ruiz\u2005Encinar"):    ("Jorge", "Ruiz Encinar"),
    ("Jorge R.", "Encinar"):           ("Jorge", "Ruiz Encinar"),
    ("Jorge Ruiz", "Encinar"):         ("Jorge", "Ruiz Encinar"),

    # Bouyssiere
    ("B.", "Bouyssiere"):              ("Brice", "Bouyssiere"),
    ("Brice", "Bouyssière"):           ("Brice", "Bouyssiere"),

    # Rodgers
    ("R.P.", "Rodgers"):               ("Ryan P.", "Rodgers"),
    ("RP", "Rodgers"):                 ("Ryan P.", "Rodgers"),
    ("Ryan P", "Rodgers"):             ("Ryan P.", "Rodgers"),
    ("Ryan P.", "Rodgers"):            ("Ryan P.", "Rodgers"),

    # Afonso
    ("C", "Afonso"):                   ("Carlos", "Afonso"),
    ("C.", "Afonso"):                  ("Carlos", "Afonso"),
    ("Carlos", "Alfonso"):             ("Carlos", "Afonso"),

    # Giusti
    ("P.", "Giusti"):                  ("Pierre", "Giusti"),
    ("Pierre", "Giustie"):             ("Pierre", "Giusti"),
}

def normalize_author(given, family):
    return NAME_ALIASES.get((given, family), (given, family))

# with open(ROOT_DIR / "_data" / "database.json") as f:
#     works = json.load(f)
with open(ROOT_DIR / "_data" / "synergie" / "database.json") as f:
    works = json.load(f)

# Get publication per year
pub_by_year = Counter(w["year"] for w in works if w.get("year"))
pub_by_year = dict(sorted(pub_by_year.items()))

# Get citations per year
cit_by_year = defaultdict(int)
for w in works:
    if w.get("year") and w.get("cited_by_count"):
        cit_by_year[w["year"]] += w["cited_by_count"]
cit_by_year = dict(sorted(cit_by_year.items()))

# Top journals
journal_count = Counter(w["journal"] for w in works if w.get("journal"))
top_journals = dict(journal_count.most_common(20))

# weighted concepts
concept_scores = defaultdict(float)
for w in works:
    for c in w.get("concepts", []):
        if isinstance(c, dict):                # nouveau format avec score
            concept_scores[c["name"]] += c["score"]
        else:                                  # ancien format liste simple
            concept_scores[c] += 1.0

# Filter broad concepts
exclude = {"Chemistry", "Physics", "Biology", "Science", "Mathematics"}
concept_scores = {
    k: round(v, 3)
    for k, v in sorted(concept_scores.items(), key=lambda x: -x[1])
    if k not in exclude
}

# are publications open access?
oa_count = Counter(
    "Open Access" if w.get("open_access") else "Closed"
    for w in works
)

# Network of co-authors
# main_authors = {"Giusti", "Bouyssiere", "Rodgers", "Afonso", "Salvato Vallverdu"}
main_authors = {"Giusti", "Bouyssiere", "Rodgers", "Afonso", "Salvato Vallverdu", "Ruiz Encinar"}

coauthor_links = defaultdict(int)

# first pass to count publications per author
author_pub_count = Counter()
for w in works:
    for a in w.get("authors", []):
        given = a.get("given", "")
        family = a.get("family", "")
        _, norm_family = normalize_author(given, family)
        author_pub_count[norm_family] += 1

# build co-author links, but only between authors who have at least 3 publications
coauthor_links = defaultdict(int)
for w in works:
    authors = []
    for a in w.get("authors", []):
        given = a.get("given", "")
        family = a.get("family", "")
        _, norm_family = normalize_author(given, family)
        authors.append(norm_family)
    # Filtrer sur le compte final — ajustez le seuil selon la densité voulue
    filtered = [a for a in authors if author_pub_count[a] >= 3]
    for a1, a2 in combinations(filtered, 2):
        key = tuple(sorted([a1, a2]))
        coauthor_links[key] += 1

# Keep only links with at least 1 co-publication
coauthor_links = {
    f"{k[0]}|{k[1]}": v 
    for k, v in coauthor_links.items() 
    if v >= 1
}

# --- Export ---
output = {
    "publications_per_year": pub_by_year,
    "citations_per_year":    cit_by_year,
    "top_journals":          top_journals,
    "concepts":              concept_scores,
    "open_access":           dict(oa_count),
    "total":                 len(works),
    "coauthor_network": {
        "links": coauthor_links,
        "main_authors": list(main_authors),
        "author_pub_count": dict(author_pub_count.most_common(50))
    },
}

# with open(ROOT_DIR / "assets" / "data" / "biblio_stats.json", "w") as f:
#     json.dump(output, f, indent=2, ensure_ascii=False)
with open(ROOT_DIR / "_data" / "synergie" / "biblio_stats.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"✓ {len(works)} publications processed")
print(f"✓ Years: {list(pub_by_year.keys())}")
print(f"✓ Top journal: {next(iter(top_journals))}")


