"""La ficha esperada de un caso generado, con las reglas y costumbres del curado.

``admision.generador`` da casos sin respuesta. Para optimizar el prompt (Parte 3)
sin tocar los 50 casos de práctica, que se usan para reportar, cada caso
generado se etiqueta con las mismas reglas con que se clasificó el historial:
el caso se pasa al formato de una fila del historial y se le aplican
``curado.reglas`` y ``curado.costumbres``.

Devuelve lo mismo que una línea de ``esperadas-<versión>.jsonl``, así el
comparador del kit la puede usar sin cambios.

    uv run python -m curado.etiquetar --kit <ruta al kit>

corre el control: etiqueta los 50 casos de práctica y los compara con las
fichas esperadas de la cátedra, con las normas original, b y c.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from admision.casos import Caso, cargar_casos, cargar_esperadas

from curado.costumbres import EDAD_VOLUNTARIADO
from curado.reglas import cargar_parametros, ficha_esperada

TIPO_TEXTO = {"obra_social": "obra social", "prepaga": "prepaga"}


def _credencial_texto(credencial: tuple[str, str, str]) -> str:
    tipo, entidad, numero = credencial
    return f"{entidad} ({TIPO_TEXTO[tipo]}) {numero}"


def _a_verificar(caso: Caso) -> tuple[str, str, str] | None:
    """La cobertura (no ART) que corresponde verificar.

    Con credenciales, la presentada; con dos, la prepaga (costumbre 2). Sin
    credenciales, la que declara quien puede contestar; si el paciente no puede
    responder y no tiene acompañante, no se le pregunta a nadie (NOR-COB-01 §3).
    """
    if len(caso.credenciales) >= 2:
        return next(c for c in caso.credenciales if c[0] == "prepaga")
    if caso.credenciales:
        return caso.credenciales[0]
    if caso.puede_responder or caso.acompanante:
        return caso.declarada
    return None


def como_fila(caso: Caso) -> dict:
    """El caso con las columnas del historial que usan las reglas."""
    credencial = _a_verificar(caso)
    respuesta = ""
    if credencial:
        respuesta = "activa" if caso.afiliaciones[f"{credencial[1]}|{credencial[2]}"] else "inactiva"
    return {
        "edad": caso.edad,
        "nivel": caso.nivel,
        "motivo": caso.motivo,
        "sospecha_sepsis": caso.sepsis,
        "llegada": caso.llegada,
        "documento_tipo": caso.documento_tipo or "",
        "documento_numero": caso.documento_numero or "",
        "credenciales": "; ".join(_credencial_texto(c) for c in caso.credenciales),
        "acompanante": caso.acompanante or "",
        "lesion_trabajo": caso.trabajo or "no",
        "cobertura_declarada": _credencial_texto(credencial) if credencial and not caso.credenciales else "",
        "art_declarada": f"{caso.art[0]} CUIL {caso.art[1]}" if caso.art else "",
        "entidad_verificada": credencial[1] if credencial else "",
        "respuesta_verificacion": respuesta,
    }


def esperada(caso: Caso, parametros: dict[str, int]) -> dict:
    """La ficha y la verificación que corresponden, en el formato de las esperadas del kit."""
    fila = como_fila(caso)
    ficha = ficha_esperada(fila, parametros)
    ficha["aviso_al_voluntariado"] = caso.edad >= EDAD_VOLUNTARIADO and not caso.acompanante
    credencial = _a_verificar(caso)
    otras = [c[1] for c in caso.credenciales if c != credencial]
    if caso.trabajo:
        # Accidente de trabajo: se verifica la ART con el CUIL, no la cobertura propia (NOR-COB-02 §5).
        requerida = list(caso.art)
        prohibidas = [credencial[1]] + otras if credencial else otras
    else:
        requerida = [credencial[1], credencial[2]] if credencial else None
        prohibidas = otras
    return {"caso": caso.id, "ficha": ficha, "verificacion": {"requerida": requerida, "prohibidas": prohibidas}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", type=Path, required=True)
    a = ap.parse_args()
    casos = cargar_casos(a.kit / "practica" / "casos.jsonl")
    for version in ("original", "b", "c"):
        parametros = cargar_parametros(a.kit / "normas" / version)
        oficiales = cargar_esperadas(a.kit / "practica" / f"esperadas-{version}.jsonl")
        distintos = []
        for caso in casos:
            nuestra, oficial = esperada(caso, parametros), oficiales[caso.id]
            campos = [k for k in oficial["ficha"] if nuestra["ficha"][k] != oficial["ficha"][k]]
            if nuestra["verificacion"] != oficial["verificacion"]:
                campos.append("verificacion")
            if campos:
                distintos.append((caso.id, campos))
        print(f"{version}: {len(casos) - len(distintos)}/{len(casos)} iguales a la esperada de la cátedra")
        for id_caso, campos in distintos:
            print(f"  {id_caso}: {', '.join(campos)}")


if __name__ == "__main__":
    main()
