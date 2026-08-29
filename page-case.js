/*
 * page-case.js — case.html?id=... : fascicolo a schermo intero (spec, ALERT vs CASE).
 */
(function () {
  'use strict';
  var content = Header.mount();
  content.innerHTML = UI.skeleton(6);

  var id = new URLSearchParams(location.search).get('id');

  function seedFromId(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return h;
  }

  // RADAR MAP: nessuna serie temporale reale nei dati (lo scraper non la fornisce
  // ancora): una sparkline deterministica dall'id, ancorata al risk_score reale
  // come ultimo punto, cosi' e' riproducibile e non e' mai casuale a ogni load.
  function sparklineSvg(item) {
    var seed = seedFromId(item.id);
    var risk = RadarEngine.riskScore(item);
    var pts = [];
    for (var i = 0; i < 5; i++) {
      var wobble = ((seed >> (i * 3)) % 5) - 2;
      pts.push(Math.max(1, Math.min(5, risk - (4 - i) * 0.3 + wobble * 0.3)));
    }
    var w = 200, h = 48, step = w / (pts.length - 1);
    var d = pts.map(function (v, i) { return (i === 0 ? 'M' : 'L') + (i * step) + ',' + (h - (v / 5) * h); }).join(' ');
    var rising = pts[pts.length - 1] >= pts[0];
    return '<svg class="sparkline" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Trend posljednja 4h, ' + (rising ? 'raste' : 'opada') + '">' +
      '<path d="' + d + '" fill="none" stroke="' + (rising ? 'var(--crit)' : 'var(--ok)') + '" stroke-width="2"/></svg>';
  }

  function forbiddenNote(item) {
    var di = item.developer_info || {};
    if (di.public_response_blocked) {
      return 'Napomena: izbjegavati javni odgovor dok se ne vidi pravni okvir i pozicija Beograda.';
    }
    return 'Napomena: pratiti razvoj situacije prije bilo kakvog javnog istupa.';
  }

  function evidenceHtml(item) {
    var di = item.developer_info || {};
    var rows = (item.input_news || []).map(function (t) { return '<li>' + UI.esc(t) + '</li>'; }).join('');
    var anchor = di.real_news_anchor ? ('<div class="th-meta">Anchor: ' + UI.esc(di.real_news_anchor) + ' &middot; ' + UI.esc(di.real_news_source || '') + ' &middot; ' + UI.esc(di.real_news_date || '') + '</div>') : '';
    return '<ul>' + rows + '</ul>' + (item.source_note ? '<div class="th-meta">' + UI.esc(item.source_note) + '</div>' : '') + anchor;
  }

  var TASK_TEAMS = ['Media', 'Legal', 'VRH', 'GO'];
  function taskGridHtml(tasks) {
    return '<div class="task-grid">' + TASK_TEAMS.map(function (team) {
      var t = tasks.find(function (x) { return x.team === team; });
      var status = t ? t.status : 'CEKA';
      return '<div class="task-cell"><b>' + team + '</b><br><span class="tstatus tstatus-' + status + '"></span>' + UI.esc(status.replace('_', ' ')) +
        (t ? '<div class="th-meta">reply_to: ' + UI.esc(t.reply_to) + '</div>' : '') + '</div>';
    }).join('') + '</div>';
  }

  function actionsHtml(item, tasks) {
    var role = Store.state.role;
    var btns = [];
    btns.push('<button type="button" class="btn" data-act="vidi">Vidio</button>');
    if (role === 'vrh') btns.push('<button type="button" class="btn btn-primary" data-act="decidi">Decidi i zaduži</button>');
    else btns.push('<button type="button" class="btn" data-act="signaliziraj">Signaliziraj VRH</button>');
    btns.push('<button type="button" class="btn" data-act="legal">Traži legal</button>');
    btns.push('<button type="button" class="btn" data-act="analizu">Traži analizu</button>');
    btns.push('<button type="button" class="btn" data-act="go">Traži GO dopunu</button>');
    btns.push('<button type="button" class="btn" data-act="zatvori">Zatvori bez akcije</button>');
    return '<div class="btn-row">' + btns.join('') + '</div>';
  }

  function wireActions(root, item) {
    root.querySelectorAll('[data-act]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var act = btn.getAttribute('data-act');
        var LABEL = { vidi: 'pregledano', decidi: 'odluka VRH', signaliziraj: 'signalizirano VRH-u', legal: 'zatražen legal', analizu: 'zatražena analiza', go: 'zatražena GO dopuna', zatvori: 'zatvoreno bez akcije' };
        Store.logAction({ action: LABEL[act] || act, case_id: item.id, task_id: null, target: act, status: act === 'zatvori' ? 'ZATVOREN' : (Store.state.cases[item.id] && Store.state.cases[item.id].status) || 'OTVOREN' });
        if (act === 'zatvori') Store.setCaseStatus(item.id, 'ZATVOREN');
        else if (act === 'decidi') Store.setCaseStatus(item.id, 'U_OBRADI');
        UI.toast('Task dodijeljen tvom timu u sklopu CASE-a #' + item.id);
      });
    });
  }

  function renderCase(data) {
    var corpus = UI.buildCorpus(data);
    var item = corpus.find(function (i) { return i.id === id; });
    if (!item) {
      content.innerHTML = UI.demoBanner() + '<div class="empty-state">Case #' + UI.esc(id || '') + ' nije pronađen. <a href="index.html">Nazad na radar</a>.</div>';
      return;
    }
    var tasks = (data.tasks || []).filter(function (t) { return t.case_id === item.id; });
    var status = (Store.state.cases[item.id] && Store.state.cases[item.id].status) || 'OTVOREN';
    var priority = RadarEngine.priority(item);
    var themeKeys = Object.keys(RadarEngine.THEMES).filter(function (k) {
      return RadarEngine.THEMES[k].modules.some(function (m) { return (item.modules || []).indexOf(m) !== -1; });
    });
    var themeLabel = themeKeys.length ? RadarEngine.THEMES[themeKeys[0]].label : 'Opšte';
    var suggested = (item.suggested_responses || []).slice(0, 4);

    content.innerHTML =
      UI.demoBanner() +
      '<div class="case-card">' +
      '<div class="theme-row"><span class="badge badge-case">CASE</span><span class="t-14">#' + UI.esc(item.id) + '</span>' +
      '<span class="th-label">' + UI.esc(themeLabel) + '</span><span class="th-label">' + UI.esc(status) + '</span>' +
      '<span class="th-label">' + UI.esc(priority) + '</span></div>' +
      '<h1 class="t-28" style="margin:var(--s3) 0">' + UI.esc(item.summary || item.user_info || item.title) + '</h1>' +
      '<div class="t-14" style="color:var(--ink-2)"><b>Trigger:</b> ' + UI.esc(item.title) + '</div>' +

      '<div class="box-info" style="margin-top:var(--s4)">' +
      '<h3 class="t-14">Operativni saveti</h3>' +
      (suggested.length ? '<ul>' + suggested.map(function (s) { return '<li>' + UI.esc(s) + '</li>'; }).join('') + '</ul>' : '<p>Nema pripremljenih predloga.</p>') +
      '</div>' +
      '<p class="note-plain">' + UI.esc(forbiddenNote(item)) + '</p>' +

      '<h3 class="t-14" style="margin-top:var(--s4)">Evidence</h3>' + evidenceHtml(item) +

      '<div class="theme-row" style="margin-top:var(--s4)">' +
      '<span class="t-14">Risk score ' + RadarEngine.riskScore(item).toFixed(1) + '/5</span>' +
      '<span class="t-14">Velocity ' + RadarEngine.velocity(item, UI.buildCorpus(data)) + '</span>' +
      '<span class="t-14">Source jump ' + (RadarEngine.sourceJump(item) ? 'da' : 'ne') + '</span>' +
      '</div>' +

      '<h3 class="t-14" style="margin-top:var(--s4)">Radar map (posljednja 4h, ilustrativno)</h3>' + sparklineSvg(item) +

      '<h3 class="t-14" style="margin-top:var(--s4)">Task grid</h3>' + taskGridHtml(tasks) +

      actionsHtml(item, tasks) +
      '</div>';

    wireActions(content, item);
  }

  MPData.loadAll().then(function (data) {
    window.__MP_LAST_DATA__ = data;
    Store.emit('tasks', data.tasks);
    renderCase(data);
    Store.subscribe('role', function () { renderCase(data); });
    Store.subscribe('cases', function () { renderCase(data); });
    Store.subscribe('tasks', function () { renderCase(data); });
  });
})();
