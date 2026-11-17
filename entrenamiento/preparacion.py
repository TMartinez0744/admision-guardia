"""Lo que ``entrenamiento.sft`` hace con los datos antes de entrenar, sin torch ni GPU.

Está aparte para poder probarlo en cualquier máquina (ver ``tests/test_preparacion.py``).
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def tramos_del_asistente(mensajes: list[dict], tokenizador) -> tuple[str, list[tuple[int, int]]]:
    """La conversación renderizada y, por cada mensaje del asistente, su tramo ``[inicio, fin)`` en ese texto.

    El tramo de una respuesta es lo que agrega la plantilla al pasar de la conversación hasta el turno
    anterior (con el comienzo del turno del modelo) a la conversación con esa respuesta y su cierre.
    """
    completo = tokenizador.apply_chat_template(mensajes, tokenize=False)
    tramos = []
    for i, mensaje in enumerate(mensajes):
        if mensaje["role"] != "assistant":
            continue
        antes = tokenizador.apply_chat_template(mensajes[:i], tokenize=False, add_generation_prompt=True)
        hasta = tokenizador.apply_chat_template(mensajes[:i + 1], tokenize=False)
        if not (completo.startswith(hasta) and hasta.startswith(antes)):
            raise ValueError("la plantilla de chat no conserva los prefijos")
        tramos.append((len(antes), len(hasta)))
    return completo, tramos


def mascara(desplazamientos: list[tuple[int, int]], tramos: list[tuple[int, int]]) -> list[int]:
    """1 en cada token que cae entero dentro de algún tramo; 0 en el resto y en los tokens vacíos."""
    return [int(any(ini <= a and b <= fin for ini, fin in tramos)) if b > a else 0 for a, b in desplazamientos]


def tokenizar(mensajes: list[dict], tokenizador) -> dict:
    """``input_ids`` y ``assistant_masks``: 1 en los tokens de cada mensaje del asistente y su cierre de turno.

    La plantilla de chat de esta revisión de Gemma 4 no trae marcas ``{% generation %}`` y TRL no sabe
    adaptarla, así que la máscara se arma acá. La plantilla conserva los prefijos: el texto de cada
    respuesta del asistente es lo que agrega a la conversación renderizada hasta el turno anterior.
    """
    completo, tramos = tramos_del_asistente(mensajes, tokenizador)
    codificado = tokenizador(completo, add_special_tokens=False, return_offsets_mapping=True)
    return {"input_ids": codificado["input_ids"], "assistant_masks": mascara(codificado["offset_mapping"], tramos)}


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()
