#!/usr/bin/env python3
"""Build the homepage.

    content/*.md          one page per file (YAML front matter + Markdown)
    data/publications.yaml
    data/profile.yaml
    site.yaml             site-wide settings, home-page sections
    templates/, static/   design
        ->  site/         static HTML, ready for GitHub Pages

Usage:  python build.py [--out site] [--check]
        --check only validates the data and exits (no output written).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

ROOT = Path(__file__).resolve().parent
STATUSES = ("accepted", "preprint", "published")
STATUS_LABELS = {"accepted": "Accepted / in press", "preprint": "Preprints"}
FILTER_YEARS = 4  # publications page: one filter chip per recent year, the rest under "Earlier"
# data/profile.yaml `links:` keys -> button labels (unknown keys are shown as they are)
LINK_LABELS = {"scholar": "Google Scholar", "orcid": "ORCID", "researchgate": "ResearchGate", "gepris": "GEPRIS",
               "scopus": "Scopus", "hu": "HU Berlin", "github": "GitHub", "osf": "OSF", "bluesky": "Bluesky",
               "mastodon": "Mastodon", "linkedin": "LinkedIn", "x": "X", "twitter": "Twitter"}
PROFILE_LINK_ORDER = ["scholar", "orcid", "github", "osf", "researchgate", "gepris", "scopus", "hu"]
BIBTYPES = {"chapter": "incollection", "proceedings": "inproceedings", "book": "book"}
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


# --------------------------------------------------------------------------- helpers

def load_yaml(path: Path, default=None):
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return default if data is None else data


def norm_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = str(doi).strip()
    return re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi, flags=re.I)


def norm_links(links) -> list[dict]:
    """Accept {label: url} dicts or [{label, url}] lists; return [{label, url}]."""
    if not links:
        return []
    if isinstance(links, dict):
        return [{"key": k, "label": LINK_LABELS.get(k, k), "url": v} for k, v in links.items() if v]
    out = []
    for item in links:
        if isinstance(item, dict):
            label = item.get("label") or item.get("name") or item.get("title")
            url = item.get("url") or item.get("href")
            if label and url:
                out.append({"label": label, "url": url})
    return out


# --------------------------------------------------------------------------- pages

class Page:
    def __init__(self, path: Path, md: markdown.Markdown):
        text = path.read_text(encoding="utf-8")
        m = FRONT_MATTER.match(text)
        meta, body = (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, text)
        self.slug = meta.get("slug") or path.stem
        self.meta = meta
        self.title = meta.get("title") or self.slug.replace("-", " ").title()
        self.nav_title = meta.get("nav_title") or self.title
        self.nav_order = meta.get("nav_order")
        self.parent_slug = meta.get("parent")
        self.description = meta.get("description")
        self.summary = meta.get("summary")
        self.template = meta.get("template")
        self.is_home = self.slug in ("home", "index")
        md.reset()
        self.html = Markup(md.convert(body))
        self.parent: Page | None = None
        self.children: list[Page] = []
        if meta.get("permalink"):
            p = meta["permalink"].strip("/")
            self.url = "/" + p + "/" if p else "/"
        elif self.is_home:
            self.url = "/"
        else:
            self.url = None  # set once parents are known

    @property
    def out_file(self) -> Path:
        return Path(self.url.strip("/")) / "index.html" if self.url != "/" else Path("index.html")


def load_pages(content_dir: Path, errors: list[str]) -> dict[str, Page]:
    md = markdown.Markdown(extensions=["extra", "sane_lists", "toc"])
    pages: dict[str, Page] = {}
    for path in sorted(content_dir.glob("*.md")):
        page = Page(path, md)
        if page.slug in pages:
            errors.append(f"content: duplicate page slug '{page.slug}' ({path.name})")
        pages[page.slug] = page
    for page in pages.values():
        if page.parent_slug:
            parent = pages.get(page.parent_slug)
            if not parent:
                errors.append(f"content/{page.slug}.md: unknown parent '{page.parent_slug}'")
            else:
                page.parent = parent
                parent.children.append(page)
    for page in pages.values():
        if page.url is None:
            prefix = f"{page.parent.slug}/" if page.parent else ""
            page.url = f"/{prefix}{page.slug}/"
        # sub-pages: by the parent's `groups:` order (if the child has a `group:`), then nav_order, then title
        groups = page.meta.get("groups") or []
        for c in page.children:
            if groups and c.meta.get("group") not in groups:
                errors.append(f"content/{c.slug}.md: group must be one of {', '.join(groups)} (see {page.slug}.md)")
        page.children.sort(key=lambda p: (groups.index(p.meta["group"]) if p.meta.get("group") in groups else 99,
                                          p.nav_order is None, p.nav_order or 0, p.title.lower()))
    return pages


# --------------------------------------------------------------------------- publications

def format_authors(authors: list[str], self_author: str) -> Markup:
    parts = []
    for a in authors:
        a = str(a).strip()
        if a.startswith(self_author):
            parts.append(Markup("<b>{}</b>").format(a))
        else:
            parts.append(escape(a))
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return Markup("{}, &amp; {}").format(*parts)
    return Markup(", ").join(parts[:-1]) + Markup(", &amp; ") + parts[-1]


def format_venue(p: dict) -> Markup:
    venue = p.get("venue")
    if not venue:
        return Markup("")
    pages = str(p.get("pages") or "").replace("--", "–")
    if p.get("type") in ("chapter", "proceedings"):
        # APA: In A. Editor & B. Editor (Eds.), *Book title* (3rd ed., Vol. 13, pp. 1–5). Publisher.
        out = Markup("In ")
        if p.get("editors"):
            eds = str(p["editors"])
            plural = "&" in eds or "," in eds
            out += Markup("{} ({}), ").format(eds, "Eds." if plural else "Ed.")
        out += Markup("<em>{}</em>").format(venue)
        details = [str(p["edition"])] if p.get("edition") else []
        if p.get("volume"):
            details.append(f"Vol. {p['volume']}")
        if pages:
            details.append(f"pp. {pages}" if re.search(r"[–-]", pages) else f"p. {pages}")
        if details:
            out += Markup(" ({})").format(", ".join(details))
        if p.get("publisher"):
            out += Markup(". {}").format(p["publisher"])
        return out
    out = Markup("<em>{}</em>").format(venue)
    if p.get("volume"):
        out += Markup(", <em>{}</em>").format(p["volume"])
        if p.get("issue"):
            out += Markup("({})").format(p["issue"])
    if p.get("pages"):
        out += Markup(", {}").format(str(p["pages"]).replace("--", "–"))
    return out


def bib_escape(s) -> str:
    return re.sub(r"(?<!\\)([&%#_])", r"\\\1", str(s))


def make_bibtex(p: dict) -> str:
    status = p["status"]
    btype = BIBTYPES.get(p.get("type")) or ("misc" if status == "preprint" else "article")
    authors = [re.sub(r"\*+$", "", str(a)).strip() for a in p["authors"]]
    real = [a for a in authors if a.strip(" .…")]
    author_field = " and ".join(real) + (" and others" if len(real) < len(authors) else "")
    fields = [("author", author_field), ("title", "{" + bib_escape(p["title"]) + "}")]
    venue_key = {"article": "journal", "inproceedings": "booktitle", "incollection": "booktitle"}.get(btype, "howpublished")
    if p.get("venue"):
        fields.append((venue_key, bib_escape(p["venue"])))
    fields.append(("year", str(p["year"])) if p.get("year") else ("note", "Accepted"))
    if p.get("editors"):
        fields.append(("editor", bib_escape(re.sub(r",?\s*&\s*|,\s*", " and ", str(p["editors"])))))
    for key, bkey in (("volume", "volume"), ("issue", "number"), ("pages", "pages"), ("edition", "edition"),
                      ("publisher", "publisher")):
        if p.get(key):
            value = str(p[key])
            if key == "pages":
                value = re.sub(r"\s*[-–]+\s*", "--", value)
            fields.append((bkey, bib_escape(value)))
    if p.get("_doi"):
        fields.append(("doi", p["_doi"]))
    elif p.get("url"):
        fields.append(("url", p["url"]))
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields)
    return f"@{btype}{{{p['id']},\n{body}\n}}"


def load_publications(path: Path, self_author: str, topics: dict, errors: list[str],
                      warnings: list[str]) -> list[dict]:
    pubs = load_yaml(path, [])
    if not isinstance(pubs, list):
        errors.append(f"{path.name}: expected a list of publications")
        return []
    ids, dois = {}, {}
    for i, p in enumerate(pubs):
        where = f"{path.name}[{i}] ({p.get('id', '?')})"
        for key in ("id", "title", "authors", "status"):
            if not p.get(key):
                errors.append(f"{where}: missing '{key}'")
        if p.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {', '.join(STATUSES)}")
        if p.get("status") != "accepted" and not p.get("year"):
            errors.append(f"{where}: missing 'year'")
        if p.get("status") == "published" and not p.get("venue"):
            errors.append(f"{where}: published entries need a 'venue'")
        if not isinstance(p.get("authors", []), list):
            errors.append(f"{where}: 'authors' must be a list")
            p["authors"] = [str(p["authors"])]
        p_topics = p.get("topics") or []
        if not isinstance(p_topics, list):
            errors.append(f"{where}: 'topics' must be a list")
            p["topics"] = p_topics = []
        for t in p_topics:
            if t not in topics:
                errors.append(f"{where}: unknown topic '{t}' (allowed: {', '.join(topics)})")
        if topics and not p_topics:
            warnings.append(f"{where}: no 'topics' (it won't appear under any topic filter)")
        if p.get("id") in ids:
            errors.append(f"{where}: duplicate id (also entry {ids[p['id']]})")
        ids.setdefault(p.get("id"), i)
        for a in p.get("authors") or []:
            a = str(a).strip()
            if a.strip(" .…") and ", " not in a:
                warnings.append(f"{where}: author '{a}' doesn't look like 'Last, F.' (unquoted comma in YAML?)")
        doi = (norm_doi(p.get("doi")) or "").lower()
        if doi:
            if doi in dois:
                errors.append(f"{where}: duplicate DOI {doi} (also entry {dois[doi]})")
            dois.setdefault(doi, i)
    if errors:
        return pubs

    md_inline = markdown.Markdown(extensions=["extra"])
    years = sorted({int(p["year"]) for p in pubs if p["status"] == "published"}, reverse=True)
    recent_years = set(years[:FILTER_YEARS])
    for p in pubs:
        p["_doi"] = norm_doi(p.get("doi"))
        p["_authors"] = format_authors(p["authors"], self_author)
        p["_venue"] = format_venue(p)
        p["_year"] = "accepted" if p["status"] == "accepted" else str(p["year"])
        links = []
        main = p.get("url") or (f"https://doi.org/{p['_doi']}" if p["_doi"] else None)
        if main:
            links.append({"label": "Paper", "url": main})
        if p.get("pdf"):
            links.append({"label": "PDF", "url": p["pdf"]})
        if p.get("data"):
            links.append({"label": "Data & code", "url": p["data"]})
        links += norm_links(p.get("extra_links"))
        p["_links"] = links
        p["_bibtex"] = make_bibtex(p)
        p["_abstract"] = Markup(md_inline.reset().convert(str(p["abstract"]))) if p.get("abstract") else None
        if p["status"] == "published":
            tags = [str(p["year"]) if int(p["year"]) in recent_years else "earlier"]
        else:
            tags = [p["status"]]
        p["_tags"] = " ".join(tags)
        p["_topics"] = [{"key": t, "label": topics[t]} for t in topics if t in (p.get("topics") or [])]
    return pubs


def group_publications(pubs: list[dict]) -> list[dict]:
    groups = []
    for status in ("accepted", "preprint"):
        items = [p for p in pubs if p["status"] == status]
        if items:
            groups.append({"key": status, "label": STATUS_LABELS[status], "pubs": items})
    published = [p for p in pubs if p["status"] == "published"]
    for year in sorted({int(p["year"]) for p in published}, reverse=True):
        groups.append({"key": str(year), "label": str(year), "pubs": [p for p in published if int(p["year"]) == year]})
    return groups


def recent_publications(pubs: list[dict], n: int) -> list[dict]:
    featured = [p for p in pubs if p.get("featured")]
    if featured:
        return featured[:n]
    accepted = [p for p in pubs if p["status"] == "accepted"]
    published = sorted((p for p in pubs if p["status"] == "published"), key=lambda p: -int(p["year"]))
    return (accepted + published)[:n]


# --------------------------------------------------------------------------- co-author network

THEME_COLORS = ["#60a5fa", "#2dd4bf", "#fbbf24", "#c084fc"]   # home-page themes, in order (dark stage)
OTHER_COLOR = "#94a3b8"


def _fold(s: str) -> str:
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def _author_key(a: str) -> str | None:
    """'Marelli, M.' → 'marelli_m' (surname + first initial); None for '…' and malformed names."""
    a = str(a).strip().rstrip("*").strip()
    if "," not in a:
        return None
    last, first = a.split(",", 1)
    return f"{_fold(last)}_{_fold(first)[:1]}" if _fold(last) else None


def network_layout(n_nodes: int, me_lengths: list[float], pair_edges: list[list[int]], seed: int = 11) -> list[list[float]]:
    """Force layout for the co-author network, computed at build time (instant and stable in the browser).

    Node 0 is me, fixed at the centre; node i+1 is co-author i. Springs pull each co-author to its
    distance from the centre (closer = more joint papers) and pull co-authors of the same paper together;
    all nodes repel each other.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    n = n_nodes + 1
    ang = rng.uniform(0, 2 * np.pi, n)
    rad = np.array([0.0] + list(me_lengths))
    pos = np.stack([np.cos(ang) * rad, np.sin(ang) * rad], axis=1)
    src = [0] * n_nodes + [a + 1 for a, b, k in pair_edges]
    dst = list(range(1, n)) + [b + 1 for a, b, k in pair_edges]
    rest = np.array(list(me_lengths) + [55.0] * len(pair_edges))
    stiff = np.array([0.06] * n_nodes + [0.004 + 0.01 * min(k, 4) for a, b, k in pair_edges])
    src, dst = np.array(src), np.array(dst)
    step = 1.0
    for it in range(600):
        d = pos[:, None, :] - pos[None, :, :]
        dist2 = (d ** 2).sum(-1) + 1e-6
        np.fill_diagonal(dist2, np.inf)
        rep = (d / dist2[..., None] * 60000.0 / np.sqrt(dist2)[..., None]).sum(1)   # ~ 1/d²
        vec = pos[dst] - pos[src]
        length = np.sqrt((vec ** 2).sum(1)) + 1e-6
        f = (stiff * (length - rest))[:, None] * vec / length[:, None]
        spring = np.zeros_like(pos)
        np.add.at(spring, src, f)
        np.add.at(spring, dst, -f)
        move = (rep + spring) * step
        cap = 25.0 * step
        norm = np.sqrt((move ** 2).sum(1))[:, None]
        move = np.where(norm > cap, move / norm * cap, move)
        move[0] = 0.0
        pos += move
        r = np.sqrt((pos[1:] ** 2).sum(1))[:, None]          # keep a clear ring around the centre (its label)
        pos[1:] = np.where(r < 210, pos[1:] / np.maximum(r, 1e-6) * 210, pos[1:])
        step = max(0.05, step * 0.993)
    return [[round(float(x), 1), round(float(y), 1)] for x, y in pos]


R_IN, R_OUT = 210.0, 560.0     # network rings: most joint papers … one joint paper


def radial_positions(nodes: list[dict], force_pos: list[list[float]], radius) -> list[list[float]]:
    """Put every co-author on the ring for its number of joint papers, keeping the order around the
    circle from the force layout. One-paper co-authors are spread evenly over two staggered rings;
    the others are nudged apart along their ring until they don't overlap."""
    import math
    ang = [math.atan2(y, x) for x, y in force_pos]
    out: list[list[float]] = [[0.0, 0.0] for _ in nodes]
    ones = sorted((i for i, nd in enumerate(nodes) if nd["n"] == 1), key=lambda i: ang[i])
    for k, i in enumerate(ones):
        a = (ang[ones[0]] if ones else 0) + 2 * math.pi * k / len(ones)
        r = radius(1) + (0 if k % 2 else 34)
        out[i] = [r * math.cos(a), r * math.sin(a)]
    inner = [i for i, nd in enumerate(nodes) if nd["n"] > 1]
    a = {i: ang[i] for i in inner}
    r = {i: radius(nodes[i]["n"]) for i in inner}
    for _ in range(1500):                      # push overlapping neighbours apart along the ring
        moved = False
        for x in inner:
            for y in inner:
                if x >= y:
                    continue
                dx = r[x] * math.cos(a[x]) - r[y] * math.cos(a[y])
                dy = r[x] * math.sin(a[x]) - r[y] * math.sin(a[y])
                if (abs(dx) < 105 and abs(dy) < 36) or dx * dx + dy * dy < 46 ** 2:   # label-sized box
                    d = (a[x] - a[y] + math.pi) % (2 * math.pi) - math.pi or 1e-3
                    step = 0.012 * (1 if d > 0 else -1)
                    a[x] += step
                    a[y] -= step
                    moved = True
        if not moved:
            break
    for i in inner:
        out[i] = [r[i] * math.cos(a[i]), r[i] * math.sin(a[i])]
    return [[round(x, 1), round(y, 1)] for x, y in out]


def coauthor_network(pubs: list[dict], self_author: str, themes: list[dict], me_name: str = "") -> dict:
    """Data for the co-author network on the publications page (built from publications.yaml only).

    nodes: every co-author with the joint papers (indices into `papers`) and a theme (the home-page
    theme most of the joint papers belong to); edges: [a, b, n] for co-authors who appear together on
    n of the papers (n = 1 pairs only shape the layout, the page draws n ≥ 2).
    """
    me = _author_key(self_author)
    papers, members = [], []
    for p in pubs:
        ks = []
        for a in p["authors"]:
            k = _author_key(a)
            if k and k != me and k not in ks:
                ks.append(k)
        papers.append({"id": p["id"], "t": p["title"], "y": p["year"] if p["status"] != "accepted" else "accepted",
                       "v": p.get("venue") or ("Preprint" if p["status"] == "preprint" else ""),
                       "topics": p.get("topics") or []})
        members.append(ks)
    names: dict[str, dict[str, int]] = {}
    for p, ks in zip(pubs, members):
        for a in p["authors"]:
            k = _author_key(a)
            if k in ks:
                spelled = str(a).strip().rstrip("*").strip()
                names.setdefault(k, {}).setdefault(spelled, 0)
                names[k][spelled] += 1
    joint: dict[str, list[int]] = {}
    for i, ks in enumerate(members):
        for k in ks:
            joint.setdefault(k, []).append(i)
    order = sorted(joint, key=lambda k: (-len(joint[k]), k))
    index = {k: i for i, k in enumerate(order)}
    theme_sets = [set(t.get("topics") or []) for t in themes]
    nodes = []
    for k in order:
        spelled = max(names[k].items(), key=lambda kv: (kv[1], len(kv[0])))[0]
        last, first = spelled.split(",", 1)
        hits = [sum(bool(ts & set(papers[i]["topics"])) for i in joint[k]) for ts in theme_sets]
        ranked = sorted(range(len(hits)), key=lambda t: (-hits[t], t))
        theme = ranked[0] if hits and hits[ranked[0]] > 0 else -1
        # second colour when the joint papers clearly span two themes (at least half as many in the second)
        theme2 = ranked[1] if theme >= 0 and len(ranked) > 1 and hits[ranked[1]] > 0 \
            and hits[ranked[1]] * 2 >= hits[ranked[0]] else -1
        nodes.append({"name": f"{first.strip()} {last.strip()}", "sort": spelled, "n": len(joint[k]),
                      "theme": theme, "theme2": theme2, "papers": joint[k]})
    pairs: dict[tuple[int, int], int] = {}
    for ks in members:
        ids = sorted(index[k] for k in ks)
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                pairs[(ids[a], ids[b])] = pairs.get((ids[a], ids[b]), 0) + 1
    for p in papers:
        del p["topics"]
    edges = [[a, b, n] for (a, b), n in sorted(pairs.items())]
    top = max(nd["n"] for nd in nodes) if nodes else 1
    radius = lambda k: R_IN + (R_OUT - R_IN) * (1 - ((k - 1) / max(1, top - 1)) ** 0.5)
    # angles from a force layout (co-authors of the same papers end up side by side),
    # radius from the number of joint papers (rings: closest collaborators in the middle)
    pos = network_layout(len(nodes), [radius(nd["n"]) for nd in nodes], edges)
    for nd, xy in zip(nodes, radial_positions(nodes, pos[1:], radius)):
        nd["x"], nd["y"] = xy
    ring_ns = sorted({1, 2, 3, 5, 10, top} & set(range(1, top + 1)))
    return {
        "rings": [[k, round(radius(k), 1)] for k in ring_ns],
        "me": me_name or (self_author.split(",")[1].strip() + " " + self_author.split(",")[0].strip()),
        "papers": papers,
        "nodes": nodes,
        "edges": edges,
        "themes": [{"title": t["title"], "color": THEME_COLORS[i % len(THEME_COLORS)]} for i, t in enumerate(themes)]
                  + [{"title": "Other", "color": OTHER_COLOR}],
    }


def filter_chips(pubs: list[dict]) -> list[dict]:
    chips = [{"f": "all", "label": "All"}]
    if any(p["status"] == "accepted" for p in pubs):
        chips.append({"f": "accepted", "label": "Accepted"})
    if any(p["status"] == "preprint" for p in pubs):
        chips.append({"f": "preprint", "label": "Preprints"})
    years = sorted({int(p["year"]) for p in pubs if p["status"] == "published"}, reverse=True)
    chips += [{"f": str(y), "label": str(y)} for y in years[:FILTER_YEARS]]
    if len(years) > FILTER_YEARS:
        chips.append({"f": "earlier", "label": "Earlier"})
    return chips


def topic_chips(pubs: list[dict], topics: dict) -> list[dict]:
    used = {t for p in pubs for t in (p.get("topics") or [])}
    chips = [{"f": "all", "label": "All topics"}]
    return chips + [{"f": k, "label": v} for k, v in topics.items() if k in used]


# --------------------------------------------------------------------------- build

def build(out: Path, check_only: bool) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    site = load_yaml(ROOT / "site.yaml", {})
    profile = load_yaml(ROOT / "data" / "profile.yaml", {})
    raw_links = profile.get("links") or {}
    if isinstance(raw_links, dict):
        profile["cv_pdf"] = raw_links.pop("cv_pdf", None)
        raw_links = dict(sorted(raw_links.items(), key=lambda kv: PROFILE_LINK_ORDER.index(kv[0])
                                if kv[0] in PROFILE_LINK_ORDER else 99))
    profile["links"] = norm_links(raw_links)
    if profile.get("email_display") and not profile.get("email"):  # "name -dot- x [AT] y -dot- de"
        profile["email"] = profile["email_display"].replace(" -dot- ", ".").replace(" [AT] ", "@")
    if profile.get("email"):  # obfuscated; site.js turns it back into a mailto: link
        profile["_mail"] = profile["email"][::-1].replace("@", " ta ").replace(".", " tod ")
    pages = load_pages(ROOT / "content", errors)
    topics = {str(k): str(v) for k, v in (site.get("publication_topics") or {}).items()}
    pubs = load_publications(ROOT / "data" / "publications.yaml", site.get("self_author", ""), topics,
                             errors, warnings)
    if "home" not in pages:
        errors.append("content/home.md is missing")

    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        print("Build failed:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print(f"OK: {len(pages)} pages, {len(pubs)} publications")
    if check_only:
        return 0

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    md_card = markdown.Markdown(extensions=["extra"])

    def md_filter(text, block: bool = False) -> Markup:
        """Markdown for short texts in front matter (cards, timeline); inline unless block=True."""
        html = md_card.reset().convert(str(text or ""))
        if not block and html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
            html = html[3:-4]
        return Markup(html)

    env.filters["md"] = md_filter
    topic_counts = {k: sum(k in (p.get("topics") or []) for p in pubs) for k in topics}
    nav = sorted((p for p in pages.values() if p.parent is None and p.nav_order is not None),
                 key=lambda p: p.nav_order)
    net = coauthor_network(pubs, site.get("self_author", ""), site.get("themes") or [], profile.get("name", ""))
    net_json = json.dumps(net, ensure_ascii=False, separators=(",", ":"))
    ctx = {
        "site": site,
        "profile": profile,
        "nav": nav,
        "pages": pages,
        "publications": pubs,
        "groups": group_publications(pubs),
        "chips": filter_chips(pubs),
        "topic_chips": topic_chips(pubs, topics) if topics else [],
        "topics": topics,
        "topic_counts": topic_counts,
        "recent": recent_publications(pubs, site.get("recent_publications", 5)),
        "coauthors": {"people": len(net["nodes"]), "repeat": sum(n["n"] > 1 for n in net["nodes"]),
                      "data_version": hashlib.sha1(net_json.encode()).hexdigest()[:10]},
        "year": date.today().year,
        # cache-buster for CSS/JS: changes whenever their content changes
        "version": hashlib.sha1(b"".join((ROOT / "static" / f).read_bytes()
                                         for f in ("css/site.css", "js/site.js", "js/coauthors.js"))).hexdigest()[:10],
    }

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(ROOT / "static", out / "static")

    for page in pages.values():
        if page.meta.get("redirect"):     # moved page: forward old links (GitHub Pages has no server redirects)
            to = escape(page.meta["redirect"])
            html = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Moved</title>'
                    f'<meta http-equiv="refresh" content="0; url={to}"><link rel="canonical" href="{to}">'
                    f'<meta name="robots" content="noindex"></head><body><p>This page has moved: '
                    f'<a href="{to}">{to}</a></p></body></html>\n')
            target = out / page.out_file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html, encoding="utf-8")
            continue
        template = page.template or ("home.html" if page.is_home else
                                     "publications.html" if page.slug == "publications" else "page.html")
        html = env.get_template(template).render(page=page, **ctx)
        target = out / page.out_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    (out / "coauthors.json").write_text(net_json, encoding="utf-8")   # loaded by static/js/coauthors.js
    (out / "publications.bib").write_text("\n\n".join(p["_bibtex"] for p in pubs) + "\n", encoding="utf-8")
    (out / "404.html").write_text(env.get_template("404.html").render(page=None, **ctx), encoding="utf-8")
    base = site.get("base_url", "").rstrip("/")
    urls = "\n".join(f"  <url><loc>{base}{p.url}</loc></url>" for p in pages.values() if not p.meta.get("redirect"))
    (out / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n', encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", out / "CNAME")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "site")
    ap.add_argument("--check", action="store_true", help="validate content and data only")
    args = ap.parse_args()
    sys.exit(build(args.out, args.check))
