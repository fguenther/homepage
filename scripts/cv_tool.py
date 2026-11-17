#!/usr/bin/env python3
"""Keep the long-format CV (Word .docx) in step with data/publications.yaml (used by the add-publication skill).

    cv_tool.py list [section]                    numbered entries per publication section
    cv_tool.py find <doi | title words>          CV entries that match (section + number)
    cv_tool.py render <id>                       preview how the YAML entry will look in the CV, and its section
    cv_tool.py add <id>                          insert the entry at the top of its section with the next number
    cv_tool.py replace <section> <num> <id>      replace CV entry <num> of <section> by the YAML entry; same
                                                 section → keeps its number and place; other section → removed
                                                 there (later numbers shift down) and added on top of the new one
    cv_tool.py remove <section> <num>            delete an entry and renumber the section
    cv_tool.py fix <section> <num> <old> <new>   small text correction inside one entry (keeps its formatting)

<section> is a word from the heading: journal | proceedings | chapters | preprints | books | preregistrations | software.
Writing commands take --dry-run (show only) and --no-date (keep the date line on the title page;
by default it is set to today). Before writing, a copy goes to <cv folder>/.cv_backups/ (last 15 kept).
The CV path defaults to G:/Bewerbungen/Anlagen/CV_FritzGuenther_longformat.docx (override with --cv <path>
or the CV_DOCX environment variable). Needs lxml.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import os
import re
import shutil
import sys
import unicodedata
import zipfile
from pathlib import Path

import yaml
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
PUBS = ROOT / "data" / "publications.yaml"
DEFAULT_CV = "/mnt/g/Bewerbungen/Anlagen/CV_FritzGuenther_longformat.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
W = "{%s}" % W_NS
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
HYPERLINK_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"

SECTION_KEYS = {  # keyword in the Heading2 text → short name
    "journal": "journal", "proceedings": "proceedings", "chapter": "chapters", "preprint": "preprints",
    "book": "books", "pre-registration": "preregistrations", "software": "software",
}
ME = "Günther, F."
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


# --------------------------------------------------------------------------- helpers

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def ptext(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t"))


def style_of(p) -> str | None:
    st = p.find(f"{W}pPr/{W}pStyle")
    return st.get(W + "val") if st is not None else None


def load_pubs() -> dict[str, dict]:
    with PUBS.open(encoding="utf-8") as f:
        return {e["id"]: e for e in yaml.safe_load(f) or []}


def ordinal_date(d: dt.date) -> str:
    suf = "th" if 11 <= d.day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th")
    return f"{MONTHS[d.month - 1]} {d.day}{suf}, {d.year}"


# --------------------------------------------------------------------------- the document

class CV:
    def __init__(self, path: Path):
        self.path = path
        with zipfile.ZipFile(path) as z:
            self.infos = z.infolist()
            self.files = {i.filename: z.read(i.filename) for i in self.infos}
        self.doc = etree.fromstring(self.files["word/document.xml"])
        self.rels = etree.fromstring(self.files["word/_rels/document.xml.rels"])
        self.body = self.doc.find(W + "body")

    # ---- structure
    def sections(self) -> dict[str, tuple]:
        """short name → (heading paragraph, [entry paragraphs]) for the 'Publications' chapter."""
        out, cur, in_pubs = {}, None, False
        for el in self.body:
            if el.tag != W + "p":
                continue
            st, txt = style_of(el), ptext(el)
            if st == "Heading1":
                in_pubs = "publication" in txt.lower()
                cur = None
                continue
            if not in_pubs:
                continue
            if st == "Heading2":
                low = txt.lower()
                key = next((v for k, v in SECTION_KEYS.items() if k in low), norm(txt))
                out[key] = (el, [])
                cur = key
            elif cur and st == "CVPublication":
                out[cur][1].append(el)
        return out

    def section(self, name: str):
        secs = self.sections()
        name = name.lower().rstrip("s")
        for k, v in secs.items():
            if k.rstrip("s").startswith(name) or name in k:
                return k, v
        sys.exit(f"no publication section matching '{name}' (have: {', '.join(secs)})")

    @staticmethod
    def number(p) -> int | None:
        m = re.match(r"\s*(\d+)\.", ptext(p))
        return int(m.group(1)) if m else None

    @staticmethod
    def set_number(p, n: int) -> None:
        """Rewrite the leading 'NN.' that may be split over several runs."""
        old = re.match(r"\s*\d+", ptext(p)).group(0)
        remaining, first = len(old), True
        for t in p.iter(W + "t"):
            if remaining <= 0:
                break
            s = t.text or ""
            take = min(len(s), remaining)
            if take == 0:
                continue
            t.text = (str(n) if first else "") + s[take:]
            first = False
            remaining -= take

    def entry(self, sec: str, num: int):
        key, (_, entries) = self.section(sec)
        for p in entries:
            if self.number(p) == num:
                return key, p
        sys.exit(f"no entry {num} in section '{key}'")

    # ---- building an entry
    def _rid(self, url: str) -> str:
        for r in self.rels:
            if r.get("Type") == HYPERLINK_TYPE and r.get("Target") == url:
                return r.get("Id")
        used = {r.get("Id") for r in self.rels}
        n = 1
        while f"rId{n}" in used:
            n += 1
        rel = etree.SubElement(self.rels, f"{{{PR_NS}}}Relationship")
        rel.set("Id", f"rId{n}")
        rel.set("Type", HYPERLINK_TYPE)
        rel.set("Target", url)
        rel.set("TargetMode", "External")
        return f"rId{n}"

    @staticmethod
    def _run(text: str, bold=False, italic=False, link=False):
        r = etree.Element(W + "r")
        rpr = etree.SubElement(r, W + "rPr")
        if link:
            etree.SubElement(rpr, W + "rStyle").set(W + "val", "Hyperlink")
        if bold:
            etree.SubElement(rpr, W + "b")
            etree.SubElement(rpr, W + "bCs")
        if italic:
            etree.SubElement(rpr, W + "i")
            etree.SubElement(rpr, W + "iCs")
        if not link:
            etree.SubElement(rpr, W + "color").set(W + "val", "auto")
        if text == "\n":
            etree.SubElement(r, W + "br")
        else:
            t = etree.SubElement(r, W + "t")
            t.text = text
            t.set(XML_SPACE, "preserve")
        return r

    def build(self, segments, template_p, num: int):
        p = etree.Element(W + "p")
        ppr = template_p.find(W + "pPr")
        if ppr is not None:
            p.append(copy.deepcopy(ppr))
        p.append(self._run(f"{num}. "))
        for seg in segments:
            text, fmt = seg
            if fmt == "link":
                h = etree.SubElement(p, W + "hyperlink")
                h.set(f"{{{R_NS}}}id", self._rid(text))
                h.set(W + "history", "1")
                h.append(self._run(text, link=True))
            else:
                p.append(self._run(text, bold="b" in fmt, italic="i" in fmt))
        return p

    # ---- saving
    def set_date(self, d: dt.date) -> str | None:
        pat = re.compile(rf"^\s*({'|'.join(MONTHS)}) \d{{1,2}}(st|nd|rd|th)?, \d{{4}}\s*$")
        for el in self.body:
            if el.tag == W + "p" and style_of(el) == "Heading1":
                break  # only the title page
            if el.tag == W + "p" and pat.match(ptext(el)):
                ts = list(el.iter(W + "t"))
                old = ptext(el)
                ts[0].text = ordinal_date(d)
                for t in ts[1:]:
                    t.text = ""
                return old.strip()
        return None

    def save(self, ignore_lock: bool = False) -> Path:
        lock = self.path.with_name("~$" + self.path.name[2:])
        if lock.exists() and not ignore_lock:
            sys.exit(f"The CV is open in Word ({lock.name} exists). Close it in Word and run again. "
                     "(If Word is closed and the lock file is stale, rerun with --ignore-lock.)")
        bdir = self.path.parent / ".cv_backups"
        bdir.mkdir(exist_ok=True)
        stamp = f"{dt.datetime.now():%Y%m%d-%H%M%S}"
        backup, k = bdir / f"{self.path.stem}_{stamp}{self.path.suffix}", 1
        while backup.exists():
            k += 1
            backup = bdir / f"{self.path.stem}_{stamp}-{k}{self.path.suffix}"
        shutil.copy2(self.path, backup)
        for old in sorted(bdir.glob(f"{self.path.stem}_*{self.path.suffix}"))[:-15]:
            old.unlink()
        self.files["word/document.xml"] = etree.tostring(self.doc, xml_declaration=True, encoding="UTF-8",
                                                         standalone=True)
        self.files["word/_rels/document.xml.rels"] = etree.tostring(self.rels, xml_declaration=True,
                                                                    encoding="UTF-8", standalone=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        with zipfile.ZipFile(tmp, "w") as z:
            for info in self.infos:
                z.writestr(info, self.files[info.filename], compress_type=zipfile.ZIP_DEFLATED)
        try:
            os.replace(tmp, self.path)
        except OSError as e:
            tmp.unlink(missing_ok=True)
            sys.exit(f"could not write the CV ({e}); is it open in Word?")
        return backup


# --------------------------------------------------------------------------- formatting an entry

def target_section(e: dict) -> str:
    if e.get("type") == "chapter":
        return "chapters"
    if e.get("type") == "proceedings":
        return "proceedings"
    if e.get("status") == "preprint":
        return "preprints"
    return "journal"


def end(s: str) -> str:
    s = s.strip()
    return s if s[-1:] in ".?!" else s + "."


def segments(e: dict) -> list[tuple[str, str]]:
    """The entry as (text, fmt) pieces; fmt: '' | 'b' | 'i' | 'link' | 'br'."""
    segs: list[tuple[str, str]] = []
    authors = list(e.get("authors") or [])
    for k, a in enumerate(authors):
        last = k == len(authors) - 1
        sep = "" if last else ","
        if last and len(authors) > 1:
            segs.append(("& ", ""))
        if a.startswith(ME):
            segs.append((a + sep, "b"))
        else:
            segs.append((a + sep, ""))
        if not last:
            segs.append((" ", ""))
    when = "accepted" if e.get("status") == "accepted" else str(e.get("year", "n.d."))
    segs.append((f" ({when}). ", ""))

    title, venue = e.get("title", "").strip(), (e.get("venue") or "").strip()
    vol, pages = e.get("volume"), e.get("pages")
    pages = str(pages).replace("–", "-") if pages else None
    notes = str(e.get("notes") or "")
    link = f"https://doi.org/{e['doi']}" if e.get("doi") else e.get("url")
    kind = e.get("type")

    if kind in ("chapter", "proceedings") and e.get("editors"):
        segs.append((end(title) + " In " + e["editors"] + " (Eds.), ", ""))
        segs.append((venue, "i"))
        bits = [str(x) for x in (e.get("edition"),) if x]
        if vol:
            bits.append(f"Vol. {vol}")
        if pages:
            bits.append(f"pp. {pages}")
        segs.append(((f" ({', '.join(bits)})" if bits else "") + ".", ""))
        if e.get("publisher"):
            segs.append((" " + end(e["publisher"]), ""))
    elif e.get("status") == "preprint":
        segs.append((end(title) + " ", ""))
        v = venue or "Preprint"
        v = v[0].lower() + v[1:] if v.lower().startswith("psyarxiv") else v
        if "preprint" not in v.lower():
            v += " preprint"
        segs.append((v + ",", "i"))
    else:
        segs.append((end(title) + " ", ""))
        if vol:
            segs.append((f"{venue}, {vol}", "i"))
            segs.append(((f", {pages}" if pages else "") + ".", ""))
        else:
            segs.append((end(venue) if venue else "", "i"))
            if pages:
                segs[-1] = (venue + ",", "i")
                segs.append((f" {pages}.", ""))
        if "advance online" in notes.lower():
            segs.append((" Advance online publication.", ""))
    if link:
        segs.append((" ", ""))
        segs.append((link, "link"))
    for note in [n.strip() for n in notes.split(";") if "*" in n]:
        segs.append(("\n", ""))
        segs.append((re.sub(r"^(\*+)\s+", r"\1", note), "i"))
    return [s for s in segs if s[0]]


def preview(segs) -> str:
    out = []
    for text, fmt in segs:
        out.append({"b": f"**{text}**", "i": f"_{text}_", "link": f"<{text}>"}.get(fmt, text))
    return "".join(out).replace("\n", "\n    ")


# --------------------------------------------------------------------------- commands

def cv_path(arg: str | None) -> Path:
    p = arg or os.environ.get("CV_DOCX") or DEFAULT_CV
    if re.match(r"^[A-Za-z]:[\\/]", p):  # Windows path given → WSL path
        p = "/mnt/" + p[0].lower() + "/" + p[3:].replace("\\", "/")
    path = Path(p)
    if not path.exists():
        sys.exit(f"CV not found: {path}")
    return path


def get_entry(pid: str) -> dict:
    pubs = load_pubs()
    if pid not in pubs:
        sys.exit(f"no entry with id '{pid}' in {PUBS.name}")
    return pubs[pid]


def trailing_lines(p) -> list:
    """Runs from the first line break on (extra lines such as '- selected as Editor's Choice paper -')."""
    runs = [r for r in p.iter(W + "r")]
    for k, r in enumerate(runs):
        if r.find(W + "br") is not None:
            return [copy.deepcopy(x) for x in runs[k:]]
    return []


def renumber_after_removal(entries, removed_num: int) -> None:
    for p in entries:
        n = CV.number(p)
        if n is not None and n > removed_num:
            CV.set_number(p, n - 1)


def insert_top(cv: CV, sec: str, e: dict):
    key, (heading, entries) = cv.section(sec)
    nums = [n for n in map(CV.number, entries) if n is not None]
    num = max(nums, default=0) + 1
    template = entries[0] if entries else heading
    p = cv.build(segments(e), template, num)
    heading.addnext(p)
    return key, num


def finish(cv: CV, args, changes: list[str]) -> None:
    if not args.no_date:
        old = cv.set_date(dt.date.today())
        if old and old != ordinal_date(dt.date.today()):
            changes.append(f"date line: {old} → {ordinal_date(dt.date.today())}")
    print("\n".join(changes))
    if args.dry_run:
        print("(dry run — nothing written)")
        return
    backup = cv.save(ignore_lock=args.ignore_lock)
    print(f"saved {cv.path}\nbackup {backup}")


def cmd_list(args):
    cv = CV(cv_path(args.cv))
    for key, (h, entries) in cv.sections().items():
        if args.section and not key.startswith(args.section.lower().rstrip("s")):
            continue
        print(f"== {key}: {ptext(h)}")
        for p in entries:
            print("  " + ptext(p)[:160])


def cmd_find(args):
    cv = CV(cv_path(args.cv))
    q = " ".join(args.query)
    doi = re.search(r"10\.\d{4,9}/\S+", q)
    words = [w for w in norm(q).split() if len(w) > 2]
    for key, (_, entries) in cv.sections().items():
        for p in entries:
            t = ptext(p)
            if doi and doi.group(0).lower().rstrip(".") in t.lower():
                hit = True
            else:
                nt = norm(t)
                hit = bool(words) and sum(w in nt for w in words) >= max(1, round(0.8 * len(words)))
            if hit:
                print(f"[{key} {CV.number(p)}] {t[:220]}")


def cmd_render(args):
    e = get_entry(args.id)
    print(f"section: {target_section(e)}")
    print(preview(segments(e)))


def cmd_add(args):
    cv = CV(cv_path(args.cv))
    e = get_entry(args.id)
    sec = args.section or target_section(e)
    key, num = insert_top(cv, sec, e)
    finish(cv, args, [f"added as {key} {num}: {preview(segments(e))}"])


def cmd_replace(args):
    cv = CV(cv_path(args.cv))
    e = get_entry(args.id)
    old_key, old_p = cv.entry(args.section, args.num)
    new_key = cv.section(args.to or target_section(e))[0]
    changes = [f"removed {old_key} {args.num}: {ptext(old_p)[:200]}"]
    tail = trailing_lines(old_p)
    if tail and not any(f == "" and t == "\n" for t, f in segments(e)):
        changes.append("kept the extra line(s) under the old entry: "
                       + " / ".join(filter(None, ("".join(x.text or "" for x in r.iter(W + "t")) for r in tail))))
    else:
        tail = []
    if new_key == old_key:
        p = cv.build(segments(e), old_p, args.num)
        for r in tail:
            p.append(r)
        old_p.addprevious(p)
        old_p.getparent().remove(old_p)
        changes.append(f"replaced in place as {new_key} {args.num}: {preview(segments(e))}")
    else:
        entries = cv.section(old_key)[1][1]
        old_p.getparent().remove(old_p)
        renumber_after_removal(entries, args.num)
        key, num = insert_top(cv, new_key, e)
        new_p = cv.section(key)[1][1][0]
        for r in tail:
            new_p.append(r)
        changes.append(f"(later {old_key} entries renumbered)")
        changes.append(f"added as {key} {num}: {preview(segments(e))}")
    finish(cv, args, changes)


def replace_text(p, old: str, new: str) -> bool:
    """Replace the first occurrence of `old` in the paragraph text, even across runs (formatting of the first
    affected run is used for `new`)."""
    ts = list(p.iter(W + "t"))
    full = "".join(t.text or "" for t in ts)
    i = full.find(old)
    if i < 0:
        return False
    j, pos, done = i + len(old), 0, False
    for t in ts:
        s = t.text or ""
        a, b = pos, pos + len(s)
        pos = b
        if b <= i or a >= j:
            continue
        lo, hi = max(i, a) - a, min(j, b) - a
        t.text = s[:lo] + ("" if done else new) + s[hi:]
        t.set(XML_SPACE, "preserve")
        done = True
    return True


def cmd_fix(args):
    cv = CV(cv_path(args.cv))
    key, p = cv.entry(args.section, args.num)
    before = ptext(p)
    if not replace_text(p, args.old, args.new):
        sys.exit(f"'{args.old}' not found in {key} {args.num}: {before[:200]}")
    finish(cv, args, [f"{key} {args.num}: '{args.old}' → '{args.new}'", "now: " + ptext(p)[-220:]])


def cmd_remove(args):
    cv = CV(cv_path(args.cv))
    key, p = cv.entry(args.section, args.num)
    entries = cv.section(key)[1][1]
    p.getparent().remove(p)
    renumber_after_removal(entries, args.num)
    finish(cv, args, [f"removed {key} {args.num}: {ptext(p)[:200]}", f"(later {key} entries renumbered)"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cv")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list"); s.add_argument("section", nargs="?"); s.set_defaults(f=cmd_list)
    s = sub.add_parser("find"); s.add_argument("query", nargs="+"); s.set_defaults(f=cmd_find)
    s = sub.add_parser("render"); s.add_argument("id"); s.set_defaults(f=cmd_render)
    for name, fn in (("add", cmd_add), ("replace", cmd_replace), ("remove", cmd_remove), ("fix", cmd_fix)):
        s = sub.add_parser(name)
        if name in ("replace", "remove", "fix"):
            s.add_argument("section"); s.add_argument("num", type=int)
        if name == "fix":
            s.add_argument("old"); s.add_argument("new")
        if name in ("add", "replace"):
            s.add_argument("id")
        if name == "add":
            s.add_argument("--section", help="override the target section")
        if name == "replace":
            s.add_argument("--to", help="override the target section")
        s.add_argument("--dry-run", action="store_true")
        s.add_argument("--no-date", action="store_true")
        s.add_argument("--ignore-lock", action="store_true",
                       help="write even though Word's ~$ lock file exists (only if Word has the CV closed)")
        s.set_defaults(f=fn)
    args = ap.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
