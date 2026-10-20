# Agente de admision de guardia

TP final — Inteligencia Artificial Generativa — Universidad Austral — Grupo 11

| | |
|---|---|
| Modelo en Hugging Face | `<link>` — revision del punto de control final: `<revision>` |
| Proyecto de W&B | `<link>` |
| Presentacion en Loom | `<link>` |

Integrantes:

- Pedro Del Aguila
- Celina Arias Duval
- Elias Ballesteros
- Trinidad Martinez

Todo lo de abajo se sigue **con el punto de control publicado y sin entrenar**.

## 1. Entorno

```bash
uv sync
cp .env.example .env   # completar con los valores reales
```

El kit de la catedra se agrega como dependencia, con la ruta a su carpeta:

```bash
uv add <ruta>/talksmith-ing/missions/admision-guardia
```

Variables necesarias: ver `.env.example`.

## 2. Un caso

```bash
uv run python -m admision.correr practica --entrega entrega.py \
    --casos <kit>/practica/casos.jsonl \
    --esperadas <kit>/practica/esperadas-original.jsonl \
    --normas <kit>/normas/original --salida corridas/original
```

Que se ve: `<TODO: la conversacion, las busquedas en las normas, la ficha registrada y los 9 controles>`

## 3. El buscador

```bash
uv run python -m admision.evaluar_rag --entrega entrega.py \
    --normas <kit>/normas/original --consultas <kit>/rag/consultas_dev.jsonl
```

## 4. La evaluacion completa

Los 50 casos de practica con las normas original, b y c, que producen la tabla del informe:

```bash
<TODO: comando>
```

## 5. De donde sale cada archivo

| Archivo | Lo genera | Configuracion y semilla |
|---|---|---|
| `historial_clasificado.csv` | `<TODO>` | `<TODO>` |
| conversaciones de entrenamiento | `<TODO>` | `<TODO>` |
| prompt optimizado | `<TODO>` | `<TODO>` |
| cada entrenamiento | `<TODO>` | `<TODO>` |

Volver a entrenar: `<TODO: comando>`. No hace falta para verificar nada de lo de arriba.

## 6. Diagrama

`<TODO: como se conectan el agente, sus cinco herramientas, el buscador y el modelo>`
