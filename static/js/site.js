// Small progressive enhancements; the site works without JavaScript.

// --- mobile menu -----------------------------------------------------------
(() => {
  const nav = document.querySelector('.topnav'), btn = nav && nav.querySelector('.menu-btn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', open);
  });
})();

// --- "semantic space" animation in the header band ---------------------------
(() => {
  const c = document.querySelector('.band .space');
  if (!c) return;
  const x = c.getContext('2d');
  const home = document.querySelector('.band--home') !== null;
  const words = ['dog', 'cat', 'wolf', 'house', 'home', 'river', 'bank', 'money', 'light', 'lamp',
                 'sun', 'moon', 'idea', 'thought', 'word', 'name', 'sea', 'boat', 'apple', 'tree'];
  const animate = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  let W, H, pts, dpr, visible = true;

  function init() {
    dpr = window.devicePixelRatio || 1;
    const r = c.getBoundingClientRect();
    W = c.width = r.width * dpr; H = c.height = r.height * dpr;
    const n = Math.round(Math.min(80, (r.width * r.height) / (home ? 9000 : 6000)));
    pts = Array.from({ length: n }, (_, i) => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - .5) * .15 * dpr, vy: (Math.random() - .5) * .15 * dpr,
      w: home && r.width > 860 && i < words.length ? words[i] : null,  // labels would collide with text on phones
    }));
  }
  function draw() {
    x.clearRect(0, 0, W, H);
    const d = 140 * dpr;
    for (const p of pts) { p.x = (p.x + p.vx + W) % W; p.y = (p.y + p.vy + H) % H; }
    x.lineWidth = dpr;
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
      const a = pts[i], b = pts[j], dist = Math.hypot(a.x - b.x, a.y - b.y);
      if (dist < d) {
        x.strokeStyle = `rgba(120,160,200,${.18 * (1 - dist / d)})`;
        x.beginPath(); x.moveTo(a.x, a.y); x.lineTo(b.x, b.y); x.stroke();
      }
    }
    x.font = `${11 * dpr}px "IBM Plex Sans", sans-serif`;
    for (const p of pts) {
      x.fillStyle = p.w ? 'rgba(245,158,11,.75)' : 'rgba(140,175,210,.45)';
      x.beginPath(); x.arc(p.x, p.y, (p.w ? 2.4 : 1.6) * dpr, 0, 7); x.fill();
      if (p.w) { x.fillStyle = 'rgba(200,215,230,.35)'; x.fillText(p.w, p.x + 6 * dpr, p.y + 4 * dpr); }
    }
  }
  function loop() { if (visible) draw(); if (animate) requestAnimationFrame(loop); }
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(c);
  addEventListener('resize', () => { init(); draw(); });
  init(); draw(); loop();
})();

// --- publications: filter chips, search, BibTeX toggles ----------------------
(() => {
  document.querySelectorAll('.pub .toggle').forEach(btn => btn.addEventListener('click', () => {
    const pub = btn.closest('.pub'), box = pub.querySelector('.' + btn.dataset.target);
    box.hidden = !box.hidden;
    btn.setAttribute('aria-expanded', !box.hidden);
    pub.classList.toggle('open', !!pub.querySelector('.abs:not([hidden]), .bib:not([hidden])'));
  }));

  const chips = document.querySelectorAll('.chip'), search = document.querySelector('.search');
  if (!chips.length) return;
  const pubs = [...document.querySelectorAll('.pubgroup .pub')];
  const groups = document.querySelectorAll('.pubgroup');
  const count = document.getElementById('pubcount'), empty = document.querySelector('.empty');
  pubs.forEach(p => { p._text = p.textContent.toLowerCase(); });
  // Several chips per row can be on; "All" (= nothing selected) clears its row.
  // AND (default): an entry needs every selected topic and one of the selected years
  //                (a paper has only one year, so years always count as alternatives).
  // OR:            an entry matching any selected chip is shown.
  // The search always narrows the result further.
  const filter = { year: new Set(), topic: new Set() };
  const attr = { year: 'tags', topic: 'topics' };
  const reset = document.querySelector('.reset');
  let mode = 'and';
  const values = (p, k) => (p.dataset[attr[k]] || '').split(' ');
  function chipsMatch(p) {
    const yearSel = filter.year.size, topicSel = filter.topic.size;
    if (!yearSel && !topicSel) return true;
    const yearHit = values(p, 'year').some(v => filter.year.has(v));
    if (mode === 'or') return yearHit || values(p, 'topic').some(v => filter.topic.has(v));
    const topics = values(p, 'topic');
    return (!yearSel || yearHit) && [...filter.topic].every(t => topics.includes(t));
  }

  function apply() {
    const terms = search.value.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    pubs.forEach(p => {
      const ok = chipsMatch(p) && terms.every(t => p._text.includes(t));
      p.hidden = !ok; if (ok) shown++;
    });
    groups.forEach(g => { g.hidden = !g.querySelector('.pub:not([hidden])'); });
    count.textContent = shown;
    empty.hidden = shown > 0;
    if (reset) reset.hidden = !(filter.year.size || filter.topic.size || terms.length);
  }
  function render(kind) {
    const row = document.querySelector(`.chips[data-kind="${kind}"]`);
    if (!row) return;
    row.querySelectorAll('.chip').forEach(c => {
      const on = c.dataset.f === 'all' ? !filter[kind].size : filter[kind].has(c.dataset.f);
      c.classList.toggle('on', on); c.setAttribute('aria-pressed', on);
    });
  }
  function toggle(kind, f) {
    if (f === 'all') filter[kind].clear();
    else if (filter[kind].has(f)) filter[kind].delete(f);
    else filter[kind].add(f);
    render(kind); apply();
  }
  function only(kind, values) {
    const row = document.querySelector(`.chips[data-kind="${kind}"]`);
    filter[kind] = new Set(values.filter(v => row && row.querySelector(`.chip[data-f="${v}"]`)));
    render(kind); apply();
  }
  chips.forEach(chip => chip.addEventListener('click', () => toggle(chip.closest('.chips').dataset.kind, chip.dataset.f)));
  // a topic label on an entry shows just that topic
  document.querySelectorAll('.pub .tp a[data-topic]').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); only('topic', [a.dataset.topic]);
    document.querySelector('.toolbar').scrollIntoView({ behavior: 'smooth' });
  }));
  if (reset) reset.addEventListener('click', () => {
    search.value = ''; only('year', []); only('topic', []);
  });
  search.addEventListener('input', apply);
  const combine = document.querySelectorAll('.combine button');
  function setMode(m) {
    mode = m === 'or' ? 'or' : 'and';
    combine.forEach(b => { const on = b.dataset.m === mode; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
    apply();
  }
  combine.forEach(b => b.addEventListener('click', () => setMode(b.dataset.m)));
  // allow links like /publications/?q=ViSpa, ?topic=llm or ?topic=llm,novel&year=2025,2024&match=or
  const params = new URLSearchParams(location.search);
  if (params.get('q')) search.value = params.get('q');
  if (params.get('match')) setMode(params.get('match'));
  const list = k => (params.get(k) || '').split(',').filter(Boolean);
  if (list('topic').length) only('topic', list('topic'));
  if (list('year').length) only('year', list('year'));
  apply();
})();

// --- YouTube embeds: load only after a click (no requests to Google before consent) ---
(() => {
  document.querySelectorAll('.video[data-youtube]').forEach(el => {
    const id = el.dataset.youtube;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'video-consent';
    btn.innerHTML = '<span class="play" aria-hidden="true">▶</span><span>Load video from YouTube</span>' +
                    '<small>By loading the video, data is sent to Google/YouTube.</small>';
    btn.addEventListener('click', () => {
      el.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1"
        title="YouTube video" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>`;
    });
    el.appendChild(btn);
  });
})();

// --- co-author network: load the graph library and script only when the stage comes into view ---
(() => {
  const st = document.getElementById('coauthor-stage');
  if (!st) return;
  const load = src => new Promise((ok, fail) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = fail; document.head.appendChild(s); });
  const go = () => load(st.dataset.lib).then(() => load(st.dataset.script))
    .catch(() => { document.getElementById('stage-msg').textContent = 'The network could not be loaded.'; });
  if (!('IntersectionObserver' in window)) return go();
  const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { io.disconnect(); go(); } }, { rootMargin: '300px' });
  io.observe(st);
})();
