# Informe

Un apartado por parte, con **cada pasada del desarrollo y no solo la final**, incluidos los
experimentos que no funcionaron. Cada número dice qué comando, qué punto de control y qué prompt
lo producen.

## Parte 1 — Curado e ingeniería de datos

### Cómo clasificamos el historial

Las normas escritas que determinan la ficha se codificaron como reglas en `curado/reglas.py`:
NOR-ADM-01 a NOR-ADM-03 para el registro y la ubicación en el box, NOR-TDE-01 a NOR-TDE-04 para
el circuito y su plazo, y NOR-COB-01 a NOR-COB-04 para la cobertura y la entidad a notificar. Los
valores de los parámetros se leen de la carpeta de normas que se recibe, nunca fijos.

Con esas reglas se deriva la ficha que corresponde a cada fila y se compara contra la registrada,
campo por campo. Una diferencia en cualquiera de los siete campos que las normas determinan es un
**error**. El octavo campo, `aviso_al_voluntariado`, no lo cubre ninguna norma, así que se compara
contra la costumbre; apartarse de ella es **ruido**. Lo que no cae en ninguna de las dos es
**correcta**.

Lo produce `curado/clasificar.py`:

```bash
uv run python -m curado.clasificar --kit <ruta al kit>
```

### Filas de cada tipo

| Tipo | Filas | Proporción |
|---|---|---|
| correcta | 1600 | 80,0% |
| error | 240 | 12,0% |
| ruido | 160 | 8,0% |

Los errores, por campo: `plazo_circuito_min` 97, `registro` 64, `box_antes_del_registro` 61,
`cobertura` 12, `entidad_a_notificar` 6. Los campos `numero_documento` y `circuito` no tienen
ningún error en las 2000 filas.

El ruido, por campo: `aviso_al_voluntariado` 151 y `entidad_verificada` 9.

### Cómo encontramos las costumbres

El detalle y la evidencia están en `costumbres.md`. Son dos: el aviso al voluntariado a partir de
los 75 años sin acompañante, y la elección de la prepaga cuando el paciente presenta dos
credenciales.

El hallazgo que las destrabó fue mirar el comportamiento **por operador**. En el agregado, el
aviso al voluntariado parecía casi aleatorio: 17% de las filas, sin ninguna condición que lo
explicara por encima del 60%. Separando por operador aparece el corte: 17 de los 20 avisan
únicamente con 75 años o más y sin acompañante, con cero excepciones en 1674 filas, mientras que
OP-11, OP-17 y OP-04 avisan también fuera de esa situación.

**Las 160 filas de ruido son exactamente las de esos tres operadores**, y ninguna de los otros 17.

Un desvío que al principio parecía costumbre y no lo era: el `plazo_circuito_min` con cinco
minutos de menos. Lo fija NOR-TDE-04 §1 para los pacientes que llegan en ambulancia, así que las
97 filas que no lo respetan son errores.

### Conversaciones de entrenamiento

**1600 reales, 0 sintéticas.**

Cada traza del historial es una lista de pasos; el modelo se entrena con diálogos. `curado/conversaciones.py`
hace la conversión al formato del agente de ejemplo: mensaje de sistema, pedido inicial, y después un mensaje
del asistente con cada llamada en JSON seguido de uno del usuario con el resultado, salvo tras
`registrar_decision`.

```bash
uv run python -m curado.conversaciones --kit <ruta al kit>
```

Entraron **solo las 1600 filas correctas**. Las 240 con error enseñarían a violar una norma escrita y las 160
con ruido, a apartarse de una costumbre. Quedan disponibles para un experimento posterior: las de ruido no
violan ninguna norma, así que corrigiéndoles el campo que se aparta se podrían sumar 160 ejemplos más y medir
si el modelo mejora. El script acepta `--tipos` para incluirlas.

Dos controles sobre la salida: las 1600 conversaciones quedaron bien formadas —sistema primero, roles
alternados y cierre del asistente con `registrar_decision`— y en las 1600 el último mensaje registra
exactamente la ficha que figura en la traza.

El archivo resultante pesa 18,6 MB y no se versiona: lo regenera el comando de arriba.

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
