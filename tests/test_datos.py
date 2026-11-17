"""``entrenamiento.datos``: el formato de las conversaciones, el plan del operador experto y las normas sorteadas.

Necesita el kit instalado. Los tests del final juegan casos en el entorno de la cátedra: buscan el kit en
``ADMISION_KIT`` o junto al repo (``pyproject.toml``) y usan BM25 en lugar de bge-m3, así no hace falta GPU.
"""

import json
import os
import random
from pathlib import Path

import pytest
import yaml

datos = pytest.importorskip("entrenamiento.datos")

from admision.generador import generar  # noqa: E402

from tests.test_etiquetar import ART, OS, PREPAGA, caso  # noqa: E402

FICHA = {"circuito": "ninguno"}


def consultas(pasos):
    return [a["consulta"] for h, a in pasos if h == "buscar_normativa"]


def herramientas(pasos):
    return [h for h, _ in pasos]


# --- Formato de las conversaciones ----------------------------------------------------------------

def test_mensajes_en_el_formato_del_agente_de_ejemplo():
    pasos = [("leer_triage", {"paciente_id": "P-1234"}, "Nivel 2, acompañante: su hija"),
             ("registrar_decision", {"circuito": "ninguno"}, "Ficha registrada.")]
    mensajes = datos._mensajes("sistema", "P-1234", pasos)
    assert [m["role"] for m in mensajes] == ["system", "user", "assistant", "user", "assistant"]
    assert mensajes[0]["content"] == "sistema"
    assert "P-1234" in mensajes[1]["content"]
    assert json.loads(mensajes[2]["content"]) == {"herramienta": "leer_triage", "argumentos": {"paciente_id": "P-1234"}}
    assert mensajes[3]["content"] == "Resultado de leer_triage:\nNivel 2, acompañante: su hija"
    # Después de registrar la ficha no hay resultado: la conversación termina con el asistente.
    assert json.loads(mensajes[-1]["content"])["herramienta"] == "registrar_decision"


def test_los_acentos_quedan_como_texto_y_no_escapados():
    mensajes = datos._mensajes("s", "P-1", [("buscar_normativa", {"consulta": "cédula"}, "x")])
    assert "cédula" in mensajes[2]["content"]


class Fragmento:
    def __init__(self, texto):
        self.texto = texto


class Buscador:
    k_entorno = 2

    def __init__(self, resultados):
        self.resultados = resultados
        self.pedidos = []

    def recuperar(self, consulta, k):
        self.pedidos.append((consulta, k))
        return self.resultados[:k]


def test_busqueda_une_los_fragmentos_como_el_entorno():
    buscador = Buscador([Fragmento("## NOR-ADM-01 uno"), "## NOR-COB-01 dos", "tres"])
    assert datos._busqueda(buscador, "registro") == "## NOR-ADM-01 uno\n\n## NOR-COB-01 dos"
    assert buscador.pedidos == [("registro", 2)]


def test_busqueda_sin_resultados():
    assert datos._busqueda(Buscador([]), "nada") == "No se encontró ninguna sección."


def test_pasos_reales_vuelven_a_buscar_y_conservan_el_resto():
    traza = {"pasos": [
        {"herramienta": "leer_triage", "argumentos": {"paciente_id": "P-1"}, "resultado": "triage original"},
        {"herramienta": "buscar_normativa", "argumentos": {"consulta": "sepsis"}, "resultado": "BM25 de la cátedra"},
    ]}
    pasos = datos._pasos_reales(traza, Buscador(["bge-m3"]))
    assert [r for _, _, r in pasos] == ["triage original", "bge-m3"]


def test_trazas_correctas_filtra_por_la_clasificacion_y_conserva_el_orden(tmp_path):
    clasificado = tmp_path / "clasificado.csv"
    clasificado.write_text("id,tipo\nh1,correcta\nh2,error\nh3,correcta\n", encoding="utf-8")
    trazas = tmp_path / "trazas.jsonl"
    trazas.write_text("".join(json.dumps({"id": i}) + "\n" for i in ("h3", "h2", "h1")), encoding="utf-8")
    assert [t["id"] for t in datos.trazas_correctas(trazas, clasificado)] == ["h3", "h1"]


def test_el_historial_clasificado_tiene_las_1600_reales_del_informe():
    import csv

    with open(datos.HISTORIAL_CLASIFICADO, encoding="utf-8") as f:
        assert sum(fila["tipo"] == "correcta" for fila in csv.DictReader(f)) == 1600


def test_guardar_escribe_una_conversacion_por_linea(tmp_path):
    salida = tmp_path / "carpeta" / "nueva" / "datos.jsonl"
    filas = [{"id": "a", "texto": "cédula"}, {"id": "b"}]
    datos.guardar(filas, salida)
    lineas = salida.read_text(encoding="utf-8").splitlines()
    assert [json.loads(x) for x in lineas] == filas
    assert "cédula" in lineas[0]


# --- Plan del operador experto --------------------------------------------------------------------

def test_plan_basico_lee_el_triage_busca_y_verifica_la_credencial():
    pasos = datos.plan(caso(), FICHA)
    assert pasos[0] == ("leer_triage", {"paciente_id": "P-1234"})
    assert consultas(pasos) == [datos.CONSULTAS["registro"], datos.CONSULTAS["reservado"]]
    assert pasos[-1] == ("verificar_afiliacion", {"entidad": OS[1], "numero_afiliado": OS[2]})
    assert "preguntar" not in herramientas(pasos)


@pytest.mark.parametrize("documento, busca", [("pasaporte", True), ("cédula", True), ("DNI", False), (None, False)])
def test_plan_busca_la_norma_de_pasaporte_o_cedula(documento, busca):
    pasos = datos.plan(caso(documento_tipo=documento), FICHA)
    assert (datos.CONSULTAS["documento"] in consultas(pasos)) is busca


def test_plan_la_sepsis_va_antes_que_el_motivo():
    pasos = datos.plan(caso(sepsis="probable", motivo="dolor torácico"), FICHA)
    assert datos.CONSULTAS["sepsis"] in consultas(pasos)
    assert datos.CONSULTAS_MOTIVO["dolor torácico"] not in consultas(pasos)


@pytest.mark.parametrize("motivo", list(datos.CONSULTAS_MOTIVO))
def test_plan_busca_el_plazo_del_motivo(motivo):
    assert datos.CONSULTAS_MOTIVO[motivo] in consultas(datos.plan(caso(motivo=motivo), FICHA))


@pytest.mark.parametrize("circuito, llegada, busca", [
    ("ecg", "en ambulancia", True),
    ("ecg", "por sus propios medios", False),
    ("ninguno", "en ambulancia", False),
])
def test_plan_busca_el_descuento_por_ambulancia_solo_con_circuito(circuito, llegada, busca):
    pasos = datos.plan(caso(llegada=llegada), {"circuito": circuito})
    assert (datos.CONSULTAS["ambulancia"] in consultas(pasos)) is busca


def test_plan_accidente_de_trabajo_pregunta_y_verifica_la_art():
    pasos = datos.plan(caso(trabajo="trabajando", art=ART), FICHA)
    assert consultas(pasos)[-1] == datos.CONSULTAS["art"]
    assert pasos[-2:] == [("preguntar", {"paciente_id": "P-1234", "a_quien": "paciente", "tema": "art"}),
                          ("verificar_afiliacion", {"entidad": ART[0], "numero_afiliado": ART[1]})]
    # La cobertura propia no se verifica (NOR-COB-02 §5).
    assert datos.CONSULTAS["reservado"] not in consultas(pasos)


def test_plan_sin_credencial_pregunta_al_acompanante_si_el_paciente_no_puede():
    c = caso(credenciales=(), puede_responder=False, no_responde_porque="inconsciente", acompanante="su hija")
    pasos = datos.plan(c, FICHA)
    assert ("preguntar", {"paciente_id": "P-1234", "a_quien": "acompanante", "tema": "cobertura"}) in pasos
    assert pasos[-1] == ("verificar_afiliacion", {"entidad": OS[1], "numero_afiliado": OS[2]})


def test_plan_sin_credencial_y_sin_nadie_no_pregunta_ni_verifica():
    c = caso(credenciales=(), puede_responder=False, no_responde_porque="inconsciente", declarada=None)
    pasos = datos.plan(c, FICHA)
    assert consultas(pasos)[-1] == datos.CONSULTAS["sin_credencial"]
    assert not {"preguntar", "verificar_afiliacion"} & set(herramientas(pasos))


def test_plan_con_dos_credenciales_verifica_la_prepaga():
    pasos = datos.plan(caso(credenciales=(OS, PREPAGA)), FICHA)
    assert pasos[-1] == ("verificar_afiliacion", {"entidad": PREPAGA[1], "numero_afiliado": PREPAGA[2]})


def test_plan_no_registra_la_ficha():
    for c in generar(semilla=1, n=40, prefijo="t"):
        assert "registrar_decision" not in herramientas(datos.plan(c, FICHA))


class Entorno:
    """Anota las llamadas y devuelve secciones de normas en las búsquedas."""

    def __init__(self, respuestas):
        self.respuestas = iter(respuestas)
        self.llamadas = []

    def paso(self, herramienta, argumentos):
        self.llamadas.append((herramienta, argumentos))
        return (next(self.respuestas) if herramienta == "buscar_normativa" else "ok"), False


def test_operador_registra_las_secciones_leidas_sin_repetir_y_en_orden():
    entorno = Entorno(["## NOR-ADM-01 a\n## NOR-ADM-02 b", "## NOR-COB-03 c\n## NOR-ADM-01 a"])
    ficha = {"circuito": "ninguno", "ubicacion": "box"}
    datos.operador(entorno, caso(), ficha)
    assert entorno.llamadas[:-1] == datos.plan(caso(), ficha)
    herramienta, argumentos = entorno.llamadas[-1]
    assert herramienta == "registrar_decision"
    assert argumentos == {**ficha, "fundamentos": ["NOR-ADM-01", "NOR-ADM-02", "NOR-COB-03"]}


# --- Normas sorteadas -----------------------------------------------------------------------------

@pytest.fixture
def normas(tmp_path):
    carpeta = tmp_path / "original"
    carpeta.mkdir()
    (carpeta / "NOR-ADM-01.md").write_text("## NOR-ADM-01\nhasta el nivel {P-ADM-1}\n", encoding="utf-8")
    parametros = [{"codigo": c, "valor": 0, "unidad": "u"} for c in datos.RANGOS]
    parametros.append({"codigo": "P-OTRO-1", "valor": 999, "unidad": "minutos"})
    (carpeta / "parametros.yaml").write_text(yaml.safe_dump({"parametros": parametros}), encoding="utf-8")
    return carpeta


def leer(carpeta):
    return {p["codigo"]: p["valor"] for p in yaml.safe_load((carpeta / "parametros.yaml").read_text(encoding="utf-8"))["parametros"]}


def test_normas_al_azar_sortea_dentro_de_los_rangos_y_deja_el_resto(normas, tmp_path):
    for i in range(20):
        destino = tmp_path / f"v{i}"
        datos.normas_al_azar(normas, destino, random.Random(i))
        valores = leer(destino)
        for codigo, (minimo, maximo) in datos.RANGOS.items():
            assert minimo <= valores[codigo] <= maximo
        assert valores["P-OTRO-1"] == 999
        assert (destino / "NOR-ADM-01.md").read_text(encoding="utf-8") == "## NOR-ADM-01\nhasta el nivel {P-ADM-1}\n"
    assert set(leer(normas).values()) == {0, 999}, "la carpeta original no se toca"


def test_normas_al_azar_es_reproducible(normas, tmp_path):
    datos.normas_al_azar(normas, tmp_path / "a", random.Random(5))
    datos.normas_al_azar(normas, tmp_path / "b", random.Random(5))
    assert leer(tmp_path / "a") == leer(tmp_path / "b")


# --- Con el kit: el operador juega casos de verdad ------------------------------------------------

def _kit() -> Path | None:
    candidatos = [os.environ.get("ADMISION_KIT"), Path(__file__).resolve().parents[2] / "talksmith-ing" / "missions" / "TPFinal"]
    for candidato in filter(None, candidatos):
        parametros = Path(candidato) / "normas" / "original" / "parametros.yaml"
        if parametros.exists() and parametros.stat().st_size:
            return Path(candidato)
    return None


KIT = _kit()
con_kit = pytest.mark.skipif(KIT is None, reason="falta el kit (ADMISION_KIT)")


@pytest.fixture
def bm25(monkeypatch):
    from buscador.bm25 import BuscadorBM25

    import entrega

    monkeypatch.setattr(entrega, "construir_buscador", lambda ruta: BuscadorBM25(Path(ruta), k_entorno=3))


@con_kit
def test_el_operador_resuelve_todos_los_casos_generados(bm25):
    conversaciones, descartadas = datos.sinteticas(KIT, "sistema", 120, semilla=3)
    assert descartadas == 0
    assert len(conversaciones) == 120
    for c in conversaciones:
        assert c["fuente"] == "sintetica"
        assert json.loads(c["messages"][-1]["content"])["herramienta"] == "registrar_decision"
        for codigo, (minimo, maximo) in datos.RANGOS.items():
            assert minimo <= int(c["normas"][codigo]) <= maximo


@con_kit
def test_cada_tanda_de_casos_tiene_sus_propias_normas(bm25):
    conversaciones, _ = datos.sinteticas(KIT, "sistema", 2 * datos.CASOS_POR_NORMAS, semilla=0)
    primera, segunda = conversaciones[0]["normas"], conversaciones[-1]["normas"]
    assert all(c["normas"] == primera for c in conversaciones[:datos.CASOS_POR_NORMAS])
    assert primera != segunda


@con_kit
def test_armar_es_reproducible_y_mezcla_reales_y_sinteticas(bm25):
    a, _ = datos.armar(KIT, "sistema", 50, semilla=1)
    b, _ = datos.armar(KIT, "sistema", 50, semilla=1)
    assert a == b
    assert sum(x["fuente"] == "real" for x in a) == 1600
    assert {x["fuente"] for x in a[:100]} == {"real", "sintetica"}, "las sintéticas no quedan todas al final"
