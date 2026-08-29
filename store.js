/* V21 — stato leggero: ruolo, operatore VRH, case/task e blackbox. */
(function () {
  'use strict';
  var PREFIX = 'mp_v21:';
  var BLACKBOX_MAX = 800;

  function load(key, fallback) {
    try { var raw = localStorage.getItem(PREFIX + key); return raw == null ? fallback : JSON.parse(raw); }
    catch (e) { return fallback; }
  }
  function save(key, value) { try { localStorage.setItem(PREFIX + key, JSON.stringify(value)); } catch (e) {} }

  var state = {
    role: load('role', 'media'),
    operator: load('operator', 'VRH 1'),
    cases: load('cases', {}),
    tasks: load('tasks', {}),
    blackbox: load('blackbox', []),
    seen: load('seen', []),
    navCollapsed: load('navCollapsed', false)
  };
  var subs = Object.create(null);
  function subscribe(event, fn) { (subs[event] = subs[event] || []).push(fn); return function(){ subs[event]=(subs[event]||[]).filter(function(f){return f!==fn;}); }; }
  function emit(event, payload) { (subs[event] || []).forEach(function (fn) { fn(payload); }); }
  function setRole(role) { state.role = role; save('role', role); emit('role', role); }
  function setOperator(name) { state.operator = name || 'VRH 1'; save('operator', state.operator); emit('operator', state.operator); }
  function setNavCollapsed(collapsed) { state.navCollapsed = !!collapsed; save('navCollapsed', state.navCollapsed); emit('navCollapsed', state.navCollapsed); }
  function setCaseStatus(caseId, status) { state.cases[caseId] = Object.assign({}, state.cases[caseId], { status: status }); save('cases', state.cases); emit('cases', state.cases); }
  function setTaskStatus(taskId, status) { state.tasks[taskId] = Object.assign({}, state.tasks[taskId], { status: status }); save('tasks', state.tasks); emit('tasks', state.tasks); }
  function markSeen(taskId) { if (state.seen.indexOf(taskId) === -1) { state.seen = state.seen.concat([taskId]); save('seen', state.seen); emit('seen', state.seen); } }
  function logAction(entry) {
    var row = Object.assign({ ts: new Date().toISOString(), role: state.role, actor: state.role === 'vrh' ? state.operator : state.role }, entry);
    state.blackbox = [row].concat(state.blackbox).slice(0, BLACKBOX_MAX);
    save('blackbox', state.blackbox); emit('blackbox', state.blackbox); return row;
  }

  window.Store = { state: state, subscribe: subscribe, emit: emit, setRole: setRole, setOperator: setOperator, setNavCollapsed: setNavCollapsed, setCaseStatus: setCaseStatus, setTaskStatus: setTaskStatus, markSeen: markSeen, logAction: logAction };
})();
