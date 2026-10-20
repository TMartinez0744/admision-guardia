# Informe

Un apartado por parte, con **cada pasada del desarrollo y no solo la final**, incluidos los
experimentos que no funcionaron. Cada numero dice que comando, que punto de control y que prompt
lo producen.

## Parte 1 — Curado e ingenieria de datos

- Como clasificamos el historial: `<TODO>`
- Filas de cada tipo: correcta `<n>`, error `<n>`, ruido `<n>`
- Como encontramos las costumbres: `<TODO>` (el detalle va en `costumbres.md`)
- Conversaciones de entrenamiento: `<n>` reales, `<n>` sinteticas

## Parte 2 — Buscador (RAG)

Resultado de `admision.evaluar_rag`, al lado de la referencia BM25 de la catedra:

| | Recall de evidencia | Precision | Tokens por consulta | Consultas completas |
|---|---|---|---|---|
| Referencia BM25 | 0,875 | 0,492 | 580 | 51 / 60 |
| Nuestro buscador | `<TODO>` | `<TODO>` | `<TODO>` | `<TODO>` |

Cuanto rinde el agente con nuestro buscador: `<TODO>`

## Parte 3 — Optimizacion de prompt

Con el modelo **sin entrenar**:

| | Casos resueltos | Largo del prompt (tokens) |
|---|---|---|
| Antes de optimizar | `<TODO>` | `<TODO>` |
| Despues de optimizar | `<TODO>` | `<TODO>` |

## Parte 4 — Entrenamiento

Estrategia: `<TODO>`

Casos resueltos sobre los 50 de practica:

| | Normas original | Normas b | Normas c |
|---|---|---|---|
| Referencia catedra, sin entrenar | 12 | 15 | 12 |
| Referencia catedra, con SFT | 25 | 24 | 25 |
| Nuestro modelo, sin entrenar | `<TODO>` | `<TODO>` | `<TODO>` |
| Solo prompt | `<TODO>` | `<TODO>` | `<TODO>` |
| Solo entrenamiento | `<TODO>` | `<TODO>` | `<TODO>` |
| Prompt + entrenamiento | `<TODO>` | `<TODO>` | `<TODO>` |

Corridas que no funcionaron y por que: `<TODO>`

## Parte 5 — Recursos y produccion

- Tiempo de entrenamiento: `<TODO>`
- VRAM usada: `<TODO>`
- Costo y tiempo por caso en la A100 de 40 GB: `<TODO>`
- Casos que procesamos a la vez: `<TODO>`
- Casos simultaneos que tolera en produccion: `<TODO>`
- Proyeccion de consumo: `<TODO>`
- Como escalariamos: `<TODO>`
- Trabajos futuros: `<TODO>`
