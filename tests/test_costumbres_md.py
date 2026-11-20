"""``costumbres.md`` contra el historial real: los números y las filas de ejemplo que cita.

Usan el historial del kit (``ADMISION_KIT`` o junto al repo) y se saltean si no está.
"""

import os
import re
from pathlib import Path

import pytest

from curado.clasificar import SI, leer_historial
from curado.costumbres import EDAD_VOLUNTARIADO, aviso_al_voluntariado, entidad_a_verificar
from curado.evidencia import evidencia_prepaga, evidencia_voluntariado
from curado.reglas import texto_de

COSTUMBRES = Path(__file__).resolve().parents[1] / "costumbres.md"


def _kit():
    candidatos = [os.environ.get("ADMISION_KIT"), Path(__file__).resolve().parents[2] / "talksmith-ing" / "missions" / "TPFinal"]
    for candidato in filter(None, candidatos):
        if (Path(candidato) / "historial" / "historial.csv").exists():
            return Path(candidato)
    return None


KIT = _kit()
pytestmark = pytest.mark.skipif(KIT is None, reason="falta el kit (ADMISION_KIT)")


@pytest.fixture(scope="module")
def filas():
    return leer_historial(KIT)


@pytest.fixture(scope="module")
def por_id(filas):
    return {fila["id"]: fila for fila in filas}


@pytest.fixture(scope="module")
def texto():
    """``costumbres.md`` con los espacios y saltos de línea colapsados, para buscar frases enteras."""
    return " ".join(COSTUMBRES.read_text(encoding="utf-8").split())


def ids_de(texto: str, encabezado: str) -> list[str]:
    """Las filas que cita la viñeta que empieza con ``encabezado``."""
    m = re.search(rf"- {re.escape(encabezado)}:(.*?)(?= - |$| ## )", texto)
    assert m, f"no está la viñeta «{encabezado}» en costumbres.md"
    return re.findall(r"H-\d{4}", m.group(1))


# --- Los números ----------------------------------------------------------------------------------

def test_los_numeros_de_la_costumbre_1_coinciden_con_el_historial(filas, texto):
    v = evidencia_voluntariado(filas)
    desvios = v["desvios_por_operador"]
    assert f"{len(v['cumplen'])} de los {v['operadores']} operadores" in texto
    assert f"**0 desviaciones en {v['filas_de_los_que_cumplen']} filas**" in texto
    assert f"Las {sum(desvios.values())} filas que se apartan" in texto
    assert ", ".join(f"{op} ({n})" for op, n in list(desvios.items())[:-1]) + \
        f" y {list(desvios)[-1]} ({list(desvios.values())[-1]})" in texto
    for (desde, hasta), (n, con_aviso) in v["franjas"].items():
        assert f"| {desde} a {hasta} | {n} | {con_aviso} |" in texto


def test_los_numeros_de_la_costumbre_2_coinciden_con_el_historial(filas, texto):
    p = evidencia_prepaga(filas)
    porcentaje = f"{p['cumplen'] / p['con_dos_credenciales']:.1%}".replace(".", ",")
    assert f"De las {p['con_dos_credenciales']} filas con dos credenciales, en **{p['cumplen']} ({porcentaje})**" in texto
    assert f"primera en {p['prepaga_primera']} casos y segunda en {p['prepaga_segunda']}" in texto
    assert ids_de(texto, "Se apartan, las nueve") == p["se_apartan"]


# --- Las filas de ejemplo -------------------------------------------------------------------------

def test_los_ejemplos_que_avisan_cumplen_la_costumbre_1(por_id, texto):
    for id_ in ids_de(texto, "La cumplen avisando"):
        fila = por_id[id_]
        assert fila["aviso_al_voluntariado"] == SI and aviso_al_voluntariado(fila), id_


def test_los_ejemplos_de_73_o_74_anios_no_avisan(por_id, texto):
    for id_ in ids_de(texto, "La cumplen no avisando, por tener 73 o 74 años"):
        fila = por_id[id_]
        assert int(fila["edad"]) in (73, 74) and not texto_de(fila, "acompanante"), id_
        assert fila["aviso_al_voluntariado"] != SI, id_


def test_los_ejemplos_acompaniados_de_75_o_mas_no_avisan(por_id, texto):
    for id_ in ids_de(texto, "La cumplen no avisando, por tener acompañante pese a superar los 75"):
        fila = por_id[id_]
        assert int(fila["edad"]) >= EDAD_VOLUNTARIADO and texto_de(fila, "acompanante"), id_
        assert fila["aviso_al_voluntariado"] != SI, id_


def test_los_ejemplos_que_se_apartan_de_la_costumbre_1_son_del_operador_y_la_edad_que_dice(por_id, texto):
    citados = re.findall(r"`(H-\d{4})` \((OP-\d+), (\d+)(?: años)?\)", texto)
    assert citados, "no hay ejemplos de filas que se aparten de la costumbre 1"
    for id_, operador, edad in citados:
        fila = por_id[id_]
        assert (fila["operador"], fila["edad"]) == (operador, edad), id_
        assert (fila["aviso_al_voluntariado"] == SI) != aviso_al_voluntariado(fila), id_


def test_los_ejemplos_que_cumplen_la_costumbre_2_verifican_la_prepaga(por_id, texto):
    for id_ in ids_de(texto, "La cumplen"):
        fila = por_id[id_]
        assert entidad_a_verificar(fila) and texto_de(fila, "entidad_verificada") == entidad_a_verificar(fila), id_
