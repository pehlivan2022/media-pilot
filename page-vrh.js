/* V21 — VRH: poche emergenze, decisione rapida, log piccolo nel popup. */
(function(){
  'use strict';
  var content=Header.mount(); content.innerHTML=UI.skeleton(6);

  function uniqueItems(data){
    var corpus=UI.buildCorpus(data), seen={}, out=[];
    RadarEngine.cases(corpus).concat(RadarEngine.alerts(corpus)).concat(corpus.filter(function(i){return i.signal_to_vrh===true;})).forEach(function(i){
      if(!seen[i.id]){seen[i.id]=true;out.push(i);}
    });
    var now=RadarEngine.datasetNow(corpus);
    var recent=out.filter(function(i){var t=Date.parse(i.date||'');return !isNaN(t)&&(now-t)>=0&&(now-t)<=168*3600*1000;});
    if(recent.length) out=recent;
    return out.sort(function(a,b){
      var pa=RadarEngine.priority(a),pb=RadarEngine.priority(b); var n={P1:3,P2:2,P3:1};
      if(n[pb]!==n[pa]) return n[pb]-n[pa];
      if(RadarEngine.riskScore(b)!==RadarEngine.riskScore(a)) return RadarEngine.riskScore(b)-RadarEngine.riskScore(a);
      return (Date.parse(b.date||'')||0)-(Date.parse(a.date||'')||0);
    }).slice(0,12);
  }

  function itemLog(id){
    return Store.state.blackbox.filter(function(e){return e.case_id===id;}).slice(0,8);
  }
  function logHtml(id){
    var rows=itemLog(id);
    if(!rows.length) return '<div class="th-meta">Još nema akcija.</div>';
    return '<div class="mini-log">'+rows.map(function(e){
      var tm=new Date(e.ts).toLocaleTimeString('sr-Latn',{hour:'2-digit',minute:'2-digit'});
      return '<div class="log-row"><span>'+UI.esc(tm)+'</span><span class="log-actor">'+UI.esc(e.actor||e.role)+'</span><span>'+UI.esc(e.action)+'</span></div>';
    }).join('')+'</div>';
  }

  function evidenceHtml(item){
    var ev=(item.input_news||[]).slice(0,5);
    if(!ev.length && item.source_note) ev=[item.source_note];
    return ev.length?'<ul class="sheet-list">'+ev.map(function(x){return '<li>'+UI.esc(x)+'</li>';}).join('')+'</ul>':'<div class="th-meta">Nema dodatnih evidencija u feedu.</div>';
  }

  function doAction(item, action, target){
    var label=action;
    var status='OTVOREN';
    if(action==='Samo viđeno') status='VIDJENO';
    if(action==='Pratiti') status='PRATI';
    if(action==='Zatvori') status='ZATVOREN';
    if(action==='Odluka') { label='Odluka → '+target; status='U_OBRADI'; }
    Store.logAction({action:label,case_id:item.id,task_id:null,target:target||'vrh',status:status});
    if(action==='Pratiti'||action==='Zatvori'||action==='Odluka') Store.setCaseStatus(item.id,status);
    UI.toast(label+' · zabilježeno');
  }

  function openDecision(item, triggerEl){
    var role=Store.state.role;
    var body='<div class="sheet-section"><div class="theme-row"><span class="badge '+(RadarEngine.priority(item)==='P1'?'badge-case':'badge-alert')+'">'+UI.esc(RadarEngine.priority(item))+'</span><span class="th-label">risk '+RadarEngine.riskScore(item).toFixed(1)+'/5</span><span class="th-label">'+UI.esc(item.territory_raw||item.territory||'')+'</span></div>'+
      '<p class="t-16" style="margin-top:10px;font-weight:700">'+UI.esc(item.summary||item.user_info||item.title)+'</p></div>'+
      '<div class="sheet-section"><h3>Evidence</h3>'+evidenceHtml(item)+'</div>'+
      (role==='vrh'?'<div class="sheet-section"><h3>Brza odluka</h3><div class="btn-row"><button class="btn" data-vrh-act="seen">Samo viđeno</button><button class="btn" data-vrh-act="watch">Pratiti</button></div><div class="th-meta" style="margin-top:12px">Odluka / zaduženje</div><div class="btn-row"><button class="btn btn-primary" data-vrh-target="Media">Media</button><button class="btn btn-primary" data-vrh-target="Analiza">Analiza</button><button class="btn btn-primary" data-vrh-target="Legal">Legal</button><button class="btn btn-primary" data-vrh-target="Teritorij">Teritorij</button><button class="btn" data-vrh-act="close">Zatvori</button></div></div>':'')+
      '<div class="sheet-section"><h3>Log</h3><div id="vrh-popup-log">'+logHtml(item.id)+'</div></div>';
    var sheet=UI.openSheet({title:item.title,triggerEl:triggerEl,bodyHtml:body,onRender:function(root){
      if(role!=='vrh') return;
      function refresh(){var el=root.querySelector('#vrh-popup-log');if(el)el.innerHTML=logHtml(item.id);}
      root.querySelectorAll('[data-vrh-act]').forEach(function(btn){btn.addEventListener('click',function(){var a=btn.getAttribute('data-vrh-act');if(a==='seen')doAction(item,'Samo viđeno');if(a==='watch')doAction(item,'Pratiti');if(a==='close')doAction(item,'Zatvori');refresh();});});
      root.querySelectorAll('[data-vrh-target]').forEach(function(btn){btn.addEventListener('click',function(){doAction(item,'Odluka',btn.getAttribute('data-vrh-target'));refresh();});});
    }});
    return sheet;
  }

  function cardHtml(item){
    var p=RadarEngine.priority(item), cls=p==='P1'?'':' orange';
    return '<div class="vrh-card'+cls+'"><div class="theme-row"><span class="badge '+(p==='P1'?'badge-case':'badge-alert')+'">'+p+'</span><span class="th-label">'+UI.esc(item.territory_raw||item.territory||'')+'</span></div><h3>'+UI.esc(item.title)+'</h3><div class="vrh-why">'+UI.esc(item.summary||item.user_info||'')+'</div>'+
      (Store.state.role==='vrh'?'<div class="vrh-actions"><button type="button" class="btn" data-vrh-quick="seen" data-id="'+UI.esc(item.id)+'">Samo viđeno</button><button type="button" class="btn btn-primary" data-vrh-open="'+UI.esc(item.id)+'">Otvori / odluka</button></div>':'<div class="vrh-actions"><button type="button" class="btn" data-vrh-open="'+UI.esc(item.id)+'">Otvori</button></div>')+'</div>';
  }

  function render(data){
    var corpus=UI.buildCorpus(data), items=uniqueItems(data);
    content.innerHTML=UI.demoBanner()+UI.pageHead('VRH','Samo ono što traži pažnju rukovodstva. Jedan klik za viđeno; odluka i mali audit log u popupu.',corpus)+
      (Store.state.role!=='vrh'?'<div class="card" style="margin-bottom:12px"><b>Read-only prikaz.</b> Odluke su dostupne samo u VRH prikazu.</div>':'')+
      '<div class="vrh-grid">'+(items.length?items.map(cardHtml).join(''):'<div class="empty-state">Nema aktivnih stavki za VRH.</div>')+'</div>';
    content.querySelectorAll('[data-vrh-open]').forEach(function(btn){btn.addEventListener('click',function(){var id=btn.getAttribute('data-vrh-open');var item=items.find(function(x){return x.id===id;});if(item)openDecision(item,btn);});});
    content.querySelectorAll('[data-vrh-quick="seen"]').forEach(function(btn){btn.addEventListener('click',function(){var id=btn.getAttribute('data-id');var item=items.find(function(x){return x.id===id;});if(item){doAction(item,'Samo viđeno');}});});
  }

  MPData.loadAll().then(function(data){window.__MP_LAST_DATA__=data;Store.emit('tasks',data.tasks);render(data);Store.subscribe('role',function(){render(data);});Store.subscribe('operator',function(){render(data);});Store.subscribe('blackbox',function(){});});
})();
