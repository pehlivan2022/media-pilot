---
description: Aggiunge una fonte a config/sources.yaml (e opzionalmente a un target di monitoring.yaml)
argument-hint: --id ID --name NOME --url URL --type {rss,html} [--target TARGET]
---
L'utente vuole aggiungere una fonte. Argomenti forniti: $ARGUMENTS

1. Prima esegui SEMPRE con `--dry-run` e mostra il diff all'utente:
   ```
   python -m pilot.manage add-source $ARGUMENTS --dry-run
   ```
2. Se l'utente conferma il diff, riesegui lo stesso comando senza `--dry-run` per scrivere davvero.

Non inventare valori per `--id/--name/--url/--type` che l'utente non ha fornito: chiedili invece
di indovinarli. `--type` deve essere `rss` o `html`.
