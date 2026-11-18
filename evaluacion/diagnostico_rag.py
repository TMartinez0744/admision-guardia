"""Experimento de RAG; no cambia el buscador de la entrega.

PYTHONPATH=../talksmith-ing/missions/TPFinal:. uv run --no-project --python 3.12 \
    --with sentence-transformers==6.2.0 --with pyyaml python -m evaluacion.diagnostico_rag
"""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import time
from collections import Counter
from pathlib import Path

import torch

from admision.evaluar_rag import cargar_dataset, evaluar_buscador, evaluar_recuperador
from admision.normas import cargar_normas
from buscador.bm25 import BuscadorBM25, partir
from buscador.hibrido import MODELOS, BuscadorHibrido


def auditar_trazas(raiz):
    consultas = Counter()
    fallos = []
    for version in ("original", "b", "c"):
        carpeta = raiz / "evaluacion" / "corridas" / f"entrega-{version}"
        resultados = {r["caso"]: r for r in cargar_dataset(carpeta / "resultados.jsonl")}
        for traza in cargar_dataset(carpeta / "trazas.jsonl"):
            busquedas = [s for s in traza["log"] if s["herramienta"] == "buscar_normativa"]
            consultas.update(s["argumentos"]["consulta"] for s in busquedas)
            resultado = resultados[traza["caso"]]
            if not resultado["resuelto"]:
                evidencia = "\n".join(s["observacion"] for s in busquedas)
                fallos.append({"version": version, "caso": traza["caso"],
                               "controles_fallidos": [k for k, v in resultado["controles"].items() if not v],
                               "contiene_regla_edad": "Todo paciente cuya edad es igual o mayor" in evidencia,
                               "contiene_valor_edad": "P-ADM-2 = 67 años" in evidencia})
    return {"busquedas": sum(consultas.values()), "consultas_distintas": len(consultas),
            "frecuencias": dict(consultas.most_common()), "fallos": fallos}


class SeccionesPorParrafos:
    """Ordena secciones por su mejor párrafo y devuelve la sección completa."""

    k_entorno = 2

    def __init__(self, buscador, ruta_normas):
        self.buscador = buscador
        self.secciones = {s.id: s for s in cargar_normas(ruta_normas)}

    def recuperar(self, consulta, k):
        elegidas = []
        vistas = set()
        for chunk in self.buscador.recuperar(consulta, len(self.buscador.chunks)):
            if chunk.seccion not in vistas:
                elegidas.append(self.secciones[chunk.seccion])
                vistas.add(chunk.seccion)
                if len(elegidas) == k:
                    break
        return elegidas


def main():
    raiz = Path(__file__).resolve().parents[1]
    kit = raiz.parent / "talksmith-ing" / "missions" / "TPFinal"
    ruta_dataset = kit / "rag" / "consultas_dev.jsonl"
    dataset = cargar_dataset(ruta_dataset)
    normas = kit / "normas" / "original"
    adicionales = cargar_dataset_adicional(raiz / "evaluacion/consultas_rag_adicionales.json", normas)
    auditoria = auditar_trazas(raiz)
    # Controles del experimento, no supuestos sobre una mejora de calidad.
    assert len(dataset) == 60 and auditoria["busquedas"] == 496
    assert len(auditoria["fallos"]) == 1
    torch.set_num_threads(4)
    inicio = time.perf_counter()
    informe = {
        "codigo": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=raiz, text=True).strip(),
        "plataforma": platform.platform(), "torch": torch.__version__, "hilos": torch.get_num_threads(),
        "dispositivo": "cuda" if torch.cuda.is_available() else "cpu",
        "dataset_sha256": hashlib.sha256(ruta_dataset.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "adicionales_sha256": hashlib.sha256((raiz / "evaluacion/consultas_rag_adicionales.json").read_bytes()).hexdigest(),
        "versiones": {n: importlib.metadata.version(n) for n in
                      ("sentence-transformers", "transformers", "torch", "numpy", "PyYAML")},
        "modelo": MODELOS["bge-m3"][:2],
        "advertencia": "Exploración sobre desarrollo; no es test independiente ni evaluación del agente.",
        "auditoria_trazas": auditoria, "variantes": {},
        "consultas_adicionales": {"origen": "16 consultas manuales de exploración; no son un test ciego.",
                                  "variantes": {}},
    }

    def medir(nombre, buscador):
        informe["variantes"][nombre] = {
            "entorno": evaluar_buscador(buscador, dataset),
            "presupuesto_512": evaluar_recuperador(buscador.recuperar, dataset, 512),
        }
        informe["consultas_adicionales"]["variantes"][nombre] = {
            "entorno": evaluar_buscador(buscador, adicionales),
            "presupuesto_512": evaluar_recuperador(buscador.recuperar, adicionales, 512),
        }
        print(json.dumps({nombre: informe["variantes"][nombre]}, ensure_ascii=False), flush=True)

    medir("bm25_parrafos_k2", BuscadorBM25(normas))
    denso = BuscadorHibrido(normas, modelo="bge-m3", modo="denso", k_entorno=3)
    # Cachear el ranking mantiene iguales las consultas entre variantes y evita
    # medir repetidamente el mismo embedding; esto no es un benchmark de latencia.
    rankings = {q: denso.recuperar(q, len(denso.chunks))
                for q in {r["consulta"] for r in dataset + adicionales} | set(auditoria["frecuencias"])}
    denso.recuperar = lambda consulta, k: rankings[consulta][:k]
    for k in (2, 3, 4):
        denso.k_entorno = k
        medir(f"bge_parrafos_k{k}", denso)
    secciones = SeccionesPorParrafos(denso, normas)
    assert len({s.id for s in secciones.recuperar(dataset[0]["consulta"], 2)}) == 2
    medir("bge_secciones_por_mejor_parrafo_k2", secciones)
    consulta_box = "registro del paciente y ubicación en el box"
    informe["ranking_box"] = [{"posicion": i + 1, "seccion": c.seccion, "texto": c.texto}
                              for i, c in enumerate(rankings[consulta_box][:6])]
    informe["segundos_experimento"] = round(time.perf_counter() - inicio, 2)
    salida = raiz / "evaluacion" / "corridas" / "diagnostico-rag.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resultado: {salida}", flush=True)


def cargar_dataset_adicional(ruta, normas):
    """La evidencia se toma de las normas recibidas, sin fijar sus números."""
    parrafos = {}
    for chunk in partir(normas):
        cuerpo = chunk.texto.split("\n\n")[1]
        if cuerpo.startswith("§"):
            numero, texto = cuerpo.split(". ", 1)
            parrafos[(chunk.seccion, int(numero[1:]))] = texto
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert len({d["id"] for d in datos}) == len(datos) == 16
    return [{"id": d["id"], "tipo": d["tipo"], "consulta": d["consulta"],
             "evidencia": [{"seccion": seccion, "texto": parrafos[(seccion, numero)]}
                           for seccion, numero in d["parrafos"]]} for d in datos]


if __name__ == "__main__":
    main()
