"""Contrato de la entrega.

Punto de entrada unico: de aca salen el punto de control de Hugging Face, el
prompt optimizado y el buscador.

Libres: el mensaje de sistema, el formato de los mensajes al modelo, la cantidad
de busquedas y la estrategia.
Fijos: los nombres y argumentos de las cinco herramientas y los 8 campos de la
ficha (ver admision/ejemplo.py).
"""

from pathlib import Path

from buscador.bm25 import BuscadorBM25

# El modelo se baja de este repositorio, con HF_TOKEN tomado del entorno.
# La revision es el commit o la etiqueta exacta del punto de control final.
MODELO_HF = "<usuario-o-grupo>/<repositorio-del-modelo>"
REVISION_HF = "<commit o tag>"


def construir_buscador(ruta_normas):
    """Arma el buscador con las normas que estan en ``ruta_normas``.

    Los numeros de las normas cambian entre versiones, asi que el buscador se
    arma siempre con la carpeta que recibe, que es una copia aparte.

    Devuelve un objeto con:
      - ``recuperar(consulta, k)``: lista de mas a menos relevante, de objetos
        con atributo ``texto`` (o strings).
      - ``k_entorno`` (optativo): cuantos resultados devuelve la herramienta
        ``buscar_normativa``. Si no esta definido, son 2.

    Si una busqueda falla, esa llamada vuelve como error y el caso sigue.
    """
    return BuscadorBM25(Path(ruta_normas))


def construir_agente():
    """Carga el modelo una sola vez y devuelve el agente.

    Devuelve un objeto con ``jugar_lote(entornos)``. Cada entorno tiene:
      - ``paciente_id``
      - ``paso(herramienta, argumentos)``, que devuelve la observacion y si el
        caso termino.

    El agente juega cada caso llamando a ``paso`` hasta ``registrar_decision`` y
    devuelve, por caso y en el mismo orden que ``entornos``, la conversacion
    completa con el modelo: cada mensaje que entro y cada uno que salio. Esa
    conversacion es la que se usa para medir el contexto, asi que tiene que
    estar completa.

    Tope: 40 llamadas a herramientas por caso. Al llegar a 40 sin registrar la
    ficha, el caso termina sin ficha.

    Herramientas: leer_triage, preguntar, verificar_afiliacion,
    buscar_normativa, registrar_decision.

    En operacion el agente no llama a ningun servicio externo.
    """
    raise NotImplementedError
