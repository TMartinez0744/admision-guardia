"""Clasifica cada fila del historial como correcta, error o ruido.

    uv run python -m curado.clasificar --kit ../talksmith-ing/missions/TPFinal

Criterio:
  error   -> la fila viola una norma escrita;
  ruido   -> hace algo que las normas no cubren, distinto de lo que hacen casi
             todos los operadores en esa situación;
  correcta-> todas las demas.

Escribe ``historial_clasificado.csv`` con las columnas ``id,tipo`` e imprime el
detalle de qué norma o qué costumbre se incumplió en cada caso.
"""

from __future__ import annotations

import argparse
import collections
import csv
from pathlib import Path

from curado.costumbres import aviso_al_voluntariado, entidad_a_verificar
from curado.reglas import cargar_parametros, ficha_esperada

SI = "sí"

# Qué norma respalda cada campo, para poder decir por qué la fila es un error.
NORMA_DEL_CAMPO = {
    "registro": "NOR-ADM-01 §2-§3 / NOR-ADM-03 §1",
    "numero_documento": "NOR-ADM-01 §2 / NOR-ADM-03 §1",
    "box_antes_del_registro": "NOR-ADM-01 §4 / NOR-ADM-02 §1",
    "circuito": "NOR-TDE-01 a NOR-TDE-03",
    "plazo_circuito_min": "NOR-TDE-01 a NOR-TDE-04",
    "cobertura": "NOR-COB-02 §5 / NOR-COB-03 §1 / NOR-COB-04 §1",
    "entidad_a_notificar": "NOR-COB-02 §3 / NOR-COB-03 §4 / NOR-COB-04 §1",
}


def ficha_registrada(fila: dict) -> dict:
    return {
        "registro": fila["registro"] or None,
        "numero_documento": fila["numero_documento"].strip() or None,
        "box_antes_del_registro": fila["box_antes_del_registro"] == SI,
        "circuito": fila["circuito"] or None,
        "plazo_circuito_min": int(fila["plazo_circuito_min"]) if fila["plazo_circuito_min"].strip() else None,
        "cobertura": fila["cobertura"] or None,
        "entidad_a_notificar": fila["entidad_a_notificar"].strip() or None,
    }


def clasificar(fila: dict, parametros: dict[str, int]) -> tuple[str, list[str]]:
    """(tipo, motivos). Un error gana sobre el ruido."""
    esperada, registrada = ficha_esperada(fila, parametros), ficha_registrada(fila)
    errores = [
        f"{campo}: {registrada[campo]!r} en vez de {esperada[campo]!r} ({NORMA_DEL_CAMPO[campo]})"
        for campo in NORMA_DEL_CAMPO
        if esperada[campo] != registrada[campo]
    ]
    if errores:
        return "error", errores

    ruidos = []
    if (fila["aviso_al_voluntariado"] == SI) != aviso_al_voluntariado(fila):
        ruidos.append(
            f"aviso_al_voluntariado: {fila['aviso_al_voluntariado']!r} con "
            f"{fila['edad']} anios y acompaniante {'si' if fila['acompanante'].strip() else 'no'} "
            "(costumbre 1)"
        )
    esperada_verificar = entidad_a_verificar(fila)
    if esperada_verificar and fila["entidad_verificada"].strip() != esperada_verificar:
        ruidos.append(
            f"entidad_verificada: {fila['entidad_verificada']!r} en vez de "
            f"{esperada_verificar!r} (costumbre 2)"
        )
    return ("ruido", ruidos) if ruidos else ("correcta", [])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", default="../talksmith-ing/missions/TPFinal")
    parser.add_argument("--normas", default=None, help="por defecto, <kit>/normas/original")
    parser.add_argument("--salida", default="historial_clasificado.csv")
    args = parser.parse_args()

    kit = Path(args.kit)
    normas = Path(args.normas) if args.normas else kit / "normas" / "original"
    parametros = cargar_parametros(normas)
    filas = list(csv.DictReader((kit / "historial" / "historial.csv").open(encoding="utf-8")))

    resultados, motivos_por_tipo = [], collections.defaultdict(collections.Counter)
    por_operador = collections.defaultdict(collections.Counter)
    for fila in filas:
        tipo, motivos = clasificar(fila, parametros)
        resultados.append((fila["id"], tipo))
        por_operador[fila["operador"]][tipo] += 1
        for motivo in motivos:
            motivos_por_tipo[tipo][motivo.split(":")[0]] += 1

    with Path(args.salida).open("w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["id", "tipo"])
        escritor.writerows(resultados)

    cuenta = collections.Counter(t for _, t in resultados)
    print(f"{len(filas)} filas -> {args.salida}")
    for tipo in ("correcta", "error", "ruido"):
        print(f"  {tipo:9s} {cuenta[tipo]:5d}  ({cuenta[tipo]/len(filas):5.1%})")
    for tipo in ("error", "ruido"):
        print(f"\n  {tipo} por campo:")
        for campo, n in motivos_por_tipo[tipo].most_common():
            print(f"    {campo:24s} {n:4d}")
    print("\n  operadores con mas ruido:")
    for operador, c in sorted(por_operador.items(), key=lambda x: -x[1]["ruido"])[:5]:
        print(f"    {operador}  ruido {c['ruido']:3d}  error {c['error']:3d}  correcta {c['correcta']:3d}")


if __name__ == "__main__":
    main()
