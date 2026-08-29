/* V21 — navigazione tematica. Operatività di ruolo nascosta, salvo VRH. */
(function () {
  'use strict';
  var ROLE_LABEL = { vrh: 'VRH', media: 'Media', eksperti: 'Analiza / Legal', go: 'Teritorij' };
  var VRH_USERS = ['VRH 1','VRH 2','VRH 3','VRH 4']; // sostituire con i 3–4 nomi reali quando definiti

  // VRH i Arhiva su DEMO (cases.json/archive.json, TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02
  // §15): izbačene iz operativnog menija namjerno, ne slučajno. Stranice same ostaju (i dalje
  // dostupne direktnim URL-om, sa DEMO oznakom — vidi UI.demoBanner()), samo se do njih više ne
  // dolazi normalnom navigacijom.
  function allItems() {
    return [
      { href:'index.html', label:'Radar', icon:'◉' },
      { href:'us.html', label:'US', icon:'U' },
      { href:'konkurenti.html', label:'Konkurenti', icon:'↔' },
      { href:'go.html', label:'Teritorij', icon:'⌖' },
      { href:'ostali.html', label:'Ostali', icon:'+' }
    ];
  }
  function currentPath(){ return location.pathname.split('/').pop() || 'index.html'; }
  function isActive(href){ return currentPath() === href; }

  function mobilePrimary() {
    var base = [
      { href:'index.html', label:'Radar', icon:'◉' },
      { href:'us.html', label:'US', icon:'U' },
      { href:'konkurenti.html', label:'Konkurenti', icon:'↔' }
    ];
    base.push({ href:'go.html', label:'Teritorij', icon:'⌖' });
    return base;
  }

  function menuSheet(triggerEl) {
    var rows = allItems().map(function(it){ return '<a class="btn" style="display:flex;width:100%;justify-content:flex-start;margin-bottom:8px;text-decoration:none" href="'+it.href+'"><span class="nav-ico">'+UI.esc(it.icon)+'</span>'+UI.esc(it.label)+'</a>'; }).join('');
    UI.openSheet({ title:'Meni', triggerEl:triggerEl, bodyHtml:rows });
  }

  function renderChrome(chromeEl) {
    var items = allItems();
    chromeEl.innerHTML =
      '<header class="topbar"><div class="brand"><div class="brand-mark">US</div><div><div class="topbar-title">MEDIA PILOT</div><div class="topbar-sub">US RADAR · izbori 2026</div></div></div>' +
      '<div class="topbar-actions">' +
      '<button type="button" class="btn btn-soft nav-toggle" aria-label="Meni">☰</button>' +
      (Store.state.role === 'vrh' ? '<select class="role-select operator-select" aria-label="VRH korisnik">'+VRH_USERS.map(function(n){return '<option'+(Store.state.operator===n?' selected':'')+'>'+UI.esc(n)+'</option>';}).join('')+'</select>' : '') +
      '<select class="role-select main-role" aria-label="Prikaz"><option value="media"'+(Store.state.role!=='vrh'?' selected':'')+'>Standard</option><option value="vrh"'+(Store.state.role==='vrh'?' selected':'')+'>VRH</option></select>' +
      '</div></header>' +
      '<nav class="navbar" aria-label="Navigacija">'+items.map(function(it){return '<a href="'+it.href+'" class="nav-item'+(isActive(it.href)?' active':'')+'"><span class="nav-ico">'+UI.esc(it.icon)+'</span><span class="nav-label">'+UI.esc(it.label)+'</span></a>';}).join('')+'</nav>' +
      '<nav class="mobile-nav" aria-label="Mobilna navigacija">'+mobilePrimary().map(function(it){return '<a href="'+it.href+'" class="'+(isActive(it.href)?'active':'')+'"><span class="nav-ico">'+UI.esc(it.icon)+'</span><span>'+UI.esc(it.label)+'</span></a>';}).join('')+'<button type="button" class="mobile-more"><span class="nav-ico">☰</span><span>Meni</span></button></nav>';

    var roleEl = chromeEl.querySelector('.main-role');
    if (roleEl) roleEl.addEventListener('change', function(e){ Store.setRole(e.target.value); });
    var opEl = chromeEl.querySelector('.operator-select');
    if (opEl) opEl.addEventListener('change', function(e){ Store.setOperator(e.target.value); });
    var more = chromeEl.querySelector('.mobile-more');
    if (more) more.addEventListener('click', function(e){ menuSheet(e.currentTarget); });
    var toggle = chromeEl.querySelector('.nav-toggle');
    if (toggle) toggle.addEventListener('click', function(e){
      if (window.innerWidth >= 769) {
        var next = !Store.state.navCollapsed;
        Store.setNavCollapsed(next);
        document.body.classList.toggle('nav-collapsed', next);
      } else {
        menuSheet(e.currentTarget);
      }
    });
  }

  function watchScroll() {
    // topbar comprimibile allo scroll (§2 FASE 2): niente header fisso a occupare mezzo schermo
    var scrolled = false;
    function onScroll() {
      var next = window.scrollY > 8;
      if (next !== scrolled) { scrolled = next; document.body.classList.toggle('scrolled', next); }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function mount() {
    var root = document.getElementById('app');
    root.innerHTML = '<div class="app-chrome"></div><main id="page-content"></main>';
    var chromeEl = root.querySelector('.app-chrome');
    document.body.classList.toggle('nav-collapsed', !!Store.state.navCollapsed);
    renderChrome(chromeEl);
    Store.subscribe('role', function(){ renderChrome(chromeEl); });
    Store.subscribe('operator', function(){ renderChrome(chromeEl); });
    watchScroll();
    return root.querySelector('#page-content');
  }
  window.Header = { mount: mount, ROLE_LABEL: ROLE_LABEL, VRH_USERS: VRH_USERS };
})();
