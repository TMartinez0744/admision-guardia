# Índice de corridas

Cada carpeta es la salida de una corrida (`--salida`). Las de evaluación salen de
`admision.correr practica` y tienen `trazas.jsonl` (por caso, la conversación completa con el modelo
—cada mensaje que entró y cada uno que salió— y cada llamada a una herramienta con su resultado),
`resultados.jsonl` (los 9 controles caso por caso), `resumen.json` y `tiempos.json`. Las tablas del
INFORME salen de `uv run python -m evaluacion.tabla evaluacion/corridas/<corrida>`.

Todas corrieron en una A100 de 40 GB de Modal (`modal_app.py`) con los 50 casos de práctica, y cada
nombre `<corrida>` tiene una carpeta por versión de normas: `<corrida>-original`, `-b` y `-c`.

## Qué punto de control, qué prompt y qué código usó cada una

- **Código:** el commit con el que corrió. Donde dice un rango, `entrega.py`, `buscador/`,
  `prompt/agente.py` y `modal_app.py` no cambian en todo ese rango (`git diff <a> <b> -- ...` vacío).
- **Modelo:** `google/gemma-4-E4B-it` @ `4ecc2ba6` es el modelo sin entrenar. Los entrenados están en
  `Pedro2204/admision-gemma4-e4b`, con la revisión (commit de Hugging Face) que figura en la tabla.
- **Prompt:** el archivo de `prompt/`. Se puede comprobar en cada traza: el primer mensaje de cada
  conversación es exactamente ese archivo.
- **Buscador:** bge-m3 con `k = 3`, en CPU hasta `741bcb5` y en GPU desde ahí (Parte 5).

| Corrida | Parte | Código | Modelo | Revisión | Prompt | Buscador | Original | b | c |
|---|---|---|---|---|---|---|---|---|---|
| `base` | Línea base | `5d369fd` | Gemma 4 E4B sin entrenar | `4ecc2ba6` | de la cátedra (`AgenteJSON`) | CPU | 11 | 5 | 5 |
| `ini` | 3 | `2ce3280` | Gemma 4 E4B sin entrenar | `4ecc2ba6` | `sistema_inicial.txt` | CPU | 7 | 7 | 11 |
| `opt` | 3 | `2ce3280` | Gemma 4 E4B sin entrenar | `4ecc2ba6` | `sistema_optimizado.txt` | CPU | 13 | 15 | 13 |
| `sft-reales` | 4 | `a3e3c0a`–`d171ef9` | `sft-reales` | `988eeea4` | `sistema_optimizado.txt` | CPU | 40 | 31 | 36 |
| `sft-mixto` | 4 | `a3e3c0a`–`d171ef9` | `sft-mixto` | `82c82c42` | `sistema_optimizado.txt` | CPU | 36 | 35 | 36 |
| `sft-mixto-final` (solo `-original`) | 4, intento fallido | `a3e3c0a`–`d171ef9` | `sft-mixto` | `82c82c42` | `sistema_final.txt` | CPU | 30 | – | – |
| `sft-catedra` | 4 | `a3e3c0a`–`d171ef9` | `sft-mixto-catedra` | `d1d5a224` | `sistema_catedra.txt` | CPU | 42 | 44 | 43 |
| `gpu-catedra` | 4 y 5 | `741bcb5` | `sft-mixto-catedra` | `d1d5a224` | `sistema_catedra.txt` | GPU | 42 | 45 | 42 |
| `gpu-final` | 4 y 5 | `741bcb5` | `sft-mixto-final` | `671cca68` | `sistema_final.txt` | GPU | 49 | 50 | 50 |
| **`entrega`** | **final** | **`59632ea`** | **`sft-mixto-final`** | **`671cca68`** | **`sistema_final.txt`** | **GPU** | **49** | **50** | **50** |

`entrega` es `entrega.py` tal cual, sin variables de entorno: exactamente lo que corre la cátedra. Las
demás eligen el modelo y el prompt con `ADMISION_MODELO`, `ADMISION_REVISION` y `ADMISION_PROMPT`.
`gpu-final` y `entrega` dan las mismas 150 conversaciones, palabra por palabra.

## Otras salidas

| Carpeta | Qué es | Lo genera | Código | Modelo y prompt |
|---|---|---|---|---|
| `gepa2` | Optimización de prompt (Parte 3), segunda pasada | `prompt.optimizar` | `6d6e9ce` | sin entrenar; semilla 0 |
| `capacidad-sft-catedra` | Capacidad con el buscador en CPU (Parte 5) | `evaluacion.capacidad` | `a3e3c0a`–`d171ef9` | `sft-mixto-catedra` `d1d5a224`, `sistema_catedra.txt` |
| `capacidad-entrega` | Capacidad del sistema final (Parte 5) | `evaluacion.capacidad` | `59632ea` | `sft-mixto-final` `671cca68`, `sistema_final.txt` |

Los resúmenes de cada entrenamiento (datos y su revisión, semilla, configuración, tiempo, VRAM,
revisión del modelo y corrida de W&B) están en `evaluacion/entrenamientos/<corrida>/resumen.json`.
