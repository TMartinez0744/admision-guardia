"""``buscador.hibrido``: la fusión RRF y los prefijos de cada modelo, con un modelo de embeddings de juguete.

Así no hace falta bajar bge-m3 ni tener GPU, pero sí el kit, torch y sentence-transformers instalados.
"""

from pathlib import Path

import pytest

pytest.importorskip("admision")
hibrido = pytest.importorskip("buscador.hibrido")

import numpy as np  # noqa: E402

from buscador.bm25 import BuscadorBM25  # noqa: E402
from tests.test_buscador import normas  # noqa: E402,F401  (fixture)

# Cada dimensión es un tema; las palabras de cada lista lo activan. Así una consulta coloquial
# ("una abuela de ochenta") cae cerca del párrafo de pacientes mayores sin compartir palabras con él.
TEMAS = [("mayor", "abuela", "ochenta"), ("sepsis", "infección", "fiebre"), ("definiciones", "guardia")]


class Modelo:
    def __init__(self):
        self.textos = []

    def encode(self, textos, normalize_embeddings=True):
        lista = [textos] if isinstance(textos, str) else list(textos)
        self.textos += lista
        vectores = np.array([[sum(t.lower().count(p) for p in tema) for tema in TEMAS] for t in lista], dtype=float)
        vectores += 1e-3
        vectores /= np.linalg.norm(vectores, axis=1, keepdims=True)
        return vectores[0] if isinstance(textos, str) else vectores


@pytest.fixture
def modelo(monkeypatch):
    m = Modelo()
    monkeypatch.setattr(hibrido, "_cargar", lambda nombre, revision: m)
    return m


@pytest.mark.parametrize("modo", ["denso", "hibrido"])
def test_los_embeddings_encuentran_una_consulta_coloquial_que_bm25_no(normas, modelo, modo):
    consulta = "una abuela de ochenta y pico"
    assert BuscadorBM25(normas).recuperar(consulta, 1) == []
    assert hibrido.BuscadorHibrido(normas, modo=modo).recuperar(consulta, 1)[0].seccion == "NOR-AAA-01"


def test_el_modo_bm25_ordena_igual_que_bm25(normas, modelo):
    buscador = hibrido.BuscadorHibrido(normas, modo="bm25")
    assert sorted(buscador.ranking_bm25("plazo sepsis")) == list(range(len(buscador.chunks)))
    assert buscador.recuperar("plazo sepsis", 1) == BuscadorBM25(normas).recuperar("plazo sepsis", 1)


def test_rrf_suma_uno_sobre_k_mas_el_rango_en_cada_ranking(normas, modelo):
    buscador = hibrido.BuscadorHibrido(normas, modo="hibrido")
    consulta = "fiebre y registro"
    puntajes = [0.0] * len(buscador.chunks)
    for ranking in (buscador.ranking_bm25(consulta), buscador.ranking_denso(consulta)):
        for rango, i in enumerate(ranking):
            puntajes[i] += 1 / (hibrido.RRF_K + rango + 1)
    esperado = sorted(range(len(puntajes)), key=lambda i: (-puntajes[i], i))
    assert buscador.recuperar(consulta, 4) == [buscador.chunks[i] for i in esperado]


def test_rrf_combina_los_dos_rankings(normas, modelo):
    # BM25 pone primero el párrafo de "registro" y los embeddings el de "fiebre" (sepsis): ambos quedan arriba.
    buscador = hibrido.BuscadorHibrido(normas, modo="hibrido")
    secciones = {c.seccion for c in buscador.recuperar("fiebre y registro", 2)}
    assert secciones == {"NOR-AAA-01", "NOR-BBB-01"}


@pytest.mark.parametrize("modo", ["denso", "hibrido"])
def test_los_modos_con_embeddings_siempre_devuelven_k(normas, modelo, modo):
    assert len(hibrido.BuscadorHibrido(normas, modo=modo).recuperar("xyz", 3)) == 3


def test_los_pasajes_y_las_consultas_llevan_el_prefijo_del_modelo(normas, modelo):
    buscador = hibrido.BuscadorHibrido(normas, modelo="e5-small", modo="denso")
    buscador.recuperar("sepsis", 1)
    assert all(t.startswith("passage: ") for t in modelo.textos[:-1])
    assert modelo.textos[-1] == "query: sepsis"


def test_bge_m3_no_usa_prefijos(normas, modelo):
    hibrido.BuscadorHibrido(normas, modelo="bge-m3", modo="denso").recuperar("sepsis", 1)
    assert modelo.textos[-1] == "sepsis"


def test_cada_modelo_se_carga_una_sola_vez(monkeypatch):
    cargas = []
    monkeypatch.setattr(hibrido, "SentenceTransformer", lambda *a, **k: cargas.append(a) or object())
    monkeypatch.setattr(hibrido, "_CARGADOS", {})
    primero = hibrido._cargar("modelo", "rev")
    assert hibrido._cargar("modelo", "rev") is primero
    assert len(cargas) == 1


def test_entrega_usa_bge_m3_denso_con_tres_resultados(monkeypatch):
    import entrega

    pedidos = []
    monkeypatch.setattr(entrega, "BuscadorHibrido", lambda ruta, **k: pedidos.append((ruta, k)))
    entrega.construir_buscador("normas/b")
    assert pedidos == [(Path("normas/b"), {"modelo": "bge-m3", "modo": "denso", "k_entorno": 3})]


@pytest.mark.parametrize("modo", ["denso", "hibrido"])
def test_cache_reutiliza_consulta_sin_cambiar_resultados(normas, modelo, modo):
    buscador = hibrido.BuscadorHibrido(normas, modo=modo)
    modelo.textos.clear()
    esperado = buscador.recuperar("fiebre", 3)
    assert buscador.recuperar("fiebre", 3) == esperado
    assert modelo.textos == ["query: fiebre"]


def test_cache_distingue_consulta_y_k(normas, modelo):
    buscador = hibrido.BuscadorHibrido(normas, modo="denso")
    modelo.textos.clear()
    uno = buscador.recuperar("fiebre", 1)
    tres = buscador.recuperar("fiebre", 3)
    buscador.recuperar("registro", 3)
    assert uno == tres[:1]
    assert len(tres) == 3
    assert buscador.recuperar("fiebre", 1) == uno
    assert modelo.textos == ["query: fiebre", "query: fiebre", "query: registro"]


def test_cache_respeta_cambio_de_modo_del_comparador(normas, modelo):
    buscador = hibrido.BuscadorHibrido(normas, modo="denso")
    denso = buscador.recuperar("fiebre", 1)
    buscador.modo = "bm25"
    lexical = buscador.recuperar("fiebre", 1)
    assert lexical == [buscador.chunks[buscador.ranking_bm25("fiebre")[0]]]
    assert lexical != denso
    buscador.modo = "denso"
    assert buscador.recuperar("fiebre", 1) == denso


def test_cache_no_comparte_resultados_entre_normas(normas, modelo):
    otra = normas / "otra-version"
    otra.mkdir()
    for p in normas.glob("*.md"):
        (otra / p.name).write_text(p.read_text(), encoding="utf-8")
    (otra / "parametros.yaml").write_text(
        (normas / "parametros.yaml").read_text().replace("valor: 70", "valor: 99"), encoding="utf-8")
    primero = hibrido.BuscadorHibrido(normas, modo="denso")
    segundo = hibrido.BuscadorHibrido(otra, modo="denso")
    a = primero.recuperar("pacientes mayores", 3)
    b = segundo.recuperar("pacientes mayores", 3)
    assert any("70 años" in c.texto for c in a)
    assert any("99 años" in c.texto for c in b)
    assert primero.recuperar("pacientes mayores", 3) == a
    assert segundo.recuperar("pacientes mayores", 3) == b


def test_cache_no_expone_la_lista_guardada(normas, modelo):
    buscador = hibrido.BuscadorHibrido(normas, modo="denso")
    modelo.textos.clear()
    salida = buscador.recuperar("fiebre", 3)
    esperado = salida.copy()
    salida.clear()
    assert buscador.recuperar("fiebre", 3) == esperado
    assert modelo.textos == ["query: fiebre"]


def test_cache_descarta_entradas_antiguas_al_superar_128(normas, modelo):
    buscador = hibrido.BuscadorHibrido(normas, modo="denso")
    modelo.textos.clear()
    for i in range(129):
        buscador.recuperar(f"consulta {i}", 1)
    buscador.recuperar("consulta 128", 1)
    buscador.recuperar("consulta 0", 1)
    assert modelo.textos.count("query: consulta 128") == 1
    assert modelo.textos.count("query: consulta 0") == 2
