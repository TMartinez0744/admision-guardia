"""``buscador.bm25``: cómo se parten las normas y qué devuelve BM25. Necesita el kit instalado.

Los tests del final usan las normas del kit (``ADMISION_KIT`` o junto al repo) y se saltean si no están.
"""

import os
from pathlib import Path

import pytest

pytest.importorskip("admision")

from buscador.bm25 import BuscadorBM25, normalizar, partir  # noqa: E402

AAA = """## NOR-AAA-01 · Ubicación de pacientes mayores

§1. El paciente con edad igual o mayor que P-ADM-2 va al box antes del registro.

§2. Esta sección prevalece sobre las demás de admisión."""

BBB = """## NOR-BBB-01 · Código sepsis

§1. Con sospecha de sepsis grave el plazo del circuito es P-TDE-3."""

CCC = """## NOR-CCC-01 · Definiciones

Texto sin párrafos numerados sobre la guardia."""

PARAMETROS = """parametros:
- codigo: P-ADM-2
  valor: 70
  unidad: anios
- codigo: P-TDE-3
  valor: 15
  unidad: min
"""


@pytest.fixture
def normas(tmp_path):
    """Tres secciones chicas: una con dos párrafos, una con un párrafo y una sin párrafos numerados."""
    for nombre, texto in (("NOR-AAA-01", AAA), ("NOR-BBB-01", BBB), ("NOR-CCC-01", CCC)):
        (tmp_path / f"{nombre}.md").write_text(texto, encoding="utf-8")
    (tmp_path / "parametros.yaml").write_text(PARAMETROS, encoding="utf-8")
    return tmp_path


# --- normalizar ------------------------------------------------------------------------------------

def test_normalizar_saca_mayusculas_tildes_y_palabras_vacias():
    assert normalizar("¿Qué plazo tiene el Código Sepsis según la norma?") == ["plazo", "codigo", "sepsis", "norma"]


def test_normalizar_conserva_codigos_con_guiones():
    assert normalizar("P-ADM-2 y NOR-COB-04 §3") == ["p-adm-2", "nor-cob-04"]


def test_normalizar_descarta_letras_sueltas_y_textos_vacios():
    assert normalizar("a b c") == []
    assert normalizar("") == []


# --- partir ---------------------------------------------------------------------------------------

def test_partir_da_un_chunk_por_parrafo_con_su_encabezado(normas):
    chunks = partir(normas)
    assert [c.seccion for c in chunks] == ["NOR-AAA-01", "NOR-AAA-01", "NOR-BBB-01", "NOR-CCC-01"]
    assert all(c.texto.startswith(f"## {c.seccion} · ") for c in chunks)
    assert "§2." not in chunks[0].texto and "§1." not in chunks[1].texto


def test_partir_agrega_los_valores_que_cita_cada_parrafo(normas):
    primero, segundo, sepsis, _ = partir(normas)
    assert primero.texto.endswith("\n\nValores: P-ADM-2 = 70 años.")
    assert "Valores" not in segundo.texto
    assert sepsis.texto.endswith("Valores: P-TDE-3 = 15 min.")


def test_partir_deja_entera_una_seccion_sin_parrafos_numerados(normas):
    assert partir(normas)[-1].texto == CCC


# --- BM25 -----------------------------------------------------------------------------------------

def test_bm25_encuentra_el_parrafo_que_usa_las_palabras_de_la_consulta(normas):
    buscador = BuscadorBM25(normas)
    assert buscador.recuperar("plazo del código sepsis", 1)[0].seccion == "NOR-BBB-01"
    assert "box antes del registro" in buscador.recuperar("box antes del registro de un paciente mayor", 1)[0].texto


def test_bm25_devuelve_solo_chunks_con_puntaje_y_a_lo_sumo_k(normas):
    buscador = BuscadorBM25(normas)
    assert len(buscador.recuperar("sepsis", 3)) == 1
    assert len(buscador.recuperar("sepsis guardia edad", 2)) == 2


@pytest.mark.parametrize("consulta", ["", "el de la", "palabras inexistentes xyz"])
def test_bm25_sin_palabras_utiles_no_devuelve_nada(normas, consulta):
    assert BuscadorBM25(normas).recuperar(consulta, 3) == []


def test_bm25_k_entorno_por_defecto_es_el_de_la_catedra(normas):
    assert BuscadorBM25(normas).k_entorno == 2
    assert BuscadorBM25(normas, k_entorno=3).k_entorno == 3


def test_bm25_premia_el_parrafo_mas_corto_a_igual_frecuencia(normas):
    # "mayores" aparece una vez en el encabezado de los dos párrafos de NOR-AAA-01; §2 es más corto.
    primero, segundo = BuscadorBM25(normas).recuperar("pacientes mayores", 2)
    assert "§2." in primero.texto and "§1." in segundo.texto


# --- Con las normas del kit -----------------------------------------------------------------------

def _kit():
    candidatos = [os.environ.get("ADMISION_KIT"), Path(__file__).resolve().parents[2] / "talksmith-ing" / "missions" / "TPFinal"]
    for candidato in filter(None, candidatos):
        parametros = Path(candidato) / "normas" / "original" / "parametros.yaml"
        if parametros.exists() and parametros.stat().st_size:
            return Path(candidato)
    return None


KIT = _kit()
con_kit = pytest.mark.skipif(KIT is None, reason="falta el kit (ADMISION_KIT)")


@con_kit
@pytest.mark.parametrize("version", ["original", "b", "c"])
def test_los_valores_salen_de_la_version_de_normas_que_se_recibe(version):
    from curado.reglas import cargar_parametros

    edad = cargar_parametros(KIT / "normas" / version)["P-ADM-2"]
    chunk = next(c for c in partir(KIT / "normas" / version) if c.seccion == "NOR-ADM-02" and "§1." in c.texto)
    assert chunk.texto.endswith(f"Valores: P-ADM-2 = {edad} años.")


@con_kit
def test_las_tres_versiones_se_parten_igual():
    secciones = {v: [c.seccion for c in partir(KIT / "normas" / v)] for v in ("original", "b", "c")}
    assert secciones["original"] == secciones["b"] == secciones["c"]


@con_kit
@pytest.mark.parametrize("consulta, seccion", [
    ("ubicación en el box antes del registro de pacientes mayores", "NOR-ADM-02"),
    ("código sepsis plazo", "NOR-TDE-03"),
    ("número de afiliado con terminación reservada", "NOR-COB-04"),
])
def test_bm25_encuentra_la_norma_en_el_kit(consulta, seccion):
    assert seccion in [c.seccion for c in BuscadorBM25(KIT / "normas" / "original").recuperar(consulta, 3)]
