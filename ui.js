/*
 * ui.js — esc(), sheet (bottom sheet mobile / modal desktop), toast, skeleton.
 * Unico componente sheet per semafori, conferme e anteprime (spec, POPUP SEMAFORO).
 */
(function () {
  'use strict';

  // La CSS @view-transition (app.css) fa si' che il browser annulli una
  // transizione quando l'utente naviga di nuovo prima che finisca: e' un
  // AbortError innocuo della View Transitions API nativa, non un bug nostro.
  // Lo si silenzia qui (unica volta, ui.js e' su ogni pagina) per non sporcare
  // la console durante i test di navigazione rapida.
  window.addEventListener('unhandledrejection', function (e) {
    if (e.reason && e.reason.name === 'AbortError' && /transition/i.test(e.reason.message || '')) {
      e.preventDefault();
    }
  });

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }

  // ---- skeleton ----------------------------------------------------------
  function skeleton(n) {
    n = n || 3;
    var rows = '';
    for (var i = 0; i < n; i++) rows += '<div class="skeleton-row"></div>';
    return '<div class="skeleton" aria-hidden="true">' + rows + '</div>';
  }

  // ---- toast (solo per task assegnato: 4s, in alto, impilabile) ----------
  var toastHost = null;
  function toast(msg) {
    if (!toastHost) {
      toastHost = document.createElement('div');
      toastHost.className = 'toast-host';
      toastHost.setAttribute('aria-live', 'polite');
      document.body.appendChild(toastHost);
    }
    var el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    toastHost.appendChild(el);
    setTimeout(function () {
      el.classList.add('toast-out');
      setTimeout(function () { el.remove(); }, 200);
    }, 4000);
  }

  // ---- sheet: bottom sheet mobile / modal centrato desktop ---------------
  var current = null;

  function focusablesIn(el) {
    return Array.prototype.slice.call(el.querySelectorAll('a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])'));
  }

  function closeSheet() {
    if (!current) return;
    var c = current;
    current = null;
    c.overlay.classList.add('sheet-closing');
    document.removeEventListener('keydown', c.onKey, true);
    setTimeout(function () {
      c.overlay.remove();
      if (c.restoreFocus && typeof c.restoreFocus.focus === 'function') c.restoreFocus.focus();
    }, 180);
  }

  // opts: { title, bodyHtml, triggerEl, onRender(bodyEl) }
  function openSheet(opts) {
    closeSheet();
    var restoreFocus = opts.triggerEl || document.activeElement;

    var overlay = document.createElement('div');
    overlay.className = 'sheet-overlay';
    overlay.innerHTML =
      '<div class="sheet" role="dialog" aria-modal="true" aria-label="' + esc(opts.title || '') + '">' +
      '  <div class="sheet-handle" aria-hidden="true"></div>' +
      '  <div class="sheet-head"><h2 class="sheet-title">' + esc(opts.title || '') + '</h2>' +
      '    <button type="button" class="sheet-close" aria-label="Zatvori">&times;</button></div>' +
      '  <div class="sheet-body">' + (opts.bodyHtml || '') + '</div>' +
      '</div>';
    document.body.appendChild(overlay);
    var sheetEl = overlay.querySelector('.sheet');
    var bodyEl = overlay.querySelector('.sheet-body');

    function onKey(e) {
      if (e.key === 'Escape') { closeSheet(); return; }
      if (e.key === 'Tab') {
        var f = focusablesIn(sheetEl);
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
        else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
      }
    }
    document.addEventListener('keydown', onKey, true);

    overlay.addEventListener('mousedown', function (e) { if (e.target === overlay) closeSheet(); });
    overlay.querySelector('.sheet-close').addEventListener('click', closeSheet);

    // swipe verso il basso per chiudere (mobile)
    var startY = null;
    sheetEl.addEventListener('touchstart', function (e) { startY = e.touches[0].clientY; }, { passive: true });
    sheetEl.addEventListener('touchmove', function (e) {
      if (startY == null) return;
      var dy = e.touches[0].clientY - startY;
      if (dy > 80) { closeSheet(); startY = null; }
    }, { passive: true });

    current = { overlay: overlay, onKey: onKey, restoreFocus: restoreFocus };

    if (typeof opts.onRender === 'function') opts.onRender(bodyEl);
    var f0 = focusablesIn(sheetEl);
    (f0[0] || sheetEl.querySelector('.sheet-close')).focus();
    return { close: closeSheet, bodyEl: bodyEl };
  }

  // ---- blocco condiviso Funnel + Semafori ---------------------------------
  // Usato da index/vrh/media/eksperti/go (spec FUNNEL + SEMAFORI): un'unica
  // implementazione, mai copiata in piu' pagine (REGOLA ANTI-DUPLICAZIONE).

  // buildCorpus: rassegna (60, 5 menu) unita' a cases.json (aggiunge i 20 fascicoli
  // gia' pronti del menu "case", che rassegna esclude per definizione — spec riga
  // 97). E' il corpus che le pagine passano a RadarEngine/themeStatus: la catena
  // interna si auto-filtra comunque ai 5 menu, quindi i conteggi del funnel non
  // cambiano; cambia solo il rilevamento "rosso" nei semafori (vedi radar.js).
  function buildCorpus(data) {
    var seen = Object.create(null);
    var out = [];
    (data.rassegna || []).concat(data.cases || []).forEach(function (i) {
      if (seen[i.id]) return;
      seen[i.id] = true;
      out.push(i);
    });
    return out;
  }

  var FUNNEL_LEVELS = [
    { key: 'rassegna', label: 'Rassegna', desc: 'news pulite', cls: 'fc-rassegna' },
    { key: 'trending', label: 'Trending', desc: 'temi u rastu', cls: 'fc-trending' },
    { key: 'signal', label: 'Signal', desc: 'pol. relevantno', cls: 'fc-signal' },
    { key: 'alert', label: 'Alert', desc: 'preko praga', cls: 'fc-alert' },
    { key: 'case', label: 'Case', desc: 'traži akciju', cls: 'fc-case' }
  ];

  function radarCounts(corpus) {
    return {
      rassegna: RadarEngine.rassegna(corpus).length,
      trending: RadarEngine.trending(corpus).length,
      signal: RadarEngine.signals(corpus).length,
      alert: RadarEngine.alerts(corpus).length,
      case: RadarEngine.cases(corpus).length
    };
  }

  function funnelHtml(counts, activeKey) {
    var cells = FUNNEL_LEVELS.map(function (lv) {
      var active = lv.key === activeKey;
      return '<button type="button" class="funnel-cell ' + lv.cls + (lv.key === 'case' ? ' fc-case' : '') + '" data-level="' + lv.key + '" aria-pressed="' + (active ? 'true' : 'false') + '">' +
        '<div class="fc-label">' + esc(lv.label) + '</div>' +
        '<div class="fc-num">' + counts[lv.key] + '</div>' +
        '<div class="fc-desc">' + esc(lv.desc) + '</div>' +
        '</button>';
    }).join('');
    return '<div class="funnel-zones"><span>MONITORING</span><span>PAŽNJA</span><span>AKCIJA</span></div>' +
      '<div class="funnel" role="group" aria-label="Radar funnel">' + cells + '</div>';
  }

  function themeSheetBody(themeKey, corpus, windowHours) {
    var theme = RadarEngine.THEMES[themeKey];
    var st = RadarEngine.themeStatus(themeKey, corpus, windowHours);
    var labelText = { green: 'stabilno', orange: 'pažnja', red: 'akcija' }[st.level];
    var caseItem = st.top.find(function (i) { return RadarEngine.cases(corpus).some(function (c) { return c.id === i.id; }); });
    var reasons = st.reasons.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join('');
    var sources = st.sources.length ? st.sources.map(function (s) {
      var line = esc(s.title) + ' — ' + esc(s.source || 'izvor nepoznat') + ', ' + esc(s.date || '');
      return '<li>' + (s.url ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + line + '</a>' : line) + '</li>';
    }).join('') : '<li>Nema izvora u ovom periodu.</li>';
    var related = st.top.length ? st.top.map(function (i) {
      return '<li>' + esc(i.title) + ' &middot; ' + (RadarEngine.riskScore(i) >= 4 ? 'R' : 'O') + ' &middot; ' + esc(i.date || '') + '</li>';
    }).join('') : '<li>Nema povezanih stavki.</li>';
    var actionHref = caseItem ? ('case.html?id=' + encodeURIComponent(caseItem.id)) : ('index.html?level=' + encodeURIComponent(themeKey));

    return '<div class="theme-sheet" data-theme="' + esc(themeKey) + '">' +
      '<div class="win-select btn-row" role="group" aria-label="Vremenski prozor">' +
      '<button type="button" class="btn win-btn' + (windowHours === 24 ? ' btn-primary' : '') + '" data-win="24">Danas</button>' +
      '<button type="button" class="btn win-btn' + (windowHours === 72 ? ' btn-primary' : '') + '" data-win="72">3 dana</button>' +
      '<button type="button" class="btn win-btn' + (windowHours === 168 ? ' btn-primary' : '') + '" data-win="168">Sedmica</button>' +
      '</div>' +
      '<div class="theme-row" style="margin:var(--s4) 0"><span class="dot dot-' + st.level + '" style="width:20px;height:20px"></span>' +
      '<span class="t-20">' + esc(theme.label) + '</span><span class="th-label">' + esc(labelText) + '</span></div>' +
      '<p class="t-16">' + esc(theme.label) + ': ' + st.count + ' stavki u praćenju, nivo ' + esc(labelText) + '.</p>' +
      '<h3 class="t-14" style="margin-top:var(--s4)">Zašto ova boja</h3><ul>' + reasons + '</ul>' +
      '<h3 class="t-14" style="margin-top:var(--s4)">Vijesti koje su odredile boju</h3><ul>' + sources + '</ul>' +
      '<h3 class="t-14" style="margin-top:var(--s4)">Povezane stavke</h3><ul>' + related + '</ul>' +
      '<div class="btn-row"><a class="btn btn-primary" href="' + actionHref + '">Otvori detalje</a></div>' +
      '</div>';
  }

  function openThemeSheet(themeKey, corpus, triggerEl) {
    var windowHours = 24;
    var theme = RadarEngine.THEMES[themeKey];
    var handle = openSheet({
      title: theme ? theme.label : themeKey,
      triggerEl: triggerEl,
      bodyHtml: themeSheetBody(themeKey, corpus, windowHours),
      onRender: wire
    });
    function wire(bodyEl) {
      bodyEl.querySelectorAll('.win-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          windowHours = Number(btn.getAttribute('data-win'));
          bodyEl.innerHTML = themeSheetBody(themeKey, corpus, windowHours);
          wire(bodyEl);
        });
      });
    }
    return handle;
  }

  function semaforiHtml(corpus) {
    return '<div class="semafori">' + Object.keys(RadarEngine.THEMES).map(function (key) {
      var theme = RadarEngine.THEMES[key];
      var st = RadarEngine.themeStatus(key, corpus, 24);
      var labelText = { green: 'stabilno', orange: 'pažnja', red: 'akcija' }[st.level];
      return '<button type="button" class="theme-card" data-theme="' + key + '">' +
        '<div class="th-title">' + esc(theme.label) + '</div>' +
        '<div class="theme-row"><span class="dot dot-' + st.level + '"></span><span class="th-label">' + esc(labelText) + '</span></div>' +
        '<div class="th-meta">' + st.count + ' stavki &middot; trend ' + (st.trend24h > 0 ? '+' : '') + st.trend24h + '</div>' +
        '</button>';
    }).join('') + '</div>';
  }

  // renderRadarBlock: disegna funnel+semafori in `el`, richiama onFilterChange(level|null)
  // quando l'utente clicca una cella del funnel (secondo click sulla stessa = rimuove filtro).
  function renderRadarBlock(el, corpus, opts) {
    opts = opts || {};
    var activeLevel = opts.activeLevel || null;
    el.innerHTML = funnelHtml(radarCounts(corpus), activeLevel) + semaforiHtml(corpus);
    el.querySelectorAll('.funnel-cell').forEach(function (cell) {
      cell.addEventListener('click', function () {
        var level = cell.getAttribute('data-level');
        var next = (level === activeLevel) ? null : level;
        if (typeof opts.onFilterChange === 'function') opts.onFilterChange(next);
      });
    });
    el.querySelectorAll('.theme-card').forEach(function (card) {
      card.addEventListener('click', function () {
        openThemeSheet(card.getAttribute('data-theme'), corpus, card);
      });
    });
  }



  // ---- V21 political dashboard cards ------------------------------------
  function formatDate(d) {
    var t = Date.parse(d || '');
    if (isNaN(t)) return d || '—';
    try { return new Date(t).toLocaleDateString('sr-Latn', { day: '2-digit', month: '2-digit', year: 'numeric' }); }
    catch (e) { return d || '—'; }
  }

  function pageHead(title, desc, corpus) {
    var now = RadarEngine.datasetNow(corpus || []);
    var fresh = now ? formatDate(new Date(now).toISOString()) : '—';
    return '<div class="page-head"><div><div class="page-kicker">US RADAR</div>' +
      '<h1 class="page-title">' + esc(title) + '</h1>' +
      (desc ? '<div class="page-desc">' + esc(desc) + '</div>' : '') +
      '</div><div class="page-fresh">Podaci do ' + esc(fresh) + '</div></div>';
  }

  function cardSummary(card, st) {
    if (st.top) return st.top.summary || st.top.user_info || st.top.title || 'Aktivnost zabilježena.';
    if (card.type === 'model') return 'Nema novog signala. Osnovni položaj ostaje u praćenju.';
    return 'Nema značajne promjene u trenutnom feedu.';
  }

  function trendHtml(n) {
    if (n > 0) return '<span class="trend-up">↑ +' + n + '</span>';
    if (n < 0) return '<span class="trend-down">↓ ' + n + '</span>';
    return '<span class="trend-flat">→ 0</span>';
  }

  function trendArrow(n) {
    if (n > 0) return '↑';
    if (n < 0) return '↓';
    return '→';
  }

  function themeClass(card) {
    return card.theme || 'indigo';
  }

  function dashboardCardHtml(row) {
    var card = row.card, st = row.status;
    return '<button type="button" class="radar-card orb-card theme-' + themeClass(card) + ' status-' + st.level + '" data-card-key="' + esc(card.key) + '"' + (card.ij ? ' data-ij="' + esc(card.ij) + '"' : '') + ' aria-label="' + esc(card.label + ': ' + st.label) + '">' +
      '<div class="orb-accent"></div>' +
      '<div class="orb-card-head"><span class="card-mark">' + esc(card.mark || '•') + '</span><div class="card-copy"><div class="card-name">' + esc(card.label) + '</div><div class="card-meta">' + esc(card.meta || '') + '</div></div></div>' +
      '<div class="status-orb" aria-hidden="true"><span class="orb-arrow">' + trendArrow(st.trend) + '</span></div>' +
      '<div class="orb-status">' + esc(st.label) + '</div>' +
      '<div class="orb-stats"><span><b>' + st.count24 + '</b> 24h</span><span><b>' + st.count7 + '</b> 7d</span><span>' + trendHtml(st.trend) + '</span></div>' +
      '</button>';
  }

  function dashboardGridHtml(rows, cls) {
    return '<div class="' + (cls || 'dashboard-grid') + '">' + rows.map(dashboardCardHtml).join('') + '</div>';
  }

  function cardSheetBody(card, st) {
    var statusText = { red: 'Traži pažnju / akciju', orange: 'Pažnja — signal za provjeru', green: 'Stabilno', grey: 'Nema dovoljno podataka / bez skorašnje aktivnosti' }[st.level];
    var items = st.items.length ? st.items.map(function (i) {
      var di = i.developer_info || {};
      var src = di.real_news_source || i.source_note || '';
      var titleHtml = i.url ? ('<a href="' + esc(i.url) + '" target="_blank" rel="noopener">' + esc(i.title || '') + '</a>') : esc(i.title || '');
      return '<li><b>' + titleHtml + '</b>' +
        '<div class="th-meta">' + esc(formatDate(i.date || '')) + (src ? ' · ' + esc(src) : '') + '</div></li>';
    }).join('') : '<li>Nema povezanih događaja u trenutnom feedu.</li>';
    return '<div class="sheet-section"><div class="theme-row"><span class="dot dot-' + st.level + '"></span><b>' + esc(statusText) + '</b></div>' +
      '<p class="t-14" style="margin-top:8px;color:var(--ink-2)">' + esc(cardSummary(card, st)) + '</p></div>' +
      '<div class="sheet-section"><h3>Brzi pregled</h3><div class="theme-row"><span class="th-label">24h: <b>' + st.count24 + '</b></span><span class="th-label">7 dana: <b>' + st.count7 + '</b></span><span class="th-label">promjena: <b>' + (st.trend > 0 ? '+' : '') + st.trend + '</b></span></div></div>' +
      '<div class="sheet-section"><h3>Posljednji povezani događaji</h3><ul class="sheet-list">' + items + '</ul></div>';
  }

  function openDashboardCard(card, corpus, triggerEl, signals) {
    var st = RadarEngine.cardStatus(card, corpus, signals);
    return openSheet({ title: card.label, triggerEl: triggerEl, bodyHtml: cardSheetBody(card, st) });
  }

  function wireDashboardCards(root, cards, corpus, signals) {
    var map = {};
    cards.forEach(function (c) { map[c.key] = c; });
    root.querySelectorAll('[data-card-key]').forEach(function (el) {
      el.addEventListener('click', function () {
        var card = map[el.getAttribute('data-card-key')];
        if (card) openDashboardCard(card, corpus, el, signals);
      });
    });
  }

  // demoBanner: unico marker riusato dalle pagine DEMO/DEV (vrh/media/eksperti/case/simulator —
  // TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02 §15). Non e' un componente nuovo per una singola
  // pagina: e' lo stesso banner in tutte e cinque, cosi' un URL diretto rende ovvio che i dati
  // sotto sono simulati, non operativi.
  function demoBanner(){
    return '<div class="demo-banner">DEMO / DEV — podaci simulirani, nije operativni prikaz</div>';
  }

  window.UI = {
    esc: esc, skeleton: skeleton, toast: toast, openSheet: openSheet, closeSheet: closeSheet,
    radarCounts: radarCounts, renderRadarBlock: renderRadarBlock, openThemeSheet: openThemeSheet, buildCorpus: buildCorpus,
    FUNNEL_LEVELS: FUNNEL_LEVELS,
    pageHead: pageHead, dashboardCardHtml: dashboardCardHtml, dashboardGridHtml: dashboardGridHtml,
    openDashboardCard: openDashboardCard, wireDashboardCards: wireDashboardCards, formatDate: formatDate,
    demoBanner: demoBanner
  };
})();
