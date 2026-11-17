"""Lo que escriben ``curado.clasificar`` y ``curado.conversaciones``: el CSV, el resumen y las conversaciones."""

import csv
import json

import pytest

from curado.clasificar import guardar, resumen


def fila(id_, operador="op-1"):
    return {"id": id_, "operador": operador}


# --- clasificar -----------------------------------------------------------------------------------

def test_guardar_escribe_id_y_tipo_en_el_orden_del_historial(tmp_path):
    salida = tmp_path / "clasificado.csv"
    guardar([fila("h2"), fila("h1")], ["error", "correcta"], salida)
    with open(salida, encoding="utf-8", newline="") as f:
        assert list(csv.reader(f)) == [["id", "tipo"], ["h2", "error"], ["h1", "correcta"]]
    assert b"\r\n" in salida.read_bytes(), "el CSV usa los fin de línea de csv.writer, como el del repo"


def test_resumen_cuenta_tipos_campos_y_operadores():
    filas = [fila("h1", "ana"), fila("h2", "ana"), fila("h3", "beto"), fila("h4", "beto")]
    clasificaciones = [
        ("correcta", []),
        ("error", ["registro: 'definitivo' en vez de 'provisorio' (NOR-ADM-01)", "circuito: x en vez de y (NOR-TDE)"]),
        ("ruido", ["aviso_al_voluntariado: 'sí' con 60 anios (costumbre 1)"]),
        ("ruido", ["aviso_al_voluntariado: 'no' con 80 anios (costumbre 1)"]),
    ]
    lineas = resumen(filas, clasificaciones)
    assert lineas[:3] == ["  correcta      1  (25.0%)", "  error         1  (25.0%)", "  ruido         2  (50.0%)"]
    assert "    registro                    1" in lineas and "    circuito                    1" in lineas
    assert "    aviso_al_voluntariado       2" in lineas
    # El operador con más ruido va primero.
    operadores = lineas[lineas.index("\n  operadores con mas ruido:") + 1:]
    assert operadores == ["    beto  ruido   2  error   0  correcta   0", "    ana  ruido   0  error   1  correcta   1"]


# --- conversaciones -------------------------------------------------------------------------------

@pytest.fixture
def conversaciones():
    """``curado.conversaciones`` importa el kit: sin él, solo se saltean estos tests."""
    return pytest.importorskip("curado.conversaciones")


def traza(id_, *herramientas):
    return {"id": id_, "paciente_id": "P-1",
            "pasos": [{"herramienta": h, "argumentos": {}, "resultado": f"r {h}"} for h in herramientas]}


def test_conversacion_en_el_formato_del_agente_de_ejemplo(conversaciones):
    mensajes = conversaciones.conversacion(traza("h1", "leer_triage", "registrar_decision"))
    assert [m["role"] for m in mensajes] == ["system", "user", "assistant", "user", "assistant"]
    assert json.loads(mensajes[2]["content"]) == {"herramienta": "leer_triage", "argumentos": {}}
    assert mensajes[3]["content"] == "Resultado de leer_triage:\nr leer_triage"
    assert conversaciones.bien_formada(mensajes)


@pytest.mark.parametrize("herramientas", [
    (),                                # sin pasos
    ("leer_triage",),                  # no registra la ficha
    ("leer_triage", "buscar_normativa"),
])
def test_una_traza_sin_registrar_la_ficha_esta_mal_formada(conversaciones, herramientas):
    assert not conversaciones.bien_formada(conversaciones.conversacion(traza("h", *herramientas)))


def test_roles_que_no_alternan_estan_mal_formados(conversaciones):
    mensajes = conversaciones.conversacion(traza("h", "leer_triage", "registrar_decision"))
    assert not conversaciones.bien_formada(mensajes[:3] + mensajes[4:])


def test_seleccionar_filtra_por_tipo_y_separa_las_mal_formadas(conversaciones):
    trazas = [traza("h1", "leer_triage", "registrar_decision"), traza("h2", "registrar_decision"),
              traza("h3", "leer_triage"), traza("h4", "leer_triage", "registrar_decision")]
    clasificacion = {"h1": "correcta", "h2": "error", "h3": "correcta", "h4": "ruido"}
    elegidas, descartadas, mal_formadas = conversaciones.seleccionar(trazas, clasificacion, {"correcta", "ruido"})
    assert [c["id"] for c in elegidas] == ["h1", "h4"]
    assert (descartadas, mal_formadas) == (1, ["h3"])


def test_una_traza_sin_clasificar_se_descarta(conversaciones):
    _, descartadas, _ = conversaciones.seleccionar([traza("h9", "registrar_decision")], {}, {"correcta"})
    assert descartadas == 1


def test_guardar_conversaciones_crea_la_carpeta_y_no_escapa_acentos(conversaciones, tmp_path):
    salida = tmp_path / "datos" / "conversaciones.jsonl"
    conversaciones.guardar([{"id": "h1", "texto": "cédula"}], salida)
    assert salida.read_bytes() == '{"id": "h1", "texto": "cédula"}\n'.encode("utf-8")
