/* V21 — izbori, institucije i spoljni faktori. */
(function(){
 'use strict'; var content=Header.mount(); content.innerHTML=UI.skeleton(9);
 function render(data){ var items=data.rassegna||[]; var signals=data.signals||[]; var cards=DashboardConfig.OSTALI; var rows=RadarEngine.rankCards(cards,items,signals);
   content.innerHTML=UI.pageHead('Ostali','Predsjedničke trke, CIK, OHR, Vijeće naroda i drugi faktori koji mogu promijeniti kampanju.',items)+UI.dashboardGridHtml(rows);
   UI.wireDashboardCards(content,cards,items,signals);
 }
 MPData.loadAll().then(function(data){window.__MP_LAST_DATA__=data;Store.emit('tasks',data.tasks);render(data);Store.subscribe('role',function(){render(data);});});
})();
