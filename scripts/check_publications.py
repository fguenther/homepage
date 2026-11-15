#!/usr/bin/env python3
"""Sanity checks for data/publications.yaml (and the imported content pages).

    python scripts/check_publications.py [--expected N]

Exits non-zero on errors. Warnings are printed but do not fail the run.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATUSES = {"accepted", "preprint", "published"}
TYPES = {"chapter", "proceedings"}
FIELDS = {"id", "status", "type", "year", "authors", "title", "venue", "editors", "edition",
          "volume", "issue", "pages", "publisher", "doi", "url", "pdf", "data", "extra_links",
          "notes", "abstract"}
AUTHOR_RE = re.compile(r"^[^,]+, [A-ZÀ-ÖØ-Þ][a-zà-ÿ]?\.(?:[ -][A-ZÀ-ÖØ-Þ][a-zà-ÿ]?\.)*\**$|^…$")
URL_RE = re.compile(r"^(https?://\S+|/\S*)$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", type=int, help="publication count on the live page")
    ap.add_argument("--file", default=str(ROOT / "data" / "publications.yaml"))
    a = ap.parse_args()

    pubs = yaml.safe_load(Path(a.file).read_text(encoding="utf-8"))
    errors, warnings = [], []
    err = lambda i, m: errors.append(f"[{i}] {m}")
    warn = lambda i, m: warnings.append(f"[{i}] {m}")

    ids, dois = {}, {}
    last_rank = (-1, -10**9)
    for n, p in enumerate(pubs):
        pid = p.get("id", f"#{n}")
        for k in p:
            if k not in FIELDS:
                err(pid, f"unknown field {k!r}")
        for k in ("id", "status", "title", "venue", "authors"):
            if not p.get(k):
                err(pid, f"missing {k}")
        if p.get("status") not in STATUSES:
            err(pid, f"bad status {p.get('status')!r}")
        if p.get("status") in ("published", "preprint") and not isinstance(p.get("year"), int):
            err(pid, "published/preprint entry without integer year")
        if p.get("status") == "accepted" and "year" in p:
            warn(pid, "accepted entry has a year")
        if "type" in p and p["type"] not in TYPES:
            err(pid, f"bad type {p['type']!r}")
        authors = p.get("authors") or []
        if not isinstance(authors, list):
            err(pid, "authors is not a list")
            authors = []
        for au in authors:
            if not AUTHOR_RE.match(au):
                err(pid, f"author not in 'Last, F. M.' form: {au!r}")
        if not any(au.startswith("Günther, F.") for au in authors):
            warn(pid, "Günther, F. not among the authors")
        if "*" in "".join(authors) and not p.get("notes"):
            err(pid, "equal-contribution marker without notes")
        if pid in ids:
            err(pid, f"duplicate id (also entry {ids[pid]})")
        ids[pid] = n
        if not re.fullmatch(r"[a-z]+\d{4}[a-z0-9]+", pid):
            err(pid, "id does not look like <author><year><word>")
        doi = p.get("doi")
        if doi:
            if not DOI_RE.match(doi):
                err(pid, f"malformed doi {doi!r}")
            if doi.lower() in dois:
                err(pid, f"duplicate doi {doi} (also {dois[doi.lower()]})")
            dois[doi.lower()] = pid
        for k in ("url", "pdf", "data"):
            if k in p and not URL_RE.match(p[k]):
                err(pid, f"{k} is not a URL: {p[k]!r}")
            if k in p and ("%20" in p[k] or p[k].count("http") > 1):
                warn(pid, f"{k} looks broken: {p[k]}")
        for x in p.get("extra_links", []):
            if set(x) != {"label", "url"} or not URL_RE.match(x["url"]):
                err(pid, f"bad extra_link {x!r}")
        if not p.get("url"):
            warn(pid, "no main url")
        # ordering: accepted < preprint < published by year desc
        rank = ({"accepted": 0, "preprint": 1, "published": 2}.get(p.get("status"), 3),
                -(p.get("year") or 0) if p.get("status") == "published" else 0)
        if rank < last_rank:
            err(pid, "out of order (accepted, preprints, then published by year desc)")
        last_rank = rank

    # content pages
    pages = ["home", "cv", "publications", "data", "software-resources", "r_packages",
             "semantic_spaces", "vispa", "video_tutorials", "centroid-analysis", "psychoembeddings",
             "the-flickr-frequency-norms", "english_st", "german_st",
             "vision-based-semantic-transparency-measures-for-english-compounds",
             "taboo-language-database", "media-coverage", "profiles", "contact"]
    for slug in pages:
        f = ROOT / "content" / f"{slug}.md"
        if not f.exists():
            err(slug, "content page missing")
            continue
        txt = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
        fm = yaml.safe_load(m.group(1)) if m else None
        if not fm or "title" not in fm or "nav_order" not in fm:
            err(slug, "front matter lacks title/nav_order")

    if a.expected is not None and len(pubs) != a.expected:
        errors.append(f"count {len(pubs)} != expected {a.expected}")

    by_status = {s: sum(p.get("status") == s for p in pubs) for s in STATUSES}
    print(f"{len(pubs)} publications ({by_status}); {len(dois)} DOIs; "
          f"{sum('abstract' in p for p in pubs)} abstracts; {len(pages)} content pages checked")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
