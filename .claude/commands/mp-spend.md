---
description: Report spesa LLM (totale, per modello, per giorno, per caller)
argument-hint: "[--days N]"
---
Esegui nella working directory del progetto, passando eventuali argomenti dell'utente
($ARGUMENTS, es. `--days 7`):

```
python -m pilot.spend --report $ARGUMENTS
```

Mostra l'output esatto all'utente. Se `$ARGUMENTS` e' vuoto, esegui senza `--days` (report su
tutto lo storico in `data/spend.jsonl`).
