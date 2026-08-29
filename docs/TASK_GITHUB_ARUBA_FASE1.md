# TASK — MEDIA PILOT: GitHub → Aruba / FASE 1

Prompt per Claude Code. Si incolla intero.

## RUOLO

Senior DevOps + Python engineer + GitHub Actions engineer + sysadmin Aruba. Lavori sul progetto
Media Pilot **esistente**. Non riscrivere architettura né scraper. Prima audit, poi riuso, poi
modifiche. È un progetto **beta**: niente hardening esagerato, ma le credenziali non entrano mai
nel repository.

## OBIETTIVO FASE 1

Dimostrare end-to-end che GitHub Actions può prendere i JSON già prodotti dalla pipeline,
validarli e pubblicarli su Aruba, in modo verificabile e ripetibile.

**Non** si esegue ancora lo scraper. **Non** si attiva lo scheduler giornaliero. Il workflow parte
solo con `workflow_dispatch`.

---

## FASE 0 — Il repository non esiste ancora: crealo (fallo per primo)

Stato verificato oggi: **non c'è nessuna cartella `.git`**. Ogni passo che parla di "audit del
repository", "checkout", "repository privato" presuppone qualcosa che va creato adesso.

### 0.1 — Sistemare `.gitignore` PRIMA del primo commit

Questo è il punto in cui il lavoro fallisce se lo salti. `.gitignore` oggi contiene:

```
.env
__pycache__/
*.pyc
data/raw/
data/corpus.db
*.zip
```

**Non copre i file che fanno esplodere il push.** Misurati:

- `data/clean.jsonl` → **132 MB** (GitHub rifiuta i file oltre 100 MB, hard block)
- `data/scored_items.jsonl` → 18 MB
- `data/items.jsonl` → 18 MB

Se fai `git add .` così com'è, il primo push viene rifiutato e ti ritrovi un file enorme già dentro
la storia, da estirpare. Quindi: **ignora tutta `data/`, con una sola eccezione**, perché
`data/pipeline_health.json` serve alla dashboard e va pubblicato:

```
data/*
!data/pipeline_health.json
```

Verifica con `git status --short` e `git count-objects -vH` prima di committare: senza `data/` il
progetto pesa **~4 MB**, tutto commitabile.

### 0.2 — Init, commit, repo privato, push

`git` (2.55) e `gh` (2.96) sono installati e funzionanti sulla macchina. Fai `git init`, il primo
commit, poi crea il repository **privato** e pusha. Mostrami i comandi prima di eseguirli.

Se `gh auth status` dice che non sei autenticato, **fermati e dimmelo**: l'autenticazione la faccio
io, non provare ad aggirarla.

### 0.3 — Nota sul percorso

Il progetto oggi sta in:

```
C:\Users\frontofficedx\Desktop\NIK 2026\US\________media-pilot-v21-2026-08-26\media-pilot-v21-simple
```

Potrebbe essere spostato in `C:\Users\frontofficedx\Desktop\media-pilot`. **Non scrivere questo
percorso dentro nessun file** del repository o del workflow: usa percorsi relativi alla radice del
repo.

---

## 1. AUDIT DEL REPOSITORY

Dopo la Fase 0, produci `docs/GITHUB_ARUBA_DEPLOY_AUDIT.md` con: cosa esiste, cosa verrà
pubblicato, cosa resta privato, problemi trovati.

Parti da questi fatti **già verificati** — confermali, non riscoprirli da zero, e correggimi se
trovi che sono cambiati:

- Pipeline Python in `pilot/`, config YAML in `config/`, dashboard statica multipagina nella radice.
- **I file destinati alla dashboard sono nove JSON in `assets/data/` più uno in `data/`.** Di questi,
  solo **quattro sono prodotti dalla pipeline e cambiano a ogni run**:
  `assets/data/rassegna.json`, `assets/data/trending.json`, `assets/data/signals.json`,
  `data/pipeline_health.json`.
  Gli altri cinque (`alerts`, `archive`, `candidates`, `cases`, `tasks`) sono **ancora dati demo**,
  fermi al 26 agosto: vanno pubblicati lo stesso perché la dashboard li legge, ma dichiarali come
  demo nell'audit.
- `assets/data/rassegna.json.demo-backup` **non va pubblicato**.
- `assets/data/` pesa in tutto ~1,9 MB.
- `.env` contiene due API key (Anthropic, DeepSeek) ed è già in `.gitignore`.

Non inventare path. Se un file che cerchi non c'è, scrivilo.

---

## 2. SICUREZZA (versione beta, essenziale)

- Repository **privato**.
- `.env` fuori dal repo (già coperto da `.gitignore` — verifica con `git check-ignore -v .env`).
- Credenziali Aruba **solo** in `Settings → Secrets and variables → Actions` su GitHub.
- Mai stampare secret nei log del workflow.

**Le credenziali le inserisco io a mano nella UI di GitHub.** Tu non me le chiedere, non provare a
leggerle dal browser o dall'ambiente, non metterle in nessun file. Dimmi solo **quali nomi di
secret** devo creare (es. `ARUBA_FTP_HOST`, `ARUBA_FTP_USER`, `ARUBA_FTP_PASS`, `ARUBA_FTP_DIR`) e
io li creo prima che tu lanci il workflow.

---

## 3. ARUBA — prima capire cosa supporta, poi progettare

Sul mio hosting Aruba c'è già **un WordPress attivo di un altro progetto**: non deve essere toccato
in nessun modo.

**Non assumere che ci sia SSH/SFTP.** Sugli hosting Linux condivisi Aruba tipicamente c'è FTP/FTPS
e non SSH. Prima di scrivere il workflow, determina cosa è realmente disponibile sul mio piano e
scrivilo nell'audit. Se non riesci a determinarlo da solo, **fermati e chiedimelo** — te lo guardo
io dal pannello.

Ordine di preferenza per l'upload: **SFTP/SSH** se c'è davvero, altrimenti **FTPS**, altrimenti
FTP semplice dichiarando che è FTP semplice (progetto beta, ma voglio saperlo).

Struttura: una directory dedicata dentro lo spazio web, separata da WordPress. Il percorso esatto e
l'URL pubblico **chiedimeli**, non inventarli — dipendono da quale dominio o sottodominio voglio
usare, e non l'ho ancora deciso.

Il workflow non deve mai cancellare o toccare file fuori dalla directory Media Pilot.

---

## 4. PERSISTENZA / RAG — solo predisposizione

Niente vector DB, niente embeddings, niente architettura nuova. Crea soltanto le directory vuote
per il futuro:

```
private/
  corpus/
  rag/
  state/
  archive/
  backup/
```

Se l'hosting condiviso **non** permette una directory realmente fuori dalla webroot, scrivilo
nell'audit e non simulare una separazione che non c'è. Obiettivo futuro (non ora): permettere a
GitHub Actions di scaricare lo stato prima del run e ricaricarlo dopo.

---

## 5. WORKFLOW

Crea `.github/workflows/publish-existing-data.yml`, trigger **solo** `workflow_dispatch`.

Passi:

1. checkout;
2. Python 3.12 solo se serve alla validazione;
3. prendi i JSON elencati al punto 1 (i nove di `assets/data/` meno il `.demo-backup`, più
   `data/pipeline_health.json`);
4. valida: JSON sintatticamente corretto, non vuoto, non zero byte;
5. genera il manifest (punto 7);
6. pubblica su Aruba col protocollo determinato al punto 3;
7. non toccare nulla fuori dalla directory Media Pilot;
8. verifica post-upload: riscarica i file appena caricati e confronta gli SHA256.

Nessuno scraping, nessuna chiamata LLM in questo workflow.

---

## 6. DEPLOY ATOMICO

La dashboard non deve mai leggere un JSON caricato a metà. Concretamente, con FTP/FTPS:
carica ogni file come `<nome>.json.new`, e **solo dopo che tutti gli upload sono riusciti**,
rinomina tutti i `.new` sui nomi definitivi. Se il server non supporta `RNFR/RNTO`, dichiaralo nel
report e usa la soluzione più vicina disponibile — senza spacciarla per atomica.

---

## 7. MANIFEST

Genera `assets/data/deploy-manifest.json`:

```json
{
  "generated_at": "...",
  "source": "github-actions",
  "status": "ok",
  "commit": "...",
  "files": [
    { "name": "...", "size": 0, "sha256": "..." }
  ]
}
```

Serve alla dashboard, in futuro, per mostrare ultimo aggiornamento, commit e stato dei dati.

---

## 8. TEST

Lancia il workflow a mano (`gh workflow run`, oppure dimmi di premere il bottone). **PASS solo se**:
Action verde, nessun secret nei log, JSON validi, file presenti su Aruba, checksum coerenti,
manifest presente, URL remoto verificabile, WordPress intatto, nessun dato storico cancellato.

Se fallisce: correggi e rilancia. Non dichiarare PASS con un punto scoperto.

---

## 9. REPORT FINALE

`docs/GITHUB_ARUBA_PHASE1_REPORT.md`, con la checklist dei punti sopra (spuntati o no) più:
durata del workflow, MB trasferiti, path/URL di destinazione, limiti Aruba incontrati, e cosa serve
per la FASE 2.

---

## STOP

Quando la FASE 1 è PASS, **fermati**. Non implementare: cron/scheduler 06:00, esecuzione dello
scraper, chiamate Anthropic/DeepSeek, modifiche alla pipeline, GitHub Pages, nuova dashboard,
vector DB.

La FASE 2 sarà: GitHub Actions → esecuzione reale dello scraper → persistenza dello stato →
scheduler su fuso Europe/Sarajevo → deploy JSON → deploy della dashboard.

## Principi

Niente overengineering. Niente riscritture non necessarie. Niente supposizioni: prima verifichi,
poi modifichi. Nessuna credenziale nel repository. Ogni modifica reversibile.

**Fermati e chiedimi** invece di indovinare, su: autenticazione `gh`, protocollo supportato da
Aruba, dominio/percorso di destinazione. Sono le tre cose che non puoi dedurre dal codice.
