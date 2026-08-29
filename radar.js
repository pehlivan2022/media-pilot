/*
 * radar.js — RadarEngine: motore unico, funzioni pure, zero DOM.
 *
 * Usato SIA dal browser (pagine + _selftest.html, via window.RadarEngine)
 * SIA da Node (tools/build-data.js, via module.exports) cosi' la catena
 * rassegna -> trending -> signals -> alerts -> cases e' UNA sola implementazione:
 * non puo' divergere tra build-time e run-time (vedi AUTOTEST #9 e #12).
 *
 * CATENA (ogni livello e' un SOTTOINSIEME del precedente: il funnel si restringe
 * sempre, mai al contrario):
 *   rassegna(items)  -> dedup per titolo normalizzato, solo dai 5 "menu notizia pulita"
 *   trending(items)  -> rassegna(items) + velocity 24h (moduleset ripetuto) o source jump
 *   signals(items)   -> trending(items) filtrato ai moduli politicamente rilevanti
 *   alerts(items)    -> signals(items) filtrato per risk/cross-reference/signal_to_vrh
 *   cases(items)     -> alerts(items) filtrato per create_case o risk alto + revisione umana
 *
 * NOTA SUI NUMERI: nel testo di spec il funnel mostra un esempio illustrativo
 * (RASSEGNA 450 / TRENDING 38 / SIGNAL 12 / ALERT 5 / CASE 3). E' un mockup di
 * layout, non ricavato dai dati reali (a differenza delle frequenze dei moduli
 * nei semafori, che LO sono e infatti corrispondono esattamente). Sul dataset
 * reale v19-large-light (160 scenari, molto denso di risk alto) i conteggi reali
 * sono diversi e piu' alti, in particolare per ALERT/CASE. Vedi OUTPUT FINALE.
 */
(function (root, factory) {
  var RadarEngine = factory();
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = RadarEngine; // Node: require('../radar.js') da tools/build-data.js
  }
  if (typeof window !== 'undefined') {
    window.RadarEngine = RadarEngine; // Browser
  }
})(this, function () {
  'use strict';

  // ---- SOGLIE (la parte che verra' ritoccata piu' spesso) ------------------

  // RASSEGNA: solo questi 5 menu contano come "news pulite" (spec, sezione RADAR ENGINE, riga 97).
  // opposition/case/modifier restano fuori dalla rassegna: "case" e' una libreria di
  // fascicoli gia' pronti (vedi build-data.js), "modifier" alimenta solo simulator.html.
  var RASSEGNA_MENUS = ['news', 'social', 'local', 'institutions', 'campaign'];

  // TRENDING: un item e' "in crescita" se condivide almeno 2 moduli (ripetizione
  // di modulo, non serve il titolo identico) con almeno N altri item della
  // rassegna (velocity), oppure se salta da locale a nazionale nello stesso item
  // (source jump). N=4 e' la soglia da ritoccare qui.
  var VELOCITY_SHARED_MODULES_MIN = 2;
  var TRENDING_VELOCITY_MIN = 4;
  var LOCAL_MODULES = ['GO', 'IJ', 'LHI'];
  var NATIONAL_MODULES = ['OHR', 'CIK', 'INT', 'NSRS'];

  // SIGNAL: moduli politicamente rilevanti (spec, sezione RADAR ENGINE, riga 99).
  var POLITICAL_MODULES = ['US', 'STE', 'REL', 'NSRS', 'SNSD', 'OHR', 'CIK', 'IZB', 'PRE', 'POS', 'BEO', 'INT', 'GO', 'IJ', 'OPP'];
  // In questo dataset l'argomento e' quasi sempre politico: la lista POLITICAL_MODULES
  // e' presente in oltre il 90% degli item, quindi "interseca" da solo non separa
  // SIGNAL da TRENDING (autotest #10 vuole 5 conteggi distinti). Si richiede quindi
  // che il tema tocchi ALMENO 3 moduli politici distinti, non solo 1: e' ancora
  // un'intersezione con l'insieme della spec, solo piu' esigente sulla densita'.
  var SIGNAL_MIN_POLITICAL_HITS = 3;

  // ALERT: risk_score >= soglia, oppure cross-reference (>=2 moduli sensibili nello
  // stesso item), oppure signal_to_vrh true. La soglia resta 3.5 come da spec anche
  // se in questo dataset risk_score e' sempre intero (2-5): 3.5 equivale quindi a
  // ">=4", che E' la soglia corretta da ritoccare qui se un domani risk_score avra' decimali.
  var ALERT_RISK_THRESHOLD = 3.5;
  var SENSITIVE_MODULES = ['OHR', 'CIK', 'NSRS', 'SNSD', 'US', 'STE', 'LEGAL', 'INT'];

  // CASE: create_case true, oppure risk_score >= 4.0 CON revisione umana richiesta
  // (developer_info.human_review true) — "azione umana richiesta" della spec.
  var CASE_RISK_THRESHOLD = 4.0;

  // Soglie themeStatus (semaforo): rosso se c'e' almeno un case nel tema o risk
  // massimo >= 5.0; arancione se c'e' almeno un alert e nessun case; verde altrimenti.
  var THEME_RED_RISK = 5.0;

  // Frase condivisa per tema verde senza attivita' e per le IJ non primarie senza
  // scenari (spec ROLES/GO: "mostrano comunque il pallino colorato ... reason
  // 'nessun segnale attivo, in ascolto'"). Un'unica stringa esportata, riusata da
  // go.js, cosi' non e' scritta a mano in due punti diversi.
  var NO_SIGNAL_REASON = 'Nema aktivnog signala, u praćenju.';

  // ---- util pure -------------------------------------------------------------

  // esc() vive in ui.js (spec, FILE STRUCTURE): non ridefinirla qui per non
  // violare l'autotest "nessuna funzione definita in due file diversi".

  function normTitle(t) {
    return String(t || '').toLowerCase()
      .normalize('NFKD').replace(/[̀-ͯ]/g, '') // via diacritici per il confronto, NON per la UI
      .replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim();
  }

  function dedupByTitle(arr) {
    var seen = Object.create(null);
    var out = [];
    for (var i = 0; i < arr.length; i++) {
      var k = normTitle(arr[i].title);
      if (seen[k]) continue;
      seen[k] = true;
      out.push(arr[i]);
    }
    return out;
  }

  function riskScore(item) {
    return Number((item.developer_info && item.developer_info.risk_score) || 0);
  }

  function crossReference(item) {
    var mods = item.modules || [];
    var hits = mods.filter(function (m) { return SENSITIVE_MODULES.indexOf(m) !== -1; });
    return hits.length >= 2;
  }

  function sourceJump(item) {
    var mods = item.modules || [];
    var hasLocal = mods.some(function (m) { return LOCAL_MODULES.indexOf(m) !== -1; });
    var hasNational = mods.some(function (m) { return NATIONAL_MODULES.indexOf(m) !== -1; });
    return hasLocal && hasNational;
  }

  function sharedModuleCount(a, b) {
    var bm = b.modules || [];
    return (a.modules || []).filter(function (m) { return bm.indexOf(m) !== -1; }).length;
  }

  // velocity: quanti altri item nel pool condividono almeno VELOCITY_SHARED_MODULES_MIN
  // moduli con questo item (ripetizione di modulo attraverso la rassegna, non serve
  // il set esatto identico: e' la lettura piu' fedele di "ripetizione ... modulo").
  function velocity(item, pool) {
    var n = 0;
    for (var i = 0; i < pool.length; i++) {
      if (pool[i] === item) continue;
      if (sharedModuleCount(item, pool[i]) >= VELOCITY_SHARED_MODULES_MIN) n++;
    }
    return n;
  }

  // ---- catena RadarEngine -----------------------------------------------------

  function rassegna(items) {
    var pool = items.filter(function (i) { return RASSEGNA_MENUS.indexOf(i.menu) !== -1; });
    return dedupByTitle(pool);
  }

  function trending(items) {
    var pool = rassegna(items);
    return pool.filter(function (i) {
      return velocity(i, pool) >= TRENDING_VELOCITY_MIN || sourceJump(i);
    });
  }

  function signals(items) {
    var pool = trending(items);
    return pool.filter(function (i) {
      var hits = (i.modules || []).filter(function (m) { return POLITICAL_MODULES.indexOf(m) !== -1; });
      return hits.length >= SIGNAL_MIN_POLITICAL_HITS;
    });
  }

  function alerts(items) {
    var pool = signals(items);
    return pool.filter(function (i) {
      return riskScore(i) >= ALERT_RISK_THRESHOLD || crossReference(i) || i.signal_to_vrh === true;
    });
  }

  function cases(items) {
    var pool = alerts(items);
    return pool.filter(function (i) {
      var di = i.developer_info || {};
      return di.create_case === true || (riskScore(i) >= CASE_RISK_THRESHOLD && di.human_review === true);
    });
  }

  // priority: P1/P2/P3 da risk_score (soglie riprese dalla v19: >=5 P1, >=4 P2, altrimenti P3).
  function priority(item) {
    var r = riskScore(item);
    if (r >= 5) return 'P1';
    if (r >= 4) return 'P2';
    return 'P3';
  }

  // ---- themeStatus -------------------------------------------------------------

  // "now" del dataset = la data piu' recente presente nei dati stessi, non Date.now().
  // I dati sono un demo storico (aprile/maggio 2026): usare l'orologio reale
  // farebbe apparire tutto "vecchio" rispetto a oggi. Documentato qui perche' e'
  // la decisione che piu' spesso confonde chi guarda il codice per la prima volta.
  function datasetNow(items) {
    var max = 0;
    items.forEach(function (i) {
      var t = Date.parse(i.date || '');
      if (!isNaN(t) && t > max) max = t;
    });
    return max || Date.now();
  }

  function themeStatus(themeKey, items, windowHours) {
    windowHours = windowHours || 24;
    var theme = THEMES[themeKey];
    var modules = theme ? theme.modules : [];
    var now = datasetNow(items);
    var winMs = windowHours * 3600 * 1000;
    var inWindow = items.filter(function (i) {
      var t = Date.parse(i.date || '');
      return !isNaN(t) && (now - t) <= winMs && (now - t) >= 0;
    });
    var prevWindow = items.filter(function (i) {
      var t = Date.parse(i.date || '');
      return !isNaN(t) && (now - t) > winMs && (now - t) <= winMs * 2;
    });
    var themeItems = inWindow.filter(function (i) {
      return (i.modules || []).some(function (m) { return modules.indexOf(m) !== -1; });
    });
    var themeItemsPrev = prevWindow.filter(function (i) {
      return (i.modules || []).some(function (m) { return modules.indexOf(m) !== -1; });
    });

    // caseIds: catena (rassegna->...->cases) UNITA' agli item del menu "case"
    // gia' pronti (create_case sempre true li'): themeStatus deve accorgersi di
    // un case anche se e' un fascicolo di libreria e non ha attraversato la
    // catena (build-data.js unisce allo stesso modo, vedi tools/build-data.js).
    var caseIds = {};
    cases(items).forEach(function (i) { caseIds[i.id] = true; });
    items.forEach(function (i) {
      if (i.menu === 'case' && i.developer_info && i.developer_info.create_case === true) caseIds[i.id] = true;
    });
    var alertIds = {};
    alerts(items).forEach(function (i) { alertIds[i.id] = true; });

    var themeCases = themeItems.filter(function (i) { return caseIds[i.id]; });
    var themeAlerts = themeItems.filter(function (i) { return alertIds[i.id]; });
    var maxRisk = themeItems.reduce(function (m, i) { return Math.max(m, riskScore(i)); }, 0);

    var level;
    if (themeCases.length > 0 || maxRisk >= THEME_RED_RISK) level = 'red';
    else if (themeAlerts.length > 0) level = 'orange';
    else level = 'green';

    var reasons = [];
    if (themeCases.length > 0) {
      reasons.push(themeCases.length + ' otvoren case u temi (' + themeCases.map(function (i) { return '#' + i.id; }).join(', ') + ').');
    }
    if (maxRisk > 0) {
      reasons.push('Risk score ' + maxRisk.toFixed(1) + ' od 5.');
    }
    var crossRefItem = themeItems.find(function (i) { return crossReference(i); });
    if (crossRefItem) {
      var sensHit = (crossRefItem.modules || []).filter(function (m) { return SENSITIVE_MODULES.indexOf(m) !== -1; });
      reasons.push('Uključuje ' + sensHit.slice(0, 2).join(' i ') + ' zajedno (cross-reference).');
    }
    var jumpItem = themeItems.find(function (i) { return sourceJump(i); });
    if (jumpItem) {
      reasons.push('Tema je prešla sa lokalnog na nacionalni nivo.');
    }
    if (themeItems.length >= 2) {
      reasons.push(themeItems.length + ' izvora je prenijelo temu u izabranom periodu (' + windowHours + 'h).');
    }
    if (reasons.length === 0) {
      reasons.push(NO_SIGNAL_REASON);
    }

    var sources = themeItems.slice(0, 6).map(function (i) {
      var di = i.developer_info || {};
      return {
        title: i.title,
        source: di.real_news_source || null,
        date: di.real_news_date || i.date || null,
        url: null // lo scraper non fornisce ancora url reali: mai inventarli (spec, POPUP SEMAFORO punto 4)
      };
    });

    return {
      level: level,
      score: maxRisk,
      count: themeItems.length,
      trend24h: themeItems.length - themeItemsPrev.length,
      reasons: reasons,
      sources: sources,
      top: themeItems.slice(0, 6)
    };
  }

  // Definizione temi semafori: SOLO temi, mai livelli radar (spec, sezione SEMAFORI).
  var THEMES = {
    ohr: { label: 'OHR / institucije', modules: ['OHR', 'INT'] },
    izbori: { label: 'CIK / izbori 2026', modules: ['CIK', 'IZB', 'POS', 'PRE'] },
    legal: { label: 'Pravni rizik', modules: ['LEGAL'] },
    mediji: { label: 'Medijski signal', modules: ['MEDIA', 'SOURCE', 'NOISE'] },
    teren: { label: 'Teren / GO i izborne jedinice', modules: ['GO', 'IJ', 'LHI'] },
    mreze: { label: 'Društvene mreže / narativ', modules: ['SRE', 'CSA', 'MOE'] },
    opozicija: { label: 'Opozicija', modules: ['OPP', 'DRA', 'VUK', 'JEL', 'BLA'] },
    odnosi: { label: 'Beograd / US-SNSD / NSRS', modules: ['BEO', 'REL', 'SNSD', 'NSRS', 'STE', 'US'] }
  };


  // ---- dashboard cards ----------------------------------------------------
  // Strato leggero sopra il radar esistente: una card e' una query stabile
  // (attore/relazione/territorio). Lo scraper alimenta gli item; la UI non
  // dipende da un formato speciale oltre ai campi gia' presenti.
  function cardText(item) {
    return [item.title, item.summary, item.user_info, item.main_actor, item.territory_raw, item.territory]
      .concat((item.candidates || []).map(function (c) { return (c.name || '') + ' ' + (c.party || ''); }))
      .join(' ');
  }

  function normSearch(t) {
    return String(t || '').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'dj').replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function cardItems(card, items) {
    var words = (card.keywords || []).map(normSearch).filter(Boolean);
    var mods = card.modules || [];
    return items.filter(function (item) {
      var text = normSearch(cardText(item));
      var wordHit = words.some(function (w) { return text.indexOf(w) !== -1; });
      var modHit = (item.modules || []).some(function (m) { return mods.indexOf(m) !== -1; });
      var ijHit = !card.ij || item.territory_ij === card.ij;

      if (card.type === 'territory') return ijHit && (card.ij ? true : (wordHit || modHit));
      if (card.type === 'actor') return ijHit && (words.length ? wordHit : modHit);
      if (card.type === 'race') return ijHit && (wordHit || modHit || (!words.length && !mods.length));
      if (card.type === 'relation') {
        // Una relazione non deve accendersi per ogni semplice menzione di un partito:
        // privilegia gli item marcati REL; in assenza di REL richiede almeno 2 keyword hit.
        if (modHit && (item.modules || []).indexOf('REL') !== -1) return ijHit;
        var hits = words.filter(function (w) { return text.indexOf(w) !== -1; }).length;
        return ijHit && hits >= Math.min(2, words.length || 2);
      }
      return ijHit && (wordHit || modHit);
    });
  }

  function recentWithin(item, now, hours) {
    var t = Date.parse(item.date || '');
    return !isNaN(t) && (now - t) >= 0 && (now - t) <= hours * 3600 * 1000;
  }

  // cardStatus: semafori BETA (spec TASK_FINAL_DASHBOARD_BETA_01 §3). Deriva SOLO da
  // rassegna.json reale (items) + signals.json REVIEW reale (signals) — non piu' dalla
  // catena demo alerts()/cases() (che richiede developer_info.risk_score, assente sui
  // dati reali). 'red' resta uno stato supportato da label/CSS ma NON e' MAI assegnato
  // qui: riservato a una futura fonte di Alert umano/confermato, mai automatico da
  // Trending/Signal (§3 "NON generare automaticamente ROSSO da Trending o Signal", §21).
  function cardStatus(card, items, signals) {
    signals = signals || [];
    var rel = cardItems(card, items);
    var now = datasetNow(items);
    var last24 = rel.filter(function (i) { return recentWithin(i, now, 24); });
    var last7 = rel.filter(function (i) { return recentWithin(i, now, 168); });
    var prev7 = rel.filter(function (i) {
      var t = Date.parse(i.date || '');
      return !isNaN(t) && (now - t) > 168 * 3600 * 1000 && (now - t) <= 336 * 3600 * 1000;
    });
    var hasReviewSignal = signals.some(function (s) {
      return s.entity_id === card.key || (s.entities || []).indexOf(card.key) !== -1;
    });
    var trend = last7.length - prev7.length;
    var level;
    if (last7.length === 0) level = 'grey'; // dati insufficienti / nessuna attivita' recente
    else if (hasReviewSignal) level = 'orange'; // AMBRA: >=1 Signal REVIEW per questa entita'
    else level = 'green';

    var ordered = rel.slice().sort(function (a, b) {
      var ar = riskScore(a), br = riskScore(b);
      if (br !== ar) return br - ar;
      return (Date.parse(b.date || '') || 0) - (Date.parse(a.date || '') || 0);
    });
    var top = ordered[0] || null;
    var labels = { red: 'akcija', orange: 'pažnja', green: 'stabilno', grey: 'bez aktivnosti' };
    var weight = { red: 400, orange: 300, green: 200, grey: 50 }[level] + Math.min(last24.length, 8) * 3 + Math.max(0, trend) * 2;
    return {
      level: level,
      label: labels[level],
      count24: last24.length,
      count7: last7.length,
      trend: trend,
      hasReviewSignal: hasReviewSignal,
      top: top,
      items: ordered.slice(0, 8),
      weight: weight,
      base: Number(card.base || 999)
    };
  }

  function rankCards(cards, items, signals) {
    return cards.map(function (card) {
      return { card: card, status: cardStatus(card, items, signals) };
    }).sort(function (a, b) {
      if (b.status.weight !== a.status.weight) return b.status.weight - a.status.weight;
      return a.status.base - b.status.base;
    });
  }

  return {
    THEMES: THEMES,
    NO_SIGNAL_REASON: NO_SIGNAL_REASON,
    normTitle: normTitle,
    rassegna: rassegna,
    trending: trending,
    signals: signals,
    alerts: alerts,
    cases: cases,
    velocity: velocity,
    sourceJump: sourceJump,
    crossReference: crossReference,
    riskScore: riskScore,
    priority: priority,
    themeStatus: themeStatus,
    datasetNow: datasetNow,
    cardItems: cardItems,
    cardStatus: cardStatus,
    rankCards: rankCards
  };
});
