"""Buscador BM25 sobre las normas, partidas en parrafos.

El corpus se parte por parrafo (cada "§N.") en vez de por seccion entera: la
evidencia que mide `admision.evaluar_rag` son oraciones sueltas, asi que un
chunk mas chico sube la precision sin perder recall, mientras el parrafo entre
completo.

Cada chunk lleva el encabezado de su seccion, para que el agente sepa de donde
sale, y la linea de valores de los parametros que ese parrafo cita. Los valores
salen siempre de la carpeta que se recibe, porque cambian entre versiones.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from admision.normas import cargar_normas, cargar_parametros, linea_de_valores

K1 = 1.5
B = 0.75

PALABRAS_VACIAS = {
    "a", "al", "ante", "antes", "como", "con", "contra", "cual", "cuando", "de", "del", "desde", "donde", "dos",
    "el", "ella", "ellas", "ellos", "en", "entre", "era", "es", "esa", "ese", "eso", "esta", "estan", "este",
    "esto", "estos", "fue", "ha", "hace", "hacer", "hasta", "hay", "la", "las", "le", "les", "lo", "los", "mas",
    "me", "mi", "mientras", "muy", "ni", "no", "o", "para", "pero", "por", "porque", "que", "qué", "se", "segun",
    "ser", "si", "sin", "sobre", "son", "su", "sus", "tambien", "tengo", "tiene", "todo", "un", "una", "uno",
    "y", "ya",
}

PATRON_PARRAFO = re.compile(r"(?=^§\d+\.)", re.MULTILINE)
PATRON_PALABRA = re.compile(r"[a-z0-9áéíóúñü-]+")


def normalizar(texto: str) -> list[str]:
    """Minusculas, sin tildes, sin palabras vacias."""
    plano = unicodedata.normalize("NFD", texto.lower())
    plano = "".join(c for c in plano if unicodedata.category(c) != "Mn")
    return [p for p in PATRON_PALABRA.findall(plano) if p not in PALABRAS_VACIAS and len(p) > 1]


@dataclass(frozen=True)
class Chunk:
    seccion: str
    texto: str


def partir(ruta_normas: Path) -> list[Chunk]:
    """Un chunk por parrafo, con el encabezado de la seccion y sus valores."""
    valores = cargar_parametros(ruta_normas)
    chunks: list[Chunk] = []
    for seccion in cargar_normas(ruta_normas):
        lineas = seccion.cuerpo.split("\n")
        encabezado = lineas[0].strip()
        resto = "\n".join(lineas[1:]).strip()
        parrafos = [p.strip() for p in PATRON_PARRAFO.split(resto) if p.strip()]
        if not parrafos:
            parrafos = [resto]
        for parrafo in parrafos:
            partes = [encabezado, parrafo]
            linea = linea_de_valores(parrafo, valores)
            if linea:
                partes.append(linea)
            chunks.append(Chunk(seccion.id, "\n\n".join(partes)))
    return chunks


class BuscadorBM25:
    def __init__(self, ruta_normas: Path, k_entorno: int = 2):
        self.k_entorno = k_entorno
        self.chunks = partir(Path(ruta_normas))
        self.tokens = [normalizar(c.texto) for c in self.chunks]
        self.largos = [len(t) for t in self.tokens]
        self.largo_medio = sum(self.largos) / len(self.largos)
        self.frecuencias = [Counter(t) for t in self.tokens]
        documentos_por_palabra = Counter(p for t in self.tokens for p in set(t))
        n = len(self.chunks)
        self.idf = {
            p: math.log(1 + (n - df + 0.5) / (df + 0.5))
            for p, df in documentos_por_palabra.items()
        }

    def puntaje(self, consulta: list[str], i: int) -> float:
        total = 0.0
        norma = K1 * (1 - B + B * self.largos[i] / self.largo_medio)
        for palabra in consulta:
            f = self.frecuencias[i].get(palabra, 0)
            if f:
                total += self.idf[palabra] * f * (K1 + 1) / (f + norma)
        return total

    def recuperar(self, consulta: str, k: int) -> list[Chunk]:
        palabras = normalizar(consulta)
        if not palabras:
            return []
        puntajes = [(self.puntaje(palabras, i), i) for i in range(len(self.chunks))]
        puntajes.sort(key=lambda x: (-x[0], x[1]))
        return [self.chunks[i] for puntaje, i in puntajes[:k] if puntaje > 0]
