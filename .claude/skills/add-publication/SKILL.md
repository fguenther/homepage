---
name: add-publication
description: Add a new publication to Fritz Günther's homepage (fritzguenther.de) or update an existing entry — e.g. a preprint or accepted paper that is now published, a new DOI, PDF or data/OSF link. Use whenever the user mentions a new paper, an acceptance, a publication, a preprint, gives a DOI / arXiv / PsyArXiv / journal link, pastes a reference or shares a paper PDF and it should go on the website or publication list — even if they don't say "homepage" or "skill".
---

# Add or update a publication on fritzguenther.de

The site is a static site in this repository. Publications live in **`data/publications.yaml`**;
`build.py` renders them, GitHub Actions deploys every push to `main`. Your job: get the entry right,
show it to Fritz, and publish only after his OK.

## Environment

- Python runs in WSL (no Python on Windows). Venv: `~/.venvs/homepage`. If it is missing:
  `wsl -e bash -c 'python3.12 -m venv ~/.venvs/homepage && ~/.venvs/homepage/bin/pip install -r /mnt/g/Berlin/Homepage/requirements.txt'`
- Run tools as `wsl -e bash -c 'cd /mnt/g/Berlin/Homepage && ~/.venvs/homepage/bin/python <script> <args>'`
  (adjust `/mnt/g/Berlin/Homepage` if the repo has moved: `wslpath -u "<windows path>"`).
- Helper: `scripts/pub_tool.py` — `fetch <doi>`, `find <doi|title words>`, `add <file>`, `update <id> <file>`, `show <id>`.
- git runs on Windows (normal Bash/PowerShell tool), remote `origin` = github.com/fguenther/homepage.

## Workflow

### 1. Collect the metadata
Depending on what Fritz gives you:
- **DOI / doi.org link / arXiv / PsyArXiv link** → `pub_tool.py fetch <doi>` (Crossref → DataCite → OSF).
  arXiv IDs become DOIs as `10.48550/arXiv.<id>`; PsyArXiv `osf.io/preprints/psyarxiv/<id>` → `10.31234/osf.io/<id>`.
- **Journal landing page without DOI** → read the page (WebFetch or browser) and take title, authors, venue, year, volume/issue/pages.
- **PDF** → read the first page for title, authors, venue, DOI; then `fetch` the DOI if there is one.
- **Pasted reference** → parse it; look up the DOI if one is given.

Then check and fix the draft — fetched metadata is often imperfect:
- **Author order and spelling** must match the paper itself. OSF metadata in particular can have the wrong
  order or split compound surnames ("Tomás, C. M." instead of "Martinez-Tomás, C."). `fetch` already reuses
  spellings found elsewhere in the file and prints a `note:` for each change — check those.
- Authors are `"Last, F. M."`. Fritz is always **`Günther, F.`** (never "Guenther").
  Equal-contribution markers go directly after the initials (`"Smith, J.*"`) plus a `notes:` line.
- Very long author lists (> 20) are shortened to first 6, `…`, Günther, `…`, last — `fetch` does this.
- Title: keep the paper's capitalisation; strip HTML/LaTeX remnants.
- Pages as `930–944` (en dash), article numbers as `"106440"`.

### 2. Is it already on the list?
Always run `pub_tool.py find <doi>` **and** `pub_tool.py find <a few title words>` first.
Typical cases:
- A **preprint or accepted** paper that is now **published** → *update* that entry: set `status: published`,
  `year`, `venue`, `volume`, `issue`, `pages`, new `doi` and `url`; keep `data`, `extra_links`, `notes`.
  The preprint link can move to `extra_links: [{label: Preprint, url: ...}]` if Fritz wants to keep it.
  Titles often change slightly between preprint and publication — ask if a fuzzy match is ambiguous.
- Accepted → in press/online first: `status: published` with year; "Advance online publication" goes in `notes`.
- Not on the list → *add*.

### 3. Ask only for what is missing
Fritz's entries usually have: main link (`url`, normally the DOI link), sometimes an author copy (`pdf`,
often a Google Drive or preprint link), and a "Data, Material, & Scripts" link (`data`, OSF/GitHub).
Ask in one short message for whatever is missing and plausible (typically: data link? author PDF?).
Don't block on it — if he doesn't know yet, add without and he can tell you later.

### 4. Write the entry
Write the entry (one YAML list item, or a plain mapping) to a temp file in the scratchpad, then
- new: `pub_tool.py add <file>` — it creates the `id` (`<firstauthor><year><firstword>`) if absent,
  refuses duplicates and inserts the entry in the right group (accepted → preprints → years, newest first),
  alphabetically by first author.
- existing: `pub_tool.py update <id> <file>` with only the changed fields (`field: null` deletes a field);
  it moves the entry if status/year changed.

Field reference (see the comment block at the top of `data/publications.yaml` for the full list):

```yaml
- id: guenther2026crosslinguistic   # optional on add
  status: published                 # accepted | preprint | published
  year: 2026                        # not for accepted
  authors: ["Günther, F.", "Petrenco, A.", "Gatti, D."]   # always quote — names contain commas
  title: Cross-linguistic zero-shot communication via ad-hoc pseudowords
  venue: Cognition
  volume: "271"
  issue: "2"
  pages: "106440"
  doi: 10.1016/j.cognition.2026.106440
  url: https://doi.org/10.1016/j.cognition.2026.106440
  pdf: https://drive.google.com/...      # author copy
  data: https://osf.io/xxxxx/            # data, material & scripts
  extra_links: [{label: Trained model, url: https://huggingface.co/...}]
  notes: "* equal contribution"
```
Book chapters / proceedings: add `type: chapter` or `type: proceedings` (and `editors`, `publisher`
where known), `venue` = book or proceedings title.

### 5. Build and show it
1. `build.py --check` must print `OK` with no warnings about the new entry (a warning like
   `author 'L.' doesn't look like 'Last, F.'` means a quoting problem).
2. Start the preview with `preview_start` name `homepage` (from `.claude/launch.json`; it builds and serves
   on port 8000) and open `http://localhost:8000/publications/#<id>` — the entry is highlighted.
   Take a screenshot so Fritz sees the rendered entry. If the entry is recent it also appears on the home page.
3. Show the YAML diff: `git diff data/publications.yaml`.

### 6. Publish — only after Fritz says so
- `git add data/publications.yaml && git commit -m "Add publication: <short title>"`
  (or `"Update publication: <short title> (now published in <venue>)"`), then `git push`.
- The GitHub Action deploys in ~1 minute. Tell him the live link:
  `https://fritzguenther.de/publications/#<id>`.
- If the push is rejected (remote has newer commits): `git pull --rebase`, re-run `build.py --check`, push again.

## Several papers at once
Handle them one by one through steps 1–4, then build, show all, and make one commit
("Add N publications") after a single OK.

## Related requests
- "Feature this on the home page" → `featured: true` on the entry (when any entry is featured, the
  home page shows featured entries instead of the most recent ones).
- Media coverage of a paper → `content/media-coverage.md`.
- Removing an entry → delete it from the YAML, show the diff, same publish rule.
