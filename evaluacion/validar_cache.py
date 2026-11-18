"""Valida la caché de la entrega con las búsquedas guardadas de original, b y c.

    python -m evaluacion.validar_cache

No ejecuta el agente ni necesita sus pesos privados. Requiere bge-m3 descargado.
"""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path
from types import SimpleNamespace

import torch

from admision.evaluar_rag import cargar_dataset, evaluar_buscador
from admision.normas import cargar_parametros
from buscador.hibrido import MODELOS
from entrega import construir_buscador
from evaluacion.lectura import VERSIONES
from evaluacion.medir_buscador import firma, medir_consultas


def main():
    raiz = Path(__file__).resolve().parents[1]
    kit = raiz.parent / "talksmith-ing/missions/TPFinal"
    torch.set_num_threads(4)
    informe = {
        "codigo_base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=raiz, text=True).strip(),
        "fuentes_sha256": {p: hashlib.sha256((raiz / p).read_bytes()).hexdigest() for p in
                           ("buscador/hibrido.py", "entrega.py", "evaluacion/validar_cache.py", "evaluacion/medir_buscador.py")},
        "plataforma": platform.platform(), "hilos": torch.get_num_threads(),
        "modelo_hf": MODELOS["bge-m3"][:2],
        "versiones": {n: importlib.metadata.version(n) for n in
                      ("sentence-transformers", "transformers", "torch", "numpy", "PyYAML")},
        "limite": "Una reproducción por versión con las consultas guardadas; no ejecuta el agente. "
                  "Los tiempos excluyen carga e indexación y no son una medición de la A100.",
        "normas": {},
    }
    for i, version in enumerate(VERSIONES):
        ruta_normas = kit / "normas" / version
        buscador = construir_buscador(ruta_normas)
        ruta_trazas = raiz / f"evaluacion/corridas/entrega-{version}/trazas.jsonl"
        consultas = [s["argumentos"]["consulta"] for t in cargar_dataset(ruta_trazas)
                     for s in t["log"] if s["herramienta"] == "buscar_normativa"]

        def sin_cache(consulta, k):
            return list(buscador._recuperar.__wrapped__(consulta, k, buscador.modo))

        for q in consultas[:3]:
            sin_cache(q, 3)
        buscador._recuperar.cache_clear()
        if i % 2:
            con, t_con = medir_consultas(buscador.recuperar, consultas)
            sin, t_sin = medir_consultas(sin_cache, consultas)
        else:
            sin, t_sin = medir_consultas(sin_cache, consultas)
            con, t_con = medir_consultas(buscador.recuperar, consultas)
        info = buscador._recuperar.cache_info()
        assert sin == con, f"La caché alteró los resultados de {version}"
        assert info.misses == len(set(consultas))
        assert info.hits == len(consultas) - len(set(consultas))
        fila = {
            "dispositivo": str(buscador.modelo.device), "modelo": "bge-m3", "k": buscador.k_entorno,
            "trazas_sha256": hashlib.sha256(ruta_trazas.read_bytes()).hexdigest(),
            "normas_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(ruta_normas.iterdir()) if p.is_file()},
            "parametros": cargar_parametros(ruta_normas), "busquedas": len(consultas),
            "cache": info._asdict(), "resultados_identicos": True,
            "sin_cache": t_sin, "con_cache": t_con,
            "resultados": {q: firma(s) for q, s in zip(consultas, con, strict=True)},
        }
        if version == "original":
            ruta_dev = kit / "rag/consultas_dev.jsonl"
            dataset = cargar_dataset(ruta_dev)
            fila["dev_sha256"] = hashlib.sha256(ruta_dev.read_bytes()).hexdigest()
            fila["metricas_sin_cache"] = evaluar_buscador(
                SimpleNamespace(k_entorno=3, recuperar=sin_cache), dataset)
            fila["metricas_con_cache"] = evaluar_buscador(buscador, dataset)
            assert fila["metricas_sin_cache"] == fila["metricas_con_cache"]
        informe["normas"][version] = fila
        print(f"{version}: {len(consultas)} búsquedas, {info.misses} cálculos y {info.hits} reutilizaciones; "
              f"{t_sin['segundos']:.3f} → {t_con['segundos']:.3f} s; resultados idénticos", flush=True)
    salida = raiz / "evaluacion/corridas/cache-entrega.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resultado: {salida}", flush=True)


if __name__ == "__main__":
    main()
