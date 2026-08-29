/* V21 — Arhiva: ricerca semplice + audit log. */
(function(){
 'use strict'; var content=Header.mount(); content.innerHTML=UI.skeleton(6); var q='';
 function text(a){return ((a.title||'')+' '+(a.category||'')+' '+(a.main_actor||'')+' '+(a.territory||'')+' '+(a.learning_note||'')).toLowerCase();}
 function logHtml(){var log=Store.state.blackbox.slice(0,60);return log.length?log.map(function(e){return '<div class="card"><div class="th-meta">'+UI.esc(new Date(e.ts).toLocaleString('sr-Latn'))+' · <b>'+UI.esc(e.actor||e.role)+'</b></div><div class="t-14">'+UI.esc(e.action)+(e.case_id?' · #'+UI.esc(e.case_id):'')+'</div></div>';}).join(''):'<div class="empty-state">Nema zabilježenih akcija.</div>';}
 function render(data){var corpus=UI.buildCorpus(data);var archive=data.archive||[];var f=q?archive.filter(function(a){return text(a).indexOf(q.toLowerCase())!==-1;}):archive;
   content.innerHTML=UI.demoBanner()+UI.pageHead('Arhiva','Pretraga prethodnih događaja i mali audit log odluka / pregleda.',corpus)+
    '<div class="card" style="margin-bottom:14px"><input type="search" id="arh-q" class="role-select" style="width:100%;max-width:none" placeholder="Pretraga: akter, tema, teritorij..." value="'+UI.esc(q)+'"></div>'+
    '<div class="section-title"><h2>Zapisi</h2><span class="section-note">'+f.length+' / '+archive.length+'</span></div><div class="archive-list">'+(f.length?f.slice(0,40).map(function(a){return '<div class="card"><div class="theme-row"><span class="th-label">'+UI.esc(a.category||'')+'</span><span class="th-label">'+UI.esc(a.outcome||'')+'</span></div><div class="t-14" style="font-weight:700;margin-top:6px">'+UI.esc(a.title||'')+'</div><div class="th-meta">'+UI.esc(a.date||'')+' · '+UI.esc(a.main_actor||'')+' · '+UI.esc(a.territory||'')+'</div></div>';}).join(''):'<div class="empty-state">Nema rezultata.</div>')+'</div>'+
    '<div class="section-title"><h2>Audit log</h2><span class="section-note">ko je vidio / odlučio / zadužio</span></div><div id="audit-log">'+logHtml()+'</div>';
   var input=document.getElementById('arh-q');input.addEventListener('input',function(){q=input.value;render(data);});
 }
 MPData.loadAll().then(function(data){window.__MP_LAST_DATA__=data;Store.emit('tasks',data.tasks);render(data);Store.subscribe('role',function(){render(data);});Store.subscribe('blackbox',function(){render(data);});});
})();
