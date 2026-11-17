"""Pasa las trazas aprovechables del historial a conversaciones de entrenamiento.

    uv run python -m curado.conversaciones --kit ../talksmith-ing/missions/TPFinal

Cada traza es una lista de pasos: la herramienta que usó el operador, con qué
argumentos y qué le devolvió el entorno. El modelo, en cambio, se entrena con
diálogos. El formato es el del agente de ejemplo del kit:

1. el mensaje de sistema;
2. un mensaje del usuario con el pedido inicial;
3. por cada paso, un mensaje del asistente con la llamada en JSON y, salvo
   después de ``registrar_decision``, uno del usuario con el resultado.

Entran solo las filas que ``historial_clasificado.csv`` marca como correctas:
las que tienen error enseñarían a violar una norma, y las que tienen ruido, a
apartarse de una costumbre.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from admision.ejemplo import mensaje_de_sistema, primer_mensaje

from curado.clasificar import KIT, RAIZ

FIN = "registrar_decision"


def conversacion(traza: dict) -> list[dict]:
    """Los mensajes de una traza, en orden."""
    mensajes = [
        {"role": "system", "content": mensaje_de_sistema()},
        {"role": "user", "content": primer_mensaje(traza["paciente_id"])},
    ]
    for paso in traza["pasos"]:
        herramienta = paso["herramienta"]
        llamada = {"herramienta": herramienta, "argumentos": paso["argumentos"]}
        mensajes.append({"role": "assistant", "content": json.dumps(llamada, ensure_ascii=False)})
        if herramienta != FIN:
            mensajes.append({"role": "user", "content": f"Resultado de {herramienta}:\n{paso['resultado']}"})
    return mensajes


def bien_formada(mensajes: list[dict]) -> bool:
    """El sistema primero, roles alternados y cierre del asistente."""
    if len(mensajes) < 4 or mensajes[0]["role"] != "system" or mensajes[1]["role"] != "user":
        return False
    if mensajes[-1]["role"] != "assistant" or FIN not in mensajes[-1]["content"]:
        return False
    esperado = "assistant"
    for mensaje in mensajes[2:]:
        if mensaje["role"] != esperado:
            return False
        esperado = "user" if esperado == "assistant" else "assistant"
    return True


def leer_clasificacion(ruta: Path) -> dict[str, str]:
    """{id de la fila: tipo}, de ``historial_clasificado.csv``."""
    with open(ruta, encoding="utf-8") as f:
        return {fila["id"]: fila["tipo"] for fila in csv.DictReader(f)}


def leer_trazas(kit: Path) -> list[dict]:
    texto = (kit / "historial" / "trazas.jsonl").read_text(encoding="utf-8")
    return [json.loads(x) for x in texto.splitlines() if x.strip()]


def seleccionar(trazas: list[dict], clasificacion: dict[str, str], tipos: set[str]) -> tuple[list[dict], int, list[str]]:
    """Las conversaciones de las trazas con un tipo de ``tipos``, las descartadas por tipo y los ids mal formados."""
    conversaciones, descartadas, mal_formadas = [], 0, []
    for traza in trazas:
        if clasificacion.get(traza["id"]) not in tipos:
            descartadas += 1
            continue
        mensajes = conversacion(traza)
        if not bien_formada(mensajes):
            mal_formadas.append(traza["id"])
            continue
        conversaciones.append({"id": traza["id"], "paciente_id": traza["paciente_id"], "messages": mensajes})
    return conversaciones, descartadas, mal_formadas


def guardar(conversaciones: list[dict], salida: Path) -> None:
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in conversaciones)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", default=str(KIT))
    parser.add_argument("--clasificacion", default=str(RAIZ / "historial_clasificado.csv"))
    parser.add_argument("--salida", default=str(RAIZ / "datos" / "conversaciones.jsonl"))
    parser.add_argument("--tipos", default="correcta", help="separados por coma")
    args = parser.parse_args()

    tipos = {t.strip() for t in args.tipos.split(",")}
    trazas = leer_trazas(Path(args.kit))
    conversaciones, descartadas, mal_formadas = seleccionar(trazas, leer_clasificacion(Path(args.clasificacion)), tipos)
    salida = Path(args.salida)
    guardar(conversaciones, salida)

    print(f"{len(conversaciones)} conversaciones -> {salida}")
    print(f"  descartadas por tipo: {descartadas}")
    print(f"  mal formadas: {len(mal_formadas)}{' ' + str(mal_formadas[:5]) if mal_formadas else ''}")
    print(f"  tamaño: {salida.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
