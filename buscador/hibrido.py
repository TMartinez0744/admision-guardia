"""Buscador híbrido: BM25 más embeddings, fusionados por rango (RRF).

BM25 solo encuentra la norma si la consulta usa sus palabras. Las consultas
coloquiales ("una abuela de ochenta y pico", "la cara torcida") no las usan, y
ahí el BM25 por párrafo no acierta ninguna. Los embeddings comparan por
significado; BM25 sigue siendo mejor con códigos y números. Se combinan los dos
rankings con Reciprocal Rank Fusion, que no necesita calibrar puntajes.

Los chunks son los mismos del BM25: un párrafo con el encabezado de su sección y
la línea de valores de los parámetros que cita, armados con la carpeta recibida.

El modelo de embeddings corre en CPU: es chico, el corpus tiene ~100 chunks y así
no le quita VRAM al modelo del agente en la A100.
"""

from __future__ import annotations

from pathlib import Path

from sentence_transformers import SentenceTransformer

from buscador.bm25 import BuscadorBM25, normalizar

# Constante de RRF: puntaje = suma de 1 / (RRF_K + rango).
RRF_K = 60

# Modelos probados, fijados a su commit de Hugging Face, con el prefijo que cada
# uno espera en la consulta y en el pasaje.
MODELOS = {
    "e5-small": ("intfloat/multilingual-e5-small", "614241f622f53c4eeff9890bdc4f31cfecc418b3", "query: ", "passage: "),
    "e5-base": ("intfloat/multilingual-e5-base", "d128750597153bb5987e10b1c3493a34e5a4502a", "query: ", "passage: "),
    "bge-m3": ("BAAI/bge-m3", "5617a9f61b028005a4858fdac845db406aefb181", "", ""),
}


class BuscadorHibrido:
    def __init__(self, ruta_normas: Path, modelo: str = "e5-small", modo: str = "hibrido", k_entorno: int = 2):
        """``modo`` es ``hibrido``, ``denso`` (solo embeddings) o ``bm25``."""
        self.k_entorno = k_entorno
        self.modo = modo
        self.bm25 = BuscadorBM25(Path(ruta_normas))
        self.chunks = self.bm25.chunks
        nombre, revision, self.prefijo_consulta, prefijo_pasaje = MODELOS[modelo]
        self.modelo = SentenceTransformer(nombre, revision=revision, device="cpu")
        self.vectores = self.modelo.encode([prefijo_pasaje + c.texto for c in self.chunks], normalize_embeddings=True)

    def ranking_bm25(self, consulta: str) -> list[int]:
        palabras = normalizar(consulta)
        puntajes = [(self.bm25.puntaje(palabras, i), i) for i in range(len(self.chunks))]
        return [i for _, i in sorted(puntajes, key=lambda x: (-x[0], x[1]))]

    def ranking_denso(self, consulta: str) -> list[int]:
        vector = self.modelo.encode(self.prefijo_consulta + consulta, normalize_embeddings=True)
        similitudes = self.vectores @ vector
        return sorted(range(len(self.chunks)), key=lambda i: (-similitudes[i], i))

    def recuperar(self, consulta: str, k: int):
        if self.modo == "bm25":
            orden = self.ranking_bm25(consulta)
        elif self.modo == "denso":
            orden = self.ranking_denso(consulta)
        else:
            puntajes = [0.0] * len(self.chunks)
            for ranking in (self.ranking_bm25(consulta), self.ranking_denso(consulta)):
                for rango, i in enumerate(ranking):
                    puntajes[i] += 1 / (RRF_K + rango + 1)
            orden = sorted(range(len(self.chunks)), key=lambda i: (-puntajes[i], i))
        return [self.chunks[i] for i in orden[:k]]
