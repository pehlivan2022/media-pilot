/*
 * data.js — caricamento dati + fallback embedded (spec, sezione DATI).
 *
 * DATA_SOURCE.mode 'local' legge assets/data/*.json via fetch. Se il fetch
 * fallisce (tipicamente CORS su file://, doppio click sul file) cade su
 * window.__MP_EMBEDDED__ senza errori in console: la demo funziona sia con
 * doppio click sia servita via http (condizione di accettazione della spec).
 *
 * Per collegare il media scraper futuro: cambiare DATA_SOURCE.mode in 'api' e
 * FILES sotto con gli endpoint (vedi commento). loadAll() e il resto del
 * codice non cambiano.
 */
(function () {
  'use strict';

  var DATA_SOURCE = { mode: 'local', base: 'assets/data/' };
  // mode: 'api' -> FILES diventa una mappa nome->endpoint, es:
  //   rassegna: '/api/radar-feed', cases: '/api/cases', tasks: '/api/tasks', archive: '/api/archive'
  var FILES = ['rassegna', 'trending', 'signals', 'alerts', 'cases', 'tasks', 'archive', 'candidates'];

  var memo = null;

  function urlFor(name) {
    if (DATA_SOURCE.mode === 'api') return DATA_SOURCE.apiEndpoints ? DATA_SOURCE.apiEndpoints[name] : ('/api/' + name);
    return DATA_SOURCE.base + name + '.json';
  }

  function fetchOne(name) {
    return fetch(urlFor(name)).then(function (res) {
      if (!res.ok) throw new Error('http ' + res.status);
      return res.json();
    });
  }

  function fromEmbedded() {
    var emb = window.__MP_EMBEDDED__ || {};
    var out = {};
    FILES.forEach(function (name) { out[name] = emb[name] || (name === 'candidates' ? {} : []); });
    out.pipeline_health = null;
    out.__missing = [];
    return out;
  }

  // pipeline_health.json vive fuori da assets/data/ (data/pipeline_health.json), quindi
  // non passa da urlFor()/FILES: caricato nello stesso giro cosi' loadAll() resta l'unico
  // punto di fetch (spec §19, "caricare i JSON una volta").
  var ALL_NAMES = FILES.concat(['pipeline_health']);
  function urlForAny(name) { return name === 'pipeline_health' ? 'data/pipeline_health.json' : urlFor(name); }
  function fetchAny(name) {
    return fetch(urlForAny(name)).then(function (res) {
      if (!res.ok) throw new Error('http ' + res.status);
      return res.json();
    });
  }

  function loadAll() {
    if (memo) return memo;
    memo = Promise.all(ALL_NAMES.map(function (name) {
      return fetchAny(name).then(
        function (v) { return { name: name, ok: true, data: v }; },
        function () { return { name: name, ok: false, data: null }; }
      );
    })).then(function (results) {
      var allFailed = results.every(function (r) { return !r.ok; });
      if (allFailed) return fromEmbedded(); // file:// o rete assente: nessun errore in console, si continua

      // Un singolo file mancante/rotto NON deve far cadere l'intera dashboard sui dati
      // demo (spec §13/§20/§21): ogni file fallito resta con un default vuoto (mai null,
      // cosi' i consumer esistenti che fanno .filter/.concat non si rompono) e il suo
      // nome finisce in __missing, cosi' le sezioni HOME possono mostrare "Dati non
      // disponibili" solo per quel file, non per tutta la pagina.
      var out = {};
      var missing = [];
      results.forEach(function (r) {
        if (r.name === 'pipeline_health') { out.pipeline_health = r.ok ? r.data : null; }
        else { out[r.name] = r.ok ? r.data : (r.name === 'candidates' ? {} : []); }
        if (!r.ok) missing.push(r.name);
      });
      out.__missing = missing;
      return out;
    });
    return memo;
  }

  window.MPData = { loadAll: loadAll, DATA_SOURCE: DATA_SOURCE };
})();
