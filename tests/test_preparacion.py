"""``entrenamiento.preparacion``: la máscara del asistente y la huella del archivo de datos.

Con un tokenizador de juguete de un token por carácter: así se puede leer qué texto quedó marcado.
"""

import hashlib

import pytest

from entrenamiento.preparacion import mascara, sha256, tokenizar, tramos_del_asistente


class Tokenizador:
    """Plantilla ``<rol>contenido<fin>`` y un token por carácter, más un token vacío al principio (como BOS)."""

    def apply_chat_template(self, mensajes, tokenize=False, add_generation_prompt=False):
        texto = "".join(f"<{m['role']}>{m['content']}<fin>" for m in mensajes)
        return texto + ("<assistant>" if add_generation_prompt else "")

    def __call__(self, texto, add_special_tokens=False, return_offsets_mapping=False):
        return {"input_ids": [0] + [ord(c) for c in texto], "offset_mapping": [(0, 0)] + [(i, i + 1) for i in range(len(texto))]}


class SinPrefijos(Tokenizador):
    """Una plantilla que borra las respuestas viejas del asistente (como las que sacan el razonamiento)."""

    def apply_chat_template(self, mensajes, tokenize=False, add_generation_prompt=False):
        ultimo = max((i for i, m in enumerate(mensajes) if m["role"] == "assistant"), default=-1)
        visibles = [m if m["role"] != "assistant" or i == ultimo else {**m, "content": ""}
                    for i, m in enumerate(mensajes)]
        return super().apply_chat_template(visibles, tokenize, add_generation_prompt)


CONVERSACION = [
    {"role": "system", "content": "sos un operador"},
    {"role": "user", "content": "ingresó P-1234"},
    {"role": "assistant", "content": '{"herramienta": "leer_triage"}'},
    {"role": "user", "content": "Resultado: nivel 2"},
    {"role": "assistant", "content": '{"herramienta": "registrar_decision"}'},
]


def marcado(conversacion, tokenizador=Tokenizador()):
    salida = tokenizar(conversacion, tokenizador)
    texto = tokenizador.apply_chat_template(conversacion)
    # El primer token es el vacío: los demás son un carácter cada uno.
    return "".join(texto[i - 1] for i, m in enumerate(salida["assistant_masks"]) if m), salida


def test_se_marcan_solo_las_respuestas_del_asistente_y_su_cierre():
    texto, salida = marcado(CONVERSACION)
    assert texto == '{"herramienta": "leer_triage"}<fin>{"herramienta": "registrar_decision"}<fin>'
    assert len(salida["assistant_masks"]) == len(salida["input_ids"])


def test_el_comienzo_del_turno_del_modelo_no_se_marca():
    texto, _ = marcado(CONVERSACION)
    assert "<assistant>" not in texto
    assert "operador" not in texto and "nivel 2" not in texto


def test_sin_respuestas_del_asistente_la_mascara_es_toda_cero():
    _, salida = marcado(CONVERSACION[:2])
    assert set(salida["assistant_masks"]) == {0}


def test_una_plantilla_que_no_conserva_los_prefijos_se_rechaza():
    with pytest.raises(ValueError, match="prefijos"):
        tokenizar(CONVERSACION, SinPrefijos())


def test_los_tramos_caen_sobre_el_texto_de_cada_respuesta():
    completo, tramos = tramos_del_asistente(CONVERSACION, Tokenizador())
    assert [completo[a:b] for a, b in tramos] == [m["content"] + "<fin>" for m in CONVERSACION if m["role"] == "assistant"]


@pytest.mark.parametrize("desplazamiento, esperado", [
    ((10, 12), 1),  # entero adentro
    ((10, 20), 1),  # justo el tramo
    ((8, 12), 0),   # empieza antes
    ((18, 22), 0),  # termina después
    ((15, 15), 0),  # token vacío
    ((30, 31), 0),  # afuera
])
def test_mascara_por_token(desplazamiento, esperado):
    assert mascara([desplazamiento], [(10, 20)]) == [esperado]


def test_sha256_coincide_con_hashlib_en_un_archivo_de_varios_bloques(tmp_path):
    ruta = tmp_path / "datos.jsonl"
    contenido = b"x" * ((1 << 20) * 2 + 123)
    ruta.write_bytes(contenido)
    assert sha256(ruta) == hashlib.sha256(contenido).hexdigest()
