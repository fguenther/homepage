---
name: add-publication
description: Add a new publication to Fritz Günther's homepage (fritzguenther.de) and his long-format Word CV (G:/Bewerbungen/Anlagen/CV_FritzGuenther_longformat.docx), or update an existing entry — e.g. a preprint or accepted paper that is now published, a new DOI, PDF or data/OSF link. Use whenever the user mentions a new paper, an acceptance, a publication, a preprint, gives a DOI / arXiv / PsyArXiv / journal link, pastes a reference or shares a paper PDF and it should go on the website or publication list — even if they don't say "homepage" or "skill".
---

# Add or update a publication on fritzguenther.de

The site is a static site in this repository. Publications live in **`data/publications.yaml`**;
`build.py` renders them, GitHub Actions deploys every push to `main`. The same entry also goes into his
**long-format CV**, `G:\Bewerbungen\Anlagen\CV_FritzGuenther_longformat.docx` (outside this repo, not in git).
Your job: get the entry right, show it to Fritz, and publish to the website and write the CV only after his OK.

## Environment

- Python runs in WSL (no Python on Windows). Venv: `~/.venvs/homepage`. If it is missing:
  `wsl -e bash -c 'python3.12 -m venv ~/.venvs/homepage && ~/.venvs/homepage/bin/pip install -r /mnt/g/Berlin/Homepage/requirements.txt'`
- Run tools as `wsl -e bash -c 'cd /mnt/g/Berlin/Homepage && ~/.venvs/homepage/bin/python <script> <args>'`
  (adjust `/mnt/g/Berlin/Homepage` if the repo has moved: `wslpath -u "<windows path>"`).
- Helper: `scripts/pub_tool.py` — `fetch <doi>`, `find <doi|title words>`, `add <file>`, `update <id> <file>`, `show <id>`.
- Helper: `scripts/cv_tool.py` — `find`, `render <id>`, `add <id>`, `replace <section> <num> <id>`, `fix`, `remove`,
  `list [section]` (see "CV" below). Needs `lxml` in the venv (not in requirements.txt, the site build doesn't
  need it): `~/.venvs/homepage/bin/pip install lxml`.
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
  it moves the entry if status/year changed. Keep the existing `id` (it is the link anchor), even if the year changes.

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
  topics: [llm, novel]                  # keys from site.yaml → publication_topics
```
Book chapters / proceedings: add `type: chapter` or `type: proceedings` (and `editors`, `publisher`
where known), `venue` = book or proceedings title.

### 4b. Assign topics
Every entry gets `topics:` — one or more keys from `publication_topics` in `site.yaml`
(e.g. `dsm`, `llm`, `vision`, `grounding`, `compounds`, `novel`, `production`, `emotion`, `crossling`,
`methods`). Pick them from title and abstract (usually 1–3; `methods` for datasets, norms, tools and
methods papers) and mention your choice to Fritz when showing the entry. `build.py --check` rejects unknown
keys and warns about entries without topics. A new topic = a new line in `site.yaml`, only if Fritz asks.

### 5. Build and show it
1. `build.py --check` must print `OK` with no warnings about the new entry (a warning like
   `author 'L.' doesn't look like 'Last, F.'` means a quoting problem).
2. Start the preview with `preview_start` name `homepage` (from `.claude/launch.json`; it builds and serves
   on port 8000) and open `http://localhost:8000/publications/#<id>` — the entry is highlighted.
   Take a screenshot so Fritz sees the rendered entry. If the entry is recent it also appears on the home page.
3. Show the YAML diff: `git diff data/publications.yaml`.
4. Show the CV plan (see "CV" below): the rendered CV entry from `cv_tool.py render <id>`, the section, and
   whether it is a new entry or replaces CV entry *N*.

### 6. Publish — only after Fritz says so
- **CV first** (it can fail if the file is open in Word): run the planned `cv_tool.py add` / `replace`.
  If it says the CV is open in Word, ask Fritz to close it and run again. If he has closed it and the
  `~$` lock file is stale, check from PowerShell that nothing holds the file
  (`[IO.File]::Open(<path>,'Open','ReadWrite','None').Close()` succeeds) and rerun with `--ignore-lock`. Report the section and number.
- `git add data/publications.yaml && git commit -m "Add publication: <short title>"`
  (or `"Update publication: <short title> (now published in <venue>)"`), then `git push`.
- The GitHub Action deploys in ~1 minute. Tell him the live link:
  `https://fritzguenther.de/publications/#<id>`.
- If the push is rejected (remote has newer commits): `git pull --rebase`, re-run `build.py --check`, push again.

## CV (long-format Word CV)

`scripts/cv_tool.py` edits the .docx directly. It writes entries in the CV's own style (APA-like; **Günther, F.**
bold; journal + volume italic; DOI as a clickable link; equal-contribution notes as an italic extra line).
Each publication section is numbered **descending, newest on top**, and the numbers are typed text.
Run it like `pub_tool.py`; the CV path is built in (`--cv <path>` overrides it).

Sections (`<section>` argument, from the heading): `journal`, `proceedings`, `chapters`, `preprints`, `books`,
`preregistrations`, `software`. `render`/`add` choose the section from the YAML: `type: chapter` → chapters,
`type: proceedings` → proceedings, `status: preprint` → preprints, everything else (incl. accepted) → journal.

1. **Look it up**: `cv_tool.py find <doi>` and `cv_tool.py find <a few title words>` (the preprint DOI may
   differ from the journal DOI, so always try title words too).
2. **Decide**:
   - Not in the CV → `cv_tool.py add <id>`: new top entry of its section, number = highest + 1.
   - In the CV, same section (e.g. accepted → published in the journal list) →
     `cv_tool.py replace journal <N> <id>`: replaced in place, keeps number *N*.
   - In the CV as a preprint, now accepted/published → `cv_tool.py replace preprints <N> <id>`: removed from the
     preprints (numbers above *N* move down by one) and added on top of the journal list (or `--to <section>`).
   - **The CV entry may already be ahead of the website** (Fritz sometimes updates the CV by hand: volume,
     pages, final DOI). Compare the old CV text with `render`; if the CV has information the YAML lacks, put it
     into the YAML first (it belongs on the website too) or skip the CV, and mention it, never downgrade the CV.
   - Only a detail is wrong/outdated (page or article number, "(in press)" → year) → prefer
     `cv_tool.py fix <section> <N> "<old text>" "<new text>"`: edits the text in place and keeps hand-made
     formatting and author lists that the YAML may have shortened.
   - Extra lines under an old entry (e.g. "- selected as Editor's Choice paper -") are kept automatically by `replace`.
3. Every write also sets the date line on the title page ("November 17th, 2026") to today (`--no-date` to keep
   it) and first puts a backup in `G:\Bewerbungen\Anlagen\.cv_backups\` (last 15 kept). Use `--dry-run`
   to see what would happen. To undo: copy the latest backup back.
4. Things the tool does **not** do: the PDF version (`CV_FritzGuenther_longformat.pdf`), the German CV
   (`..._DE.docx`), the short `CV_FritzGuenther_homepage.docx`, the table-of-contents page numbers, and
   the citation counts. Mention them; if Fritz wants the PDF refreshed, export it with Word (after the
   CV is closed in Word):
   ```powershell
   $w = New-Object -ComObject Word.Application; $n = $w.Documents.Count
   $d = $w.Documents.Open("G:\Bewerbungen\Anlagen\CV_FritzGuenther_longformat.docx", $false, $true)
   $d.Fields.Update() | Out-Null; $d.TablesOfContents | ForEach-Object { $_.UpdatePageNumbers() }
   $d.ExportAsFixedFormat("G:\Bewerbungen\Anlagen\CV_FritzGuenther_longformat.pdf", 17); $d.Close($false)
   if ($n -eq 0) { $w.Quit() }
   ```
   (Never call `Quit()` when Word already had documents open: that would close Fritz's other documents.)
5. If the file is not where expected (moved/renamed), ask Fritz for the new path and use `--cv`.

## Several papers at once
Handle them one by one through steps 1–4, then build, show all, and make one commit
("Add N publications") after a single OK. In the CV, add them oldest first, so the newest ends up on top.

## Related requests
- "Feature this on the home page" → `featured: true` on the entry (when any entry is featured, the
  home page shows featured entries instead of the most recent ones).
- Media coverage of a paper → `content/media-coverage.md`.
- Removing an entry → delete it from the YAML, show the diff, same publish rule; in the CV
  `cv_tool.py remove <section> <N>` (renumbers the rest).
- "Only the CV" / "only the website" → do just that part.
