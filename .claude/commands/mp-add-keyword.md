---
description: Aggiunge una parola chiave a config/topics.yaml (weak_keywords)
argument-hint: --term PAROLA
---
L'utente vuole aggiungere una parola chiave al filtro di rilevanza. Argomenti forniti: $ARGUMENTS

1. Prima esegui SEMPRE con `--dry-run` e mostra il diff all'utente:
   ```
   python -m pilot.manage add-keyword $ARGUMENTS --dry-run
   ```
2. Se l'utente conferma, riesegui senza `--dry-run`.

Nota per te, non per l'utente: `config/topics.yaml` oggi e' una lista piatta `weak_keywords`,
senza raggruppamento per topic — `--topic` viene accettato ma non ha effetto (vedi commento in
`pilot/manage.py`).
