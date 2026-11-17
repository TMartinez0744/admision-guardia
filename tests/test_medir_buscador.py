from evaluacion.medir_buscador import firma, medir_consultas
from buscador.bm25 import Chunk
from functools import lru_cache


def test_cache_evitar_repeticiones_sin_cambiar_texto_orden_ni_k():
    llamadas = []

    def recuperar(consulta, k):
        llamadas.append((consulta, k))
        return [Chunk("NOR-AAA-01", consulta), Chunk("NOR-BBB-01", "segundo")]

    consultas = ["edad", "plazo", "edad", "edad", "plazo"]
    esperado, _ = medir_consultas(recuperar, consultas)
    llamadas.clear()
    cache = lru_cache(maxsize=128)(recuperar)
    obtenido, tiempos = medir_consultas(cache, consultas)
    assert obtenido == esperado
    assert llamadas == [("edad", 3), ("plazo", 3)]
    assert cache.cache_info().hits == 3
    assert len(tiempos["tiempos_segundos"]) == len(consultas)
    assert tiempos["p95_ms"] >= tiempos["mediana_ms"]
    assert firma(obtenido[0]) != firma(list(reversed(obtenido[0])))
