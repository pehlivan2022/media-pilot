/*
 * page-simulator.js — simulator.html: bottone "Random scenario", genera un
 * flusso coerente da scenarios.json (via rassegna.json/cases.json gia' caricati)
 * e mostra riassunto, livello raggiunto, perche', le notizie usate, i task.
 */
(function () {
  'use strict';
  var content = Header.mount();
  content.innerHTML = UI.skeleton(4);

  function levelOf(item, corpus) {
    if (RadarEngine.cases(corpus).some(function (c) { return c.id === item.id; }) || (item.menu === 'case' && item.developer_info.create_case)) return 'case';
    if (RadarEngine.alerts(corpus).some(function (c) { return c.id === item.id; })) return 'alert';
    if (RadarEngine.signals(corpus).some(function (c) { return c.id === item.id; })) return 'signal';
    if (RadarEngine.trending(corpus).some(function (c) { return c.id === item.id; })) return 'trending';
    return 'rassegna';
  }

  function whyText(item, level, corpus) {
    var di = item.developer_info || {};
    if (level === 'case') {
      return di.create_case === true
        ? 'Postao je CASE jer je developer_info.create_case=true (fascikl je već pripremljen).'
        : 'Postao je CASE jer risk_score ' + di.risk_score + ' prelazi prag 4.0 uz human_review.';
    }
    if (level === 'alert') {
      var reasons = [];
      if (RadarEngine.riskScore(item) >= 3.5) reasons.push('risk_score ' + RadarEngine.riskScore(item));
      if (RadarEngine.crossReference(item)) reasons.push('cross-reference (2+ osjetljiva modula)');
      if (item.signal_to_vrh) reasons.push('signal_to_vrh=true');
      return 'Postao je ALERT jer: ' + (reasons.join(', ') || 'prešao prag') + '. Nije još CASE: nema create_case i nije prešao prag 4.0 sa human_review.';
    }
    if (level === 'signal') return 'Ostaje SIGNAL: moduli su politički relevantni, ali nije dovoljno u porastu ili rizičan da postane alert.';
    if (level === 'trending') return 'Ostaje TRENDING: ponavlja se kroz module, ali nije dovoljno politički gust da postane signal.';
    return 'Ostaje u RASSEGNA/monitoring: nema dovoljno ponavljanja ni rizika za dalje eskalaciju.';
  }

  function relatedNews(item, corpus) {
    var lines = (item.input_news || []).slice();
    var related = corpus.filter(function (i) { return i.id !== item.id && (i.modules || []).some(function (m) { return (item.modules || []).indexOf(m) !== -1; }); }).slice(0, 2);
    related.forEach(function (r) { lines = lines.concat(r.input_news || []); });
    return lines.slice(0, 10);
  }

  function runSimulation(data, triggerEl) {
    var corpus = UI.buildCorpus(data);
    var pick = corpus[Math.floor(Math.random() * corpus.length)];
    var level = levelOf(pick, corpus);
    var tasks = (data.tasks || []).filter(function (t) { return t.case_id === pick.id; });
    var news = relatedNews(pick, corpus);

    var body = '<div class="theme-row"><span class="badge badge-' + (level === 'case' ? 'case' : (level === 'alert' ? 'alert' : '')) + '" style="' + (level !== 'case' && level !== 'alert' ? 'background:var(--surface-2);color:var(--ink-2);border-color:var(--line)' : '') + '">' + level.toUpperCase() + '</span></div>' +
      '<h3 class="t-20" style="margin:var(--s3) 0">' + UI.esc(pick.title) + '</h3>' +
      '<p class="t-16">' + UI.esc(pick.summary || pick.user_info || '') + '</p>' +
      '<h4 class="t-14" style="margin-top:var(--s4)">Zašto ovaj nivo</h4><p class="t-14">' + UI.esc(whyText(pick, level, corpus)) + '</p>' +
      '<h4 class="t-14" style="margin-top:var(--s4)">Vijesti korištene (' + news.length + ')</h4><ul>' + news.map(function (n) { return '<li>' + UI.esc(n) + '</li>'; }).join('') + '</ul>' +
      '<h4 class="t-14" style="margin-top:var(--s4)">Task-ovi kreirani</h4>' +
      (tasks.length ? '<div class="task-grid">' + tasks.map(function (t) { return '<div class="task-cell"><b>' + UI.esc(t.team) + '</b><br><span class="tstatus tstatus-' + t.status + '"></span>' + UI.esc(t.status.replace('_', ' ')) + '</div>'; }).join('') + '</div>' : '<p class="t-14">Nijedan: flow ostaje u monitoringu, bez case-a nema task-a (spec pravilo: nema case-a bez task-a, pa ni obrnuto ovdje nema case-a).</p>') +
      (level === 'case' ? '<div class="btn-row"><a class="btn btn-primary" href="case.html?id=' + encodeURIComponent(pick.id) + '">Otvori case</a></div>' : '');

    UI.openSheet({ title: 'Random scenario', triggerEl: triggerEl, bodyHtml: body });
  }

  function renderSimulator(data) {
    content.innerHTML = UI.demoBanner() + '<h2 class="t-20">Simulator</h2>' +
      '<p class="t-14" style="color:var(--ink-2)">Generiše nasumičan tok iz scenarios.json i pokazuje do kojeg nivoa radar dolazi i zašto.</p>' +
      '<button type="button" class="btn btn-primary" id="sim-run" style="margin-top:var(--s4)">Random scenario</button>';
    document.getElementById('sim-run').addEventListener('click', function (e) { runSimulation(data, e.currentTarget); });
  }

  MPData.loadAll().then(function (data) {
    window.__MP_LAST_DATA__ = data;
    Store.emit('tasks', data.tasks);
    renderSimulator(data);
    Store.subscribe('role', function () { renderSimulator(data); });
  });
})();
