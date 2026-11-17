"""Lectura de las corridas y los entrenamientos guardados en el repo.

``evaluacion.graficos``, ``evaluacion.tabla`` y ``evaluacion.estadistica`` leen los mismos archivos;
las rutas y el formato están acá una sola vez. Las rutas salen de la raíz del repo, así que los
scripts funcionan desde cualquier carpeta.
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CORRIDAS = RAIZ / "evaluacion" / "corridas"
ENTRENAMIENTOS = RAIZ / "evaluacion" / "entrenamientos"
VERSIONES = ("original", "b", "c")


def leer_json(ruta: Path) -> dict:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def resumen(corrida: str, version: str, carpeta: Path = CORRIDAS) -> dict:
    """El ``resumen.json`` de ``<corrida>-<version>``."""
    return leer_json(carpeta / f"{corrida}-{version}" / "resumen.json")


def resumenes(corrida: str, carpeta: Path = CORRIDAS) -> list[dict]:
    """Los resúmenes de la corrida con las tres versiones de normas, en el orden de ``VERSIONES``."""
    return [resumen(corrida, v, carpeta) for v in VERSIONES]


def resueltos(corrida: str) -> list[int]:
    """Casos resueltos con cada versión de normas."""
    return [r["resueltos"] for r in resumenes(corrida)]


def resultados(corrida: str, version: str) -> dict[str, dict]:
    """El ``resultados.jsonl`` de ``<corrida>-<version>``: los controles de cada caso, por id de caso."""
    with (CORRIDAS / f"{corrida}-{version}" / "resultados.jsonl").open(encoding="utf-8") as f:
        filas = [json.loads(linea) for linea in f if linea.strip()]
    return {fila["caso"]: fila for fila in filas}


def entrenamiento(nombre: str) -> dict:
    """El ``resumen.json`` que dejó ``entrenamiento/sft.py`` al terminar."""
    return leer_json(ENTRENAMIENTOS / nombre / "resumen.json")


def perdida(nombre: str) -> list[dict]:
    """Los puntos ``{paso, perdida}`` de la curva bajada de W&B."""
    return leer_json(ENTRENAMIENTOS / nombre / "perdida.json")["puntos"]


def capacidad(carpeta: str) -> list[dict]:
    """Los lotes de una corrida de ``evaluacion.capacidad``."""
    return leer_json(CORRIDAS / carpeta / "capacidad.json")["lotes"]
