"""Mide bge-m3 en CPU o Metal sin cambiar la entrega.

    python -m evaluacion.medir_buscador --dispositivo cpu --hilos 4

Los pesos deben estar descargados. Ver los comandos completos en INFORME.md.
"""

import argparse
import gc
import hashlib
import importlib.metadata
import json
import math
import platform
import statistics
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import torch

from admision.evaluar_rag import cargar_dataset, evaluar_buscador
from buscador import hibrido


def medir_consultas(recuperar, consultas, sincronizar=lambda: None):
    tiempos, salidas = [], []
    sincronizar()
    inicio = time.perf_counter()
    for consulta in consultas:
        desde = time.perf_counter()
        salidas.append(recuperar(consulta, 3))
        sincronizar()
        tiempos.append(time.perf_counter() - desde)
    total = time.perf_counter() - inicio
    ordenados = sorted(tiempos)
    return salidas, {
        "segundos": total,
        "media_ms": statistics.mean(tiempos) * 1000,
        "mediana_ms": statistics.median(tiempos) * 1000,
        "p95_ms": ordenados[math.ceil(0.95 * len(ordenados)) - 1] * 1000,
        "tiempos_segundos": tiempos,
    }


def firma(chunks):
    return [{"seccion": c.seccion, "texto_sha256": hashlib.sha256(c.texto.encode()).hexdigest()}
            for c in chunks]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dispositivo", choices=("cpu", "mps"), required=True)
    ap.add_argument("--hilos", type=int, default=4)
    a = ap.parse_args()
    if a.hilos < 1:
        ap.error("--hilos debe ser positivo")
    if a.dispositivo == "mps" and not torch.backends.mps.is_available():
        ap.error("Metal no está disponible; no se reemplaza por CPU")
    torch.set_num_threads(a.hilos)
    sincronizar = torch.mps.synchronize if a.dispositivo == "mps" else lambda: None
    raiz = Path(__file__).resolve().parents[1]
    kit = raiz.parent / "talksmith-ing/missions/TPFinal"
    normas = kit / "normas/original"
    ruta_dataset = kit / "rag/consultas_dev.jsonl"
    ruta_trazas = raiz / "evaluacion/corridas/entrega-original/trazas.jsonl"
    dataset = cargar_dataset(ruta_dataset)
    consultas = [d["consulta"] for d in dataset]
    reales = [s["argumentos"]["consulta"] for t in cargar_dataset(ruta_trazas)
              for s in t["log"] if s["herramienta"] == "buscar_normativa"]
    assert len(consultas) == len(set(consultas)) == 60
    assert len(reales) == 152 and len(set(reales)) == 14
    nombre, revision, _, _ = hibrido.MODELOS["bge-m3"]
    informe = {
        "codigo": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=raiz).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dataset_sha256": hashlib.sha256(ruta_dataset.read_bytes()).hexdigest(),
        "trazas_sha256": hashlib.sha256(ruta_trazas.read_bytes()).hexdigest(),
        "normas_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(normas.iterdir()) if p.is_file()},
        "chip": subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip(),
        "memoria_bytes": int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)),
        "plataforma": platform.platform(), "python": platform.python_version(),
        "versiones": {n: importlib.metadata.version(n) for n in
                      ("sentence-transformers", "transformers", "torch", "numpy", "PyYAML")},
        "modelo": nombre, "revision": revision, "dispositivo": a.dispositivo, "hilos": a.hilos,
        "limite": "Tres cargas del modelo en el mismo proceso con archivos locales en caché; "
                  "sin descarga, sin tiempo de importar bibliotecas y sin ejecutar el agente. "
                  "No es una comparación controlada con el M1 Max ni predice la A100.",
        "repeticiones": [],
    }
    for repeticion in range(3):
        hibrido._CARGADOS.clear()
        gc.collect()
        if a.dispositivo == "mps":
            torch.mps.empty_cache()
        desde = time.perf_counter()
        modelo = hibrido.SentenceTransformer(nombre, revision=revision, device=a.dispositivo)
        hibrido._CARGADOS[nombre, revision] = modelo
        sincronizar()
        carga = time.perf_counter() - desde
        desde = time.perf_counter()
        buscador = hibrido.BuscadorHibrido(normas, modelo="bge-m3", modo="denso", k_entorno=3)
        # Mantener el protocolo sin caché de las mediciones originales.
        buscador._recuperar = buscador._recuperar.__wrapped__
        sincronizar()
        indice = time.perf_counter() - desde
        assert len(buscador.chunks) == 81
        for consulta in consultas[:3]:
            buscador.recuperar(consulta, 3)
        sincronizar()
        salidas, latencias = medir_consultas(buscador.recuperar, consultas, sincronizar)
        resultados = [{"id": d["id"], "consulta": d["consulta"], "chunks": firma(s)}
                      for d, s in zip(dataset, salidas, strict=True)]
        por_consulta = dict(zip(consultas, salidas, strict=True))
        medicion = evaluar_buscador(SimpleNamespace(k_entorno=3, recuperar=lambda q, k: por_consulta[q][:k]), dataset)
        recuperar = lru_cache(maxsize=128)(buscador.recuperar)
        # Alternar el orden evita que una variante siempre se mida más tarde.
        if repeticion % 2:
            con_cache, t_con = medir_consultas(recuperar, reales, sincronizar)
            sin_cache, t_sin = medir_consultas(buscador.recuperar, reales, sincronizar)
        else:
            sin_cache, t_sin = medir_consultas(buscador.recuperar, reales, sincronizar)
            con_cache, t_con = medir_consultas(recuperar, reales, sincronizar)
        assert sin_cache == con_cache, "La caché modificó los resultados"
        assert recuperar.cache_info().misses == 14 and recuperar.cache_info().hits == 138
        if informe["repeticiones"]:
            assert resultados == informe["resultados_dev"], "El ranking varió entre repeticiones"
        informe["resultados_dev"] = resultados
        informe["resultados_reales"] = {q: firma(s) for q, s in zip(reales, sin_cache, strict=True)}
        informe["repeticiones"].append({
            "carga_modelo_s": carga, "indexacion_s": indice, "construccion_total_s": carga + indice,
            "dtype": str(next(modelo.parameters()).dtype), "dev": latencias, "metricas_dev": medicion,
            "reales_sin_cache": t_sin, "reales_con_cache": t_con, "cache_identica": True,
        })
        print(f"{a.dispositivo}/{a.hilos}, pasada {repeticion + 1}: "
              f"construcción {carga + indice:.2f} s; consulta {latencias['mediana_ms']:.2f} ms; "
              f"152 búsquedas {t_sin['segundos']:.2f} → {t_con['segundos']:.2f} s", flush=True)
        del recuperar, buscador, modelo
    r = informe["repeticiones"]
    informe["resumen"] = {
        "construccion_mediana_s": statistics.median(x["construccion_total_s"] for x in r),
        "carga_modelo_mediana_s": statistics.median(x["carga_modelo_s"] for x in r),
        "indexacion_mediana_s": statistics.median(x["indexacion_s"] for x in r),
        "consulta_media_ms": statistics.median(x["dev"]["media_ms"] for x in r),
        "consulta_mediana_ms": statistics.median(x["dev"]["mediana_ms"] for x in r),
        "consulta_p95_ms": statistics.median(x["dev"]["p95_ms"] for x in r),
        "reales_sin_cache_mediana_s": statistics.median(x["reales_sin_cache"]["segundos"] for x in r),
        "reales_con_cache_mediana_s": statistics.median(x["reales_con_cache"]["segundos"] for x in r),
        "metricas_dev": r[0]["metricas_dev"],
    }
    salida = raiz / f"evaluacion/corridas/buscador-m5-{a.dispositivo}-{a.hilos}.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resultado: {salida}", flush=True)


if __name__ == "__main__":
    main()
