"""Contrato de la entrega.

Punto de entrada unico: de acá salen el punto de control de Hugging Face, el
prompt optimizado y el buscador.

Libres: el mensaje de sistema, el formato de los mensajes al modelo, la cantidad
de busquedas y la estrategia.
Fijos: los nombres y argumentos de las cinco herramientas y los 8 campos de la
ficha (ver admision/ejemplo.py).
"""

from pathlib import Path

from buscador.hibrido import BuscadorHibrido

# El modelo se baja de este repositorio, con HF_TOKEN tomado del entorno.
# La revision es el commit o la etiqueta exacta del punto de control final.
# Punto de control final: Gemma 4 E4B con SFT (LoRA fusionado), corrida
# sft-mixto-final (ver INFORME, Parte 4). Repositorio privado: hace falta HF_TOKEN.
MODELO_HF = "Pedro2204/admision-gemma4-e4b"
REVISION_HF = "671cca684d39f1e78a5856ae6414e3fff20e8a06"

# Mensaje de sistema: el optimizado por GEPA (Parte 3) con la regla del voluntariado
# corregida (Parte 4). Es el mismo con el que se entrenó el punto de control final.
RUTA_PROMPT = Path(__file__).parent / "prompt" / "sistema_final.txt"

# Contexto maximo por conversacion. Si una conversacion lo supera, vLLM falla.
MAX_CONTEXTO = 32768
# Fracción de la GPU para vLLM (pesos + caché). El resto queda para el buscador,
# que corre bge-m3 en la misma GPU (unos 2 GB).
MEMORIA_VLLM = 0.85
# Tokens maximos por respuesta del modelo: una llamada a herramienta en JSON.
MAX_RESPUESTA = 512


def construir_buscador(ruta_normas):
    """Arma el buscador con las normas que están en ``ruta_normas``.

    Los números de las normas cambian entre versiones, así que el buscador se
    arma siempre con la carpeta que recibe, que es una copia aparte.

    Devuelve un objeto con:
      - ``recuperar(consulta, k)``: lista de más a menos relevante, de objetos
        con atributo ``texto`` (o strings).
      - ``k_entorno`` (optativo): cuantos resultados devuelve la herramienta
        ``buscar_normativa``. Si no está definido, son 2.

    Si una busqueda falla, esa llamada vuelve como error y el caso sigue.
    """
    # Embeddings de bge-m3 sobre los párrafos, 3 por búsqueda: la mejor variante
    # de buscador.comparar (ver INFORME, Parte 2).
    return BuscadorHibrido(Path(ruta_normas), modelo="bge-m3", modo="denso", k_entorno=3)


def construir_agente():
    """Carga el modelo una sola vez y devuelve el agente.

    Devuelve un objeto con ``jugar_lote(entornos)``. Cada entorno tiene:
      - ``paciente_id``
      - ``paso(herramienta, argumentos)``, que devuelve la observacion y si el
        caso termino.

    El agente juega cada caso llamando a ``paso`` hasta ``registrar_decision`` y
    devuelve, por caso y en el mismo orden que ``entornos``, la conversación
    completa con el modelo: cada mensaje que entró y cada uno que salió. Esa
    conversación es la que se usa para medir el contexto, así que tiene que
    estar completa.

    Tope: 40 llamadas a herramientas por caso. Al llegar a 40 sin registrar la
    ficha, el caso termina sin ficha.

    Herramientas: leer_triage, preguntar, verificar_afiliacion,
    buscar_normativa, registrar_decision.

    En operacion el agente no llama a ningún servicio externo.

    El agente de ejemplo de la cátedra (protocolo JSON) sobre vLLM, con el
    mensaje de sistema de ``RUTA_PROMPT``. Decodificacion greedy (temperatura 0)
    para que la evaluacion sea reproducible. Para los experimentos, la variable
    de entorno ``ADMISION_PROMPT`` apunta a otro archivo de prompt.
    """
    import os

    from prompt.agente import AgenteConPrompt

    sistema = Path(os.environ.get("ADMISION_PROMPT", RUTA_PROMPT)).read_text(encoding="utf-8")
    return AgenteConPrompt(modelo_lote_de(cargar_modelo()), sistema)


def cargar_modelo():
    """El modelo en vLLM. Lo usan construir_agente y la optimización de prompt."""
    import os

    # vLLM arranca su motor en otro proceso. Por defecto lo crea con fork, y si el
    # proceso padre ya tocó CUDA (torch al armar el buscador) el hijo falla con
    # "CUDA error: initialization error". Con spawn el hijo arranca limpio.
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    # El muestreador de FlashInfer se compila al arrancar y necesita nvcc, que la
    # máquina puede no tener. Sin él, vLLM usa su muestreador de PyTorch.
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    from vllm import LLM

    # Para comparar puntos de control sin editar este archivo; la cátedra corre con los fijados arriba.
    modelo = os.environ.get("ADMISION_MODELO", MODELO_HF)
    revision = os.environ.get("ADMISION_REVISION", REVISION_HF)
    return LLM(model=modelo, revision=revision, dtype="bfloat16", max_model_len=MAX_CONTEXTO, seed=0,
               gpu_memory_utilization=MEMORIA_VLLM)


def modelo_lote_de(llm, max_tokens: int = MAX_RESPUESTA):
    """Una función que recibe conversaciones y devuelve una respuesta por cada una, greedy."""
    from vllm import SamplingParams

    parametros = SamplingParams(temperature=0, max_tokens=max_tokens)

    def modelo_lote(conversaciones):
        salidas = llm.chat(conversaciones, parametros, use_tqdm=False)
        return [s.outputs[0].text for s in salidas]

    return modelo_lote
