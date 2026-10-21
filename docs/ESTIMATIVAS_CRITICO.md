# Estimativas de tempo do crítico — registro e conferência

Por que existe: em 18/10, as minhas estimativas (e as do time) erraram por semanas a meses, **sempre para o lado
pessimista**. A partir de 20/10, cada estimativa entra aqui com data e é conferida no fechamento seguinte. O fator de
erro medido corrige a próxima.

## Histórico (estimado × real)

| Data da estimativa | O quê | Estimado | Real | Erro |
|---|---|---|---|---|
| 18/10 04:40 (reunião) | 30 fps estáveis | meados de novembro | 19/10 07:40 (T21) | ~4 semanas pessimista |
| 18/10 04:40 | 60 fps | janeiro | 19/10 14:00 (T23) | ~2–3 meses pessimista |
| 18/10 04:40 | partida LAN na mesma luta / até o fim | meados de novembro | luta 18/10 22:00 (T20); fim 19/10 19:22 (T25) | ~4 semanas pessimista |
| 18/10 04:40 | luta jogável completa | fim de novembro | Samuel: "quase indistinguível do RPCS3" em 19/10 23:10 | ~5 semanas pessimista |
| 18/10 04:37 | "30 fps nesta semana" (eu, e depois retirei) | ≤ 25/10 | 19/10 | eu **acertei** e retirei por pressão do consenso |

**Fator medido:** a realidade veio de **3 a 10 vezes mais rápida** que a estimativa.
Causa [I]: estimei somando sintomas e cortes de +5–10%, um de cada vez. Na prática eram poucas causas globais, ganhos em
salto e 8 a 10 agentes em paralelo (ver `docs/RETROSPECTIVA_5_DIAS.md` §5).

## Estimativa corrigida (20/10, ~13:40) — base: rubrica 60,2% (offline 71, online 35)

Fiz a estimativa pelo tipo de trabalho que falta e dividi por ~3, que é o meu histórico. Incerteza alta.

| O que falta | Pontos em aberto | Estimativa corrigida | Conferir em |
|---|---|---|---|
| Só prova ou medida: aba Controles (Samuel), 2º run do 1.12 em build padrão, CPU/RAM < RPCS3 | ~4 | **1–2 temporadas** | 21/10 |
| Cobertura visual: 14 cenários e 20 lutadores × RPCS3, céu e sombras, modos, saves e diálogos | ~20 | **3–5 dias** (era 1–2 semanas) | 24/10 |
| Trava do anel (~1 em 8 lutas) | ~2 + confiança | **imprevisível**: pode cair numa temporada, como a piscada | a cada fechamento |
| LAN entre 2 PCs (Samuel + amigo) | ~8 (N2) + até 10 (N4) | **depende só do teste dos dois** | quando jogarem |
| Servidor próprio + hospedagem | ~50 do online | **2–4 semanas**, se o Samuel decidir fazer | decisão do Samuel |
| **Total ~75–80%** | — | **menos de 1 semana** (era ~2 semanas) | 26/10 |
| **Offline perto de completo (≥ 90)** | — | **3–5 dias** (era 2–3 semanas) | 25/10 |

Regra: no fechamento de cada temporada, comparo com o real e atualizo o fator.
