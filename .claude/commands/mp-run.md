---
description: Lancia una raccolta mirata (run_monitor) o l'intera pipeline (run_all)
argument-hint: "[--target ID | --priority high|medium|low | --no-collect]"
---
L'utente vuole lanciare una raccolta. Argomenti forniti: $ARGUMENTS

- Se `$ARGUMENTS` contiene `--target` o `--priority`: esegui
  ```
  python -m pilot.run_monitor $ARGUMENTS
  ```
- Se `$ARGUMENTS` contiene `--no-collect`: esegui
  ```
  python -m pilot.run_all --no-collect
  ```
  (rigenera clean/dedup/score/trending/signals/export dai `data/raw/` gia' presenti, nessuna
  raccolta di rete).
- Se `$ARGUMENTS` e' vuoto: NON lanciare nulla di tua iniziativa (una raccolta completa
  `python -m pilot.run_all` tocca la rete e dura diversi minuti) — chiedi all'utente se vuole un
  target/priorita' specifico (vedi `config/monitoring.yaml`: `us_core`, `doboj`, `institutions`,
  `opposition_competitors`, `background`, `pilot_daily_all`), `--no-collect`, o la raccolta
  completa `python -m pilot.run_all`.
