# 13 — S3 SPEC (mondo persistente FFA, macro-finale tecnico)

Attiva da: 21/09/2026. 1v1 e squadre restano validi e invariati.

## S3.1 Formato stagione
Mappa 64x64 di default (128/256 come scale-up con sharding futuro). N agenti free-for-all (default 12, max 50), OGNUNO col suo bot. 500 tick/stagione (~4 min simulati in <30s). Respawn agenti morti dopo 50 tick allo spawn. Respawn risorse come S1 (20 tick). Snapshot stato ogni 100 tick. Report `season.json` con standings + territorio.

## S3.2 OBS compatibile 1v1
Stesso shape di `to_obs` S1 + `name` + `agents_alive`. Bot greedy/llm esistenti girano invariati nel mondo. `enemy` = nemico visibile più vicino, `nearby` = 5 risorse vicine, `squad` assente (FFA). Memoria per-nome come nel runner 1v1.

## S3.3 Azioni
Subset S1: move, gather, attack (primo nemico adiacente), craft_sword/wall_kit, place_wall, message (udito entro raggio 7), noop. Niente stick? Tenuto per compatibilità ma inutile.

## S3.4 Score + territorio
Score individuale come S1 (wood+stone+gold*3+kill*10+totem15). Territorio: 4 quadranti, ogni 100 tick il quadrante va a chi ha più unità vive dentro (pareggio = nessuno). Campione stagione = score max; re dei territori = più quadranti tenuti all'ultimo snapshot.

## S3.5 Replay delta (efficienza)
Non 70 posizioni/tick: `delta.jsonl` con solo `{tick, dead:[...], respawned:[...], moved:{name:[x,y,hp]...}, gathered:{...}, msgs:{...}}` per agenti CAMBIATI + snapshot pieno ogni 100 tick. Stima: ~150B/tick vs 925B → stagione 500 tick ≈ 75KB invece di 460KB.

## S3.6 Cosa NON c'è (futuro)
Sharding per zone, alleanze formali (solo message emergenti), Postgres (SQLite regge fino a ~100 stagioni, poi 1 env var), costruzioni oltre i muri.
