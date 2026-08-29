/*
 * page-eksperti.js — eksperti.html?tab=analiticar|legal (spec ROLES: ESPERTI).
 * Analitičar i Legal odgovaraju default-no onome ko je tražio intervenciju
 * (reply_to), ne svima: akcije ovdje uvijek djeluju na jedan item/task odjednom.
 */
(function () {
  'use strict';
  var content = Header.mount();
  content.innerHTML = UI.skeleton(6);
  var params = new URLSearchParams(location.search);
  var tab = params.get('tab') === 'legal' ? 'legal' : 'analiticar';

  function tabsHtml() {
    return '<div class="media-tabs" style="display:flex">' +
      '<a class="btn' + (tab === 'analiticar' ? ' btn-primary' : '') + '" href="?tab=analiticar">Analitičar</a>' +
      '<a class="btn' + (tab === 'legal' ? ' btn-primary' : '') + '" href="?tab=legal">Legal</a>' +
      '</div>';
  }

  function confidenceFrom(item) {
    var r = RadarEngine.riskScore(item);
    return Math.round((r / 5) * 100);
  }

  function analiticarHtml(corpus) {
    var pool = RadarEngine.signals(corpus).filter(function (i) { return !RadarEngine.alerts(corpus).some(function (a) { return a.id === i.id; }); });
    if (!pool.length) return '<div class="empty-state">Nema AI inputa za procjenu. Radar prati ' + RadarEngine.trending(corpus).length + ' tema u rastu.</div>';
    return pool.map(function (i) {
      return '<div class="card">' +
        '<div class="t-14" style="font-weight:600">' + UI.esc(i.title) + '</div>' +
        '<div class="th-meta">confidence ' + confidenceFrom(i) + '% &middot; risk ' + RadarEngine.riskScore(i).toFixed(1) + '/5 &middot; cross-ref ' + (RadarEngine.crossReference(i) ? 'da' : 'ne') + '</div>' +
        '<div class="btn-row">' +
        '<button type="button" class="btn" data-an-act="cross" data-id="' + UI.esc(i.id) + '">Aktiviraj cross-reference</button>' +
        '<button type="button" class="btn" data-an-act="alert" data-id="' + UI.esc(i.id) + '">Signaliziraj alert</button>' +
        '<button type="button" class="btn" data-an-act="case" data-id="' + UI.esc(i.id) + '">Predloži case</button>' +
        '</div></div>';
    }).join('');
  }

  function legalHtml(data) {
    var tasks = (data.tasks || []).filter(function (t) { return t.owner === 'Legal'; });
    if (!tasks.length) return '<div class="empty-state">Nema pravnih task-ova trenutno.</div>';
    return tasks.map(function (t) {
      return '<div class="card">' +
        '<div class="theme-row"><span class="tstatus tstatus-' + t.status + '"></span><span class="th-label">' + UI.esc(t.status.replace('_', ' ')) + '</span></div>' +
        '<div class="t-14">' + UI.esc(t.task) + '</div>' +
        '<div class="th-meta">case #' + UI.esc(t.case_id) + ' &middot; reply_to ' + UI.esc(t.reply_to) + '</div>' +
        '<div class="btn-row">' +
        '<a class="btn" href="case.html?id=' + encodeURIComponent(t.case_id) + '">Otvori case</a>' +
        '<button type="button" class="btn" data-leg-act="blokiraj" data-case="' + UI.esc(t.case_id) + '">Blokiraj formulaciju</button>' +
        '<button type="button" class="btn" data-leg-act="dokumenti" data-case="' + UI.esc(t.case_id) + '">Zatraži dokumente</button>' +
        '<button type="button" class="btn" data-leg-act="review" data-case="' + UI.esc(t.case_id) + '">Legal review</button>' +
        '</div></div>';
    }).join('');
  }

  function renderEksperti(data) {
    var corpus = UI.buildCorpus(data);
    content.innerHTML = UI.demoBanner() + tabsHtml() +
      '<h2 class="t-20" style="margin:var(--s4) 0 var(--s3)">' + (tab === 'legal' ? 'Legal — pravni rizik' : 'Analitičar — AI input na procjenu') + '</h2>' +
      '<div id="eks-body">' + (tab === 'legal' ? legalHtml(data) : analiticarHtml(corpus)) + '</div>';

    content.querySelectorAll('[data-an-act]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        var LABEL = { cross: 'aktiviran cross-reference', alert: 'signaliziran alert', 'case': 'predložen case' };
        Store.logAction({ action: LABEL[btn.getAttribute('data-an-act')], case_id: id, task_id: null, target: 'analiticar->media', status: 'PROSLIJEĐENO' });
        UI.toast('Prijedlog poslat timu koji je tražio intervenciju.');
      });
    });
    content.querySelectorAll('[data-leg-act]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var caseId = btn.getAttribute('data-case');
        var LABEL = { blokiraj: 'blokirana formulacija', dokumenti: 'zatraženi dokumenti', review: 'legal review završen' };
        Store.logAction({ action: LABEL[btn.getAttribute('data-leg-act')], case_id: caseId, task_id: null, target: 'legal->reply_to', status: 'ODGOVORENO' });
        UI.toast('Odgovor poslat onome ko je tražio intervenciju.');
      });
    });
  }

  MPData.loadAll().then(function (data) {
    window.__MP_LAST_DATA__ = data;
    Store.emit('tasks', data.tasks);
    renderEksperti(data);
    Store.subscribe('role', function () { renderEksperti(data); });
  });
})();
