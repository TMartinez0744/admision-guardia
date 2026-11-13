"""Resume corridas de admision.correr en una tabla del INFORME.

Cada argumento es un prefijo de corrida: lee ``<prefijo>-original``,
``<prefijo>-b`` y ``<prefijo>-c`` (lo que deja ``--salida``) y escribe una fila
por prefijo con los casos resueltos de cada versión de normas, el promedio de
búsquedas, el contexto por caso (4 caracteres por token) y el tiempo por caso.

    uv run python -m evaluacion.tabla evaluacion/corridas/base
"""

import argparse
import json
from pathlib import Path

VERSIONES = ("original", "b", "c")


def fila(prefijo: str) -> str:
    resumenes = [json.loads(Path(f"{prefijo}-{v}/resumen.json").read_text(encoding="utf-8")) for v in VERSIONES]
    resueltos = [f"{r['resueltos']} / {r['casos']}" for r in resumenes]
    busquedas = sum(r["busquedas_por_caso"] for r in resumenes) / len(resumenes)
    tokens = sum(r["caracteres_de_contexto_por_caso"] for r in resumenes) / len(resumenes) / 4
    segundos = sum(r["segundos"]["jugar_lote_por_caso"] for r in resumenes) / len(resumenes)
    errores = [r.get("error") for r in resumenes if r.get("error")]
    nota = f" (error: {errores[0]})" if errores else ""
    return (f"| {Path(prefijo).name}{nota} | {' | '.join(resueltos)} | {busquedas:.2f} | {tokens:,.0f} | "
            f"{segundos:.2f} |")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prefijos", nargs="+")
    a = ap.parse_args()
    print("| Corrida | Original | b | c | Búsquedas por caso | Tokens de contexto por caso | Segundos por caso |")
    print("|---|---|---|---|---|---|---|")
    for prefijo in a.prefijos:
        print(fila(prefijo))


if __name__ == "__main__":
    main()
