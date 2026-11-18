"""Mide reutilización exacta del buscador con las consultas de las trazas.

Mismo entorno y comando que diagnostico_rag, cambiando el módulo a
evaluacion.cache_rag. Es una medición local exploratoria, no de la A100.
"""

import json
import hashlib
import platform
import statistics
import time
from functools import lru_cache
from pathlib import Path

import torch

from admision.evaluar_rag import cargar_dataset
from buscador.hibrido import MODELOS, BuscadorHibrido


def reproducir(recuperar, consultas):
    inicio = time.perf_counter()
    salidas = [[(c.seccion, c.texto) for c in recuperar(q, 3)] for q in consultas]
    return salidas, time.perf_counter() - inicio


def main():
    raiz = Path(__file__).resolve().parents[1]
    kit = raiz.parent / "talksmith-ing" / "missions" / "TPFinal"
    torch.set_num_threads(4)
    buscador = BuscadorHibrido(kit / "normas" / "original", modelo="bge-m3", modo="denso", k_entorno=3)
    buscador._recuperar = buscador._recuperar.__wrapped__
    consultas = [s["argumentos"]["consulta"]
                 for t in cargar_dataset(raiz / "evaluacion/corridas/entrega-original/trazas.jsonl")
                 for s in t["log"] if s["herramienta"] == "buscar_normativa"]
    assert len(consultas) == 152 and len(set(consultas)) == 14
    # Calentar el modelo en ambos casos; el cronómetro excluye carga y descarga.
    buscador.recuperar(consultas[0], 3)
    recuperar = lru_cache(maxsize=128)(buscador.recuperar)
    mediciones = []
    for _ in range(3):
        sin_cache, segundos_sin = reproducir(buscador.recuperar, consultas)
        recuperar.cache_clear()
        con_cache, segundos_con = reproducir(recuperar, consultas)
        assert sin_cache == con_cache, "La optimización cambió los resultados recuperados"
        mediciones.append({"sin_cache": segundos_sin, "con_cache": segundos_con})
    assert recuperar.cache_info().misses == 14 and recuperar.cache_info().hits == 138
    segundos_sin = statistics.median(m["sin_cache"] for m in mediciones)
    segundos_con = statistics.median(m["con_cache"] for m in mediciones)
    informe = {"version_normas": "original", "consultas": len(consultas), "consultas_distintas": 14,
               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "modelo": MODELOS["bge-m3"][:2], "torch": torch.__version__,
               "trazas_sha256": hashlib.sha256((raiz / "evaluacion/corridas/entrega-original/trazas.jsonl").read_bytes()).hexdigest(),
               "plataforma": platform.platform(), "dispositivo": str(buscador.modelo.device),
               "hilos": torch.get_num_threads(), "salidas_identicas": True,
               "segundos_sin_cache": round(segundos_sin, 3), "segundos_con_cache": round(segundos_con, 3),
               "aceleracion_buscador": round(segundos_sin / segundos_con, 2),
               "repeticiones": mediciones, "estadistico": "mediana de 3 pasadas con caché vacía en cada pasada",
               "limite": "Consultas grabadas; no mide el agente ni predice tiempos de A100. "
                         "La caché solo vale para la misma instancia con las mismas normas, modelo y configuración."}
    salida = raiz / "evaluacion/corridas/cache-rag.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(informe, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
