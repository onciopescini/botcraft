# 12 — PIANO ESTETICO Botcraft (alto livello, dopo tecnica)

Brand restiamo Botcraft. Regola: estetica MAI davanti alla leggibilità tattica (un pro deve leggere hp/risorse in 1s).

## Fase E1 — Identità (1 settimana)
- Logo: cubo-capsula blu/rosso + totem oro, font geometrico (es. Space Grotesk), palette già in uso `#0b0e14/#4da3ff/#ff5d5d/#ffd700`
- Landing: hero con viewer embeddato in autoplay (demo.jsonl), 3 CTA (gioca / guarda ladder / leggi docs), card share tornei con commentary
- Favicon + OG card con score finale (generata da result.json)

## Fase E2 — Viewer cinematografico (1-2 settimane)
- Skin low-poly vere (non più capsule): bot con occhi/team-stripe, alberi/roccie/oro distinti, totem con glow, muri con crepe per durata
- Effetti: particelle gather, flash hit, scia movimento, KO explosion, day/night per stagione
- Audio: blip gather/craft, thud hit, fanfara finale (WebAudio, mute default)
- Camera: follow leader + free orbit, slow-mo automatico sui KO (rallenta a 0.25x per 2s)

## Fase E3 — Spettacolo sociale (1 settimana)
- Share card video: export 15s webm del momento top (KO o rush) con score overlay, pronta per Discord/X
- Pagina torneo con bracket grafico + commentary caster + replay embeddati
- Profili agente: avatar generato da hash, storico Elo con grafico, badge (rusher/farmer/turtle da stats)

## Fase E4 — Mondo (con S3)
- Biomi per quadranti, stagioni con palette, costruzioni persistenti visibili
- Non ora: niente cambio engine (Three.js resta), niente asset store pesanti

## Non fare
Niente skin pay-to-win (solo cosmetici), niente bloom che copre la minimappa, niente autoplay audio.
