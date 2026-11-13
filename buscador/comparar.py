"""Compara variantes del buscador con la misma métrica de admision.evaluar_rag.

Para cada modelo de embeddings y cada modo (bm25, denso, hibrido) imprime el
resultado con k_entorno = 2 y con presupuesto fijo de 512 tokens. Es lo que
produce la tabla de la Parte 2 del INFORME.

    uv run python -m buscador.comparar --kit <ruta al kit>
"""

import argparse
import json
from pathlib import Path

from admision.evaluar_rag import cargar_dataset, evaluar_buscador, evaluar_recuperador

from buscador.hibrido import MODELOS, BuscadorHibrido


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--normas", default="original")
    ap.add_argument("--modelos", nargs="+", default=list(MODELOS))
    a = ap.parse_args()
    dataset = cargar_dataset(a.kit / "rag" / "consultas_dev.jsonl")
    for modelo in a.modelos:
        buscador = BuscadorHibrido(a.kit / "normas" / a.normas, modelo=modelo)
        for modo in ("bm25", "denso", "hibrido"):
            if modo == "bm25" and modelo != a.modelos[0]:
                continue
            buscador.modo = modo
            fila = {"modelo": modelo if modo != "bm25" else "-", "modo": modo,
                    "entorno": evaluar_buscador(buscador, dataset),
                    "presupuesto_512": evaluar_recuperador(buscador.recuperar, dataset, 512)}
            print(json.dumps(fila, ensure_ascii=False))


if __name__ == "__main__":
    main()
