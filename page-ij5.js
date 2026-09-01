/*
 * page-ij5.js — ij5.html: vista unica per IJ5 (Doboj / Teslić / Petrovo / Stanari).
 *
 * Versione "light" pensata per un solo lettore (Rade Tešić): apre e vede se stesso, i cinque
 * capolista avversari della stessa izborna jedinica, i partiti, e cosa hanno scritto oggi le
 * testate locali. Nessuna operativita' di ruolo, nessun triage, nessun case.
 *
 * NON introduce dati nuovi: legge gli stessi assets/data/*.json che produce la pipeline
 * esistente (collect -> clean -> entities -> dedup -> score -> trending -> signals ->
 * export_dashboard). Nessuna chiamata di rete propria, nessun campo inventato.
 *
 * Il perimetro territoriale e' fatto su `source_note` (i source_id che hanno prodotto l'item),
 * non su `territory_ij`: quest'ultimo la pipeline lo lascia sempre null di proposito
 * (pilot/score.py:112, test_9), perche' dedurre l'izborna jedinica dal testo di un articolo
 * sarebbe un'invenzione. "L'ha scritto RTV Doboj" e' invece un fatto verificabile.
 */
(function () {
  'use strict';
  var content = Header.mount();
  content.innerHTML = UI.skeleton(8);

  var SRC = DashboardConfig.IJ5_SOURCES;
  var IJ5_IDS = Object.keys(SRC);
  var FEED_LIMIT = 40;

  // Gli URL arrivano dal feed raccolto, cioe' da testo di terze parti: UI.esc() protegge
  // l'attributo ma non impedirebbe un href 'javascript:'. Questa e' la prima pagina che
  // pubblica item.url come link cliccabile, quindi il controllo va fatto qui.
  function safeUrl(u) {
    return /^https?:\/\//i.test(String(u || '')) ? String(u) : '';
  }

  function itemSourceIds(item) {
    return String(item.source_note || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
  }

  function isLocal(item) {
    return itemSourceIds(item).some(function (id) { return !!SRC[id]; });
  }

  function sourceLabels(item) {
    var seen = {};
    return itemSourceIds(item).map(function (id) {
      return SRC[id] ? SRC[id].name : id;
    }).filter(function (n) {
      if (seen[n]) return false;
      seen[n] = true;
      return true;
    }).join(', ');
  }

  /* --- 1. Lista IJ5: chi si presenta, per partito ------------------------------------- */
  // Sorgente: assets/data/candidates.json (generato da candidates_source.json, scritto a mano
  // da fonti datate). Oggi contiene SOLO il capolista per partito: quando le liste complete
  // verranno trascritte nello stesso formato, questa tabella cresce da sola, senza toccare
  // questo file.
  function listaHtml(data) {
    var cand = (data.candidates && data.candidates.by_race && data.candidates.by_race.nsrs) || [];
    var rows = cand.filter(function (c) { return c.unit === 'IJ5'; });
    if (!rows.length) {
      return '<h3 class="t-16">Lista IJ5</h3><div class="empty-state">Nema podataka o kandidatima za IJ5.</div>';
    }
    rows = rows.slice().sort(function (a, b) { return String(a.party).localeCompare(String(b.party)); });
    var body = rows.map(function (r) {
      var csrc = safeUrl(r.source_url);
      var src = csrc
        ? '<a href="' + UI.esc(csrc) + '" target="_blank" rel="noopener">' + UI.esc(r.source_name || 'izvor') + '</a>'
        : UI.esc(r.source_name || '—');
      return '<div class="card" style="margin-bottom:var(--s2)">' +
        '<div class="th-meta">' + UI.esc(r.party) + '</div>' +
        '<div class="t-14" style="font-weight:600">' + UI.esc(r.name) + '</div>' +
        '<div class="th-meta">nosilac liste &middot; ' + src + ' &middot; ' + UI.esc(r.fetched_at || '') + '</div>' +
        '</div>';
    }).join('');
    return '<h3 class="t-16">Lista IJ5 &mdash; nosioci lista (' + rows.length + ')</h3>' +
      '<div class="th-meta" style="margin-bottom:var(--s2)">Prijavljena kandidatura, izvor i datum uz svako ime' +
      ' &middot; izbori ' + UI.esc((data.candidates && data.candidates.election_date) || '') + '</div>' +
      body;
  }

  /* --- 3. Teren: solo le testate locali ----------------------------------------------- */
  function terenHtml(items) {
    var local = items.filter(isLocal).sort(function (a, b) {
      return (Date.parse(b.date || '') || 0) - (Date.parse(a.date || '') || 0);
    });
    var counts = IJ5_IDS.map(function (id) {
      var n = items.filter(function (it) { return itemSourceIds(it).indexOf(id) !== -1; }).length;
      return UI.esc(SRC[id].name) + ' (' + SRC[id].territory + '): ' + n;
    }).join(' &middot; ');

    var head = '<h3 class="t-16">Teren &mdash; lokalni izvori (' + local.length + ')</h3>' +
      '<div class="th-meta" style="margin-bottom:var(--s2)">' + counts + '</div>';

    if (!local.length) return head + '<div class="empty-state">Lokalni izvori nisu objavili ništa u ovom korpusu.</div>';

    return head + local.slice(0, FEED_LIMIT).map(function (it) {
      var href = safeUrl(it.url);
      var title = href
        ? '<a href="' + UI.esc(href) + '" target="_blank" rel="noopener">' + UI.esc(it.title || '') + '</a>'
        : UI.esc(it.title || '');
      return '<div class="card" style="margin-bottom:var(--s2)">' +
        '<div class="th-meta">' + UI.esc(UI.formatDate(it.date)) + ' &middot; ' + sourceLabels(it) + '</div>' +
        '<div class="t-14" style="font-weight:600">' + title + '</div>' +
        (it.summary ? '<div class="th-meta">' + UI.esc(String(it.summary).slice(0, 220)) + '</div>' : '') +
        '</div>';
    }).join('') +
      (local.length > FEED_LIMIT ? '<div class="th-meta">Prikazano ' + FEED_LIMIT + ' od ' + local.length + '.</div>' : '');
  }

  /* --- nota di provenienza ------------------------------------------------------------ */
  function napomenaHtml(data) {
    var h = data.pipeline_health;
    var when = h && h.run_finished_at ? UI.formatDate(h.run_finished_at) : '—';
    return '<div class="card" style="margin-top:var(--s4)">' +
      '<div class="th-meta">Napomena o podacima</div>' +
      '<div class="t-14">Sve na ovoj stranici dolazi iz stvarnog feeda (posljednji run: ' + UI.esc(when) + ').</div>' +
      '<div class="th-meta">Semafor postaje narandžast samo za entitete koje pipeline prati ' +
      '(Tešić, Jošić, Škrebić, stranke). Jović, Smiljanić i Hurtić se broje po ključnim riječima: ' +
      'njihov broj članaka je tačan, ali za njih nema vlastitog signala.</div>' +
      '</div>';
  }

  // I tre gruppi sono renderizzati separatamente, non in un'unica griglia ordinata per peso:
  // in un solo blocco rankCards() spingerebbe in cima le card di partito (SNSD, US: centinaia
  // di articoli) e la card di Tešić finirebbe decima, con "bez aktivnosti". Per il lettore di
  // questa pagina la prima cosa da vedere e' se stesso, anche quando il numero e' zero.
  var GROUPS = [
    { title: 'Ja', keys: ['tesic'] },
    { title: 'Protivnici u IJ5', keys: ['josic', 'skrebic', 'jovic-ij5', 'smiljanic-ij5', 'hurtic-ij5'] },
    { title: 'Stranke i teritorij', keys: ['us', 'snsd', 'sps', 'sp-demos', 'sds', 'doboj', 'ij5-konkurencija'] }
  ];

  function groupHtml(group, cards, items, signals) {
    var mine = cards.filter(function (c) { return group.keys.indexOf(c.key) !== -1; });
    if (!mine.length) return '';
    return '<h3 class="t-16" style="margin-top:var(--s4)">' + UI.esc(group.title) + '</h3>' +
      UI.dashboardGridHtml(RadarEngine.rankCards(mine, items, signals));
  }

  function render(data) {
    var items = data.rassegna || [];
    var signals = data.signals || [];
    var cards = DashboardConfig.IJ5;

    content.innerHTML =
      UI.pageHead('IJ5 · Doboj', 'Rade Tešić i direktni protivnici u istoj izbornoj jedinici: Doboj, Teslić, Petrovo, Stanari.', items) +
      GROUPS.map(function (g) { return groupHtml(g, cards, items, signals); }).join('') +
      '<div style="margin-top:var(--s4)">' + listaHtml(data) + '</div>' +
      '<div style="margin-top:var(--s4)">' + terenHtml(items) + '</div>' +
      napomenaHtml(data);

    UI.wireDashboardCards(content, cards, items, signals);
  }

  MPData.loadAll().then(function (data) {
    window.__MP_LAST_DATA__ = data;
    Store.emit('tasks', data.tasks);
    render(data);
    Store.subscribe('role', function () { render(data); });
  });
})();
