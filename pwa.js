/* FASE 2 passo 2: registrazione service worker, INERTE su file:// per costruzione — i service
   worker non si registrano su quell'origine (spec del browser, non solo questo guard), e qui
   evitiamo pure il tentativo per non lasciare una Promise rifiutata in console. Il doppio click
   su index.html resta identico a prima. */
(function () {
  'use strict';
  if (!('serviceWorker' in navigator) || location.protocol === 'file:') return;
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('sw.js').catch(function () { /* silenzioso: la pagina funziona comunque */ });
  });
})();
