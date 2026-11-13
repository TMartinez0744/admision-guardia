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

### Segunda pasada: embeddings y búsqueda híbrida

`buscador/hibrido.py` agrega embeddings sobre los **mismos chunks por párrafo** y tres modos:
solo BM25, solo embeddings (`denso`) e `hibrido`, que fusiona los dos rankings con Reciprocal Rank
Fusion (constante 60). Probamos tres modelos de embeddings multilingües, cada uno fijado a su commit
de Hugging Face: `intfloat/multilingual-e5-small`, `intfloat/multilingual-e5-base` y `BAAI/bge-m3`.
Corren en CPU, para no quitarle VRAM al modelo del agente.

```bash
uv run python -m buscador.comparar --kit <ruta al kit>
```

Normas originales, `k = 2`:

| Variante | Recall | Precisión | Tokens | Completas | Recall coloquial | Recall a 512 tokens |
|---|---|---|---|---|---|---|
| BM25 | 0,625 | 0,358 | 173 | 36 / 60 | 0,000 | 0,783 |
| e5-small, denso | 0,767 | 0,433 | 178 | 44 / 60 | 0,333 | 0,892 |
| e5-small, híbrido | 0,700 | 0,392 | 182 | 39 / 60 | 0,083 | 0,833 |
| e5-base, denso | 0,767 | 0,433 | 173 | 43 / 60 | 0,417 | 0,908 |
| e5-base, híbrido | 0,742 | 0,417 | 174 | 42 / 60 | 0,250 | 0,842 |
| **bge-m3, denso** | **0,792** | **0,458** | 179 | **46 / 60** | **0,500** | **0,950** |
| bge-m3, híbrido | 0,708 | 0,400 | 179 | 40 / 60 | 0,250 | 0,850 |

El BM25 de esta tabla da 173 tokens y no 166 porque acá devuelve siempre `k` chunks, aunque alguno
tenga puntaje cero.

**Lo que no funcionó: el híbrido.** Esperábamos que combinar los dos sumara, y en los tres modelos
rindió peor que los embeddings solos. En las consultas coloquiales BM25 pone arriba párrafos que
comparten palabras sueltas pero no el sentido, y la fusión los mete entre los primeros. Los
embeddings solos también resuelven las consultas directas y numéricas, que era donde BM25 servía.

Después, la cantidad de chunks por búsqueda con bge-m3:

| `k_entorno` | Recall | Precisión | Tokens | Completas |
|---|---|---|---|---|
| 2 | 0,792 | 0,458 | 179 | 46 / 60 |
| **3** | **0,883** | 0,339 | 270 | **52 / 60** |
| 4 | 0,892 | 0,258 | 352 | 53 / 60 |

Pasar de 3 a 4 casi no suma recall y agrega 80 tokens por búsqueda.

### Buscador elegido

**bge-m3, solo embeddings, `k_entorno = 3`**, que es el que arma `entrega.py`:

```bash
uv run python -m admision.evaluar_rag --entrega entrega.py --normas <kit>/normas/original \
    --consultas <kit>/rag/consultas_dev.jsonl
```

| | Recall de evidencia | Precisión | Tokens por consulta | Consultas completas |
|---|---|---|---|---|
| Referencia BM25 | 0,875 | 0,492 | 580 | 51 / 60 |
| BM25 propio, por párrafo | 0,625 | 0,358 | 166 | 36 / 60 |
| **bge-m3 por párrafo, k = 3** | **0,883** | 0,339 | **270** | **52 / 60** |

Supera a la referencia en recall y en consultas completas con menos de la mitad del contexto. La
precisión es menor porque trae 3 chunks chicos en vez de 2 secciones enteras: el tercero muchas
veces sobra, pero cuesta poco. Con presupuesto fijo, el mismo buscador da 0,842 a 256 tokens, 0,950
a 512 y 0,983 a 1024. Sigue fallando en 5 de las 12 consultas coloquiales (recall 0,583).

En un M1 Max, armar el buscador tarda 7 s (81 chunks) y cada búsqueda unos 100 ms en CPU.

Dos salvedades:

- Elegimos el modelo y `k` mirando estas 60 consultas, que son las mismas con las que lo medimos.
  El número real es lo que rinda el agente con el test.
- Con las normas b y c las consultas de la cátedra no sirven para medir: su evidencia trae los
  números de las normas originales, que en b y c no aparecen. Por eso el recall numérico cae de
  1,000 a 0,250, y no porque el buscador empeore.

### Cuánto rinde el agente con nuestro buscador

Línea base: Gemma 4 E4B sin entrenar, con el agente y el mensaje de sistema de ejemplo de la
cátedra, y nuestro buscador (bge-m3, `k = 3`), sobre los 50 casos de práctica. Corrió en una A100
de 40 GB de Modal (`modal_app.py`), en el commit `5d369fd`:

```bash
uv run modal run modal_app.py --comando "python -m admision.correr practica --entrega entrega.py \
    --casos ../talksmith-ing/missions/TPFinal/practica/casos.jsonl \
    --esperadas ../talksmith-ing/missions/TPFinal/practica/esperadas-<versión>.jsonl \
    --normas ../talksmith-ing/missions/TPFinal/normas/<versión> --salida /cache/corridas/base-<versión>"
uv run python -m evaluacion.tabla evaluacion/corridas/base
```

Las trazas completas (cada mensaje que entró y salió del modelo), el resultado caso por caso y los
tiempos están en `evaluacion/corridas/base-<versión>/`.

| | Original | b | c | Búsquedas por caso | Tokens de contexto por caso |
|---|---|---|---|---|---|
| Referencia: BM25 por sección, sin entrenar | 12 | 15 | 12 | | |
| **Nuestro buscador, sin entrenar** | **11** | **5** | **5** | 1,28 | 4.278 |

Por control, sobre los 50 casos:

| Control | Original | b | c |
|---|---|---|---|
| registro | 0,60 | 0,54 | 0,62 |
| numero_documento | 1,00 | 1,00 | 1,00 |
| box_antes_del_registro | 0,64 | 0,62 | 0,66 |
| circuito | 0,94 | 0,98 | 0,96 |
| plazo_circuito_min | 0,80 | 0,80 | 0,80 |
| cobertura | 0,80 | 0,84 | 0,74 |
| entidad_a_notificar | 0,84 | 0,80 | 0,82 |
| aviso_al_voluntariado | 0,72 | 0,72 | 0,72 |
| verificacion | 0,80 | 0,82 | 0,78 |

Lo que leemos:

- **La caída de 11 a 5 con b y c no es de un control en particular.** Los nueve controles dan casi
  igual en las tres versiones; `plazo_circuito_min`, el que más depende de los números, da 0,80 en
  las tres. Con cada control alrededor del 80%, acertar los nueve juntos es poco probable y unos
  pocos campos mueven mucho el total: la diferencia entre 11 y 5 es sobre todo varianza de un
  modelo poco confiable.
- **El modelo no está usando los números de las normas originales.** De los 70 campos que falla
  con las normas b, solo 12 coinciden con lo que correspondería con las originales.
- **Busca poco:** 1,28 búsquedas por caso y 4,9 llamadas en total, así que muchas fichas se deciden
  sin leer la norma que corresponde. El prompt (Parte 3) y el entrenamiento (Parte 4) apuntan a eso.
- **`aviso_al_voluntariado` queda en 0,72 en las tres versiones:** es una costumbre que no está
  escrita en ninguna norma, así que el modelo sin entrenar no tiene cómo saberla.
- **Contra la referencia, el resultado es algo peor**, sobre todo con b y c. No podemos separar
  cuánto viene del buscador y cuánto de la varianza: con el modelo sin entrenar, el número que
  importa es el del agente entrenado.

## Parte 3 — Optimización de prompt

### Cómo optimizamos

Usamos **GEPA** (`gepa==0.1.4`), el optimizador que sugiere la consigna, sobre el mensaje de
sistema del agente de ejemplo. GEPA juega casos con un prompt candidato, junta en qué controles
falló cada uno y le pide a un modelo reflector que proponga una versión mejor. Se queda con las
que mejoran en un conjunto de validación.

- **El reflector es la misma Gemma 4 E4B** del agente, en la misma A100: no pagamos ninguna API.
- **Casos para optimizar: 100 generados** con `admision.generador` (semilla 0), 60 para proponer y
  40 para validar. Los 50 de práctica no se tocan, porque con ellos se mide el antes y el después.
- **La respuesta de cada caso generado la calcula `curado/etiquetar.py`** con las reglas y
  costumbres de la Parte 1. Antes de usarlo lo controlamos con los 50 casos de práctica: da
  **50/50 fichas iguales a las de la cátedra con las normas original, b y c**. Eso también
  confirma las reglas y costumbres de la Parte 1.

  ```bash
  uv run python -m curado.etiquetar --kit <ruta al kit>
  ```

- **Las normas rotan** entre original, b y c, una por caso. Un prompt que escriba un número de las
  normas falla en las otras dos versiones, y además la devolución al reflector le pide no
  escribirlos.
- **El puntaje de un caso** es la fracción de los 9 controles que pasa, no solo resuelto o no: así
  GEPA distingue una ficha casi bien de una vacía.
- `prompt/agente.py` es el agente de la cátedra con el mensaje de sistema como parámetro; el
  protocolo JSON no cambia.

```bash
uv run python -m prompt.optimizar --kit <ruta al kit> --salida corridas/gepa
```

Deja el prompt ganador en `prompt/sistema_optimizado.txt` y los registros de GEPA y
`resultado.json` en `--salida`. Antes de correrlo en GPU, lo probamos de punta a punta en CPU con un
modelo falso, para controlar el circuito: el entorno, el puntaje, la devolución y el guardado.

### Resultados

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
| Nuestro modelo, sin entrenar | 11 | 5 | 5 |
| Solo prompt | `<TODO>` | `<TODO>` | `<TODO>` |
| Solo entrenamiento | `<TODO>` | `<TODO>` | `<TODO>` |
| Prompt + entrenamiento | `<TODO>` | `<TODO>` | `<TODO>` |

Corridas que no funcionaron y por qué: `<TODO>`

## Parte 5 — Recursos y producción

- Tiempo de entrenamiento: `<TODO>`
- VRAM usada: `<TODO>`
- Costo y tiempo por caso en la A100 de 40 GB: con el modelo sin entrenar, los 50 casos juegan a la
  vez en unos 37 s, o sea **0,74 s por caso**, con 4.278 tokens de contexto por caso. Cargar el
  modelo tarda 271 s y armar el buscador 50 s, una sola vez por proceso
  (`evaluacion/corridas/base-<versión>/resumen.json`). `<TODO: costo con el modelo final>`
- Casos que procesamos a la vez: al evaluar, **los 50 casos en el mismo lote**: vLLM agrupa en cada
  vuelta las conversaciones que siguen activas. `<TODO: entrenamiento>`
- Casos simultáneos que tolera en producción: `<TODO>`
- Proyección de consumo: `<TODO>`
- Cómo escalaríamos: `<TODO>`
- Trabajos futuros: `<TODO>`
