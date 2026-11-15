#!/usr/bin/env python3
"""One-off importer: Google Site (sites.google.com/site/fritzgntr) -> structured sources.

Kept for reference. It was used once to migrate the old site; the files it wrote
(content/*.md, data/publications.yaml, data/profile.yaml) were then checked and
lightly hand-polished, so re-running it with --write will overwrite those edits.

Usage (from the repo root, Python 3.10+ with beautifulsoup4, lxml, pyyaml):

    python scripts/import_gsites.py fetch          # download pages to scripts/raw/*.html
    python scripts/import_gsites.py parse          # parse raw HTML -> scripts/raw/*.json + preview
    python scripts/import_gsites.py parse --write  # ... and (over)write content/ and data/

The new Google Sites serve their content in the initial HTML (the browser only
hydrates it), so plain HTTP fetching is enough. Layout facts this relies on:

* every content block is a <section class="yaqOZd">; the page title is the <h1>;
* text lives in <p>/<h1-3> elements made of <span style="..."> runs, where
  `font-weight: 700` = bold, `font-style: italic` = italic;
* on the publications page each publication is one section: the citation <p>
  (usually inside a <ul><li>), a <p> of link buttons ("Link/Download",
  "Download", "Data, Material, & Scripts", ...), optional "* equal contribution"
  notes, and the abstract in the collapsed body of a collapsible group (a
  div.oKdM2c without the header class Kzv0Me);
* "Custom embed" widgets keep their HTML in the `data-code` attribute;
* external links may be wrapped as https://www.google.com/url?q=<target>.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "scripts" / "raw"
CONTENT = ROOT / "content"
DATA = ROOT / "data"
BASE = "https://sites.google.com/site/fritzgntr"

# slug, path on the old site, nav_order, parent slug
PAGES = [
    ("home", "home", 1, None),
    ("cv", "cv", 2, None),
    ("publications", "publications", 3, None),
    ("data", "data", 4, None),
    ("software-resources", "software-resources", 5, None),
    ("r_packages", "software-resources/r_packages", 1, "software-resources"),
    ("semantic_spaces", "software-resources/semantic_spaces", 2, "software-resources"),
    ("vispa", "software-resources/vispa", 3, "software-resources"),
    ("video_tutorials", "software-resources/video_tutorials", 4, "software-resources"),
    ("centroid-analysis", "software-resources/centroid-analysis", 5, "software-resources"),
    ("psychoembeddings", "software-resources/psychoembeddings", 6, "software-resources"),
    ("the-flickr-frequency-norms", "software-resources/the-flickr-frequency-norms", 7, "software-resources"),
    ("english_st", "software-resources/english_st", 8, "software-resources"),
    ("german_st", "software-resources/german_st", 9, "software-resources"),
    ("vision-based-semantic-transparency-measures-for-english-compounds",
     "software-resources/vision-based-semantic-transparency-measures-for-english-compounds", 10, "software-resources"),
    ("taboo-language-database", "software-resources/taboo-language-database", 11, "software-resources"),
    ("media-coverage", "media-coverage", 6, None),
    ("profiles", "profiles", 7, None),
    ("contact", "contact", 8, None),
]
PATH_TO_SLUG = {p: s for s, p, _, _ in PAGES}

# Pages whose text came from the classic Google Sites and is hard-wrapped into
# one <p> per visual line; consecutive lines are re-joined into paragraphs.
JOIN_LINES = {"semantic_spaces", "contact"}


# --------------------------------------------------------------------------- fetch
def fetch() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for slug, path, _, _ in PAGES:
        req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=60).read()
        (RAW / f"{slug}.html").write_bytes(html)
        print(f"{slug}: {len(html)} bytes")


# --------------------------------------------------------------------------- helpers
def soup_of(slug: str):
    from bs4 import BeautifulSoup
    return BeautifulSoup((RAW / f"{slug}.html").read_text(encoding="utf-8"), "lxml")


def clean_ws(s: str) -> str:
    s = s.replace("\u00a0", " ").replace("\u200b", "")
    return re.sub(r"[ \t\r\n]+", " ", s)


def unwrap_url(href: str) -> str:
    """Undo Google redirect wrapping and map old-site links to new paths."""
    href = (href or "").strip()
    u = urllib.parse.urlparse(href)
    if u.netloc.endswith("google.com") and u.path == "/url":
        q = urllib.parse.parse_qs(u.query).get("q")
        if q:
            href = q[0]
            u = urllib.parse.urlparse(href)
    if href.startswith("/site/fritzgntr") or href.startswith(BASE):
        path = href.split("/site/fritzgntr", 1)[1].strip("/")
        path, _, frag = path.partition("#")
        if path in PATH_TO_SLUG or path == "":
            return "/" + (path + "/" if path else "") + (("#" + frag) if frag else "")
    return href


def style_of(el) -> str:
    return (el.get("style") or "").replace(" ", "")


def runs_of(el, bold=False, italic=False, href=None, out=None):
    """Flatten an element into (text, bold, italic, href) runs."""
    from bs4 import NavigableString, Tag
    if out is None:
        out = []
    for ch in el.children:
        if isinstance(ch, NavigableString):
            t = str(ch)
            if t:
                out.append([t, bold, italic, href])
        elif isinstance(ch, Tag):
            if ch.name == "br":
                out.append(["\n", False, False, None])
                continue
            st = style_of(ch)
            b = bold or "font-weight:700" in st or ch.name in ("b", "strong")
            i = italic or "font-style:italic" in st or ch.name in ("i", "em")
            h = href
            if ch.name == "a" and ch.get("href"):
                h = unwrap_url(ch["href"])
            runs_of(ch, b, i, h, out)
    return out


def md_escape(t: str) -> str:
    # '*' and '`' always; '_' only at word edges (intra-word '_' is literal in Markdown)
    t = re.sub(r"([*`])", r"\\\1", t)
    return re.sub(r"(?<!\w)_|_(?!\w)", r"\\_", t)


CODE_LINE = re.compile(r"^(?:[A-Za-z_][\w.]*\s*(?:\(|<-)).*\)\s*$")


def runs_to_md(runs, keep_bold=True) -> str:
    """Render runs as inline Markdown, merging adjacent runs with equal formatting."""
    # normalise whitespace and merge
    merged: list[list] = []
    for t, b, i, h in runs:
        t = t.replace("\u00a0", " ").replace("\u200b", "")
        if t != "\n":
            t = re.sub(r"[ \t\r\n]+", " ", t)
        b = b and keep_bold
        if not t.strip() and t != "\n":
            b = i = False  # formatting on pure whitespace is irrelevant
        if merged and merged[-1][1:] == [b, i, h] and t != "\n" and merged[-1][0] != "\n":
            merged[-1][0] += t
        else:
            merged.append([t, b, i, h])

    def fmt(t, b, i):
        if t == "\n":
            return "<br>\n"
        if not t.strip():
            return t
        lead = t[: len(t) - len(t.lstrip())]
        trail = t[len(t.rstrip()):]
        core = md_escape(t.strip())
        if b and i:
            core = f"***{core}***"
        elif b:
            core = f"**{core}**"
        elif i:
            core = f"*{core}*"
        return lead + core + trail

    out = []
    k = 0
    while k < len(merged):
        h = merged[k][3]
        if h:
            group = []
            while k < len(merged) and merged[k][3] == h:
                group.append(merged[k])
                k += 1
            inner = "".join(fmt(t, b, i) for t, b, i, _ in group)
            lead = inner[: len(inner) - len(inner.lstrip())]
            trail = inner[len(inner.rstrip()):]
            if inner.strip():
                out.append(f"{lead}[{inner.strip()}]({h}){trail}")
            else:
                out.append(inner)  # empty link (Google Sites leaves these) -> drop
        else:
            out.append(fmt(*merged[k][:3]))
            k += 1
    s = "".join(out)
    s = re.sub(r"\*\*\s*\*\*", "", s)
    return re.sub(r" {2,}", " ", s).strip()


def plain(el) -> str:
    return clean_ws(el.get_text("")).strip()


# --------------------------------------------------------------------------- generic pages
def html_table_to_md(html: str) -> str:
    """Convert a custom-embed HTML table to Markdown.

    Tables with <th> become Markdown tables; header-less two-column tables (the CV
    timeline, the list of semantic spaces) become "- **left** — right" lists.
    """
    from bs4 import BeautifulSoup
    s = BeautifulSoup(html, "lxml")
    rows = []
    for tr in s.find_all("tr"):
        cells = []
        for td in tr.find_all(["td", "th"]):
            c = runs_to_md(runs_of(td)).replace("<br>\n", "<br>")
            c = re.sub(r"\s*<br>\s*", "<br>", c)
            c = re.sub(r"^(<br>)+|(<br>)+$", "", c).strip()
            c = re.sub(r"(<br>){2,}", "<br>", c)
            cells.append(c)
        if any(cells):
            rows.append(cells)
    if not rows:
        return plain(s)
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    if s.find("th") is None and n == 2:
        return "\n".join(f"- **{a}** — {b}" for a, b in rows)
    rows = [[c.replace("|", "\\|") for c in r] for r in rows]
    header, body = (rows[0], rows[1:]) if s.find("th") is not None else ([""] * n, rows)
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * n]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def is_heading_p(p, runs) -> int:
    """0 = normal paragraph, else Markdown heading level for a bold-only short line."""
    text = clean_ws("".join(r[0] for r in runs)).strip()
    if not text or len(text) > 90 or text.endswith(":") or p.find("a"):
        return 0
    if not all(b for t, b, i, h in runs if t.strip()):
        return 0
    big = any(re.search(r"font-size:(1[3-9]|[2-9]\d)", style_of(sp)) for sp in p.find_all("span"))
    return 2 if big else 3


def section_blocks(section, slug):
    """Yield Markdown blocks (or None for an empty paragraph) for one section."""
    from bs4 import Tag
    for el in section.find_all(["h1", "h2", "h3", "h4", "p", "img", "iframe", "div"]):
        if el.name == "div":
            if el.get("data-code"):
                code = el["data-code"]
                yield ("embed", html_table_to_md(code) if "<table" in code else code)
            continue
        if el.name == "h1":
            continue  # page title -> front matter
        if el.name == "img":
            yield ("img", f"![]({el.get('src')})")
            continue
        if el.name == "iframe":
            src = el.get("src") or ""
            m = re.search(r"youtube\.com/embed/([\w-]+)", src)
            if m:
                label = (el.get("aria-label") or "YouTube video").replace("YouTube Video, ", "")
                yield ("video", f'<div class="video" data-youtube="{m.group(1)}"></div>\n\n'
                                f"[{label} (YouTube)](https://www.youtube.com/watch?v={m.group(1)})")
            continue
        runs = runs_of(el)
        text = clean_ws("".join(r[0] for r in runs)).strip()
        if not text:
            yield None
            continue
        if text == "token" and "color:#ffffff" in str(el).replace(" ", ""):
            continue  # invisible white-on-white text on the home page
        if re.fullmatch(r"-{10,}", text):
            continue  # decorative separator lines
        if CODE_LINE.match(text) and not el.find("a"):
            yield ("p", f"`{text}`")
            continue
        if el.name in ("h2", "h3", "h4"):
            yield ("h", "## " + md_escape(text))
            continue
        lvl = is_heading_p(el, runs)
        if lvl:
            yield ("h", "#" * lvl + " " + md_escape(text))
            continue
        md = runs_to_md(runs)
        md = re.sub(r"^([-+]) ", r"\\\1 ", md)  # a line like "- or ..." is text, not a list
        if el.find_parent("li") is not None:
            yield ("li", "- " + md)
        else:
            yield ("p", md)


def page_to_md(slug: str) -> tuple[str, str]:
    s = soup_of(slug)
    title = plain(s.select_one("section.yaqOZd h1"))
    title = re.sub(r"\s+", " ", title)
    blocks = []
    for sec in s.select("section.yaqOZd"):
        blocks.extend(section_blocks(sec, slug))
        blocks.append(None)
    out: list[str] = []
    prev = None
    for b in blocks:
        if b is None:
            prev = None
            continue
        kind, md = b
        if kind == "li" and prev == "li":
            out[-1] += "\n" + md
        elif slug in JOIN_LINES and kind == "p" and prev == "p":
            # a line wrapped mid-sentence continues the paragraph; anything else is a line break
            soft = (not re.search(r"[.:!?)]\**$", out[-1]) and re.match(r"^[a-z(\[]", md)
                    and not out[-1].endswith("`") and not md.startswith("`"))
            out[-1] += ("\n" if soft else "<br>\n") + md
        else:
            out.append(md)
        prev = kind
    body = "\n\n".join(out)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return title, body


def front_matter(title, nav_order, parent, path, extra=None) -> str:
    import yaml
    fm = {"title": title, "nav_order": nav_order}
    if parent:
        fm["parent"] = parent
    fm["permalink"] = "/" if path == "home" else f"/{path}/"
    fm["source"] = f"{BASE}/{path}"
    if extra:
        fm.update(extra)
    return "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n\n"


# --------------------------------------------------------------------------- publications
LINK_LABELS = {
    "link/download": "url", "link / download": "url", "link": "url",
    "download": "pdf",
    "data, material, & scripts": "data", "data, material, and scripts": "data",
}
STATUS_HEADINGS = {"accepted": "accepted", "preprints": "preprint"}


def strip_bold_runs(runs):
    return [[t, False, i, h] for t, b, i, h in runs]


def parse_authors(s: str) -> list[str]:
    s = clean_ws(s).strip().rstrip(",")
    s = re.sub(r"\s*&\s*", ", ", s)
    toks = [t.strip() for t in s.split(",") if t.strip()]
    initials = re.compile(r"^(?:[A-ZÀ-ÖØ-Þ][a-zà-ÿ]?\.\s*-?\s*)+\**$")
    authors, k = [], 0
    while k < len(toks):
        t = toks[k]
        if t in ("...", "…"):
            authors.append("…")
            k += 1
            continue
        if k + 1 < len(toks) and initials.match(toks[k + 1].replace(" ", "")):
            ini = re.sub(r"\.\s*(?=[A-ZÀ-ÖØ-Þ])", ". ", toks[k + 1].strip())
            ini = re.sub(r"\.\s+\*", ".*", ini)
            surname = re.sub(r"\s+", " ", t)
            authors.append(f"{surname}, {ini}")
            k += 2
        else:
            authors.append(t)  # unparsed -> flagged by the checker
            k += 1
    return authors


def citation_parts(p):
    """Split a citation <p> into authors / year / title / venue tail using italics."""
    runs = strip_bold_runs(runs_of(p))
    full = clean_ws("".join(r[0] for r in runs)).strip()
    # tidy spacing artefacts like "( 2026 )", "(202 4 )", "Günther, F. ,"
    full_t = re.sub(r"\(\s*((?:\d\s*){4}[a-z]?|accepted|in press)\s*\)",
                    lambda m: "(" + m.group(1).replace(" ", "") + ")", full)
    full_t = re.sub(r"\s+,", ",", full_t)
    m = re.match(r"^(?P<authors>.+?)\s*\((?P<year>\d{4}[a-z]?|accepted|in press)\)\s*\.?\s*(?P<rest>.*)$", full_t)
    if not m:
        return {"_unparsed": full}
    rest = m.group("rest").strip()
    # italic text = venue (journal / book / preprint server), possibly with volume
    italic = clean_ws("".join(t for t, b, i, h in runs if i)).strip()
    italic = re.sub(r"\s+,", ",", italic)
    return {"authors_raw": m.group("authors"), "year": m.group("year"), "rest": rest,
            "italic": italic, "full": full_t}


def split_title_venue(rest: str, italic: str):
    """Return title, venue-tail. Venue starts at the italic run (or 'In ...' for chapters)."""
    rest = rest.strip()
    m = re.search(r"\.\s+(In\s+[A-Z][^()]*\((?:Eds?\.)\),)", rest)
    if m:
        return rest[: m.start() + 1].strip(), rest[m.start() + 1:].strip()
    if italic:
        key = italic.strip(" .,")[:25]
        idx = rest.find(key)
        if idx > 0:
            return rest[:idx].strip(), rest[idx:].strip()
    # fallback: last ". " that precedes something venue-like
    parts = re.split(r"(?<=[.?!])\s+", rest, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return rest, ""


def parse_venue(tail: str, italic: str, entry: dict) -> None:
    tail = clean_ws(tail).strip()
    url_in_text = re.search(r"https?://\S+", tail)
    if url_in_text:
        entry["_text_url"] = url_in_text.group(0).rstrip(".,")
        tail = (tail[: url_in_text.start()] + tail[url_in_text.end():]).strip(" ,.")
    # book chapter / proceedings paper:
    #   In Eds (Eds.), Book Title (3rd ed., Vol. 13, pp. 1-2). Publisher.
    m = re.match(r"^In\s+(?P<eds>.+?)\s*\((?:Eds?\.)\),\s*(?P<rest>.+)$", tail)
    if m:
        rest = m.group("rest")
        # the last parenthetical holding ed./Vol./pp. information
        inner_m = None
        for im in re.finditer(r"\(([^()]*)\)", rest):
            if re.search(r"\b(pp?\.|Vol\.|ed\.)", im.group(1)):
                inner_m = im
        book = rest[: inner_m.start()] if inner_m else rest
        pub = rest[inner_m.end():] if inner_m else ""
        entry["type"] = "proceedings" if book.strip().lower().startswith("proceedings") else "chapter"
        entry["editors"] = m.group("eds").strip()
        entry["venue"] = book.strip(" .,")
        if inner_m:
            for piece in [x.strip() for x in inner_m.group(1).split(",")]:
                if re.match(r"^\d+\w*\s+ed\.?$", piece):
                    entry["edition"] = piece
                elif piece.lower().startswith("vol"):
                    entry["volume"] = re.sub(r"^vol\.?\s*", "", piece, flags=re.I)
                elif re.match(r"^pp?\.", piece):
                    entry["pages"] = re.sub(r"\s*[-–]\s*", "–", re.sub(r"^pp?\.\s*", "", piece))
        pub = pub.strip(" .,")
        if pub:
            entry["publisher"] = pub
        return
    # "Journal. Advance online publication."
    am = re.search(r"\.\s*(Advance online publication)\.?$", tail)
    if am:
        entry["_note"] = am.group(1)
        tail = tail[: am.start()]
    # journal: Venue, vol(issue), pages.
    m = re.match(r"^(?P<venue>.+?)(?:,\s*(?P<vol>\d+)\s*(?:\((?P<issue>[^)]+)\))?)?"
                 r"(?:,\s*(?P<pages>[A-Za-z]?\d+(?:\s*[-–]\s*[A-Za-z]?\d+)?))?\s*\.?$", tail)
    if m and not re.search(r"\(pp\.", tail):
        entry["venue"] = m.group("venue").strip(" .,")
        for k in ("vol", "issue", "pages"):
            if m.group(k):
                entry[{"vol": "volume"}.get(k, k)] = re.sub(r"\s*[-–]\s*", "–", m.group(k)) if k == "pages" else m.group(k)
        return
    # proceedings etc.: keep the whole tail as venue, pull out pages if present
    pm = re.search(r"\(pp\.\s*([^)]+)\)", tail)
    if pm:
        entry["pages"] = re.sub(r"\s*[-–]\s*", "–", pm.group(1).strip())
    entry["venue"] = tail.strip(" .")


DOI_RE = re.compile(r"10\.\d{4,9}/[^\s?#&\"<>]+")


def doi_from(url: str) -> str | None:
    if not url:
        return None
    u = urllib.parse.unquote(url)
    m = DOI_RE.search(u)
    if not m:
        return None
    d = m.group(0).rstrip("./")
    d = re.sub(r"/(abstract|full|pdf)$", "", d)
    return d


def ascii_key(s: str) -> str:
    import unicodedata
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s


ID_STOP = {"a", "an", "the", "of", "on", "in", "and", "for", "to", "from", "with", "via", "is",
           "are", "do", "not", "as", "at", "by", "what", "how", "can", "be", "into", "does", "this"}


def make_id(authors, year, title, used) -> str:
    """<first author surname><year><first content word of title>, extended until unique."""
    first = authors[0].split(",")[0] if authors else "anon"
    first = re.sub(r"[^a-z]", "", ascii_key(first))
    words = [w for w in re.findall(r"[a-z0-9]+", ascii_key(title)) if w not in ID_STOP] or ["x"]
    k = 1
    cand = f"{first}{year}{words[0]}"
    while cand in used:
        k += 1
        cand = f"{first}{year}{''.join(words[:k])}" if k <= len(words) else f"{first}{year}{words[0]}{k}"
    used.add(cand)
    return cand


# Fixes for obvious errors on the old site, applied after parsing (listed in the import report).
CORRECTIONS = {
    # href on the site is two URLs glued together; the second one is this paper's OSF project
    ("martineztomas2026conveying", "data"): (
        "https://osf.io/nuvh8/?view_only=81f2d52c74ac44528f52d99b9fb44023https://osf.io/9zbx6/",
        "https://osf.io/9zbx6/"),
}
VENUE_FIXES = {
    "Philosophical Transcactions of the Royal Society A": "Philosophical Transactions of the Royal Society A",
    "psyArXiv preprint": "PsyArXiv preprint",
    "psyArXiV preprint": "PsyArXiv preprint",
}


def parse_publications():
    s = soup_of("publications")
    pubs, flags, inline_links = [], [], []
    status_ctx, year_ctx = None, None
    # accepted entries carry no year; their id uses the newest year on the page
    newest_year = max(int(y) for y in re.findall(r">\s*(20\d\d)\s*</span></p>", str(s)))
    used_ids: set[str] = set()
    for sec in s.select("section.yaqOZd"):
        ps = [p for p in sec.find_all("p") if plain(p)]
        if not ps:
            continue
        if len(ps) == 1 and not sec.find("li") and len(plain(ps[0])) < 20:
            head = plain(ps[0]).lower()
            if head in STATUS_HEADINGS:
                status_ctx = STATUS_HEADINGS[head]
            elif re.fullmatch(r"\d{4}", head):
                status_ctx, year_ctx = "published", int(head)
            continue
        if sec.find("h1"):
            continue
        cite_p, link_ps, note_ps, abstract_ps = None, [], [], []
        for p in ps:
            txt = plain(p)
            # collapsible group: header tile = div.oKdM2c.Kzv0Me, hidden body = div.oKdM2c alone
            tile = p.find_parent("div", class_="oKdM2c")
            in_abstract = tile is not None and "Kzv0Me" not in (tile.get("class") or [])
            if in_abstract:
                abstract_ps.append(p)
            elif cite_p is None and re.search(r"\(\s*(?:\d\s*){4}|\(\s*accepted", txt):
                cite_p = p
            elif txt.startswith("*"):
                note_ps.append(p)
            elif p.find("a") and not re.sub(r"[\s/]", "", "".join(
                    str(x) for x in p.find_all(string=True) if not x.find_parent("a"))):
                link_ps.append(p)
            else:
                flags.append(f"unclassified paragraph: {txt[:100]}")
        if cite_p is None:
            flags.append(f"section without citation: {plain(sec)[:100]}")
            continue
        parts = citation_parts(cite_p)
        if "_unparsed" in parts:
            flags.append(f"unparsed citation: {parts['_unparsed'][:120]}")
            continue
        e: dict = {}
        authors = parse_authors(parts["authors_raw"])
        title, tail = split_title_venue(parts["rest"], parts["italic"])
        title = title.strip()
        if title.endswith("."):
            title = title[:-1]
        venue_info: dict = {}
        parse_venue(tail, parts["italic"], venue_info)
        yr = parts["year"]
        e["id"] = make_id(authors, yr if yr.isdigit() else newest_year, title, used_ids)
        if venue_info.get("venue") in VENUE_FIXES:
            venue_info["venue"] = VENUE_FIXES[venue_info["venue"]]
        e["status"] = "published" if status_ctx == "published" else status_ctx
        if yr.isdigit():
            e["year"] = int(yr)
        e["authors"] = authors
        e["title"] = title
        if venue_info.get("type"):
            e["type"] = venue_info["type"]
        for k in ("venue", "editors", "edition", "volume", "issue", "pages", "publisher"):
            if venue_info.get(k):
                e[k] = venue_info[k]
        # links
        extra = []
        for lp in link_ps:
            for a in lp.find_all("a"):
                label = clean_ws(a.get_text("")).strip()
                href = unwrap_url(a.get("href", ""))
                if not label or not href:
                    continue
                field = LINK_LABELS.get(label.lower().replace("  ", " "))
                if field and field not in e:
                    e[field] = href
                elif field and e.get(field) == href:
                    pass
                else:
                    extra.append({"label": label, "url": href})
        if "url" not in e and venue_info.get("_text_url"):
            e["url"] = venue_info["_text_url"]
        doi = doi_from(e.get("url", "")) or doi_from(venue_info.get("_text_url", ""))
        if doi:
            e["doi"] = doi
        # put doi before url for readability
        order = ["id", "status", "type", "year", "authors", "title", "venue", "editors", "edition",
                 "volume", "issue", "pages", "publisher", "doi", "url", "pdf", "data"]
        e = {k: e[k] for k in order if k in e}
        if extra:
            e["extra_links"] = extra
        for (cid, field), (old, new) in CORRECTIONS.items():
            if e["id"] == cid and e.get(field) == old:
                e[field] = new
        notes = [clean_ws(plain(n)) for n in note_ps]
        if venue_info.get("_note"):
            notes.insert(0, venue_info["_note"])
        if notes:
            e["notes"] = "; ".join(re.sub(r"^(\*+)\s*", r"\1 ", n) for n in notes)
        if abstract_ps:
            e["abstract"] = "\n\n".join(runs_to_md(strip_bold_runs(runs_of(p))) for p in abstract_ps)
        # inline links inside the citation text: recorded for review, not used
        for a in cite_p.find_all("a"):
            href = unwrap_url(a.get("href", ""))
            if href and href not in (e.get("url"), e.get("pdf"), e.get("data")):
                inline_links.append({"id": e["id"], "text": clean_ws(a.get_text("")).strip(), "href": href})
        e["_citation"] = parts["full"]
        e["_section_year"] = year_ctx if status_ctx == "published" else None
        pubs.append(e)
    return pubs, flags, inline_links


# --------------------------------------------------------------------------- profile
def build_profile() -> dict:
    """data/profile.yaml from the home, profiles and contact pages."""
    home = soup_of("home")
    secs = home.select("section.yaqOZd")
    intro_p = secs[1].find_all("p")
    intro = [p for p in intro_p if plain(p)]
    links = {clean_ws(a.get_text("")).strip(): unwrap_url(a["href"]) for a in intro[0].find_all("a")}

    def link_containing(d, *keys):
        for label, href in d.items():
            if all(k.lower() in label.lower() for k in keys):
                return href
        return None

    projects = []
    start = next(i for i, sec in enumerate(secs) if plain(sec).strip().lower() == "current projects")
    for sec in secs[start + 1:]:
        ps = [p for p in sec.find_all("p") if plain(p)]
        if len(ps) >= 2 and ps[0].find("a"):
            a = ps[0].find("a")
            title = plain(ps[0])
            m = re.match(r'^(?P<kind>.+?)\s*[:\-–]?\s*"\s*(?P<name>.+?)\s*"$', title)
            proj = {"title": m.group("name") if m else title,
                    "funding": re.sub(r"\s*-\s*Project$", "", m.group("kind").strip(" :-–")) if m else None,
                    "url": unwrap_url(a["href"]),
                    "description": "\n\n".join(runs_to_md(runs_of(p)) for p in ps[1:])}
            projects.append({k: v for k, v in proj.items() if v})

    prof = soup_of("profiles")
    plinks = {clean_ws(a.get_text("")).strip(): unwrap_url(a["href"])
              for a in prof.select("section.yaqOZd a") if a.get("href")}
    orcid = re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", " ".join(plinks.values()))

    contact = soup_of("contact")
    lines = [plain(p) for p in contact.select("section.yaqOZd p") if plain(p)]
    obf = next(l for l in lines if "[AT]" in l)
    email = re.sub(r"\s*-\s*dot\s*-\s*", ".", obf.replace(" [AT] ", "@").replace("[AT]", "@"))
    email = re.sub(r"\s+", "", email)

    def block_after(label):
        i = next(k for k, l in enumerate(lines) if l.lower().startswith(label))
        out = []
        for l in lines[i + 1:]:
            if l.endswith(":"):
                break
            out.append(l.rstrip(","))
        return out

    photo = next((img.get("src") for img in home.select("section.yaqOZd img")), None)
    site_title = plain(home.find("title")) if home.find("title") else ""
    return {
        "name": re.sub(r"^Homepage of\s+", "", site_title) or "Fritz Günther",
        "title_prefix": "Dr.",
        "position": "Junior research group leader (DFG Emmy Noether Programme)",
        "group": 'Emmy Noether Group "Computational Modelling"',
        "group_url": link_containing(links, "Computational Modelling"),
        "department": "Department of Psychology",
        "university": "Humboldt-Universität zu Berlin",
        "department_url": link_containing(links, "Department of Psychology"),
        "email": email,
        "email_display": obf,
        "office_address": block_after("my office address"),
        "postal_address": block_after("my post address"),
        "photo": photo,
        "links": {
            "hu": link_containing(plinks, "Institutional Homepage"),
            "gepris": link_containing(plinks, "Deutsche Forschungsgemeinschaft"),
            "researchgate": link_containing(plinks, "ResearchGate"),
            "scholar": link_containing(plinks, "Google Scholar"),
            "orcid": link_containing(plinks, "ORCID"),
            "scopus": link_containing(plinks, "Scopus"),
            "cv_pdf": unwrap_url(soup_of("cv").select_one("section.yaqOZd a")["href"]),
        },
        "orcid": orcid.group(0) if orcid else None,
        "intro": runs_to_md(runs_of(intro[0])),
        "research": "\n\n".join(runs_to_md(runs_of(p)) for p in intro[1:]),
        "projects": projects,
    }


# --------------------------------------------------------------------------- images
def collect_images() -> list[str]:
    lines, seen = [], set()
    for slug, path, _, _ in PAGES:
        s = soup_of(slug)
        found = []
        for l in s.find_all("link", rel=lambda r: r and "icon" in r):
            found.append(("favicon", l.get("href")))
        for m in s.find_all("meta", attrs={"property": "og:image"}):
            found.append(("og:image (site logo)", m.get("content")))
        for img in s.find_all("img"):
            where = "content image" if img.find_parent("section", class_="yaqOZd") else "header/logo image"
            found.append((where, img.get("src")))
        for el in s.find_all(style=re.compile(r"background-image")):
            for u in re.findall(r"url\(['\"]?([^'\")]+)", el["style"]):
                found.append(("header background", u))
        for kind, url in found:
            if not url or "sitesv-images" not in url and "googleusercontent" not in url:
                continue
            key = (kind, url)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"{slug}\t{kind}\t{url}")
    return lines


# --------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "parse"])
    ap.add_argument("--write", action="store_true", help="write content/ and data/ (overwrites!)")
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch()
        return
    import yaml

    pubs, flags, inline_links = parse_publications()
    (RAW / "publications.parsed.json").write_text(json.dumps(
        {"publications": pubs, "flags": flags, "inline_citation_links": inline_links},
        ensure_ascii=False, indent=1), encoding="utf-8")
    pages = {}
    for slug, path, order, parent in PAGES:
        title, body = page_to_md(slug)
        pages[slug] = (title, body)
    (RAW / "pages.parsed.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
    imgs = collect_images()
    print(f"{len(pubs)} publications, {len(flags)} flags, {len(imgs)} image refs")
    for f in flags:
        print("FLAG", f)
    if not a.write:
        return
    (RAW / "images.txt").write_text(
        "# page\tkind\turl   (not downloaded; collected by import_gsites.py)\n" + "\n".join(imgs) + "\n",
        encoding="utf-8")
    CONTENT.mkdir(exist_ok=True)
    for slug, path, order, parent in PAGES:
        title, body = pages[slug]
        if slug == "publications":
            body = ("<!-- The publication list is generated from data/publications.yaml. -->\n")
        (CONTENT / f"{slug}.md").write_text(front_matter(title, order, parent, path) + body, encoding="utf-8")
    DATA.mkdir(exist_ok=True)
    clean = [{k: v for k, v in p.items() if not k.startswith("_")} for p in pubs]
    write_publications_yaml(clean)
    prof = build_profile()
    (DATA / "profile.yaml").write_text(
        "# Personal data for templates (header, footer, home page). Imported from the old site's\n"
        "# home, profiles and contact pages.\n\n"
        + yaml_dump(prof), encoding="utf-8")


def yaml_dump(obj) -> str:
    import yaml

    class D(yaml.SafeDumper):
        pass

    def str_rep(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        if len(data) > 200:  # abstracts etc.: folded block, wrapped for easy editing
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    D.add_representer(str, str_rep)
    return yaml.dump(obj, Dumper=D, allow_unicode=True, sort_keys=False, width=100, indent=2)


def write_publications_yaml(pubs) -> None:
    header = (
        "# Publications, in the order shown on the website (newest first within each group).\n"
        "#\n"
        "# Groups: status 'accepted' first, then 'preprint', then 'published' by year (desc).\n"
        "# Fields (leave out what is empty):\n"
        "#   id          unique key: <firstauthor><year><firstword>, e.g. guenther2016latent\n"
        "#   status      accepted | preprint | published\n"
        "#   type        only for non-journal items: chapter | proceedings\n"
        "#               (these may also have editors, edition, publisher; venue = book/proceedings title)\n"
        "#   year        publication year (omitted for 'accepted' entries)\n"
        "#   authors     list of \"Last, F. M.\"; '*'/'**' after initials = equal contribution (see notes);\n"
        "#               a bare '…' stands for authors omitted on the original list\n"
        "#   title, venue, volume, issue, pages\n"
        "#   doi         bare DOI (10.xxxx/...), taken from the main link\n"
        "#   url         main link (\"Link/Download\" or \"Link\" button)\n"
        "#   pdf         separate \"Download\" link (author copy: Drive / preprint server)\n"
        "#   data        \"Data, Material, & Scripts\" link\n"
        "#   extra_links list of {label, url}, e.g. Trained model\n"
        "#   notes       footnotes such as equal-contribution markers, \"Advance online publication\"\n"
        "#   abstract    abstract text (Markdown), shown in a collapsible box on the old site\n"
        "\n"
    )
    body = yaml_dump(pubs)
    body = re.sub(r"\n- id:", "\n\n- id:", body)
    (DATA / "publications.yaml").write_text(header + body, encoding="utf-8")


if __name__ == "__main__":
    main()
