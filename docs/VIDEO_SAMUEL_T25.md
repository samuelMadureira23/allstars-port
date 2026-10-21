# Teste do Samuel nº 4 — build-samuel dbaf6b2f (ZETA + menu T-244 + ctx256 + LAN), 19/10 17:10–17:30

Vídeos (locais, NÃO versionar): `C:\Users\samue\Videos\PC port Kratos x Raiden Dojo - 3.mp4`, `Pc Port BIg Daddy x PaRappa Hades - 3.mp4`,
`PC port Video modo Arcade Kratos.mp4`. Referência RPCS3: as gravações `- 2` (mesmas lutas). Análise densa: codex (#4066/T-240).

## Relato do Samuel
**Melhorou (confirmado por ele):** modelo do Kratos "basicamente perfeito"; **menu, seleção e tela de carregamento basicamente
perfeitos** (os personagens aparecem — antes nem apareciam); no Dojo **a transparência dos carros não ocorre mais**; texturas muito
boas; no Hades o titã quase não fica translúcido; **vídeo do modo Arcade do Kratos toca** (prova; ele diz que já tocava há 2+ dias nos
runs dos agentes).

| # | Defeito restante | Leitura / dono |
|---|---|---|
| 1 | **PISCADA — ainda muita**, no cenário E nos lutadores: partes do Kratos/Raiden somem em alguns quadros (Dojo e Hades) | família #3993/#4031: draws do Edge que faltam 1 quadro (pré-passe e cor juntos) — estab/gpu/fantasma/codex; o maior defeito restante |
| 2 | **Tornado do ataque 2 do Kratos não aparece** — talvez outros efeitos não renderizem | efeito ausente (partícula/geometria) — claude-3d |
| 3 | **Corpo do titã translúcido em ALGUNS quadros** (intermitente) | provável mesma família da piscada (#1) |
| 4 | **Rosto do PaRappa na tela final alterna com/sem olhos** | idem (#1) — o decal do rosto existe (3d #4036), some em quadros |
| 5 | (do gpu) fundo da tela de resultado | corrigido por RSX_CLEAR_SCISSOR (d31e0c44), 1º trem da T25 |
| 6 | **Desempenho caiu para ~50 fps em alguns momentos no Dojo** (relato do Samuel) | build novo tem ZETA=1 + TEX_FMTS + SCREEN_AS_TEX=0 + menu: medir o Dojo no dbaf6b2f × 18b2d991 (59,7/55,0) e A/B do ZETA pelo ftrace — claude-perf, 1º exclusivo da T25 |
| ~~7~~ | ~~Menu principal sem a arte do tema~~ — **CORRIGIDO pelo próprio Samuel (17:40): no dbaf6b2f o personagem do tema APARECE no menu principal (antes não aparecia) e na tela de carregamento também.** Mal-entendido meu; T-249 cancelada | — |
