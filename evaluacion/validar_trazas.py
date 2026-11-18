"""Comprueba que el buscador actual de la entrega, con caché, le devuelve al modelo
exactamente lo mismo que vio en las corridas finales guardadas.

    python -m evaluacion.validar_trazas

Mismo entorno que ``evaluacion.validar_cache`` (README, sección 3). No necesita
el modelo del agente: con decodificación greedy, si cada observación de
``buscar_normativa`` es idéntica, la entrada del modelo en cada paso también lo
es, y las corridas ``entrega-*`` valen para el código actual.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import torch

from admision.entorno import _texto
from admision.evaluar_rag import cargar_dataset
from entrega import construir_buscador
from evaluacion.lectura import VERSIONES


def observacion(buscador, consulta):
    """Lo mismo que arma ``admision.entorno`` para ``buscar_normativa``."""
    frs = buscador.recuperar(consulta.strip(), buscador.k_entorno)
    return "\n\n".join(_texto(f) for f in frs) if frs else "No se encontró ninguna sección."


def main():
    raiz = Path(__file__).resolve().parents[1]
    kit = raiz.parent / "talksmith-ing/missions/TPFinal"
    torch.set_num_threads(4)
    informe = {
        "codigo": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=raiz, text=True).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limite": "Compara las observaciones de buscar_normativa; no ejecuta el agente ni mide tiempos.",
        "normas": {},
    }
    for version in VERSIONES:
        buscador = construir_buscador(kit / "normas" / version)
        ruta = raiz / f"evaluacion/corridas/entrega-{version}/trazas.jsonl"
        busquedas = 0
        for traza in cargar_dataset(ruta):
            mensajes = [str(m.get("content")) for m in traza["mensajes"]]
            for paso in traza["log"]:
                if paso["herramienta"] != "buscar_normativa":
                    continue
                busquedas += 1
                grabada = paso["observacion"]
                actual = observacion(buscador, paso["argumentos"]["consulta"])
                assert actual == grabada, f"{version} {traza['caso']}: cambió la observación"
                assert any(grabada in m for m in mensajes), f"{version} {traza['caso']}: no está en los mensajes"
        info = buscador._recuperar.cache_info()
        informe["normas"][version] = {"trazas_sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
                                      "busquedas": busquedas, "consultas_distintas": info.misses,
                                      "cache": info._asdict(), "observaciones_identicas": True}
        print(f"{version}: {busquedas} observaciones idénticas ({info.misses} consultas distintas)", flush=True)
    salida = raiz / "evaluacion/corridas/trazas-entrega.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resultado: {salida}", flush=True)


if __name__ == "__main__":
    main()
