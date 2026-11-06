# Informe

Un apartado por parte, con **cada pasada del desarrollo y no solo la final**, incluidos los
experimentos que no funcionaron. Cada número dice qué comando, qué punto de control y qué prompt
lo producen.

## Parte 1 — Curado e ingeniería de datos

- Cómo clasificamos el historial: `<TODO>`
- Filas de cada tipo: correcta `<n>`, error `<n>`, ruido `<n>`
- Cómo encontramos las costumbres: `<TODO>` (el detalle va en `costumbres.md`)
- Conversaciones de entrenamiento: `<n>` reales, `<n>` sintéticas

### Pistas abiertas

- **El plazo que termina en 5.** `plazo_circuito_min` toma dos valores por circuito más dos
  variantes cinco minutos menores: sepsis 15 y 60, pero también 10 y 55; ECG 10 y también 5;
  código ACV 10 y también 5. El desvío está repartido parejo entre los 20 operadores (del 12% al
  29%), así que no es un operador descuidado: o depende de alguna condición del caso, o es una
  costumbre no escrita. Falta resolverlo.

## Parte 2 — Buscador (RAG)

Resultado de `admision.evaluar_rag` sobre `rag/consultas_dev.jsonl`, con `k_entorno = 2`:

| | Recall de evidencia | Precisión | Tokens por consulta | Consultas completas |
|---|---|---|---|---|
| Referencia BM25 | 0,875 | 0,492 | 580 | 51 / 60 |
| BM25 propio, por párrafo | 0,625 | 0,358 | **166** | 36 / 60 |

Primera versión: BM25 sobre las normas partidas **por párrafo** (cada `§N.`) en vez de por sección
entera, con el encabezado de la sección y la línea de valores de los parámetros que ese párrafo
cita. Queda por debajo de la referencia en recall, pero usa 166 tokens contra 580: casi cuatro
veces menos contexto. Con presupuesto fijo de 512 tokens, comparable al de la referencia, sube a
0,767 de recall con 470 tokens.

Recall por tipo de consulta, que es donde está el problema:

| Tipo | Recall |
|---|---|
| directa | 0,850 |
| numérica | 0,833 |
| distractora | 0,750 |
| dos secciones | 0,562 |
| **coloquial** | **0,000** |

De las 12 consultas coloquiales no acierta ninguna. Es coincidencia léxica pura: si la consulta no
usa las palabras de la norma, un buscador por palabras no la encuentra. De ahí que la siguiente
versión sea vectorial.

Cuánto rinde el agente con nuestro buscador: `<TODO>`

## Parte 3 — Optimización de prompt

Con el modelo **sin entrenar**:

| | Casos resueltos | Largo del prompt (tokens) |
|---|---|---|
| Antes de optimizar | `<TODO>` | `<TODO>` |
| Después de optimizar | `<TODO>` | `<TODO>` |

## Parte 4 — Entrenamiento

Estrategia: `<TODO>`

Casos resueltos sobre los 50 de práctica:

| | Normas original | Normas b | Normas c |
|---|---|---|---|
| Referencia, sin entrenar | 12 | 15 | 12 |
| Referencia, con SFT | 25 | 24 | 25 |
| Nuestro modelo, sin entrenar | `<TODO>` | `<TODO>` | `<TODO>` |
| Solo prompt | `<TODO>` | `<TODO>` | `<TODO>` |
| Solo entrenamiento | `<TODO>` | `<TODO>` | `<TODO>` |
| Prompt + entrenamiento | `<TODO>` | `<TODO>` | `<TODO>` |

Corridas que no funcionaron y por qué: `<TODO>`

## Parte 5 — Recursos y producción

- Tiempo de entrenamiento: `<TODO>`
- VRAM usada: `<TODO>`
- Costo y tiempo por caso en la A100 de 40 GB: `<TODO>`
- Casos que procesamos a la vez: `<TODO>`
- Casos simultáneos que tolera en producción: `<TODO>`
- Proyección de consumo: `<TODO>`
- Cómo escalaríamos: `<TODO>`
- Trabajos futuros: `<TODO>`
