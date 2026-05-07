import json
with open('../_data/synergie/database.json') as f:
    works = json.load(f)

names = set()
for w in works:
    for a in w.get('authors', []):
        family = a.get('family', '')
        given = a.get('given', '')
        full = f"{given} {family}".strip()
        if 'iusti' in full.lower():
            names.add((given, family))
for g, f in sorted(names):
    print(f"given: {g!r:30} family: {f!r}")
