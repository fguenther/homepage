#!/usr/bin/env python3
"""Helper for maintaining data/publications.yaml (used by the add-publication skill).

    pub_tool.py fetch <doi>                 print a draft entry (YAML) from Crossref / DataCite
    pub_tool.py find <doi | title words>    show existing entries that match
    pub_tool.py add <entry.yaml>            insert a new entry at its proper place
    pub_tool.py update <id> <entry.yaml>    merge fields into an existing entry (null deletes a field)
                                            and move it if its status/year changed
    pub_tool.py show <id>                   print one entry
    pub_tool.py format                      rewrite the file in canonical formatting (no reordering)

Entries are grouped in the file as: accepted, preprints, then published by year (newest first);
inside a group, new entries are inserted alphabetically by first author.
"""
from __future__ import annotations

import difflib
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PUBS = ROOT / "data" / "publications.yaml"
KEY_ORDER = ["id", "status", "type", "year", "authors", "title", "venue", "editors", "edition", "volume", "issue", "pages", "publisher",
             "doi", "url", "pdf", "data", "extra_links", "notes", "featured", "abstract"]
USER_AGENT = "homepage-publication-tool/1.0 (static site maintenance script)"
STOPWORDS = {"a", "an", "the", "on", "of", "in", "and", "for", "to", "from", "with", "is", "are", "do", "does", "how", "what", "why"}


# --------------------------------------------------------------------------- YAML I/O

class _Dumper(yaml.SafeDumper):
    pass


def _str_repr(dumper, value):
    if "\n" in value:  # multi-line text (abstracts) as a readable block
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_Dumper.add_representer(str, _str_repr)


def canonical(entry: dict) -> dict:
    ordered = {k: entry[k] for k in KEY_ORDER if k in entry and entry[k] not in (None, "", [])}
    ordered.update({k: v for k, v in entry.items() if k not in ordered and v not in (None, "", [])})
    return ordered


def dump_entries(entries: list[dict]) -> str:
    chunks = []
    for e in entries:
        text = yaml.dump([canonical(e)], Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10_000,
                         default_flow_style=False)
        chunks.append(text)
    return "\n".join(chunks)


def load() -> list[dict]:
    with PUBS.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def save(entries: list[dict]) -> None:
    header = ""
    text = PUBS.read_text(encoding="utf-8")
    m = re.match(r"((?:#.*\n|\s*\n)+)", text)  # keep a leading comment block
    if m:
        header = m.group(1).rstrip() + "\n\n"
    PUBS.write_text(header + dump_entries(entries), encoding="utf-8")


# --------------------------------------------------------------------------- matching & ordering

def fold(s: str) -> str:
    s = str(s)
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        s = s.replace(a, b)  # so that "Günther" and "Guenther" match
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def norm_doi(doi) -> str:
    return re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", str(doi or "").strip(), flags=re.I).lower()


def find(entries: list[dict], query: str) -> list[tuple[float, dict]]:
    q = query.strip()
    if re.match(r"^(https?://)?(dx\.)?(doi\.org/)?10\.\d{4,9}/", q, re.I):
        d = norm_doi(q)
        hits = [e for e in entries if norm_doi(e.get("doi")) == d or d in str(e.get("url", "")).lower()]
        return [(1.0, e) for e in hits]
    fq = fold(q)
    scored = []
    for e in entries:
        ft = fold(e.get("title", ""))
        score = difflib.SequenceMatcher(None, fq, ft).ratio()
        if fq and fq in ft:
            score = max(score, 0.9)
        if score >= 0.55:
            scored.append((score, e))
    return sorted(scored, key=lambda t: -t[0])[:8]


def group_rank(e: dict) -> tuple:
    status = e.get("status")
    if status == "accepted":
        return (0, 0)
    if status == "preprint":
        return (1, 0)
    return (2, -int(e.get("year") or 0))


def author_key(e: dict) -> str:
    authors = e.get("authors") or [""]
    return fold(authors[0]) + " " + fold(e.get("title", ""))


def insert_position(entries: list[dict], new: dict) -> int:
    g = group_rank(new)
    for i, e in enumerate(entries):
        eg = group_rank(e)
        if eg > g:
            return i
        if eg == g and author_key(e) > author_key(new):
            return i
    return len(entries)


def make_id(entry: dict, entries: list[dict]) -> str:
    first = (entry.get("authors") or ["anon"])[0].split(",")[0]
    first = fold(first.replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss")).replace(" ", "")
    words = [w for w in fold(entry.get("title", "")).split() if w not in STOPWORDS]
    year = entry.get("year") or "accepted"
    base = f"{first}{year}{words[0] if words else ''}"
    taken = {e.get("id") for e in entries}
    candidate, n = base, 2
    while candidate in taken:
        candidate = f"{base}{chr(ord('a') + n - 2)}"
        n += 1
    return candidate


# --------------------------------------------------------------------------- metadata lookup

def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def initials(given: str) -> str:
    out = []
    for part in given.split():
        sub = [s for s in part.split("-") if s]
        out.append("-".join(f"{s[0]}." for s in sub))
    return " ".join(out)


def clean(s) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", "", str(s or "")))
    return re.sub(r"\s+", " ", s).strip()


def from_crossref(doi: str) -> dict | None:
    try:
        m = http_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")["message"]
    except Exception:
        return None
    authors = []
    for a in m.get("author", []):
        if a.get("family"):
            authors.append(f"{clean(a['family'])}, {initials(clean(a.get('given', '')))}".rstrip(", "))
        elif a.get("name"):
            authors.append(clean(a["name"]))
    date = (m.get("published-print") or m.get("published-online") or m.get("issued") or {}).get("date-parts", [[None]])[0]
    ctype = m.get("type", "")
    entry = {
        "status": "preprint" if ctype == "posted-content" else "published",
        "year": date[0] if date and date[0] else None,
        "authors": authors,
        "title": clean((m.get("title") or [""])[0]) + (": " + clean(m["subtitle"][0]) if m.get("subtitle") else ""),
        "venue": clean((m.get("container-title") or [""])[0]) or (clean(m.get("institution", [{}])[0].get("name")) if m.get("institution") else None),
        "volume": m.get("volume"),
        "issue": m.get("issue"),
        "pages": (m.get("page") or m.get("article-number") or "").replace("-", "–") or None,
        "publisher": m.get("publisher") if ctype in ("book-chapter", "book") else None,
        "doi": m.get("DOI", doi),
        "type": {"proceedings-article": "proceedings", "book-chapter": "chapter"}.get(ctype),
    }
    if ctype == "posted-content" and not entry["venue"]:
        entry["venue"] = f"{m.get('publisher', 'Preprint')} preprint"
    return entry


def from_datacite(doi: str) -> dict | None:
    try:
        a = http_json(f"https://api.datacite.org/dois/{urllib.parse.quote(doi)}")["data"]["attributes"]
    except Exception:
        return None
    authors = []
    for c in a.get("creators", []):
        if c.get("familyName"):
            authors.append(f"{clean(c['familyName'])}, {initials(clean(c.get('givenName', '')))}".rstrip(", "))
        else:
            authors.append(clean(c.get("name")))
    publisher = a.get("publisher")
    publisher = publisher.get("name") if isinstance(publisher, dict) else publisher
    is_preprint = (a.get("types", {}).get("resourceTypeGeneral") in ("Preprint", "Text")) or "arxiv" in doi.lower()
    return {
        "status": "preprint" if is_preprint else "published",
        "year": a.get("publicationYear"),
        "authors": authors,
        "title": clean((a.get("titles") or [{}])[0].get("title")),
        "venue": f"{publisher} preprint" if is_preprint and publisher else publisher,
        "doi": a.get("doi", doi),
    }


def from_osf(doi: str) -> dict | None:
    """PsyArXiv & other OSF preprints (Crossref often lags behind for new versions)."""
    m = re.search(r"osf\.io/([a-z0-9]+(?:_v\d+)?)$", doi, re.I)
    if not m:
        return None
    try:
        d = http_json(f"https://api.osf.io/v2/preprints/{m.group(1)}/?embed=contributors&embed=provider")["data"]
    except Exception:
        return None
    authors = []
    contributors = sorted(d["embeds"]["contributors"]["data"], key=lambda c: c["attributes"].get("index", 0))
    for c in contributors:
        if not c["attributes"].get("bibliographic", True):
            continue
        u = c["embeds"]["users"]["data"]["attributes"]
        given = " ".join(x for x in (u.get("given_name"), u.get("middle_names")) if x)
        authors.append(f"{clean(u.get('family_name'))}, {initials(clean(given))}".rstrip(", "))
    provider = d["embeds"]["provider"]["data"]["attributes"]["name"]
    return {
        "status": "preprint",
        "year": int(d["attributes"]["date_published"][:4]),
        "authors": authors,
        "title": clean(d["attributes"]["title"]),
        "venue": f"{provider} preprint",
        "doi": doi,
    }


def shorten_authors(authors: list[str], self_author: str = "Günther, F.") -> list[str]:
    """Very long author lists: first 6, '…', self, '…', last — like the old site did."""
    if len(authors) <= 20:
        return authors
    out = authors[:6]
    me = next((i for i, a in enumerate(authors) if a.startswith(self_author)), None)
    if me is not None and me >= 6 and me < len(authors) - 1:
        out += ["…", authors[me]]
    out += ["…", authors[-1]]
    return out


def harmonise_authors(authors: list[str], entries: list[dict]) -> list[str]:
    """Reuse the spelling already used in the file for a co-author (e.g. compound surnames)."""
    known = {}
    for e in entries:
        for a in e.get("authors") or []:
            a = re.sub(r"\*+$", "", str(a)).strip()
            if ", " in a:
                sur, given = a.split(", ", 1)
                known.setdefault((fold(sur), given[:1]), a)
    out = []
    for a in authors:
        if ", " not in a:
            out.append(a)
            continue
        sur, given = a.split(", ", 1)
        key = (fold(sur), given[:1])
        match = known.get(key)
        if not match:  # "Tomás, C. M." -> "Martinez-Tomás, C."
            cands = [v for (s, g), v in known.items() if g == given[:1] and s.endswith(" " + fold(sur))]
            match = cands[0] if len(cands) == 1 else None
        if match and match != a:
            print(f"note: author '{a}' -> '{match}' (spelling used elsewhere in the file)", file=sys.stderr)
        out.append(match or a)
    return out


def fetch(doi: str) -> dict:
    raw = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)
    entry = from_crossref(raw) or from_datacite(raw) or from_osf(raw)
    if not entry:
        sys.exit(f"No metadata found for DOI {raw} (Crossref, DataCite, OSF).")
    entry["doi"] = raw
    if PUBS.exists():
        entry["authors"] = harmonise_authors(entry["authors"], load())
    entry["authors"] = shorten_authors(entry["authors"])
    return canonical(entry)


# --------------------------------------------------------------------------- commands

def read_entry(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, list):
        if len(data) != 1:
            sys.exit("entry file must contain exactly one entry")
        data = data[0]
    return data


def cmd_add(path: str) -> None:
    entries = load()
    new = read_entry(path)
    for key in ("status", "authors", "title"):
        if not new.get(key):
            sys.exit(f"entry is missing '{key}'")
    if new.get("doi"):
        dup = find(entries, new["doi"])
        if dup:
            sys.exit(f"DOI already present in entry '{dup[0][1]['id']}' — use update instead.")
    if new["status"] == "accepted":
        new.pop("year", None)  # accepted entries are shown as "(accepted)"
    new["id"] = new.get("id") or make_id(new, entries)
    if any(e.get("id") == new["id"] for e in entries):
        sys.exit(f"id '{new['id']}' already exists")
    pos = insert_position(entries, new)
    entries.insert(pos, new)
    save(entries)
    print(f"Added '{new['id']}' at position {pos}.")


def cmd_update(entry_id: str, path: str) -> None:
    entries = load()
    idx = next((i for i, e in enumerate(entries) if e.get("id") == entry_id), None)
    if idx is None:
        sys.exit(f"no entry with id '{entry_id}'")
    old = entries.pop(idx)
    changes = read_entry(path)
    merged = dict(old)
    for k, v in changes.items():
        if v is None:
            merged.pop(k, None)
        else:
            merged[k] = v
    if merged.get("status") == "accepted":
        merged.pop("year", None)
    moved = group_rank(old) != group_rank(merged)
    pos = insert_position(entries, merged) if moved else idx
    entries.insert(pos, merged)
    save(entries)
    print(f"Updated '{entry_id}'" + (f" and moved it to position {pos}." if moved else " in place."))


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "fetch" and len(args) == 1:
        print(dump_entries([fetch(args[0])]))
    elif cmd == "find" and args:
        hits = find(load(), " ".join(args))
        if not hits:
            print("No matching entries.")
        for score, e in hits:
            print(f"{score:.2f}  {e.get('id')}  [{e.get('status')} {e.get('year', '')}]  {e.get('title')}")
    elif cmd == "show" and len(args) == 1:
        e = next((e for e in load() if e.get("id") == args[0]), None)
        print(dump_entries([e]) if e else f"no entry with id '{args[0]}'")
    elif cmd == "add" and len(args) == 1:
        cmd_add(args[0])
    elif cmd == "update" and len(args) == 2:
        cmd_update(args[0], args[1])
    elif cmd == "format" and not args:
        save(load())
        print("Reformatted.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
