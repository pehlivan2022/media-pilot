/* V21.3 — Radar home: US first, then competitors, territory, institutions.
 * BETA (TASK_FINAL_DASHBOARD_BETA_01): stato pipeline + Trending/Signal/Rassegna
 * reali sopra le card. Card semafori derivano da data.rassegna + data.signals REVIEW
 * (mai da cases.json demo — vedi RadarEngine.cardStatus).
 * TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02 §14: rimosso il pannello VRH (derivava da
 * cases.json demo + RadarEngine.alerts()/cases() sulla catena vecchia) — l'operativa HOME
 * non deve mai mostrare contenuto Alert/Case, a prescindere dal ruolo selezionato. */
(function(){
  'use strict';
  var content=Header.mount();
  content.innerHTML=UI.skeleton(8);

  function byKeys(cards, keys){
    return keys.map(function(k){return cards.find(function(c){return c.key===k;});}).filter(Boolean);
  }
  function section(title, href, rows, compact){
    return '<section class="home-section'+(compact?' home-compact':'')+'"><div class="home-section-head"><h2>'+UI.esc(title)+'</h2><a href="'+href+'">Vidi sve →</a></div>'+UI.dashboardGridHtml(rows)+'</section>';
  }

  // ---- BETA: stato pipeline ------------------------------------------------

  function timeHM(iso){
    var t=Date.parse(iso||'');
    if(isNaN(t)) return '';
    try{ return new Date(t).toLocaleTimeString('sr-Latn',{hour:'2-digit',minute:'2-digit'}); }catch(e){ return ''; }
  }

  // §20: tri stanja, ne dva — DATA UNAVAILABLE (fajl nedostupan) je različito od DEGRADED
  // (fajl postoji, neke fonti nisu uspjele). sources_failed je NIZ source_id (ne broj) kad
  // do_collect=True (pilot/run_all.py) — poredenje ">0" na nizu je uvijek bilo false (bug,
  // popravljeno ovdje).
  function pipelineStripHtml(data){
    var ph=data.pipeline_health;
    var missing=(data.__missing||[]).indexOf('pipeline_health')!==-1;
    if(missing || !ph){
      return '<button type="button" class="status-line" data-open-pipeline="1"><span class="dot dot-grey"></span><b>DATA UNAVAILABLE</b> · Dati o pipeline nedostupni</button>';
    }
    var failedList=Array.isArray(ph.sources_failed)?ph.sources_failed:[];
    var degraded = failedList.length>0;
    var srcTxt = (ph.sources_ok!=null) ? (ph.sources_ok+'/'+ph.sources_enabled+' fonti OK') : (ph.sources_enabled+' izvora aktivno');
    return '<button type="button" class="status-line" data-open-pipeline="1"><span class="dot '+(degraded?'dot-orange':'dot-green')+'"></span><b>'+(degraded?'DEGRADED':'ONLINE')+'</b> · ažurirano '+UI.esc(timeHM(ph.last_run)||'—')+' · '+UI.esc(srcTxt)+'</button>';
  }

  function fmtHealthVal(v){
    if(Array.isArray(v)) return v.length?v.join(', '):'—';
    return v!=null?String(v):'—';
  }
  function pipelineSheetBody(ph){
    if(!ph) return '<p class="t-14">Podaci o pipeline nisu dostupni.</p>';
    var rows=[
      ['Zadnje pokretanje', ph.last_run],
      ['Izvora aktivno', ph.sources_enabled],
      ['Fonti OK', ph.sources_ok],
      ['Fonti neuspješno', ph.sources_failed],
      ['Novih stavki (ovaj run)', ph.new_items_this_run],
      ['Clean', ph.clean_total],
      ['Dedup', ph.dedup_total],
      ['Klasteri', ph.clusters_total],
      ['Rassegna', ph.rassegna_total],
      ['Entiteta u registru', ph.trending_entities_registry],
      ['Entiteta aktivnih (24h)', ph.trending_entities_active],
      ['Signal kandidata', ph.signal_candidates_total],
      ['Signal REVIEW', ph.signal_review],
      ['Trajanje (s)', ph.duration_sec]
    ];
    return '<ul class="sheet-list">'+rows.map(function(r){return '<li><b>'+UI.esc(r[0])+':</b> '+UI.esc(fmtHealthVal(r[1]))+'</li>';}).join('')+'</ul>';
  }

  // ---- BETA: sezioni reali (helpers condivisi) -----------------------------

  function emptyState(msg){ return '<div class="empty-state t-14">'+UI.esc(msg)+'</div>'; }
  function sectionShell(title, bodyHtml, seeAllHtml){
    return '<section class="home-section"><div class="home-section-head"><h2>'+UI.esc(title)+'</h2>'+(seeAllHtml||'')+'</div>'+bodyHtml+'</section>';
  }
  function missingOrEmpty(name, data, list, sectionTitle, emptyMsg){
    if((data.__missing||[]).indexOf(name)!==-1) return sectionShell(sectionTitle, emptyState('Dati non disponibili'));
    if(!list.length) return sectionShell(sectionTitle, emptyState(emptyMsg||'Nessun dato recente'));
    return null;
  }

  // ---- BETA: Trending adesso (§6) ------------------------------------------

  function sortTrending(list){
    return list.slice().sort(function(a,b){
      function n(v){return v==null?-Infinity:v;}
      if(n(b.momentum)!==n(a.momentum)) return n(b.momentum)-n(a.momentum);
      if(n(b.unique_sources_24h)!==n(a.unique_sources_24h)) return n(b.unique_sources_24h)-n(a.unique_sources_24h);
      if(n(b.unique_events_24h)!==n(a.unique_events_24h)) return n(b.unique_events_24h)-n(a.unique_events_24h);
      if(n(b.mentions_24h)!==n(a.mentions_24h)) return n(b.mentions_24h)-n(a.mentions_24h);
      return (Date.parse(b.last_event_at||'')||0)-(Date.parse(a.last_event_at||'')||0);
    });
  }
  function trendingRowHtml(e){
    var mom = e.momentum!=null ? ('<span class="trend-up">+'+Math.round(e.momentum*100)+'%</span> momentum · ') : '';
    return '<button type="button" class="home-list-row" data-trend-entity="'+UI.esc(e.entity_id)+'"><div class="home-vrh-row-title">'+UI.esc(e.label)+'</div>'+
      '<div class="home-vrh-row-meta">'+mom+e.unique_events_24h+' eventi · '+e.unique_sources_24h+' fonti · '+UI.esc(UI.formatDate(e.last_event_at||''))+'</div></button>';
  }
  function trendingEntitySheetBody(e){
    var mom = e.momentum!=null ? ('+'+Math.round(e.momentum*100)+'% momentum · ') : '';
    var events=(e.top_events||[]).map(function(ev){
      return '<li>'+(ev.url?('<a href="'+UI.esc(ev.url)+'" target="_blank" rel="noopener">'+UI.esc(ev.title)+'</a>'):UI.esc(ev.title))+
        '<div class="th-meta">'+UI.esc(ev.source_id||'')+' · '+UI.esc(UI.formatDate(ev.published_at||''))+'</div></li>';
    }).join('');
    return '<div class="sheet-section"><p class="t-14">'+mom+e.mentions_24h+' mentions/24h · '+e.unique_events_24h+' eventi · '+e.unique_sources_24h+' fonti</p></div>'+
      '<div class="sheet-section"><h3>Događaji</h3><ul class="sheet-list">'+(events||'<li>Nema.</li>')+'</ul></div>';
  }
  function trendingListSheetBody(list){
    return '<ul class="sheet-list">'+list.map(function(e){
      var mom = e.momentum!=null ? ('+'+Math.round(e.momentum*100)+'% · ') : '';
      return '<li><b>'+UI.esc(e.label)+'</b><div class="th-meta">'+mom+e.unique_events_24h+' eventi · '+e.unique_sources_24h+' fonti</div></li>';
    }).join('')+'</ul>';
  }

  // ---- BETA: Signal "da gledati" (§7) ---------------------------------------

  function sortSignals(list){
    return list.slice().sort(function(a,b){
      if(b.confidence!==a.confidence) return (b.confidence||0)-(a.confidence||0);
      return (Date.parse(b.last_seen||'')||0)-(Date.parse(a.last_seen||'')||0);
    });
  }
  function signalRowHtml(s){
    var m=s.metrics||{};
    return '<button type="button" class="home-list-row" data-signal-idx="'+UI.esc(s.entity_id)+'"><div class="theme-row"><span class="badge badge-alert">REVIEW</span><span class="home-vrh-row-title">'+UI.esc(s.label)+'</span></div>'+
      '<div class="home-vrh-row-meta">'+UI.esc(s.why_now||'')+'</div>'+
      '<div class="home-vrh-row-meta">'+(m.unique_events_24h!=null?m.unique_events_24h+' eventi · ':'')+(m.unique_sources_24h!=null?m.unique_sources_24h+' fonti · ':'')+UI.esc(UI.formatDate(s.last_seen||''))+'</div></button>';
  }
  function signalSheetBody(s){
    var m=s.metrics||{};
    var ev=(s.evidence||[]).map(function(u){return '<li><a href="'+UI.esc(u)+'" target="_blank" rel="noopener">'+UI.esc(u)+'</a></li>';}).join('');
    return '<div class="sheet-section"><span class="badge badge-alert">REVIEW</span><p class="t-14" style="margin-top:8px">'+UI.esc(s.why_now||'')+'</p></div>'+
      '<div class="sheet-section"><h3>Brzi pregled</h3><div class="theme-row"><span class="th-label">eventi: <b>'+(m.unique_events_24h!=null?m.unique_events_24h:'—')+'</b></span><span class="th-label">fonti: <b>'+(m.unique_sources_24h!=null?m.unique_sources_24h:'—')+'</b></span></div></div>'+
      '<div class="sheet-section"><h3>Evidence</h3><ul class="sheet-list">'+(ev||'<li>Nema.</li>')+'</ul></div>';
  }
  function signalListSheetBody(list){
    return '<ul class="sheet-list">'+list.map(function(s){
      return '<li><b>'+UI.esc(s.label)+'</b><div class="th-meta">'+UI.esc(s.why_now||'')+'</div></li>';
    }).join('')+'</ul>';
  }

  // ---- BETA: Rassegna "ultime notizie rilevanti" (§8) -----------------------

  function bestCardLabel(item, allConfigCards){
    var mods=item.modules||[];
    var hit=allConfigCards.find(function(c){ return (c.modules||[]).some(function(m){ return mods.indexOf(m)!==-1; }); });
    return hit ? hit.label : '—';
  }
  function rassegnaRowHtml(item, allConfigCards){
    var titleHtml = item.url ? ('<a href="'+UI.esc(item.url)+'" target="_blank" rel="noopener">'+UI.esc(item.title||'')+'</a>') : UI.esc(item.title||'');
    return '<div class="home-list-row"><div class="home-vrh-row-title">'+titleHtml+'</div>'+
      '<div class="home-vrh-row-meta">'+UI.esc(UI.formatDate(item.date||''))+' · '+UI.esc(item.source_note||'—')+' · '+UI.esc(bestCardLabel(item, allConfigCards))+'</div></div>';
  }

  function render(data){
    var realItems=data.rassegna||[];
    var reviewSignals=data.signals||[];
    var us=byKeys(DashboardConfig.US,['us','stevandic','us-snsd','tesic']);
    var konkurenti=byKeys(DashboardConfig.KONKURENTI,['snsd','sps','skrebic','blanusa','opozicija-odnosi']);
    var teritorij=byKeys(DashboardConfig.TERITORIJ,['ij3','ij5','ij6','ij7']);
    var ostali=byKeys(DashboardConfig.OSTALI,['predsjednik-rs','jorgic','cik','ohr']);
    var all=[].concat(us,konkurenti,teritorij,ostali);
    var allConfigCards=[].concat(DashboardConfig.US,DashboardConfig.KONKURENTI,DashboardConfig.OSTALI,DashboardConfig.TERITORIJ);

    var trendingSorted=sortTrending(data.trending||[]);
    var trendingShown=trendingSorted.slice(0,8);
    var signalSorted=sortSignals(data.signals||[]);
    var signalShown=signalSorted.slice(0,5);
    var rassegnaSorted=realItems.slice().sort(function(a,b){return (Date.parse(b.date||'')||0)-(Date.parse(a.date||'')||0);});
    var rassegnaShown=rassegnaSorted.slice(0,12);

    var trendingHtml = missingOrEmpty('trending', data, trendingSorted, 'Trending adesso') ||
      sectionShell('Trending adesso', '<div class="home-list">'+trendingShown.map(trendingRowHtml).join('')+'</div>',
        trendingSorted.length>trendingShown.length ? '<a href="#" data-see-all="trending">Vidi sve →</a>' : '');
    var signalHtml = missingOrEmpty('signals', data, signalSorted, 'Da gledati') ||
      sectionShell('Da gledati', '<div class="home-list">'+signalShown.map(signalRowHtml).join('')+'</div>',
        signalSorted.length>signalShown.length ? '<a href="#" data-see-all="signal">Vidi sve →</a>' : '');
    var rassegnaHtml = missingOrEmpty('rassegna', data, rassegnaSorted, 'Ultime vijesti', 'Nessuna notizia recente') ||
      sectionShell('Ultime vijesti', '<div class="home-list">'+rassegnaShown.map(function(i){return rassegnaRowHtml(i, allConfigCards);}).join('')+'</div>', '');

    content.innerHTML=UI.pageHead('Radar pregled','Samo ono što je trenutno važno za Ujedinjenu Srpsku. Kada nema promjene, raspored ostaje stabilan.',realItems)+
      pipelineStripHtml(data)+trendingHtml+signalHtml+rassegnaHtml+
      '<div class="home-layout"><div class="home-main">'+
      section('US','us.html',RadarEngine.rankCards(us,realItems,reviewSignals),false)+
      section('Konkurenti','konkurenti.html',RadarEngine.rankCards(konkurenti,realItems,reviewSignals),false)+
      '<div class="home-duo">'+section('Teritorij','go.html',RadarEngine.rankCards(teritorij,realItems,reviewSignals),true)+section('Ostali','ostali.html',RadarEngine.rankCards(ostali,realItems,reviewSignals),true)+'</div>'+
      '</div></div>';
    UI.wireDashboardCards(content,all,realItems,reviewSignals);

    var pipeBtn=content.querySelector('[data-open-pipeline]');
    if(pipeBtn) pipeBtn.addEventListener('click', function(){
      UI.openSheet({ title:'Stato pipeline', triggerEl:pipeBtn, bodyHtml:pipelineSheetBody(data.pipeline_health) });
    });
    content.querySelectorAll('[data-trend-entity]').forEach(function(btn){
      btn.addEventListener('click', function(){
        var e=trendingSorted.find(function(x){return x.entity_id===btn.getAttribute('data-trend-entity');});
        if(e) UI.openSheet({ title:e.label, triggerEl:btn, bodyHtml:trendingEntitySheetBody(e) });
      });
    });
    content.querySelectorAll('[data-signal-idx]').forEach(function(btn){
      btn.addEventListener('click', function(){
        var s=signalSorted.find(function(x){return x.entity_id===btn.getAttribute('data-signal-idx');});
        if(s) UI.openSheet({ title:s.label, triggerEl:btn, bodyHtml:signalSheetBody(s) });
      });
    });
    var seeTrend=content.querySelector('[data-see-all="trending"]');
    if(seeTrend) seeTrend.addEventListener('click', function(e){ e.preventDefault(); UI.openSheet({ title:'Trending — svi', triggerEl:seeTrend, bodyHtml:trendingListSheetBody(trendingSorted) }); });
    var seeSignal=content.querySelector('[data-see-all="signal"]');
    if(seeSignal) seeSignal.addEventListener('click', function(e){ e.preventDefault(); UI.openSheet({ title:'Signal — svi', triggerEl:seeSignal, bodyHtml:signalListSheetBody(signalSorted) }); });
  }
  // ne piu' 'role'/'cases' subscribe qui: render() non dipende piu' da nessuno dei due
  // dopo la rimozione del pannello VRH (§14) — erano solo re-render inutili.
  MPData.loadAll().then(function(data){window.__MP_LAST_DATA__=data;Store.emit('tasks',data.tasks);render(data);});
})();
