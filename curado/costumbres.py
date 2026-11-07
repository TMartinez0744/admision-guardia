"""Las costumbres del hospital: lo que hacen casi todos los operadores en
situaciones que ninguna norma escrita cubre.

Apartarse de una costumbre es ruido, no error. Cada una se derivó del historial
y la evidencia está en ``costumbres.md``.
"""

from __future__ import annotations

from curado.reglas import credenciales_de

EDAD_VOLUNTARIADO = 75


def aviso_al_voluntariado(fila: dict) -> bool:
    """Costumbre 1: se avisa al voluntariado con 75 años o más y sin acompañante.

    Ninguna norma menciona al voluntariado. El Servicio Social de NOR-COB-03 §3
    es otra cosa y depende de la cobertura, no de la edad.
    """
    return int(fila["edad"]) >= EDAD_VOLUNTARIADO and not fila["acompanante"].strip()


def entidad_a_verificar(fila: dict) -> str | None:
    """Costumbre 2: con dos credenciales se verifica la prepaga, no la obra social.

    NOR-COB-02 §2 manda verificar la afiliación, pero no dice cuál cuando el
    paciente presenta más de una credencial.
    """
    credenciales = credenciales_de(fila)
    if len(credenciales) < 2:
        return None
    for nombre, tipo, _ in credenciales:
        if tipo == "prepaga":
            return nombre
    return credenciales[0][0]
