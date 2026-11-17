"""Cuánto se puede confiar en las diferencias entre corridas, con 50 casos por versión de normas.

Cada corrida resuelve o no cada uno de los 50 casos de práctica, en tres versiones de normas
(150 casos). Con tan pocos casos, una diferencia de 2 o 3 puede ser azar. Este script lee los
``resultados.jsonl`` ya guardados (no corre el modelo) y calcula:

1. para cada corrida, los casos resueltos con un intervalo de confianza del 95 % (Wilson), por
   versión de normas y juntando las tres;
2. para cada par de corridas consecutivas, una prueba de McNemar exacta sobre los mismos 150
   casos: cuenta los casos que resuelve solo una de las dos y pregunta si esa diferencia podría
   salir por azar (p bilateral);
3. el porcentaje de aciertos de cada uno de los 9 controles, juntando las tres versiones.

    python -m evaluacion.estadistica
    python -m evaluacion.estadistica base opt sft-catedra entrega

Solo usa la biblioteca estándar: no hace falta ``uv sync`` ni el kit.
"""

from __future__ import annotations

import argparse
import math

from evaluacion.lectura import VERSIONES
from evaluacion.lectura import resultados as cargar

POR_DEFECTO = ("base", "ini", "opt", "sft-reales", "sft-mixto", "sft-catedra", "gpu-catedra", "gpu-final",
               "entrega")
CONTROLES = ("registro", "numero_documento", "box_antes_del_registro", "circuito", "plazo_circuito_min",
             "cobertura", "entidad_a_notificar", "aviso_al_voluntariado", "verificacion")
Z_95 = 1.959963984540054


def wilson(exitos: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción. Se porta bien cerca de 0 y de 1, a diferencia del
    intervalo normal, que con 50/50 daría un intervalo de ancho cero."""
    if n == 0:
        return 0.0, 1.0
    p = exitos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    radio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    bajo = 0.0 if exitos == 0 else max(0.0, centro - radio)
    alto = 1.0 if exitos == n else min(1.0, centro + radio)
    return bajo, alto


def mcnemar_exacto(solo_a: int, solo_b: int) -> float:
    """p bilateral de McNemar exacto: con b = solo_a + solo_b casos discordantes, bajo la hipótesis
    de que las dos corridas son igual de buenas cada uno cae de un lado con probabilidad 1/2."""
    n = solo_a + solo_b
    if n == 0:
        return 1.0
    k = min(solo_a, solo_b)
    cola = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * cola)


def resueltos(resultados: dict[str, dict]) -> set[str]:
    return {caso for caso, fila in resultados.items() if fila["resuelto"]}


def _intervalo(exitos: int, n: int) -> str:
    bajo, alto = wilson(exitos, n)
    return f"{exitos}/{n} [{bajo:.0%}-{alto:.0%}]"


def tabla_intervalos(corridas: list[str], datos: dict) -> list[str]:
    lineas = ["| Corrida | Original | b | c | Total (150) |", "|---|---|---|---|---|"]
    for corrida in corridas:
        celdas, total, n_total = [], 0, 0
        for version in VERSIONES:
            res = datos[corrida, version]
            r = len(resueltos(res))
            total, n_total = total + r, n_total + len(res)
            celdas.append(_intervalo(r, len(res)))
        lineas.append(f"| {corrida} | {' | '.join(celdas)} | {_intervalo(total, n_total)} |")
    return lineas


def comparar(a: str, b: str, datos: dict) -> tuple[int, int, float]:
    """(casos que resuelve solo a, casos que resuelve solo b, p de McNemar) sobre los 150 casos."""
    solo_a = solo_b = 0
    for version in VERSIONES:
        ra, rb = datos[a, version], datos[b, version]
        if set(ra) != set(rb):
            raise ValueError(f"{a}-{version} y {b}-{version} no tienen los mismos casos")
        ok_a, ok_b = resueltos(ra), resueltos(rb)
        solo_a += len(ok_a - ok_b)
        solo_b += len(ok_b - ok_a)
    return solo_a, solo_b, mcnemar_exacto(solo_a, solo_b)


def tabla_comparaciones(corridas: list[str], datos: dict) -> list[str]:
    lineas = ["| De -> a | Solo resuelve la primera | Solo resuelve la segunda | p (McNemar exacto) |",
              "|---|---|---|---|"]
    for a, b in zip(corridas, corridas[1:]):
        solo_a, solo_b, p = comparar(a, b, datos)
        marca = " *" if p < 0.05 else ""
        lineas.append(f"| {a} -> {b} | {solo_a} | {solo_b} | {p:.3g}{marca} |")
    return lineas


def tabla_controles(corridas: list[str], datos: dict) -> list[str]:
    lineas = ["| Control | " + " | ".join(corridas) + " |", "|---" * (len(corridas) + 1) + "|"]
    for control in CONTROLES:
        celdas = []
        for corrida in corridas:
            filas = [f for v in VERSIONES for f in datos[corrida, v].values()]
            aciertos = sum(1 for f in filas if f["controles"].get(control))
            celdas.append(f"{aciertos / len(filas):.0%}")
        lineas.append(f"| `{control}` | " + " | ".join(celdas) + " |")
    return lineas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corridas", nargs="*", default=list(POR_DEFECTO),
                    help="prefijos de corrida en evaluacion/corridas, en el orden a comparar")
    a = ap.parse_args()
    datos = {(c, v): cargar(c, v) for c in a.corridas for v in VERSIONES}

    print("Casos resueltos, con intervalo de confianza del 95 % (Wilson):\n")
    print("\n".join(tabla_intervalos(a.corridas, datos)))
    print("\nCorridas consecutivas sobre los mismos 150 casos (* = p < 0,05):\n")
    print("\n".join(tabla_comparaciones(a.corridas, datos)))
    print("\nAciertos por control, juntando las tres versiones de normas:\n")
    print("\n".join(tabla_controles(a.corridas, datos)))


if __name__ == "__main__":
    main()
