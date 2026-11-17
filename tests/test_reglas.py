"""Las reglas de ``curado.reglas``: cada norma, con un caso que la dispara y uno que no."""

import pytest

from curado.reglas import (
    cargar_parametros,
    credencial_en_juego,
    credenciales_de,
    ficha_esperada,
    nombre_de_art,
    partir_credencial,
    ultimo_digito,
)

# Valores inventados a propósito: los tests no dependen de los de ninguna versión de normas.
P = {
    "P-ADM-1": 2,   # nivel hasta el cual pasa al box antes del registro
    "P-ADM-2": 80,  # edad desde la cual pasa al box antes del registro
    "P-ADM-3": 2,   # nivel hasta el cual el registro es provisorio aunque haya pasaporte o cédula
    "P-TDE-1": 10,  # plazo del ECG
    "P-TDE-2": 25,  # plazo del código ACV
    "P-TDE-3": 60,  # plazo de sepsis grave
    "P-TDE-4": 180,  # plazo de sepsis no grave
    "P-TDE-5": 5,   # descuento por llegar en ambulancia
    "P-COB-2": 7,   # último dígito reservado
}


def fila(**cambios) -> dict:
    """Un paciente adulto, sin urgencia, con DNI, sin circuito y sin cobertura."""
    base = {
        "documento_tipo": "DNI",
        "documento_numero": "30.123.456",
        "nivel": "4",
        "edad": "40",
        "motivo": "dolor abdominal",
        "sospecha_sepsis": "no",
        "llegada": "por sus medios",
        "lesion_trabajo": "no",
        "art_declarada": "",
        "credenciales": "",
        "cobertura_declarada": "",
        "entidad_verificada": "",
        "respuesta_verificacion": "",
        "acompanante": "hija",
    }
    base.update(cambios)
    return base


# --- Credenciales ---------------------------------------------------------------------------------

def test_partir_credencial_de_obra_social():
    assert partir_credencial("Obra Social Bermejo (obra social) 18-876602-7") == (
        "Obra Social Bermejo", "obra_social", "18-876602-7")


def test_partir_credencial_de_prepaga_ignora_mayusculas_del_tipo():
    assert partir_credencial("Prepaga Sierra (Prepaga) 0042") == ("Prepaga Sierra", "prepaga", "0042")


@pytest.mark.parametrize("texto", ["", "  ", "ninguna", "Ninguna", None, "sin formato", "Algo (desconocido) 12"])
def test_partir_credencial_sin_credencial_valida(texto):
    assert partir_credencial(texto) is None


def test_nombre_de_art_saca_el_cuil():
    assert nombre_de_art("Pampa Laboral ART CUIL 23-28281926-3") == "Pampa Laboral ART"


def test_nombre_de_art_sin_cuil_devuelve_el_texto():
    assert nombre_de_art("Pampa Laboral ART") == "Pampa Laboral ART"
    assert nombre_de_art("") is None


@pytest.mark.parametrize("numero, digito", [("18-876602-7", 7), ("0042", 2), ("A-1B", 1), ("sin", None)])
def test_ultimo_digito(numero, digito):
    assert ultimo_digito(numero) == digito


def test_credenciales_usa_la_declarada_si_no_presento_ninguna():
    f = fila(cobertura_declarada="Prepaga Sierra (prepaga) 0042")
    assert credenciales_de(f) == [("Prepaga Sierra", "prepaga", "0042")]


def test_credenciales_separa_por_punto_y_coma():
    f = fila(credenciales="OS Uno (obra social) 11; Prepaga Dos (prepaga) 22")
    assert [c[0] for c in credenciales_de(f)] == ["OS Uno", "Prepaga Dos"]


def test_credencial_en_juego_es_la_verificada():
    f = fila(credenciales="OS Uno (obra social) 11; Prepaga Dos (prepaga) 22", entidad_verificada="Prepaga Dos")
    assert credencial_en_juego(f) == ("Prepaga Dos", "prepaga", "22")


def test_credencial_en_juego_con_varias_y_ninguna_verificada_no_decide():
    f = fila(credenciales="OS Uno (obra social) 11; Prepaga Dos (prepaga) 22")
    assert credencial_en_juego(f) is None


# --- Registro (NOR-ADM-01 §2 §3, NOR-ADM-03 §1) -----------------------------------------------------

def test_registro_definitivo_con_documento():
    ficha = ficha_esperada(fila(), P)
    assert (ficha["registro"], ficha["numero_documento"]) == ("definitivo", "30.123.456")


def test_registro_provisorio_sin_documento():
    ficha = ficha_esperada(fila(documento_tipo="", documento_numero=""), P)
    assert (ficha["registro"], ficha["numero_documento"]) == ("provisorio", None)


@pytest.mark.parametrize("tipo", ["pasaporte", "cédula"])
def test_pasaporte_o_cedula_en_nivel_urgente_es_provisorio_pero_anota_el_numero(tipo):
    ficha = ficha_esperada(fila(documento_tipo=tipo, documento_numero="X123", nivel="2"), P)
    assert (ficha["registro"], ficha["numero_documento"]) == ("provisorio", "X123")


def test_pasaporte_en_nivel_no_urgente_es_definitivo():
    ficha = ficha_esperada(fila(documento_tipo="pasaporte", documento_numero="X123", nivel="3"), P)
    assert ficha["registro"] == "definitivo"


def test_dni_en_nivel_urgente_sigue_siendo_definitivo():
    assert ficha_esperada(fila(nivel="1"), P)["registro"] == "definitivo"


# --- Box antes del registro (NOR-ADM-02 §1) -------------------------------------------------------

@pytest.mark.parametrize("edad, nivel, esperado", [
    ("40", "4", False),
    ("80", "4", True),   # justo en el umbral de edad
    ("79", "4", False),
    ("40", "2", True),   # justo en el umbral de nivel
    ("40", "3", False),
])
def test_box_antes_del_registro(edad, nivel, esperado):
    assert ficha_esperada(fila(edad=edad, nivel=nivel), P)["box_antes_del_registro"] is esperado


# --- Circuitos (NOR-TDE-01 a 04) ------------------------------------------------------------------

@pytest.mark.parametrize("cambios, circuito, plazo", [
    ({}, "ninguno", None),
    ({"motivo": "Dolor torácico"}, "ecg", 10),
    ({"motivo": "signos neurológicos focales de inicio súbito"}, "codigo_acv", 25),
    ({"sospecha_sepsis": "probable"}, "codigo_sepsis", 60),
    ({"sospecha_sepsis": "con signos de shock"}, "codigo_sepsis", 60),
    ({"sospecha_sepsis": "posible"}, "codigo_sepsis", 180),
    # La sepsis gana sobre el motivo.
    ({"sospecha_sepsis": "probable", "motivo": "dolor torácico"}, "codigo_sepsis", 60),
    # La ambulancia descuenta P-TDE-5 del plazo, pero no crea un circuito.
    ({"motivo": "dolor torácico", "llegada": "en ambulancia"}, "ecg", 5),
    ({"llegada": "en ambulancia"}, "ninguno", None),
])
def test_circuito_y_plazo(cambios, circuito, plazo):
    ficha = ficha_esperada(fila(**cambios), P)
    assert (ficha["circuito"], ficha["plazo_circuito_min"]) == (circuito, plazo)


# --- Cobertura (NOR-COB-01 a 04) ------------------------------------------------------------------

def test_sin_credenciales_es_sin_cobertura():
    ficha = ficha_esperada(fila(), P)
    assert (ficha["cobertura"], ficha["entidad_a_notificar"]) == ("sin_cobertura", None)


def test_credencial_activa_cubre_y_se_notifica():
    f = fila(credenciales="Prepaga Sierra (prepaga) 0042", respuesta_verificacion="activa")
    ficha = ficha_esperada(f, P)
    assert (ficha["cobertura"], ficha["entidad_a_notificar"]) == ("prepaga", "Prepaga Sierra")


def test_credencial_inactiva_no_cubre_ni_se_notifica():
    f = fila(credenciales="Prepaga Sierra (prepaga) 0042", respuesta_verificacion="inactiva")
    ficha = ficha_esperada(f, P)
    assert (ficha["cobertura"], ficha["entidad_a_notificar"]) == ("sin_cobertura", None)


@pytest.mark.parametrize("respuesta", ["activa", "inactiva"])
def test_digito_reservado_no_cubre_pero_se_notifica_igual(respuesta):
    f = fila(credenciales="OS Bermejo (obra social) 18-876602-7", respuesta_verificacion=respuesta)
    ficha = ficha_esperada(f, P)
    assert (ficha["cobertura"], ficha["entidad_a_notificar"]) == ("sin_cobertura", "OS Bermejo")


def test_accidente_de_trabajo_cubre_la_art_aunque_tenga_prepaga():
    f = fila(lesion_trabajo="sí", art_declarada="Pampa Laboral ART CUIL 23-28281926-3",
             credenciales="Prepaga Sierra (prepaga) 0042", respuesta_verificacion="activa")
    ficha = ficha_esperada(f, P)
    assert (ficha["cobertura"], ficha["entidad_a_notificar"]) == ("art", "Pampa Laboral ART")


def test_ficha_tiene_los_siete_campos_de_las_normas():
    assert set(ficha_esperada(fila(), P)) == {
        "registro", "numero_documento", "box_antes_del_registro", "circuito", "plazo_circuito_min",
        "cobertura", "entidad_a_notificar"}


# --- Parámetros -----------------------------------------------------------------------------------

def test_cargar_parametros_lee_el_yaml(tmp_path):
    (tmp_path / "parametros.yaml").write_text(
        "parametros:\n  - codigo: P-ADM-1\n    valor: 2\n  - codigo: P-COB-2\n    valor: 7\n", encoding="utf-8")
    assert cargar_parametros(tmp_path) == {"P-ADM-1": 2, "P-COB-2": 7}
