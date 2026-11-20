"""``curado.evidencia``: los números de ``costumbres.md`` sobre un historial chico armado a mano."""

from curado.evidencia import evidencia_prepaga, evidencia_voluntariado, informe
from tests.test_reglas import fila

DOS = "OS Uno (obra social) 11; Prepaga Dos (prepaga) 22"
DOS_AL_REVES = "Prepaga Dos (prepaga) 22; OS Uno (obra social) 11"


def admision(id_, operador, edad="40", acompanante="hija", aviso="no", **cambios):
    return fila(id=id_, operador=operador, edad=edad, acompanante=acompanante,
                aviso_al_voluntariado=aviso, **cambios)


# --- Costumbre 1: voluntariado --------------------------------------------------------------------

def historial_voluntariado():
    return [
        admision("h1", "OP-01", edad="76", acompanante="", aviso="sí"),   # cumple avisando
        admision("h2", "OP-01", edad="72", acompanante=""),               # cumple sin avisar: menor de 75
        admision("h3", "OP-01", edad="90"),                                # cumple sin avisar: acompañado
        admision("h4", "OP-02", edad="35", aviso="sí"),                   # se aparta
        admision("h5", "OP-02", edad="74", acompanante="", aviso="sí"),   # se aparta
        admision("h6", "OP-02", edad="50"),                               # cumple, pero el OP-02 ya se apartó
    ]


def test_cuenta_los_operadores_que_cumplen_sin_excepciones_y_sus_filas():
    v = evidencia_voluntariado(historial_voluntariado())
    assert (v["filas"], v["con_aviso"], v["operadores"]) == (6, 3, 2)
    assert v["cumplen"] == ["OP-01"]
    assert v["filas_de_los_que_cumplen"] == 3
    assert v["desvios_por_operador"] == {"OP-02": 2}


def test_el_corte_de_edad_mira_solo_a_los_que_cumplen_y_sin_acompanante():
    franjas = evidencia_voluntariado(historial_voluntariado())["franjas"]
    # h5 (74, del OP-02) no entra: el OP-02 no cumple la costumbre. h3 no entra: tiene acompañante.
    assert franjas == {(70, 74): (1, 0), (75, 80): (1, 1)}


# --- Costumbre 2: prepaga -------------------------------------------------------------------------

def test_cuenta_la_prepaga_verificada_sin_importar_el_orden():
    filas = [
        admision("h1", "OP-01", credenciales=DOS, entidad_verificada="Prepaga Dos"),
        admision("h2", "OP-01", credenciales=DOS_AL_REVES, entidad_verificada="Prepaga Dos"),
        admision("h3", "OP-02", credenciales=DOS, entidad_verificada="OS Uno"),
        admision("h4", "OP-02", credenciales="OS Uno (obra social) 11", entidad_verificada="OS Uno"),
    ]
    p = evidencia_prepaga(filas)
    assert (p["con_dos_credenciales"], p["cumplen"]) == (3, 2)  # h4 tiene una sola credencial
    assert (p["prepaga_primera"], p["prepaga_segunda"]) == (1, 2)
    assert p["se_apartan"] == ["h3"]
    assert p["se_apartan_por_operador"] == {"OP-02": 1}


# --- Lo que imprime -------------------------------------------------------------------------------

def test_informe_trae_los_numeros_de_costumbres_md():
    filas = historial_voluntariado() + [admision("h7", "OP-01", credenciales=DOS, entidad_verificada="Prepaga Dos")]
    lineas = informe(evidencia_voluntariado(filas), evidencia_prepaga(filas))
    assert "  la cumplen sin excepciones: 1 de 2 operadores, 4 filas" in lineas
    assert "    75 a 80 años: 1 de 1 con aviso" in lineas
    assert "  verificaron la prepaga: 1 de 1 (100.0%)" in lineas
    assert "  se apartan: ninguna" in lineas


def test_informe_sin_filas_con_dos_credenciales_no_divide_por_cero():
    filas = historial_voluntariado()
    assert "  verificaron la prepaga: 0 de 0" in informe(evidencia_voluntariado(filas), evidencia_prepaga(filas))
