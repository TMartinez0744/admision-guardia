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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", default="../talksmith-ing/missions/TPFinal")
    parser.add_argument("--clasificacion", default="historial_clasificado.csv")
    parser.add_argument("--salida", default="datos/conversaciones.jsonl")
    parser.add_argument("--tipos", default="correcta", help="separados por coma")
    args = parser.parse_args()

    tipos = {t.strip() for t in args.tipos.split(",")}
    kit = Path(args.kit)
    clasificacion = {f["id"]: f["tipo"] for f in csv.DictReader(Path(args.clasificacion).open(encoding="utf-8"))}
    trazas = [json.loads(x) for x in (kit / "historial" / "trazas.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    escritas, descartadas, mal_formadas = 0, 0, []
    with salida.open("w", encoding="utf-8", newline="\n") as f:
        for traza in trazas:
            if clasificacion.get(traza["id"]) not in tipos:
                descartadas += 1
                continue
            mensajes = conversacion(traza)
            if not bien_formada(mensajes):
                mal_formadas.append(traza["id"])
                continue
            f.write(json.dumps({"id": traza["id"], "paciente_id": traza["paciente_id"], "messages": mensajes},
                               ensure_ascii=False) + "\n")
            escritas += 1

    print(f"{escritas} conversaciones -> {salida}")
    print(f"  descartadas por tipo: {descartadas}")
    print(f"  mal formadas: {len(mal_formadas)}{' ' + str(mal_formadas[:5]) if mal_formadas else ''}")
    print(f"  tamaño: {salida.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
