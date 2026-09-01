/*
 * dashboard-config.js — Media Pilot V21.3
 * Struttura volutamente semplice: US prima, concorrenti seconda, istituzioni/altro dopo.
 * Ordine base stabile; il RadarEngine promuove solo alert/case/cambiamenti reali.
 */
(function () {
  'use strict';

  function c(key, label, meta, opts) {
    opts = opts || {};
    return Object.assign({
      key: key,
      label: label,
      meta: meta || '',
      mark: opts.mark || '•',
      theme: opts.theme || 'indigo',
      keywords: [],
      modules: [],
      ij: null,
      type: 'actor',
      base: 999
    }, opts);
  }

  var US = [
    c('us', 'Ujedinjena Srpska', 'stranka · kampanja 2026', { base:1, mark:'US', theme:'violet', keywords:['Ujedinjena Srpska'], modules:['US'], type:'party' }),
    c('stevandic', 'Nenad Stevandić', 'predsjednik US · nosilac IJ3', { base:2, mark:'US', theme:'violet', keywords:['Nenad Stevandić','Nenad Stevandic','Stevandić','Stevandic'], modules:['STE','US'] }),
    c('us-snsd', 'US ↔ SNSD', 'savezništvo za inokosne funkcije · konkurencija za NSRS', { base:3, mark:'↔', theme:'violet', keywords:['Ujedinjena Srpska','SNSD'], modules:['REL','US','SNSD'], type:'relation' }),
    c('tesic', 'Rade Tešić', 'US · IJ5 Doboj · nosilac liste', { base:4, mark:'US', theme:'amber', keywords:['Rade Tešić','Rade Tesic'], ij:'IJ5' }),
    c('petkovic', 'Milan Petković', 'US · nosilac PSBiH IJ1', { base:5, mark:'US', theme:'blue', keywords:['Milan Petković','Milan Petkovic'] }),
    c('trninic6', 'Milan Trninić', 'US · IJ6 Bijeljina · nosilac liste', { base:6, mark:'US', theme:'teal', keywords:['Milan Trninić','Milan Trninic'], ij:'IJ6' }),
    c('radovic7', 'Miladin Radović', 'US · IJ7 Zvornik · nosilac liste', { base:7, mark:'US', theme:'teal', keywords:['Miladin Radović','Miladin Radovic'], ij:'IJ7' }),
    c('mejakic1', 'Nenad Mejakić', 'US · IJ1 Prijedor · nosilac liste', { base:8, mark:'US', theme:'teal', keywords:['Nenad Mejakić','Nenad Mejakic'], ij:'IJ1' }),
    c('trninic2', 'Aleksandar Trninić', 'US · IJ2 · nosilac liste', { base:9, mark:'US', theme:'teal', keywords:['Aleksandar Trninić','Aleksandar Trninic'], ij:'IJ2' }),
    c('ivanovic4', 'Nemanja Ivanović', 'US · IJ4 · nosilac liste', { base:10, mark:'US', theme:'teal', keywords:['Nemanja Ivanović','Nemanja Ivanovic'], ij:'IJ4' }),
    c('brezo8', 'Slavka Brezo', 'US · IJ8 · nosilac liste', { base:11, mark:'US', theme:'teal', keywords:['Slavka Brezo'], ij:'IJ8' }),
    c('kovac9', 'Milan Kovač', 'US · IJ9 · nosilac liste', { base:12, mark:'US', theme:'teal', keywords:['Milan Kovač','Milan Kovac'], ij:'IJ9' }),
    c('us-sps', 'US ↔ SPS', 'partner u većini · konkurencija za mandate', { base:13, mark:'↔', theme:'amber', keywords:['Ujedinjena Srpska','SPS','Goran Selak'], modules:['REL','US'], type:'relation' }),
    c('komp-us', 'Kompenzaciona US', 'Nenad Stevandić nosilac', { base:14, mark:'US', theme:'slate', keywords:['kompenzacion'], type:'model' }),
    c('mandati-us', 'Mandatni radar US', 'direktni + kompenzacioni mandati', { base:15, mark:'#', theme:'slate', keywords:['mandat','NSRS','Ujedinjena Srpska'], modules:['US','NSRS','IZB'], type:'model', requireAny:true })
  ];

  var KONKURENTI = [
    c('snsd', 'SNSD', 'glavni saveznik · glavni konkurent za NSRS', { base:1, mark:'SNSD', theme:'rose', keywords:['SNSD'], modules:['SNSD'], type:'party' }),
    c('dodik', 'Milorad Dodik', 'SNSD · lider · glavni politički akter RS', { base:2, mark:'SNSD', theme:'rose', keywords:['Milorad Dodik','Dodik'], modules:['SNSD'] }),
    c('sps', 'SPS · Goran Selak', 'partner većine · konkurent za mandate', { base:3, mark:'SPS', theme:'amber', keywords:['SPS','Goran Selak'], type:'party' }),
    c('skrebic', 'Dragutin Škrebić', 'SPS · IJ5 Teslić · nosilac liste', { base:4, mark:'SPS', theme:'amber', keywords:['Dragutin Škrebić','Dragutin Skrebic','Škrebić','Skrebic'], ij:'IJ5' }),
    c('josic', 'Danijel Jošić', 'SNSD · IJ5 · nosilac liste', { base:5, mark:'SNSD', theme:'rose', keywords:['Danijel Jošić','Danijel Josic'], ij:'IJ5' }),
    c('obren', 'Obren Petrović', 'SNSD · Doboj · nosilac PSBiH IJ2', { base:6, mark:'SNSD', theme:'rose', keywords:['Obren Petrović','Obren Petrovic'], ij:'IJ5' }),
    c('djurkovic', 'Sretko Đurković', 'SPS · Doboj · bivši US', { base:7, mark:'SPS', theme:'amber', keywords:['Sretko Đurković','Sreto Đurković','Sretko Djurkovic','Sreto Djurkovic'], ij:'IJ5' }),
    c('sp-demos', 'SP · DEMOS · NDP', 'koalicioni konkurent', { base:8, mark:'SP', theme:'amber', keywords:['SP-DEMOS-NDP','Socijalistička partija','Socijalisticka partija','DEMOS','NDP','Petar Đokić','Petar Djokic'], type:'party', requireAny:true }),
    c('dns-nps', 'DNS · NPS', 'manji koalicioni konkurent', { base:9, mark:'DNS', theme:'slate', keywords:['DNS-NPS','Darko Banjac','Nenad Nešić','Nenad Nesic'], type:'party', requireAny:true }),
    c('blanusa', 'Branko Blanuša', 'SDS · kandidat za predsjednika RS', { base:10, mark:'SDS', theme:'blue', keywords:['Branko Blanuša','Branko Blanusa'], modules:['BLA'] }),
    c('sds', 'SDS', 'glavna opoziciona stranka', { base:11, mark:'SDS', theme:'blue', keywords:['SDS'], modules:['OPP'], type:'party' }),
    c('stanivukovic', 'Draško Stanivuković', 'PSS · nosilac IJ3', { base:12, mark:'PSS', theme:'blue', keywords:['Draško Stanivuković','Drasko Stanivukovic'], modules:['DRA'] }),
    c('trivic', 'Jelena Trivić', 'Narodni front · nosilac IJ3', { base:13, mark:'NF', theme:'blue', keywords:['Jelena Trivić','Jelena Trivic'], modules:['JEL'] }),
    c('vukanovic', 'Vukanović / Crnadak', 'Za pravdu i red · PDP RS', { base:14, mark:'ZPR', theme:'blue', keywords:['Nebojša Vukanović','Nebojsa Vukanovic','Igor Crnadak','Za pravdu i red','PDP RS'], modules:['VUK','OPP'], type:'party', requireAny:true }),
    c('opozicija', 'Opozicija · odnosi', 'SDS · PSS · NF · ZPR/PDP RS', { base:15, mark:'OP', theme:'blue', keywords:['SDS','PSS','Narodni front','Vukanović','Vukanovic','opozicija'], modules:['OPP','DRA','JEL','VUK'], type:'relation', requireAny:true }),
    c('ij5-konkurencija', 'IJ5 · borba za mandat', 'US · SNSD · SPS · SP · SDS', { base:16, mark:'IJ5', theme:'amber', keywords:['IJ5','Doboj','Teslić','Teslic','Škrebić','Skrebic','Tešić','Tesic','Jošić','Josic'], modules:['IJ','US','SNSD'], ij:'IJ5', type:'race', requireAny:true })
  ];

  var OSTALI = [
    c('predsjednik-rs', 'Predsjednik RS', 'Savo Minić · Branko Blanuša', { base:1, mark:'RS', theme:'rose', keywords:['predsjednik RS','Savo Minić','Savo Minic','Branko Blanuša','Branko Blanusa'], modules:['PRE'], type:'race', requireAny:true }),
    c('minic', 'Savo Minić', 'SNSD · kandidat većine za predsjednika RS', { base:2, mark:'SNSD', theme:'rose', keywords:['Savo Minić','Savo Minic','Minić','Minic'], modules:['PRE'] }),
    c('predsjednistvo', 'Predsjedništvo BiH', 'Cvijanović · Božović · Vukanović', { base:3, mark:'BiH', theme:'blue', keywords:['Predsjedništvo BiH','Predsjednistvo BiH','Cvijanović','Cvijanovic','Božović','Bozovic','Vukanović','Vukanovic'], type:'race', requireAny:true }),
    c('jorgic', 'Marko Jorgić', 'nezavisni · hrvatski kandidat za potpredsjednika RS', { base:4, mark:'MJ', theme:'amber', keywords:['Marko Jorgić','Marko Jorgic'], modules:['PRE'] }),
    c('cik', 'CIK BiH', 'liste · pravila · tehnologija · rezultati', { base:5, mark:'CIK', theme:'cyan', keywords:['CIK','Centralna izborna komisija'], modules:['CIK','IZB'], type:'institution' }),
    c('izborni-proces', 'Izborni proces', 'skeneri · biometrika · biračka mjesta', { base:6, mark:'✓', theme:'cyan', keywords:['skener','biomet','izborni proces','biračko mjesto','biracko mjesto'], modules:['IZB','CIK'], type:'institution', requireAny:true }),
    c('kompenzacione', 'Kompenzacione liste', 'Stevandić · Selak · Mazalica · Čubrilović', { base:7, mark:'#', theme:'slate', keywords:['kompenzacion'], type:'model', requireAny:true }),
    c('vijece', 'Vijeće naroda RS', 'delegati · postizborni odnosi', { base:8, mark:'VN', theme:'blue', keywords:['Vijeće naroda','Vijece naroda'], type:'institution' }),
    c('ohr', 'OHR', 'institucionalni i pravni rizik', { base:9, mark:'OHR', theme:'rose', keywords:['OHR','visoki predstavnik','Crishock','Schmidt'], modules:['OHR','INT'], type:'institution', requireAny:true }),
    c('beograd', 'Beograd / Srbija', 'regionalni politički signal', { base:10, mark:'SRB', theme:'cyan', keywords:['Beograd','Srbija','Vučić','Vucic'], modules:['BEO'], type:'external', requireAny:true }),
    c('finansiranje', 'Finansiranje kampanje', 'OHR mjera za SNSD i US', { base:11, mark:'KM', theme:'slate', keywords:['finansiranje','budžetskih sredstava','budzetskih sredstava'], type:'institution', requireAny:true }),
    c('mediji', 'Medijski signal', 'promjene u intenzitetu i narativu', { base:12, mark:'M', theme:'indigo', modules:['MEDIA','SOURCE','NOISE'], type:'model' })
  ];

  var IJ_NAMES = {
    IJ1:'Prijedor', IJ2:'Gradiška / Laktaši / Prnjavor / Srbac', IJ3:'Banja Luka',
    IJ4:'Derventa / Brod / Modriča / Vukosavlje', IJ5:'Doboj / Teslić / Petrovo / Stanari',
    IJ6:'Bijeljina / Brčko', IJ7:'Zvornik', IJ8:'Istočno Sarajevo', IJ9:'Hercegovina'
  };
  var TERITORIJ = Object.keys(IJ_NAMES).map(function(ij,idx){
    return c(ij.toLowerCase(), ij+' · '+IJ_NAMES[ij], 'NSRS · izborna jedinica', { base:idx+1, mark:ij, theme:'teal', ij:ij, modules:['IJ'], type:'territory' });
  });
  TERITORIJ.push(c('doboj','Doboj','ključni lokalni centar · IJ5',{base:10,mark:'D',theme:'amber',keywords:['Doboj'],ij:'IJ5',type:'territory'}));
  TERITORIJ.push(c('banjaluka','Banja Luka','ključni centar · IJ3',{base:11,mark:'BL',theme:'teal',keywords:['Banja Luka'],ij:'IJ3',type:'territory'}));
  TERITORIJ.push(c('teren-promjene','Promjene na terenu','najveći lokalni pomak u feedu',{base:12,mark:'↑',theme:'teal',modules:['GO','IJ','LHI'],type:'territory',requireAny:true}));

  // --- IJ5 · Doboj / Teslić / Petrovo / Stanari ------------------------------------------
  // Perimetro della vista dedicata (ij5.html): Rade Tešić, i cinque capolista avversari della
  // STESSA izborna jedinica (fonte: assets/data/candidates_source.json, Zvornik Danas
  // 2026-08-18), i partiti che li portano, il territorio.
  //
  // Tre vincoli del codice esistente spiegano perche' questa lista e' costruita cosi':
  //
  // 1) parse_c_calls() (pilot/entities.py:153) legge OGNI c(...) letterale del file e NON
  //    deduplica per key: ripetere qui una card gia' definita sopra creerebbe un'entita'
  //    DOPPIA in config/entities.yaml, che run_all.py rigenera a ogni run. Quindi le card che
  //    esistono gia' vengono riusate per riferimento (pickCard), non ridichiarate.
  //
  // 2) cardItems() (radar.js) filtra con `!card.ij || item.territory_ij === card.ij`, e la
  //    pipeline lascia territory_ij SEMPRE null di proposito (pilot/score.py:112, garantito da
  //    test_9_no_item_has_territory_ij_valued). Una card con `ij` valorizzato quindi non matcha
  //    mai niente: e' il motivo per cui la card 'tesic' e le nove card IJ di go.html oggi sono
  //    vuote per costruzione. pickCard() azzera `ij` sulla COPIA locale, senza toccare le card
  //    originali (us.html e go.html restano esattamente come sono). Il perimetro territoriale
  //    lo applica page-ij5.js filtrando su source_note, che e' un dato reale per ogni item.
  //
  // 3) cardStatus() accende l'ambra solo quando card.key coincide con un entity_id di
  //    signals.json. Le tre card nuove qui sotto (Jović / Smiljanić / Hurtić) NON sono entita'
  //    della pipeline: contano articoli per keyword, ma non diventeranno mai ambra.
  //    Sono dichiarate con ij5Card() e non con c() di proposito. parse_c_calls() scarta le
  //    chiamate con argomenti non letterali (stessa regola che gia' salta il template delle IJ),
  //    quindi passando per questo wrapper le tre card NON entrano in config/entities.yaml e la
  //    pipeline resta identica a prima: nessun run cambia risultato per colpa di questo file.
  //    Per promuoverle a entita' vere (e avere l'ambra) basta riscriverle come c(...) letterali:
  //    farlo consapevolmente, perche' cambia il corpus rilevante di dedup/trending/signals.
  function ij5Card(key, label, meta, opts) { return c(key, label, meta, opts); }

  function pickCard(key, base) {
    var pools = [US, KONKURENTI, OSTALI, TERITORIJ];
    for (var p = 0; p < pools.length; p++) {
      for (var i = 0; i < pools[p].length; i++) {
        if (pools[p][i].key === key) return Object.assign({}, pools[p][i], { ij: null, base: base });
      }
    }
    return null;
  }
  var IJ5 = [
    pickCard('tesic', 1),
    pickCard('josic', 2),
    pickCard('skrebic', 3),
    ij5Card('jovic-ij5', 'Slađan Jović', 'SP-DEMOS-NDP · nosilac liste IJ5', { base:4, mark:'•', theme:'rose', keywords:['Slađan Jović','Sladan Jovic','Слађан Јовић','Јовић'] }),
    ij5Card('smiljanic-ij5', 'Stojan Smiljanić', 'SDS · nosilac liste IJ5', { base:5, mark:'•', theme:'rose', keywords:['Stojan Smiljanić','Stojan Smiljanic','Стојан Смиљанић','Смиљанић'] }),
    ij5Card('hurtic-ij5', 'Sevlid Hurtić', 'Koalicija za državu · nosilac liste IJ5', { base:6, mark:'•', theme:'rose', keywords:['Sevlid Hurtić','Sevlid Hurtic','Севлид Хуртић','Хуртић'] }),
    pickCard('us', 7),
    pickCard('snsd', 8),
    pickCard('sps', 9),
    pickCard('sp-demos', 10),
    pickCard('sds', 11),
    pickCard('doboj', 12),
    pickCard('ij5-konkurencija', 13)
  ].filter(Boolean);

  // source_id -> nome, per le fonti che config/sources.yaml dichiara su IJ5 (piu' le due IJ4
  // confinanti, tenute separate). Duplicato deliberato e piccolo: il frontend non legge YAML.
  // Se si abilitano nuove fonti locali in config/sources.yaml, aggiungerle anche qui.
  var IJ5_SOURCES = {
    RS_IJ_014: { name:'RTV Doboj', territory:'IJ5' },
    RS_IJ_013: { name:'Dobojski.info', territory:'IJ5' },
    RS_IJ_015: { name:'Granice Doboja', territory:'IJ5' },
    RS_IJ_012: { name:'Glas Regije', territory:'IJ4/IJ5' },
    RS_IJ_009: { name:'Derventski List', territory:'IJ4' }
  };

  window.DashboardConfig = { US:US, KONKURENTI:KONKURENTI, OSTALI:OSTALI, TERITORIJ:TERITORIJ, IJ_NAMES:IJ_NAMES, IJ5:IJ5, IJ5_SOURCES:IJ5_SOURCES };
})();
