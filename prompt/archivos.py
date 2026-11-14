"""Genera los archivos de prompt que no salen de GEPA.

- ``sistema_catedra.txt``: el mensaje de sistema del agente de ejemplo de la cátedra, tal cual.
- ``sistema_inicial.txt``: el mismo texto con el rol y las normas antes del contrato de
  herramientas; es el punto de partida de GEPA (``prompt.optimizar``).
- ``sistema_final.txt``: ``sistema_optimizado.txt`` (la salida de GEPA) con la regla de
  ``aviso_al_voluntariado`` reemplazada por la costumbre 1 de ``costumbres.md``. GEPA había escrito
  que el aviso es falso salvo que una norma diga lo contrario, y ninguna norma lo regula
  (ver INFORME, Parte 4).

    uv run python -m prompt.archivos
"""

from pathlib import Path

from admision.ejemplo import mensaje_de_sistema

from prompt.agente import INSTRUCCIONES_CATEDRA, sistema_con

CARPETA = Path(__file__).parent

REGLA_GEPA = ("    *   **`aviso_al_voluntariado`**: Debe ser `False` a menos que una norma específica indique lo "
              "contrario. **(Corrección basada en feedback: Revisar si alguna norma específica obliga a "
              "establecerlo en `True`).**")
COSTUMBRE = ("    *   **`aviso_al_voluntariado`**: No lo regula ninguna norma: es una costumbre del hospital. Es "
             "`True` si el paciente tiene 75 años o más y no tiene acompañante; en cualquier otro caso, `False`.")


def main() -> None:
    (CARPETA / "sistema_catedra.txt").write_text(mensaje_de_sistema(), encoding="utf-8")
    (CARPETA / "sistema_inicial.txt").write_text(sistema_con(INSTRUCCIONES_CATEDRA), encoding="utf-8")
    optimizado = (CARPETA / "sistema_optimizado.txt").read_text(encoding="utf-8")
    if optimizado.count(REGLA_GEPA) != 1:
        raise ValueError("sistema_optimizado.txt no tiene la regla de GEPA esperada")
    (CARPETA / "sistema_final.txt").write_text(optimizado.replace(REGLA_GEPA, COSTUMBRE), encoding="utf-8")
    print("prompt/sistema_catedra.txt, prompt/sistema_inicial.txt y prompt/sistema_final.txt generados")


if __name__ == "__main__":
    main()
