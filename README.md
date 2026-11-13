# Agente de admisión de guardia

Trabajo final — Inteligencia Artificial Generativa — Universidad Austral — **Grupo 11**

| | |
|---|---|
| Modelo en Hugging Face | `<link>` — revisión del punto de control final: `<revisión>` |
| Proyecto de W&B | `<link>` |
| Presentación en Loom | `<link>` |

Integrantes:

- Celina Arias Duval — cariasduval@mail.austral.edu.ar — `cmariasduval`
- Elias Ballesteros — eballesteros@mail.austral.edu.ar — `Elias85974`
- Pedro Del Aguila — pdelaguila@mail.austral.edu.ar — `pedrodelaguila`
- Trinidad Martinez — tmartinez1@mail.austral.edu.ar — `TMartinez0744`

Todo lo de abajo se sigue **con el punto de control publicado y sin entrenar**.

## 1. Entorno

```bash
uv sync
cp .env.example .env   # completar con los valores reales
```

El kit se agrega como dependencia, con la ruta a su carpeta:

```bash
uv add <ruta>/talksmith-ing/missions/TPFinal
```

Variables necesarias: ver `.env.example`.

## 2. Un caso

```bash
uv run python -m admision.correr practica --entrega entrega.py \
    --casos <kit>/practica/casos.jsonl \
    --esperadas <kit>/practica/esperadas-original.jsonl \
    --normas <kit>/normas/original --salida corridas/original
```

Qué se ve: `<TODO: la conversación, las búsquedas en las normas, la ficha registrada y los 9 controles>`

## 3. El buscador

```bash
uv run python -m admision.evaluar_rag --entrega entrega.py \
    --normas <kit>/normas/original --consultas <kit>/rag/consultas_dev.jsonl
```

## 4. La evaluación completa

Los 50 casos de práctica con las normas original, b y c, que producen la tabla del informe:

```bash
<TODO: comando>
```

## 5. De dónde sale cada archivo

| Archivo | Lo genera | Configuración y semilla |
|---|---|---|
| `historial_clasificado.csv` | `uv run python -m curado.clasificar` | sin aleatoriedad |
| `datos/conversaciones.jsonl` | `uv run python -m curado.conversaciones` | sin aleatoriedad |
| `prompt/sistema_optimizado.txt` | `uv run python -m prompt.optimizar --kit <kit> --salida corridas/gepa` | semilla 0, 60 + 40 casos generados, 600 casos jugados |
| cada entrenamiento | `<TODO>` | `<TODO>` |

Volver a entrenar: `<TODO: comando>`. No hace falta para verificar nada de lo de arriba.

## 6. Diagrama

`<TODO: cómo se conectan el agente, sus cinco herramientas, el buscador y el modelo>`
