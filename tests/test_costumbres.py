"""Las costumbres de ``curado.costumbres`` y la clasificación del historial de ``curado.clasificar``."""

import pytest

from curado.clasificar import clasificar
from curado.costumbres import EDAD_VOLUNTARIADO, aviso_al_voluntariado, entidad_a_verificar
from curado.reglas import ficha_esperada
from tests.test_reglas import P, fila


# --- Costumbre 1: voluntariado --------------------------------------------------------------------

@pytest.mark.parametrize("edad, acompanante, esperado", [
    (str(EDAD_VOLUNTARIADO), "", True),
    (str(EDAD_VOLUNTARIADO - 1), "", False),
    ("90", "hija", False),
    ("90", "   ", True),  # un acompañante en blanco es no tener acompañante
])
def test_aviso_al_voluntariado(edad, acompanante, esperado):
    assert aviso_al_voluntariado(fila(edad=edad, acompanante=acompanante)) is esperado


# --- Costumbre 2: qué credencial se verifica ------------------------------------------------------

def test_con_una_credencial_no_hay_costumbre():
    assert entidad_a_verificar(fila(credenciales="OS Uno (obra social) 11")) is None


def test_con_dos_credenciales_se_verifica_la_prepaga():
    f = fila(credenciales="OS Uno (obra social) 11; Prepaga Dos (prepaga) 22")
    assert entidad_a_verificar(f) == "Prepaga Dos"


def test_con_dos_credenciales_sin_prepaga_se_verifica_la_primera():
    f = fila(credenciales="OS Uno (obra social) 11; OS Dos (obra social) 22")
    assert entidad_a_verificar(f) == "OS Uno"


# --- Clasificación de una fila del historial ------------------------------------------------------

def registrada(f: dict, **cambios) -> dict:
    """La fila con lo que anotó el operador: por defecto, exactamente lo que piden normas y costumbres."""
    ficha = ficha_esperada(f, P)
    f = dict(f)
    f.update({
        "registro": ficha["registro"],
        "numero_documento": ficha["numero_documento"] or "",
        "box_antes_del_registro": "sí" if ficha["box_antes_del_registro"] else "no",
        "circuito": ficha["circuito"],
        "plazo_circuito_min": "" if ficha["plazo_circuito_min"] is None else str(ficha["plazo_circuito_min"]),
        "cobertura": ficha["cobertura"],
        "entidad_a_notificar": ficha["entidad_a_notificar"] or "",
        "aviso_al_voluntariado": "sí" if aviso_al_voluntariado(f) else "no",
    })
    f.update(cambios)
    return f


def test_fila_que_sigue_normas_y_costumbres_es_correcta():
    assert clasificar(registrada(fila(motivo="dolor torácico")), P) == ("correcta", [])


def test_fila_que_viola_una_norma_es_error_y_dice_cual():
    tipo, motivos = clasificar(registrada(fila(motivo="dolor torácico"), plazo_circuito_min="30"), P)
    assert tipo == "error"
    assert len(motivos) == 1 and motivos[0].startswith("plazo_circuito_min")
    assert "NOR-TDE" in motivos[0]


def test_fila_que_se_aparta_de_una_costumbre_es_ruido():
    tipo, motivos = clasificar(registrada(fila(edad="85", acompanante=""), aviso_al_voluntariado="no"), P)
    assert tipo == "ruido"
    assert "costumbre 1" in motivos[0]


def test_el_error_gana_sobre_el_ruido():
    f = registrada(fila(edad="85", acompanante=""), aviso_al_voluntariado="no", registro="provisorio")
    assert clasificar(f, P)[0] == "error"


def test_verificar_la_obra_social_teniendo_prepaga_es_ruido():
    f = fila(credenciales="OS Uno (obra social) 11; Prepaga Dos (prepaga) 22",
             entidad_verificada="OS Uno", respuesta_verificacion="activa")
    tipo, motivos = clasificar(registrada(f), P)
    assert tipo == "ruido"
    assert "costumbre 2" in motivos[0]
