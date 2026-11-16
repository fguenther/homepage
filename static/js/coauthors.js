/* Co-author network on the publications page.
   Data: /coauthors.json, written by build.py from data/publications.yaml.
   Encodings (kept apart on purpose):
     dot size + line thickness = number of joint papers (lines from the centre: with me;
                                 lines between co-authors: papers they share on my list; single ones faint)
     colour                    = home-page research theme most joint papers belong to; split left/right
                                 when the joint papers clearly span two themes
     selection                 = everything unrelated fades; the selected person's lines take their colour
   Loaded by site.js once the stage scrolls into view; needs vis-network (static/js/vendor). */
(async () => {
  const stage = document.getElementById('coauthor-stage');
  const $ = id => document.getElementById(id);
  let D;
  try { D = await (await fetch(stage.dataset.src)).json(); }
  catch (e) { $('stage-msg').textContent = 'The network could not be loaded.'; return; }

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const rgba = (hex, a) => { const v = parseInt(hex.slice(1), 16); return `rgba(${v >> 16},${(v >> 8) & 255},${v & 255},${a})`; };
  const FONT = '"IBM Plex Sans", system-ui, sans-serif', STAGE = '#0b1622';
  const ME = 'me', N = D.nodes, maxN = Math.max(...N.map(n => n.n));
  const s01 = n => Math.sqrt((n - 1) / Math.max(1, maxN - 1));          // 0 (1 paper) … 1 (most papers)
  const size = n => 6 + 15 * s01(n);
  const width = n => 0.7 + 8.5 * s01(n);
  const colorOf = n => D.themes[n.theme >= 0 ? n.theme : D.themes.length - 1].color;
  const color2Of = n => n.theme2 >= 0 ? D.themes[n.theme2].color : null;
  const initials = name => name.split(/\s+/).filter(w => /^[A-ZÀ-Ý]/.test(w)).map(w => w[0]).slice(-2).join('');
  const surname = n => n.sort.split(',')[0];
  const plural = k => k === 1 ? 'joint paper' : 'joint papers';
  N.forEach((n, i) => { n.id = i; n.set = new Set(n.papers); });

  // partners among co-authors: pairs[i] = [[j, count], …]
  const pairs = N.map(() => []);
  D.edges.forEach(([a, b, k]) => { pairs[a].push([b, k]); pairs[b].push([a, k]); });
  pairs.forEach(p => p.sort((x, y) => y[1] - x[1]));

  // ---------- legend ----------
  const used = new Set(N.map(n => n.theme >= 0 ? n.theme : D.themes.length - 1));
  const two = N.find(n => n.theme2 >= 0);
  $('net-key').innerHTML = D.themes.map((t, i) => used.has(i) ? `<span><i style="background:${t.color}"></i>${esc(t.title)}</span>` : '').join('')
    + (two ? `<span><i style="background:linear-gradient(90deg, ${D.themes[0].color} 50%, ${D.themes[2] ? D.themes[2].color : D.themes[1].color} 50%)"></i>two themes</span>` : '')
    + `<span>${[1, Math.round(maxN / 3), maxN].map(k => `<svg width="20" height="${Math.ceil(width(k)) + 2}" aria-hidden="true"><line x1="1" y1="50%" x2="19" y2="50%" stroke="rgba(255,255,255,.6)" stroke-width="${width(k)}" stroke-linecap="round"/></svg>`).join('')} 1–${maxN} joint papers</span>`;
  $('net-names').innerHTML = [...N].sort((a, b) => a.sort.localeCompare(b.sort)).map(n => `<option value="${esc(n.name)}">`).join('');

  // ---------- network ----------
  let focus = null;          // {kind: 'node'|'me'|'edge', ids: Set}
  let minPapers = 1;
  const nodeStyle = (n, on) => {
    const c = colorOf(n);
    return {
      color: { background: on ? c : rgba(c, 0.16), border: on ? rgba(c, 1) : rgba(c, 0.16),
               highlight: { background: c, border: '#ffffff' }, hover: { background: c, border: '#ffffff' } },
      shadow: { enabled: on, color: rgba(c, 0.7), size: 8 + size(n.n), x: 0, y: 0 },
    };
  };
  const meStyle = on => ({
    color: { background: '#ffffff', border: '#f59e0b', highlight: { background: '#ffffff', border: '#f59e0b' }, hover: { background: '#ffffff', border: '#fbbf24' } },
    shadow: { enabled: true, color: on ? 'rgba(245,158,11,.75)' : 'rgba(245,158,11,.25)', size: 30, x: 0, y: 0 },
  });
  const nodes = new vis.DataSet([
    Object.assign({ id: ME, label: D.me, x: 0, y: 0, fixed: true, shape: 'dot', size: 25, borderWidth: 4, borderWidthSelected: 5,
      font: { size: 17, face: FONT, color: '#ffffff', strokeWidth: 5, strokeColor: STAGE, bold: { face: FONT } }, title: D.me }, meStyle(true)),
    ...N.map(n => Object.assign({ id: n.id, label: '', x: n.x, y: n.y, shape: 'dot', size: size(n.n), borderWidth: 1.2, borderWidthSelected: 2.4,
      font: { size: 13, face: FONT, color: '#eef3f8', strokeWidth: 4, strokeColor: STAGE },
      title: `${n.name} · ${n.n} ${plural(n.n)}` }, nodeStyle(n, true))),
  ]);
  const EDGE = 'rgba(214,226,240,0.20)', EDGE_PAIR = 'rgba(214,226,240,0.30)', EDGE_ONE = 'rgba(214,226,240,0.075)', EDGE_FADE = 'rgba(214,226,240,0.03)';
  const pairColor = k => k >= 2 ? EDGE_PAIR : EDGE_ONE;
  const edges = new vis.DataSet([
    // centre → co-author: shorter for close collaborators
    ...N.map(n => ({ id: 'm' + n.id, from: ME, to: n.id, k: n.n, width: width(n.n),
      color: { color: EDGE, highlight: EDGE, hover: EDGE }, smooth: false, title: `${D.me} – ${n.name}: ${n.n} ${plural(n.n)}` })),
    // co-author ↔ co-author: every pair that appears together on one of my papers (single papers faint)
    ...D.edges.map(([a, b, k], i) => ({ id: 'p' + i, from: a, to: b, k,
      width: k >= 2 ? width(k) : 0.6, color: { color: pairColor(k), highlight: pairColor(k), hover: pairColor(k) },
      smooth: k >= 2 ? { enabled: true, type: 'curvedCW', roundness: 0.18 } : false, title: `${N[a].name} – ${N[b].name}: ${k} ${plural(k)}` })),
  ]);
  const network = new vis.Network($('network'), { nodes, edges }, {
    layout: { improvedLayout: false },
    physics: false,
    interaction: { hover: true, tooltipDelay: 120, zoomView: false, selectConnectedEdges: false, hoverConnectedEdges: false },
    edges: { selectionWidth: 0, hoverWidth: 0 },
  });
  network.once('afterDrawing', () => { stage.classList.add('ready'); });
  // two themes: paint the right half of the dot in the second colour
  network.on('afterDrawing', ctx => {
    const pos = network.getPositions(N.filter(n => n.theme2 >= 0 && n.n >= minPapers).map(n => n.id));
    for (const id in pos) {
      const n = N[id], on = !focus || focus.ids.has(n.id), r = size(n.n) - 0.6, { x, y } = pos[id];
      ctx.beginPath(); ctx.arc(x, y, r, -Math.PI / 2, Math.PI / 2); ctx.closePath();
      ctx.fillStyle = on ? color2Of(n) : rgba(color2Of(n), 0.16); ctx.fill();
    }
  });
  // faint guide rings: distance from the centre = number of joint papers
  network.on('beforeDrawing', ctx => {
    const px = 1 / network.getScale();
    ctx.save();
    ctx.lineWidth = px; ctx.setLineDash([2 * px, 5 * px]); ctx.strokeStyle = 'rgba(214,226,240,0.10)';
    ctx.font = `500 ${11 * px}px ${FONT}`; ctx.textAlign = 'left'; ctx.fillStyle = 'rgba(214,226,240,0.38)';
    for (const [k, r0] of D.rings || []) {
      if (k < minPapers) continue;
      const r = k === 1 ? r0 + 17 : r0;
      ctx.beginPath(); ctx.arc(0, 0, r, 0, 2 * Math.PI); ctx.stroke();
      const a = -Math.PI / 2 - 0.5;   // label up and to the left of the centre
      ctx.fillText(k === 1 ? '1 paper' : `${k}`, Math.cos(a) * r + 4 * px, Math.sin(a) * r - 4 * px);
    }
    ctx.restore();
  });

  // The page scrolls normally over the stage; zoom with Ctrl/⌘ + wheel or pinch (sends ctrlKey).
  $('network').addEventListener('wheel', ev => {
    if (!(ev.ctrlKey || ev.metaKey)) return;
    ev.preventDefault();
    const r = $('network').getBoundingClientRect(), p = network.DOMtoCanvas({ x: ev.clientX - r.left, y: ev.clientY - r.top });
    const s0 = network.getScale(), s1 = Math.min(4, Math.max(0.08, s0 * Math.exp(-ev.deltaY * 0.0022))), c = network.getViewPosition();
    network.moveTo({ scale: s1, position: { x: p.x - (p.x - c.x) * s0 / s1, y: p.y - (p.y - c.y) * s0 / s1 } });
    updateLabels(false);
  }, { passive: false });

  // names: close collaborators always, everyone when zoomed in or in the current selection;
  // font size is set in screen pixels (about 12.5 px whatever the zoom)
  let lastScale = null;
  function updateLabels(force) {
    const sc = network.getScale();
    if (!force && lastScale && Math.abs(sc / lastScale - 1) < 0.08) return;
    lastScale = sc;
    const z = sc >= 1.1, px = v => v / Math.min(1.6, sc);
    const named = $('network').clientWidth < 600 ? 6 : 2;     // on phones only the closer collaborators
    nodes.update(N.map(n => ({ id: n.id, label: (n.n >= named || z || (focus && focus.ids.has(n.id))) && n.n >= minPapers ? n.name : '',
      font: { size: px(n.n >= 6 ? 13.5 : 12.5), strokeWidth: px(4) } })));
    nodes.update([{ id: ME, font: { size: px(16), strokeWidth: px(5) } }]);
  }
  network.on('zoom', () => updateLabels(false));
  network.on('animationFinished', () => updateLabels(false));

  function applyView() {
    const f = focus;
    nodes.update(N.map(n => Object.assign({ id: n.id, hidden: n.n < minPapers }, nodeStyle(n, !f || f.ids.has(n.id)))));
    nodes.update([Object.assign({ id: ME }, meStyle(!f || f.ids.has(ME)))]);
    edges.update(N.map(n => {
      let c = EDGE;
      if (f) c = f.kind === 'edge' ? (f.edge === 'm' + n.id ? '#ffffff' : EDGE_FADE) : f.ids.has(n.id) && (f.kind === 'me' || f.center === n.id) ? rgba(colorOf(n), 0.9) : EDGE_FADE;
      return { id: 'm' + n.id, color: { color: c, highlight: c, hover: c } };
    }));
    edges.update(D.edges.map(([a, b, k], i) => {
      let c = pairColor(k);
      if (f) c = f.kind === 'edge' ? (f.edge === 'p' + i ? '#ffffff' : EDGE_FADE)
        : f.kind === 'node' && (a === f.center || b === f.center) ? rgba(colorOf(N[a === f.center ? b : a]), 0.85) : EDGE_FADE;
      return { id: 'p' + i, hidden: N[a].n < minPapers || N[b].n < minPapers, color: { color: c, highlight: c, hover: c } };
    }));
    updateLabels(true);
  }
  const setFocus = f => { focus = f; applyView(); };

  // ---------- detail sheet ----------
  const sheet = $('net-sheet'), body = $('net-body');
  const avatar = n => `<span class="avatar" style="background:linear-gradient(145deg, ${colorOf(n)}, ${rgba(colorOf(n), .65)})">${esc(initials(n.name))}</span>`;
  const meAvatar = `<span class="avatar" style="background:#fff;box-shadow:0 0 0 3px #f59e0b">${esc(initials(D.me))}</span>`;
  const theme = n => D.themes[n.theme >= 0 ? n.theme : D.themes.length - 1];
  const meter = (v, m) => `<span class="meter"><b style="width:${Math.max(5, 100 * v / (m || 1))}%"></b></span>`;
  const byYear = ids => [...ids].sort((x, y) => (D.papers[y].y === 'accepted' ? 9999 : +D.papers[y].y || 0) - (D.papers[x].y === 'accepted' ? 9999 : +D.papers[x].y || 0));
  const paperList = ids => `<ul class="papers">${byYear(ids).map(i => { const p = D.papers[i];
    return `<li><a href="#${esc(p.id)}" data-paper="${esc(p.id)}">${esc(p.t)}</a><div>${p.y === 'accepted' ? 'Accepted' : esc(p.y)}${p.v ? ' · ' + esc(p.v) : ''}</div></li>`; }).join('')}</ul>`;
  const people = list => { const m = Math.max(1, ...list.map(x => x[1]));
    return `<ul class="people">${list.map(([j, k]) => `<li data-node="${j}"><i style="background:${colorOf(N[j])}"></i><span class="nm">${esc(N[j].name)}</span>${meter(k, m)}<span class="n">${k}</span></li>`).join('')}</ul>`; };
  const firstYear = n => Math.min(...n.papers.map(i => +D.papers[i].y).filter(Boolean));

  function open(html) { body.innerHTML = html; body.scrollTop = 0; sheet.classList.add('open'); wire(); }
  function close() { sheet.classList.remove('open'); network.unselectAll(); setFocus(null); }

  function viewNode(i) {
    const n = N[i], ps = pairs[i].filter(([j]) => N[j].n >= minPapers).slice(0, 12), fy = firstYear(n);
    open(`${avatar(n)}<h3>${esc(n.name)}</h3><div class="sub">${n.n} ${plural(n.n)}${isFinite(fy) ? ` · since ${fy}` : ''}</div>
      <span class="pill"><i style="background:${theme(n).color}"></i>${esc(theme(n).title)}</span>${n.theme2 >= 0 ? ` <span class="pill"><i style="background:${D.themes[n.theme2].color}"></i>${esc(D.themes[n.theme2].title)}</span>` : ''}
      <div class="btns"><button type="button" class="primary" data-list="${esc(surname(n))}">Show in the list below</button>
        <a href="https://scholar.google.com/scholar?q=${encodeURIComponent('author:"' + n.name + '" ' + D.me)}" target="_blank" rel="noopener">Google Scholar ↗</a></div>
      <div class="lbl">Joint papers</div>${paperList(n.papers)}
      ${ps.length ? `<div class="lbl">Also co-authored with<span>papers</span></div>${people(ps)}` : ''}`);
  }
  function viewMe() {
    const top = N.filter(n => n.n >= Math.max(2, minPapers)).slice(0, 15).map(n => [n.id, n.n]);
    open(`${meAvatar}<h3>${esc(D.me)}</h3><div class="sub">${D.papers.length} publications</div>
      <div class="nums"><div class="num"><b>${N.length}</b><span>co-authors</span></div><div class="num"><b>${N.filter(n => n.n > 1).length}</b><span>on more than one paper</span></div><div class="num"><b>${maxN}</b><span>most with one person</span></div></div>
      <div class="lbl">Most frequent co-authors<span>papers</span></div>${people(top)}`);
  }
  function viewEdge(id) {
    const e = edges.get(id), a = e.from === ME ? null : N[e.from], b = N[e.to];
    const ids = a ? [...a.set].filter(x => b.set.has(x)) : b.papers;
    open(`<span class="pair">${a ? avatar(a) : meAvatar}${avatar(b)}</span><h3>${esc(a ? a.name : D.me)} &amp; ${esc(b.name)}</h3>
      <div class="sub">${ids.length} ${plural(ids.length)}${a ? ' on this list' : ''}</div>
      <div class="btns">${a ? `<button type="button" data-node="${a.id}">${esc(a.name)}</button>` : ''}<button type="button" data-node="${b.id}">${esc(b.name)}</button></div>
      <div class="lbl">Papers</div>${paperList(ids)}`);
  }

  const ANIM = { duration: 650, easingFunction: 'easeInOutCubic' };
  function fit(animate) {
    const ids = [ME, ...N.filter(n => n.n >= minPapers).map(n => n.id)];
    network.fit({ nodes: ids, animation: animate ? ANIM : false, minZoomLevel: 0.1 });
  }
  function selectNode(i, zoom) {
    const n = N[i], ids = new Set([ME, i, ...pairs[i].map(([j]) => j)]);
    network.selectNodes([i], false); setFocus({ kind: 'node', center: i, ids }); viewNode(i);
    if (zoom) { const p = network.getPositions([i])[i], sc = Math.max(network.getScale(), 1.1), w = $('network').clientWidth;
      network.moveTo({ position: { x: p.x + (w > 760 ? 190 / sc : 0), y: p.y }, scale: sc, animation: ANIM }); }
  }
  function selectMe() { network.selectNodes([ME], false); setFocus({ kind: 'me', ids: new Set([ME, ...N.map(n => n.id)]) }); viewMe(); }
  function selectEdge(id) { const e = edges.get(id); network.selectEdges([id]); setFocus({ kind: 'edge', edge: id, ids: new Set([e.from, e.to]) }); viewEdge(id); }

  // links in the sheet: people, paper cards in the list below, "show in list"
  function showInList(fn) {
    const reset = document.querySelector('.count .reset');
    fn(reset);
    document.querySelector('.toolbar').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function wire() {
    body.querySelectorAll('[data-node]').forEach(el => el.onclick = () => selectNode(+el.dataset.node, true));
    body.querySelectorAll('[data-list]').forEach(el => el.onclick = () => showInList(reset => {
      if (reset && !reset.hidden) reset.click();
      const s = document.querySelector('.toolbar .search'); s.value = el.dataset.list; s.dispatchEvent(new Event('input'));
    }));
    body.querySelectorAll('[data-paper]').forEach(el => el.onclick = ev => {
      ev.preventDefault();
      const card = document.getElementById(el.dataset.paper);
      if (!card) return;
      if (card.hidden || card.closest('[hidden]')) { const reset = document.querySelector('.count .reset'); if (reset) reset.click(); }
      history.replaceState(null, '', '#' + el.dataset.paper);
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      card.classList.remove('flash'); void card.offsetWidth; card.classList.add('flash');
    });
  }

  network.on('click', p => {
    if (p.nodes.length) return p.nodes[0] === ME ? selectMe() : selectNode(p.nodes[0]);
    if (p.edges.length) return selectEdge(p.edges[0]);
    close();
  });
  network.on('hoverNode', () => { $('network').style.cursor = 'pointer'; });
  network.on('blurNode', () => { $('network').style.cursor = ''; });
  $('net-close').onclick = close;
  stage.addEventListener('keydown', ev => { if (ev.key === 'Escape') close(); });
  $('net-search').addEventListener('change', ev => {
    const q = ev.target.value.trim().toLowerCase(); if (!q) return;
    const n = N.find(n => n.name.toLowerCase() === q) || N.find(n => n.name.toLowerCase().includes(q) || n.sort.toLowerCase().includes(q));
    if (n) { if (n.n < minPapers) setMin(1); selectNode(n.id, true); }
  });
  function setMin(k) {
    minPapers = k;
    $('net-min').querySelectorAll('button').forEach(b => b.classList.toggle('on', +b.dataset.k === k));
    if (focus && focus.kind === 'node' && N[focus.center].n < k) close(); else applyView();
    fit(true);
  }
  $('net-min').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b) setMin(+b.dataset.k); });
  $('net-zin').onclick = () => network.moveTo({ scale: network.getScale() * 1.35, animation: { duration: 300 } });
  $('net-zout').onclick = () => network.moveTo({ scale: network.getScale() / 1.35, animation: { duration: 300 } });
  $('net-fit').onclick = () => fit(true);
  addEventListener('resize', () => { if (!sheet.classList.contains('open')) fit(false); });
  fit(false); updateLabels(true);
  window.coauthorNet = { selectNode, selectMe, setMin, network };   // handy for debugging
})();
