#!/usr/bin/env node
/*
 * tools/build-data.js — eseguito a mano una volta (node tools/build-data.js).
 *
 * Legge scenarios.json + archive_cases.json dalla sorgente v19 (NON la modifica)
 * e assets/data/candidates_source.json (scritto a mano in questo repo), normalizza,
 * e genera NELLA STESSA ESECUZIONE:
 *   assets/data/rassegna.json, trending.json, signals.json, alerts.json,
 *   assets/data/cases.json, tasks.json, archive.json, candidates.json
 *   embedded-data.js  ->  window.__MP_EMBEDDED__ = { ...stessi oggetti... }
 *
 * I due output (file JSON + embedded-data.js) sono costruiti dagli STESSI oggetti
 * JS, serializzati con lo STESSO JSON.stringify: non possono divergere (AUTOTEST #9).
 *
 * Usa radar.js (require, vedi UMD guard in fondo al file) per calcolare la catena
 * rassegna->trending->signals->alerts->cases: stessa identica logica del browser,
 * zero duplicazione (AUTOTEST #12).
 */
'use strict';
const path = require('path');
const fsx = require('fs');

const SRC_DIR = 'C:\\Users\\frontofficedx\\Desktop\\NIK 2026\\US\\_____us-demo-media-pilot-v19-large-light\\us-demo-media-pilot-v19-large-light';
const OUT_DIR = path.join(__dirname, '..');
const DATA_DIR = path.join(OUT_DIR, 'assets', 'data');

const RadarEngine = require(path.join(OUT_DIR, 'radar.js'));

function readJson(p) {
  return JSON.parse(fsx.readFileSync(p, 'utf8'));
}
function writeUtf8NoBom(p, str) {
  fsx.writeFileSync(p, str, { encoding: 'utf8' });
}

// ---- 1. carica sorgenti --------------------------------------------------

const scenarios = readJson(path.join(SRC_DIR, 'scenarios.json'));
const archiveCasesRaw = readJson(path.join(SRC_DIR, 'archive_cases.json'));
const candidatesSource = readJson(path.join(DATA_DIR, 'candidates_source.json'));

// ---- 2. normalizza corpus scenari ----------------------------------------

// Vecchia numerazione errata (scenarios.json) -> nuova numerazione reale (legge
// elettorale BiH, confini 2014). Spec ROLES: "rinominati dalla vecchia numerazione
// errata IJ2/3/4/5 di scenarios.json". Si applica SOLO a scenarios.json: le
// stringhe territory di archive_cases.json restano testo libero (non rimappate,
// l'archivio storico non segue lo schema delle 9 IJ correnti).
const IJ_REMAP = {
  'IJ 2': { code: 'IJ3', name: 'Banja Luka' },
  'IJ 3': { code: 'IJ5', name: 'Doboj' },
  'IJ 4': { code: 'IJ6', name: 'Bijeljina' },
  'IJ 5': { code: 'IJ7', name: 'Zvornik' }
};
function remapTerritory(territory) {
  if (!territory) return { raw: territory, ij: null };
  const m = /^IJ\s*(\d)/.exec(territory);
  if (m) {
    const key = 'IJ ' + m[1];
    const mapped = IJ_REMAP[key];
    if (mapped) return { raw: territory, ij: mapped.code };
  }
  return { raw: territory, ij: null };
}

// race/candidates: aggiunti "quando pertinente" (spec DATI ELETTORALI REALI).
// Regola dedotta dai moduli/territorio, deterministica, mai inventata:
//  - modules include 'PRE'                -> race predsjednik_rs (gara RS-wide)
//  - modules include CIK/IZB/POS e territorio mappa su una delle 4 IJ note -> race nsrs, candidates = capolista di quella IJ
//  - modules include 'NSRS' (senza IJ nota) -> race nsrs, candidates assenti (unita' non nota)
const nsrsRace = candidatesSource.races.find(r => r.race === 'nsrs');
const predRace = candidatesSource.races.find(r => r.race === 'predsjednik_rs');
function nsrsCandidatesForUnit(ij) {
  return nsrsRace.candidates.filter(c => c.unit === ij);
}
function attachRace(item) {
  const mods = item.modules || [];
  if (mods.indexOf('PRE') !== -1) {
    return { race: 'predsjednik_rs', candidates: predRace.candidates };
  }
  if (item._territoryIj && (mods.indexOf('CIK') !== -1 || mods.indexOf('IZB') !== -1 || mods.indexOf('POS') !== -1)) {
    const cands = nsrsCandidatesForUnit(item._territoryIj);
    if (cands.length) return { race: 'nsrs', candidates: cands };
  }
  if (mods.indexOf('NSRS') !== -1) {
    return { race: 'nsrs', candidates: [] };
  }
  return { race: null, candidates: [] };
}

let seq = 0;
function normalizeScenario(raw, menu) {
  const terr = remapTerritory(raw.territory);
  const item = Object.assign({}, raw, {
    menu: menu,
    territory_raw: terr.raw,
    territory_ij: terr.ij,
    _seq: seq++
  });
  item._territoryIj = terr.ij;
  const race = attachRace(item);
  item.race = race.race;
  if (race.candidates && race.candidates.length) item.candidates = race.candidates;
  delete item._territoryIj;
  return item;
}

let corpus = [];
Object.keys(scenarios).forEach(menu => {
  scenarios[menu].forEach(raw => corpus.push(normalizeScenario(raw, menu)));
});

// ---- 3. catena RadarEngine (unica fonte di verita', stessa del browser) --

const rassegnaItems = RadarEngine.rassegna(corpus);
const trendingItems = RadarEngine.trending(corpus);
const signalItems = RadarEngine.signals(corpus);
const alertItems = RadarEngine.alerts(corpus);
const chainCaseItems = RadarEngine.cases(corpus); // per il NUMERO del funnel (monotono)

// ---- 4. cases.json = catena + libreria "case" gia' pronta -----------------
// I 20 item del menu "case" sono fascicoli gia' pre-scritti (create_case=true su
// tutti e 20): finiscono nel Case Board / case.html anche se non hanno attraversato
// rassegna (che esclude il menu "case" per definizione, spec riga 97). Il NUMERO
// mostrato nel funnel resta pero' quello della sola catena (chainCaseItems), per
// restare monotono/coerente con rassegna->trending->signal->alert.
const authoredCaseItems = corpus.filter(i => i.menu === 'case');
function dedupById(arr) {
  const seen = new Set();
  return arr.filter(i => (seen.has(i.id) ? false : (seen.add(i.id), true)));
}
const allCaseItems = dedupById(chainCaseItems.concat(authoredCaseItems));

// Regole invarianti (ROLES, punto 6): "Nessun case senza almeno un task. Nessun
// task senza owner e senza reply_to." Un task per team pertinente (Media/Legal/
// VRH/GO), owner = team, reply_to = chi ha chiesto l'intervento (route_owner del
// case), stato deterministico dall'id del case (nessun Math.random: riproducibile).
const TEAMS = ['Media', 'Legal', 'VRH', 'GO'];
const STATUSES = ['CEKA', 'U_RADU', 'ZAVRSENO', 'HITNO'];
function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) >>> 0; }
  return h;
}
function teamsForCase(item) {
  const mods = item.modules || [];
  const out = new Set();
  if (mods.some(m => ['MEDIA', 'SOURCE', 'NOISE', 'SRE', 'CSA', 'MOE'].indexOf(m) !== -1)) out.add('Media');
  if (mods.some(m => ['LEGAL', 'OHR', 'CIK'].indexOf(m) !== -1)) out.add('Legal');
  if (item.signal_to_vrh || RadarEngine.priority(item) === 'P1') out.add('VRH');
  if (mods.some(m => ['GO', 'IJ', 'LHI'].indexOf(m) !== -1)) out.add('GO');
  if (out.size === 0) out.add('Media'); // ogni case ha sempre almeno un team/task
  return TEAMS.filter(t => out.has(t));
}
let taskSeq = 0;
const tasks = [];
allCaseItems.forEach(item => {
  const teams = teamsForCase(item);
  const requester = (item.developer_info && item.developer_info.route_owner) || item.owner || 'media';
  teams.forEach((team, idx) => {
    const h = hashStr(item.id + '|' + team);
    tasks.push({
      task_id: 'TSK-' + item.id + '-' + team,
      case_id: item.id,
      team: team,
      owner: team,
      reply_to: requester,
      task: 'Obradi case #' + item.id + ' (' + (item.title || '').slice(0, 60) + ')',
      status: STATUSES[h % STATUSES.length],
      priority: RadarEngine.priority(item),
      deadline: item.deadline || null
    });
  });
});
allCaseItems.forEach(item => { item.task_ids = tasks.filter(t => t.case_id === item.id).map(t => t.task_id); });

// ---- 5. archive.json -------------------------------------------------------
// Passa attraverso archive_cases.json: territory NON rimappata (vedi nota sopra).
const archive = archiveCasesRaw.map(a => Object.assign({}, a));

// ---- 6. candidates.json -----------------------------------------------------
// Reshape leggero per lookup rapido in go.html (by_unit) e vrh/eksperti (by_race).
const candidatesByRace = {};
const candidatesByUnit = {};
candidatesSource.races.forEach(r => {
  candidatesByRace[r.race] = r.candidates;
  if (r.race === 'nsrs') {
    r.candidates.forEach(c => {
      if (!c.unit) return;
      (candidatesByUnit[c.unit] = candidatesByUnit[c.unit] || []).push(c);
    });
  }
});
const candidates = {
  disclaimer_label: candidatesSource.disclaimer_label,
  election_date: candidatesSource.election_date,
  campaign_start: candidatesSource.campaign_start,
  by_race: candidatesByRace,
  by_unit: candidatesByUnit
};

// ---- 7. scrivi assets/data/*.json + accumula per embedded-data.js --------

const OUTPUTS = {
  rassegna: rassegnaItems,
  trending: trendingItems,
  signals: signalItems,
  alerts: alertItems,
  cases: allCaseItems,
  tasks: tasks,
  archive: archive,
  candidates: candidates
};

if (!fsx.existsSync(DATA_DIR)) fsx.mkdirSync(DATA_DIR, { recursive: true });

const embeddedParts = [];
Object.keys(OUTPUTS).forEach(name => {
  const json = JSON.stringify(OUTPUTS[name], null, 2); // STESSO serializzatore per file ed embedded
  writeUtf8NoBom(path.join(DATA_DIR, name + '.json'), json);
  embeddedParts.push(JSON.stringify(name) + ': ' + json);
});

const embeddedJs = 'window.__MP_EMBEDDED__ = {\n' + embeddedParts.map(p => '  ' + p.replace(/\n/g, '\n  ')).join(',\n') + '\n};\n';
writeUtf8NoBom(path.join(OUT_DIR, 'embedded-data.js'), embeddedJs);

// ---- 8. report a console ----------------------------------------------------

console.log('build-data.js OK');
console.log('corpus totale (8 menu x 20)      :', corpus.length);
console.log('RASSEGNA (5 menu, dedup titolo)  :', rassegnaItems.length);
console.log('TRENDING                          :', trendingItems.length);
console.log('SIGNAL                            :', signalItems.length);
console.log('ALERT                             :', alertItems.length);
console.log('CASE (solo catena, numero funnel) :', chainCaseItems.length);
console.log('CASE (catena + libreria "case")   :', allCaseItems.length);
console.log('TASKS generati                    :', tasks.length);
console.log('ARCHIVE                           :', archive.length);
console.log('CANDIDATES races                  :', Object.keys(candidatesByRace).join(', '));
console.log('File scritti in                   :', DATA_DIR);
console.log('embedded-data.js scritto in       :', path.join(OUT_DIR, 'embedded-data.js'));
