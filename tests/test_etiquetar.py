"""``curado.etiquetar``: qué cobertura se verifica y la ficha esperada de un caso generado. Necesita el kit instalado."""

import pytest

pytest.importorskip("admision")

from admision.casos import Caso  # noqa: E402

from curado.costumbres import EDAD_VOLUNTARIADO  # noqa: E402
from curado.etiquetar import como_fila, credencial_a_verificar, esperada  # noqa: E402
from tests.test_reglas import P  # noqa: E402

OS = ("obra_social", "OSDE Norte", "123456")
PREPAGA = ("prepaga", "Prepaga Sierra", "498055/03")
ART = ("ART Andina", "20-12345678-3")


def caso(**cambios) -> Caso:
    """Un adulto que puede responder, sin urgencia, con DNI y una obra social activa."""
    base = dict(id="t-001", paciente_id="P-1234", nombre="Ana Pérez", edad=40, nivel=4, motivo="dolor de garganta",
                nota="Dolor de garganta desde hace 3 días.", sepsis="no", llegada="por sus propios medios",
                documento_tipo="DNI", documento_numero="30111222", credenciales=(OS,), puede_responder=True,
                no_responde_porque=None, acompanante=None, trabajo=None, declarada=OS, art=None,
                afiliaciones={f"{OS[1]}|{OS[2]}": True})
    base.update(cambios)
    return Caso(**base)


def test_con_una_credencial_se_verifica_esa():
    assert credencial_a_verificar(caso()) == OS


@pytest.mark.parametrize("orden", [(OS, PREPAGA), (PREPAGA, OS)])
def test_con_dos_credenciales_se_verifica_la_prepaga(orden):
    assert credencial_a_verificar(caso(credenciales=orden)) == PREPAGA


def test_sin_credencial_se_verifica_la_que_declara_el_paciente():
    assert credencial_a_verificar(caso(credenciales=())) == OS


def test_sin_credencial_y_sin_poder_responder_contesta_el_acompanante():
    c = caso(credenciales=(), puede_responder=False, no_responde_porque="inconsciente", acompanante="su hija")
    assert credencial_a_verificar(c) == OS


def test_sin_credencial_y_sin_nadie_que_conteste_no_se_verifica_nada():
    c = caso(credenciales=(), puede_responder=False, no_responde_porque="inconsciente", declarada=None)
    assert credencial_a_verificar(c) is None
    assert como_fila(c)["entidad_verificada"] == ""
    assert esperada(c, P)["verificacion"] == {"requerida": None, "prohibidas": []}


def test_la_fila_lleva_la_respuesta_de_la_entidad():
    assert como_fila(caso())["respuesta_verificacion"] == "activa"
    inactiva = caso(afiliaciones={f"{OS[1]}|{OS[2]}": False})
    assert como_fila(inactiva)["respuesta_verificacion"] == "inactiva"


def test_la_cobertura_declarada_solo_se_llena_sin_credencial():
    assert como_fila(caso())["cobertura_declarada"] == ""
    assert como_fila(caso(credenciales=()))["cobertura_declarada"] == "OSDE Norte (obra social) 123456"


def test_con_dos_credenciales_la_obra_social_queda_prohibida():
    c = caso(credenciales=(OS, PREPAGA), afiliaciones={f"{OS[1]}|{OS[2]}": True, f"{PREPAGA[1]}|{PREPAGA[2]}": True})
    assert esperada(c, P)["verificacion"] == {"requerida": [PREPAGA[1], PREPAGA[2]], "prohibidas": [OS[1]]}


def test_en_un_accidente_de_trabajo_se_verifica_la_art_y_no_la_cobertura_propia():
    c = caso(trabajo="trabajando", art=ART)
    assert esperada(c, P)["verificacion"] == {"requerida": list(ART), "prohibidas": [OS[1]]}


@pytest.mark.parametrize("edad, acompanante, aviso", [
    (EDAD_VOLUNTARIADO, None, True),
    (EDAD_VOLUNTARIADO - 1, None, False),
    (EDAD_VOLUNTARIADO + 10, "su hijo", False),
])
def test_el_aviso_al_voluntariado_sigue_la_costumbre(edad, acompanante, aviso):
    assert esperada(caso(edad=edad, acompanante=acompanante), P)["ficha"]["aviso_al_voluntariado"] is aviso
