# fritzguenther.de

Source of Fritz Günther's academic homepage. A small Python script turns Markdown pages and YAML data
into a static site; GitHub Actions builds and publishes it to GitHub Pages on every push to `main`.

## Where things are

| What | File |
|---|---|
| Home-page intro text | `content/home.md` |
| Headline, research themes on the home page | `site.yaml` |
| Topic filter on the publications page | `site.yaml` (`publication_topics`) + `topics:` on each publication |
| Co-author network on the publications page | built automatically from the author lists in `data/publications.yaml` (`coauthor_network` in `build.py`, drawn by `static/js/coauthors.js`; colours = the home-page `themes`) |
| Name, position, e-mail, profile links, current projects | `data/profile.yaml` |
| Publications | `data/publications.yaml` (field reference at the top of the file) |
| Other pages (CV, Data & Resources, Media, …) | `content/*.md` — front matter: `title`, `nav_order` (top menu), `parent` (sub-page), `summary` |
| Design | `templates/*.html`, `static/css/site.css`, `static/js/site.js` |
| Portrait, fonts | `static/img/`, `static/fonts/` |

CV, Contact, Media and Profiles are built from lists at the top of their files (`timeline:` and `cards:`,
see the comments there and in `templates/page.html`): to add a media item, copy one card block.
Resource sub-pages carry a `kind:` (e.g. Dataset) shown as a label on their tile.

A page without `nav_order` and without `parent` is not in the menu (e.g. `imprint.md`, linked in the footer).

## Editing

Edit the files directly on github.com (pencil icon) — the site updates about a minute after you commit.
Or locally, then `git commit` and `git push`.

**New publication:** in Claude Code, just say e.g. "add this paper: 10.xxxx/…" — the
`add-publication` skill (`.claude/skills/add-publication/`) fetches the metadata, checks for duplicates
(e.g. the preprint version), shows you a preview, and commits + pushes after your OK.
By hand: copy an existing entry in `data/publications.yaml` and adapt it; always put author names in quotes.

## Local preview

Python runs in WSL:

```bash
wsl -e bash -c 'python3.12 -m venv ~/.venvs/homepage && ~/.venvs/homepage/bin/pip install -r /mnt/g/Berlin/Homepage/requirements.txt'
```

```bash
wsl -e bash -c 'cd /mnt/g/Berlin/Homepage && ~/.venvs/homepage/bin/python build.py && ~/.venvs/homepage/bin/python -m http.server 8000 -d site'
```

Then open http://localhost:8000. In Claude Code the preview config `homepage` (`.claude/launch.json`) does the same.
`build.py --check` only validates the data (missing fields, duplicate IDs/DOIs, suspicious author names).

## Helpers

- `scripts/pub_tool.py` — `fetch <doi>`, `find <doi|words>`, `add <file>`, `update <id> <file>`, `show <id>`, `format`
- `scripts/check_publications.py` — extra consistency checks (link sanity)
- `scripts/import_gsites.py` — one-off importer used to migrate from the old Google Site
