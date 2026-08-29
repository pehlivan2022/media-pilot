/* V21 — US: vrh, kandidati, mandati i ključni odnosi. */
(function(){
 'use strict'; var content=Header.mount(); content.innerHTML=UI.skeleton(10);
 function render(data){ var items=data.rassegna||[]; var signals=data.signals||[]; var cards=DashboardConfig.US; var rows=RadarEngine.rankCards(cards,items,signals);
   content.innerHTML=UI.pageHead('Ujedinjena Srpska','Stevandić, kandidati, mandatne trke i odnosi koji direktno utiču na US.',items)+UI.dashboardGridHtml(rows);
   UI.wireDashboardCards(content,cards,items,signals);
 }
 MPData.loadAll().then(function(data){window.__MP_LAST_DATA__=data;Store.emit('tasks',data.tasks);render(data);Store.subscribe('role',function(){render(data);});});
})();
