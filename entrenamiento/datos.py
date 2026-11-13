"""Parte 4: arma el archivo exacto de conversaciones de entrenamiento.

Dos fuentes, en el formato del agente de ejemplo de la cátedra (sistema, pedido
inicial, y por cada paso la llamada en JSON del asistente y el resultado como
mensaje del usuario):

1. **reales**: las trazas del historial que ``historial_clasificado.csv`` marca
   como correctas. Las búsquedas se vuelven a correr con nuestro buscador sobre
   las normas originales (las del historial): el modelo se entrena con lo que va
   a ver al usarse, 3 párrafos de bge-m3, y no con las 2 secciones del BM25 de la
   cátedra que quedaron en la traza.
2. **sintéticas**: casos de ``admision.generador`` jugados en el entorno de la
   cátedra por un operador experto programado, con normas de números al azar
   (``parametros.yaml`` sorteado). El operador usa las mismas consultas que los
   operadores del historial y registra la ficha de ``curado.etiquetar``. Así el
   modelo ve muchos valores distintos y tiene que leerlos del buscador en lugar
   de memorizarlos. Solo entran los episodios que el comparador del kit da por
   resueltos (9 controles).

    uv run python -m entrenamiento.datos --kit <kit> --sistema prompt/sistema_optimizado.txt \
        --sinteticas 1600 --semilla 0 --salida datos/entrenamiento.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
import tempfile
from pathlib import Path

import yaml
from admision.comparar import comparar
from admision.ejemplo import primer_mensaje
from admision.entorno import Entorno
from admision.generador import generar

import entrega
from curado.etiquetar import _a_verificar, esperada
from curado.reglas import cargar_parametros

# Rangos de los parámetros que deciden la ficha. El resto queda como en las normas originales.
RANGOS = {
    "P-ADM-1": (1, 3), "P-ADM-2": (60, 80), "P-ADM-3": (1, 3), "P-COB-2": (0, 9),
    "P-TDE-1": (5, 30), "P-TDE-2": (5, 30), "P-TDE-3": (10, 45), "P-TDE-4": (30, 120), "P-TDE-5": (2, 8),
}
SECCION = re.compile(r"^## (NOR-[A-Z]+-\d+)", re.MULTILINE)


def _mensajes(sistema: str, paciente_id: str, pasos: list[tuple[str, dict, str]]) -> list[dict]:
    mensajes = [{"role": "system", "content": sistema}, {"role": "user", "content": primer_mensaje(paciente_id)}]
    for herramienta, argumentos, resultado in pasos:
        llamada = {"herramienta": herramienta, "argumentos": argumentos}
        mensajes.append({"role": "assistant", "content": json.dumps(llamada, ensure_ascii=False)})
        if herramienta != "registrar_decision":
            mensajes.append({"role": "user", "content": f"Resultado de {herramienta}:\n{resultado}"})
    return mensajes


def _busqueda(buscador, consulta: str) -> str:
    """Lo mismo que devuelve buscar_normativa en el entorno de la cátedra."""
    textos = [getattr(f, "texto", f) for f in buscador.recuperar(consulta, buscador.k_entorno)]
    return "\n\n".join(textos) if textos else "No se encontró ninguna sección."


def reales(kit: Path, sistema: str, buscador) -> list[dict]:
    tipos = {f["id"]: f["tipo"] for f in csv.DictReader(open("historial_clasificado.csv", encoding="utf-8"))}
    conversaciones = []
    for linea in open(kit / "historial" / "trazas.jsonl", encoding="utf-8"):
        traza = json.loads(linea)
        if tipos[traza["id"]] != "correcta":
            continue
        pasos = [(p["herramienta"], p["argumentos"],
                  _busqueda(buscador, p["argumentos"]["consulta"]) if p["herramienta"] == "buscar_normativa"
                  else p["resultado"]) for p in traza["pasos"]]
        conversaciones.append({"id": traza["id"], "fuente": "real",
                               "messages": _mensajes(sistema, traza["paciente_id"], pasos)})
    return conversaciones


def normas_al_azar(original: Path, destino: Path, r: random.Random) -> None:
    shutil.copytree(original, destino)
    datos = yaml.safe_load((destino / "parametros.yaml").read_text(encoding="utf-8"))
    for p in datos["parametros"]:
        if p["codigo"] in RANGOS:
            p["valor"] = r.randint(*RANGOS[p["codigo"]])
    (destino / "parametros.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False),
                                             encoding="utf-8")


def operador(entorno: Entorno, caso, ficha: dict) -> None:
    """Un operador experto: las consultas de los operadores del historial y la ficha que corresponde."""
    pid = caso.paciente_id
    secciones: list[str] = []

    def paso(herramienta, argumentos):
        obs, _ = entorno.paso(herramienta, argumentos)
        if herramienta == "buscar_normativa":
            secciones.extend(s for s in SECCION.findall(obs) if s not in secciones)

    paso("leer_triage", {"paciente_id": pid})
    paso("buscar_normativa", {"consulta": "registro del paciente y ubicación en el box"})
    if caso.documento_tipo in ("pasaporte", "cédula"):
        paso("buscar_normativa", {"consulta": "registro con pasaporte o cédula"})
    motivo = {"dolor torácico": "dolor torácico plazo",
              "signos neurológicos focales de inicio súbito": "signos neurológicos focales de inicio súbito plazo"}
    if caso.sepsis != "no":
        paso("buscar_normativa", {"consulta": "código sepsis plazo"})
    elif caso.motivo in motivo:
        paso("buscar_normativa", {"consulta": motivo[caso.motivo]})
    if ficha["circuito"] != "ninguno" and caso.llegada == "en ambulancia":
        paso("buscar_normativa", {"consulta": "ingreso en ambulancia plazo del circuito"})

    quien = "paciente" if caso.puede_responder else ("acompanante" if caso.acompanante else None)
    if caso.trabajo:
        paso("buscar_normativa", {"consulta": "accidente de trabajo ART"})
        paso("preguntar", {"paciente_id": pid, "a_quien": quien, "tema": "art"})
        paso("verificar_afiliacion", {"entidad": caso.art[0], "numero_afiliado": caso.art[1]})
    else:
        if not caso.credenciales:
            paso("buscar_normativa", {"consulta": "consulta de la cobertura sin credencial"})
            if quien:
                paso("preguntar", {"paciente_id": pid, "a_quien": quien, "tema": "cobertura"})
        credencial = _a_verificar(caso)
        if credencial:
            paso("buscar_normativa", {"consulta": "número de afiliado con terminación reservada"})
            paso("verificar_afiliacion", {"entidad": credencial[1], "numero_afiliado": credencial[2]})
    paso("registrar_decision", {**ficha, "fundamentos": secciones})


def sinteticas(kit: Path, sistema: str, n: int, semilla: int) -> tuple[list[dict], int]:
    r = random.Random(semilla)
    casos = generar(semilla=semilla, n=n, prefijo="sft")
    conversaciones, descartadas = [], 0
    with tempfile.TemporaryDirectory() as carpeta:
        # Una versión de normas cada 50 casos: armar el buscador cuesta unos segundos.
        for inicio in range(0, n, 50):
            normas = Path(carpeta) / f"v{inicio}"
            normas_al_azar(kit / "normas" / "original", normas, r)
            buscador, parametros = entrega.construir_buscador(normas), cargar_parametros(normas)
            for caso in casos[inicio:inicio + 50]:
                objetivo = esperada(caso, parametros)
                entorno = Entorno(caso, buscador)
                operador(entorno, caso, objetivo["ficha"])
                if not comparar(objetivo, entorno.decision, entorno.log)["resuelto"]:
                    descartadas += 1
                    continue
                pasos = [(x["herramienta"], x["argumentos"], x["observacion"]) for x in entorno.log]
                conversaciones.append({"id": caso.id, "fuente": "sintetica", "normas": dict(parametros),
                                       "messages": _mensajes(sistema, caso.paciente_id, pasos)})
    return conversaciones, descartadas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--sistema", type=Path, required=True, help="archivo con el mensaje de sistema")
    ap.add_argument("--sinteticas", type=int, default=0)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    sistema = a.sistema.read_text(encoding="utf-8").strip()
    datos = reales(a.kit, sistema, entrega.construir_buscador(a.kit / "normas" / "original"))
    descartadas = 0
    if a.sinteticas:
        extra, descartadas = sinteticas(a.kit, sistema, a.sinteticas, a.semilla)
        datos += extra
    random.Random(a.semilla).shuffle(datos)
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    with open(a.salida, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in datos)
    reales_n = sum(x["fuente"] == "real" for x in datos)
    print(json.dumps({"reales": reales_n, "sinteticas": len(datos) - reales_n,
                      "sinteticas_descartadas": descartadas, "salida": str(a.salida)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
