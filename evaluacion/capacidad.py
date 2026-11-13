"""Parte 5: cuántos casos a la vez procesa el agente y cuánto tarda cada uno.

Arma el buscador y el agente de ``entrega.py`` una sola vez y juega lotes de
casos generados (``admision.generador``, semilla 1, distintos de los de la
optimización de prompt) de tamaño creciente con las normas originales. Por
lote mide el tiempo de ``jugar_lote``, los casos por segundo y los casos
resueltos según ``curado.etiquetar``.

vLLM reparte la memoria de la GPU entre los pesos y la caché de atención, y
agrupa en cada paso las conversaciones activas: mientras entren en la caché,
procesar más casos a la vez sube el rendimiento casi gratis.

    uv run modal run modal_app.py --comando "python -m evaluacion.capacidad --kit ../talksmith-ing/missions/TPFinal \
        --salida /cache/corridas/capacidad"
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from admision.comparar import comparar
from admision.entorno import Entorno, VistaDelAgente
from admision.generador import generar

import entrega
from curado.etiquetar import esperada
from curado.reglas import cargar_parametros


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--lotes", type=int, nargs="+", default=[25, 50, 100, 200, 400])
    a = ap.parse_args()

    normas = a.kit / "normas" / "original"
    parametros = cargar_parametros(normas)
    casos = generar(semilla=1, n=max(a.lotes), prefijo="cap")
    buscador = entrega.construir_buscador(normas)
    inicio = time.perf_counter()
    agente = entrega.construir_agente()
    carga = time.perf_counter() - inicio

    filas = []
    for n in a.lotes:
        entornos = [Entorno(c, buscador) for c in casos[:n]]
        inicio = time.perf_counter()
        agente.jugar_lote([VistaDelAgente(e.paciente_id, e.paso) for e in entornos])
        segundos = time.perf_counter() - inicio
        resueltos = sum(comparar(esperada(c, parametros), e.decision, e.log)["resuelto"]
                        for c, e in zip(casos[:n], entornos, strict=True))
        filas.append({"casos": n, "segundos": round(segundos, 1), "segundos_por_caso": round(segundos / n, 3),
                      "casos_por_segundo": round(n / segundos, 2), "resueltos": resueltos})
        print(json.dumps(filas[-1]), flush=True)

    a.salida.mkdir(parents=True, exist_ok=True)
    resumen = {"modelo": entrega.MODELO_HF, "revision": entrega.REVISION_HF, "prompt": str(entrega.RUTA_PROMPT),
               "segundos_carga_agente": round(carga, 1), "lotes": filas}
    (a.salida / "capacidad.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
