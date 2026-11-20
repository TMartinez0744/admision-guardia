"""Recalcula desde el historial la evidencia de las dos costumbres de ``costumbres.md``.

    uv run python -m curado.evidencia --kit ../talksmith-ing/missions/TPFinal

Los números de ``costumbres.md`` (operadores que siguen cada costumbre, el corte
de edad del voluntariado, cuántas filas con dos credenciales verifican la
prepaga) salen de acá. No escribe archivos: solo imprime.
"""

from __future__ import annotations

import argparse
import collections
from pathlib import Path

from curado.clasificar import KIT, SI, leer_historial
from curado.costumbres import aviso_al_voluntariado, entidad_a_verificar
from curado.reglas import credenciales_de, texto_de

# Las franjas de edad de la tabla de costumbres.md: justo debajo y justo encima del corte de 75.
FRANJAS = ((70, 74), (75, 80))


def avisa(fila: dict) -> bool:
    """Lo que anotó el operador en ``aviso_al_voluntariado``."""
    return fila["aviso_al_voluntariado"] == SI


def evidencia_voluntariado(filas: list[dict]) -> dict:
    """Costumbre 1: quién la sigue sin excepciones, quién se aparta y el corte de edad.

    Se miran todas las filas del historial, también las que son error por otro campo:
    el aviso al voluntariado no depende de ninguna norma.
    """
    desvios = collections.Counter()
    filas_por_operador = collections.Counter()
    for fila in filas:
        filas_por_operador[fila["operador"]] += 1
        if avisa(fila) != aviso_al_voluntariado(fila):
            desvios[fila["operador"]] += 1

    cumplen = sorted(op for op in filas_por_operador if desvios[op] == 0)
    franjas = {}
    for desde, hasta in FRANJAS:
        en_franja = [
            f for f in filas
            if f["operador"] in cumplen and desde <= int(f["edad"]) <= hasta and not texto_de(f, "acompanante")
        ]
        franjas[(desde, hasta)] = (len(en_franja), sum(avisa(f) for f in en_franja))

    return {
        "filas": len(filas),
        "con_aviso": sum(avisa(f) for f in filas),
        "operadores": len(filas_por_operador),
        "cumplen": cumplen,
        "filas_de_los_que_cumplen": sum(filas_por_operador[op] for op in cumplen),
        "desvios_por_operador": dict(desvios.most_common()),
        "franjas": franjas,
    }


def evidencia_prepaga(filas: list[dict]) -> dict:
    """Costumbre 2: en las filas con dos credenciales, cuántas verificaron la prepaga y quién no."""
    con_dos = [f for f in filas if entidad_a_verificar(f)]
    posicion = collections.Counter()
    for fila in con_dos:
        tipos = [tipo for _, tipo, _ in credenciales_de(fila)]
        if "prepaga" in tipos:
            posicion["primera" if tipos.index("prepaga") == 0 else "segunda"] += 1
    se_apartan = [f for f in con_dos if texto_de(f, "entidad_verificada") != entidad_a_verificar(f)]
    return {
        "con_dos_credenciales": len(con_dos),
        "cumplen": len(con_dos) - len(se_apartan),
        "prepaga_primera": posicion["primera"],
        "prepaga_segunda": posicion["segunda"],
        "se_apartan": [f["id"] for f in se_apartan],
        "se_apartan_por_operador": dict(collections.Counter(f["operador"] for f in se_apartan).most_common()),
    }


def informe(voluntariado: dict, prepaga: dict) -> list[str]:
    """Las líneas que imprime el script, en el orden de costumbres.md."""
    v, p = voluntariado, prepaga
    lineas = [
        "Costumbre 1: aviso al voluntariado con 75 años o más y sin acompañante",
        f"  filas con aviso: {v['con_aviso']} de {v['filas']} ({v['con_aviso'] / v['filas']:.1%})",
        f"  la cumplen sin excepciones: {len(v['cumplen'])} de {v['operadores']} operadores, "
        f"{v['filas_de_los_que_cumplen']} filas",
        f"  se apartan: {sum(v['desvios_por_operador'].values())} filas",
    ]
    lineas += [f"    {op}: {n}" for op, n in v["desvios_por_operador"].items()]
    lineas.append("  sin acompañante, entre los operadores que la cumplen:")
    lineas += [f"    {desde} a {hasta} años: {con_aviso} de {n} con aviso"
               for (desde, hasta), (n, con_aviso) in v["franjas"].items()]

    total = p["con_dos_credenciales"]
    lineas += [
        "",
        "Costumbre 2: con dos credenciales se verifica la prepaga",
        f"  verificaron la prepaga: {p['cumplen']} de {total}" + (f" ({p['cumplen'] / total:.1%})" if total else ""),
        f"  prepaga primera: {p['prepaga_primera']}, prepaga segunda: {p['prepaga_segunda']}",
        f"  se apartan: {', '.join(p['se_apartan']) or 'ninguna'}",
    ]
    lineas += [f"    {op}: {n}" for op, n in p["se_apartan_por_operador"].items()]
    return lineas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", default=str(KIT))
    args = parser.parse_args()

    filas = leer_historial(Path(args.kit))
    print("\n".join(informe(evidencia_voluntariado(filas), evidencia_prepaga(filas))))


if __name__ == "__main__":
    main()
