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
  // one active chip per row: year/status row (data-tags) and topic row (data-topics)
  const filter = { year: 'all', topic: 'all' };
  const attr = { year: 'tags', topic: 'topics' };

  function apply() {
    const terms = search.value.toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    pubs.forEach(p => {
      const ok = Object.keys(filter).every(k => filter[k] === 'all' ||
                   (p.dataset[attr[k]] || '').split(' ').includes(filter[k])) &&
                 terms.every(t => p._text.includes(t));
      p.hidden = !ok; if (ok) shown++;
    });
    groups.forEach(g => { g.hidden = !g.querySelector('.pub:not([hidden])'); });
    count.textContent = shown;
    empty.hidden = shown > 0;
  }
  function select(kind, f) {
    const row = document.querySelector(`.chips[data-kind="${kind}"]`);
    if (!row) return;
    const chip = row.querySelector(`.chip[data-f="${f}"]`) || row.querySelector('.chip');
    row.querySelectorAll('.chip').forEach(c => { c.classList.remove('on'); c.setAttribute('aria-pressed', 'false'); });
    chip.classList.add('on'); chip.setAttribute('aria-pressed', 'true');
    filter[kind] = chip.dataset.f; apply();
  }
  chips.forEach(chip => chip.addEventListener('click', () => select(chip.closest('.chips').dataset.kind, chip.dataset.f)));
  // topic labels on each entry select that topic
  document.querySelectorAll('.pub .tp a[data-topic]').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); select('topic', a.dataset.topic);
    document.querySelector('.toolbar').scrollIntoView({ behavior: 'smooth' });
  }));
  search.addEventListener('input', apply);
  // allow links like /publications/?q=ViSpa or ?topic=llm
  const params = new URLSearchParams(location.search);
  if (params.get('q')) search.value = params.get('q');
  if (params.get('topic')) select('topic', params.get('topic'));
  if (params.get('q')) apply();
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

// --- e-mail links: the address is stored reversed/obfuscated in the HTML to deter harvesters ---
document.querySelectorAll('a.js-mail[data-m]').forEach(a => {
  const addr = a.dataset.m.replace(/ ta /g, '@').replace(/ tod /g, '.').split('').reverse().join('');
  a.href = 'mailto:' + addr;
});
