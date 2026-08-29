/*
 * page-media.js — media.html: nodo centrale. Desktop 3 kolone (Alert Inbox |
 * Case Board | Task/Follow-up), mobile 3 taba. Ispod: funnel + semafori.
 */
(function () {
  'use strict';
  var content = Header.mount();
  content.innerHTML = UI.skeleton(6);
  var activeLevel = null;
  var activeTab = 'alert';

  function isTriaged(alertId) {
    return !!(Store.state.cases[alertId] && Store.state.cases[alertId].status === 'TRIAZIRANO');
  }

  function alertActionsHtml(item) {
    var role = Store.state.role;
    var acts = ['Triage', 'Pošalji analitičaru', 'Traži GO dopunu'];
    if (role === 'media') acts.push('Otvori kao Case');
    return '<div class="btn-row">' + acts.map(function (a) {
      return '<button type="button" class="btn" data-alert-act="' + UI.esc(a) + '" data-id="' + UI.esc(item.id) + '">' + UI.esc(a) + '</button>';
    }).join('') + '</div>';
  }

  function alertInboxHtml(alerts) {
    if (!alerts.length) return '<div class="empty-state">Nema alert-a. Radar je tih.</div>';
    return alerts.map(function (a) {
      var triaged = isTriaged(a.id);
      return '<div class="alert-card" style="margin-bottom:var(--s3)">' +
        '<div class="theme-row"><span class="badge badge-alert">ALERT</span>' + (triaged ? '<span class="th-label">triažirano</span>' : '') + '</div>' +
        '<div class="t-14" style="font-weight:600;margin-top:var(--s1)">' + UI.esc(a.title) + '</div>' +
        '<div class="th-meta">Risk ' + RadarEngine.riskScore(a).toFixed(1) + '/5 &middot; ' + UI.esc(a.territory_raw || '') + '</div>' +
        alertActionsHtml(a) + '</div>';
    }).join('');
  }

  function caseBoardHtml(cases, data) {
    if (!cases.length) return '<div class="empty-state">Nema otvorenih case-ova. Radar prati signale.</div>';
    return cases.map(function (c) {
      var tasks = (data.tasks || []).filter(function (t) { return t.case_id === c.id; });
      return '<a class="case-card" style="display:block;margin-bottom:var(--s3);text-decoration:none;color:inherit" href="case.html?id=' + encodeURIComponent(c.id) + '">' +
        '<div class="theme-row"><span class="badge badge-case">CASE</span><span class="th-label">' + RadarEngine.priority(c) + '</span></div>' +
        '<div class="t-14" style="font-weight:600;margin-top:var(--s1)">' + UI.esc(c.title) + '</div>' +
        '<div class="th-meta">' + tasks.length + ' task(ova)</div></a>';
    }).join('');
  }

  function taskColHtml(tasks) {
    var ceka = tasks.filter(function (t) { return t.status === 'CEKA'; });
    var ostalo = tasks.filter(function (t) { return t.status !== 'CEKA'; });
    function row(t) {
      return '<div class="card"><div class="th-meta"><span class="tstatus tstatus-' + t.status + '"></span>' + UI.esc(t.status.replace('_', ' ')) + '</div>' +
        '<div class="t-14">' + UI.esc(t.task) + '</div>' +
        '<div class="th-meta">owner ' + UI.esc(t.owner) + ' &middot; reply_to ' + UI.esc(t.reply_to) + '</div></div>';
    }
    return '<h4 class="t-14">Čeka odgovor (' + ceka.length + ')</h4>' + (ceka.length ? ceka.slice(0, 10).map(row).join('') : '<div class="empty-state">Nema task-ova koji čekaju.</div>') +
      '<h4 class="t-14" style="margin-top:var(--s4)">Ostali task-ovi</h4>' + (ostalo.length ? ostalo.slice(0, 10).map(row).join('') : '<div class="empty-state">Nema.</div>');
  }

  function renderMedia(data) {
    var corpus = UI.buildCorpus(data);
    var alerts = RadarEngine.alerts(corpus);
    var cases = data.cases || [];
    var TABS = [{ key: 'alert', label: 'Alert Inbox (' + alerts.length + ')' }, { key: 'case', label: 'Case Board (' + cases.length + ')' }, { key: 'task', label: 'Task / Follow-up' }];

    content.innerHTML = UI.demoBanner() + '<div id="radar-block"></div>' +
      '<div class="media-tabs" role="tablist">' + TABS.map(function (t) {
        return '<button type="button" role="tab" class="btn" aria-selected="' + (t.key === activeTab) + '" data-tab="' + t.key + '">' + UI.esc(t.label) + '</button>';
      }).join('') + '</div>' +
      '<div class="media-cols">' +
      '<div class="media-col' + (activeTab === 'alert' ? ' active' : '') + '"><h3 class="t-16">Alert Inbox</h3>' + alertInboxHtml(alerts) + '</div>' +
      '<div class="media-col' + (activeTab === 'case' ? ' active' : '') + '"><h3 class="t-16">Case Board</h3>' + caseBoardHtml(cases, data) + '</div>' +
      '<div class="media-col' + (activeTab === 'task' ? ' active' : '') + '"><h3 class="t-16">Task i Follow-up</h3>' + taskColHtml(data.tasks || []) + '</div>' +
      '</div>';

    UI.renderRadarBlock(document.getElementById('radar-block'), corpus, {
      activeLevel: activeLevel,
      onFilterChange: function (level) { activeLevel = level; renderMedia(data); }
    });

    content.querySelectorAll('[data-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () { activeTab = btn.getAttribute('data-tab'); renderMedia(data); });
    });
    content.querySelectorAll('[data-alert-act]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var alertId = btn.getAttribute('data-id');
        var act = btn.getAttribute('data-alert-act');
        Store.logAction({ action: act, case_id: alertId, task_id: null, target: 'media', status: act === 'Triage' ? 'TRIAZIRANO' : 'U_OBRADI' });
        if (act === 'Triage') Store.setCaseStatus(alertId, 'TRIAZIRANO'); // ostaje u Alert Inbox: samo se markira, ne nestaje
        if (act === 'Otvori kao Case') location.href = 'case.html?id=' + encodeURIComponent(alertId);
        UI.toast('Task dodijeljen tvom timu u sklopu CASE-a #' + alertId);
      });
    });
  }

  MPData.loadAll().then(function (data) {
    window.__MP_LAST_DATA__ = data;
    Store.emit('tasks', data.tasks);
    renderMedia(data);
    Store.subscribe('role', function () { renderMedia(data); });
    Store.subscribe('cases', function () { renderMedia(data); });
  });
})();
