/* V21 — Teritorij: svih 9 IJ + Doboj/Banja Luka + najveća promjena na terenu. */
(function(){
 'use strict'; var content=Header.mount(); content.innerHTML=UI.skeleton(10);
 function render(data){ var items=data.rassegna||[]; var signals=data.signals||[]; var cards=DashboardConfig.TERITORIJ; var rows=RadarEngine.rankCards(cards,items,signals);
   content.innerHTML=UI.pageHead('Teritorij','Izborne jedinice ostaju uvijek vidljive; alert ili značajna promjena ih automatski pomjera prema vrhu.',items)+UI.dashboardGridHtml(rows);
   UI.wireDashboardCards(content,cards,items,signals);
 }
 MPData.loadAll().then(function(data){window.__MP_LAST_DATA__=data;Store.emit('tasks',data.tasks);render(data);Store.subscribe('role',function(){render(data);});});
})();
