"""Parte 3: optimiza el mensaje de sistema con GEPA, con el modelo sin entrenar.

GEPA prueba variantes del mensaje de sistema: corre el agente con cada una, mira
en qué controles falla y le pide a un modelo "reflector" que proponga la
siguiente. El reflector es la misma Gemma del agente, para no pagar una API.

Los casos salen de ``admision.generador`` con una semilla fija y se etiquetan
con ``curado.etiquetar``. Los 50 casos de práctica no se usan: quedan para
medir el antes y el después. Cada caso se juega con una de las normas original,
b o c, en rotación, para que el prompt no aprenda ningún número.

El puntaje de un caso es la fracción de los 9 controles que pasa (``parcial``
del comparador del kit), así GEPA distingue una ficha casi bien de una vacía.

Corre en GPU (vLLM):

    uv run python -m prompt.optimizar --kit <ruta al kit> --salida corridas/gepa

Deja en ``--salida`` los registros de GEPA y ``resultado.json``, y escribe el
mensaje de sistema ganador en ``prompt/sistema_optimizado.txt``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import gepa
from admision.comparar import comparar
from admision.entorno import Entorno, VistaDelAgente
from admision.generador import generar
from gepa.core.adapter import EvaluationBatch

import entrega
from curado.etiquetar import esperada
from curado.reglas import cargar_parametros
from prompt.agente import INSTRUCCIONES_CATEDRA, AgenteConPrompt, sistema_con

VERSIONES = ("original", "b", "c")
RUTA_PROMPT = Path(__file__).parent / "sistema_optimizado.txt"
# Los casos rotan entre tres versiones de las normas y el test usa otras: un número
# escrito en el prompt falla en las demás versiones.
NOTA_NUMEROS = ("\n(Los plazos, edades y demás valores cambian entre versiones de las normas: el agente los tiene "
                "que buscar con buscar_normativa. No escribas valores numéricos de las normas en el prompt. "
                "La lista de herramientas con sus argumentos y el formato JSON se agregan aparte, después de "
                "estas instrucciones, y no se cambian: escribí solo el rol y la estrategia.)")


def armar_casos(kit: Path, semilla: int, n: int) -> list[dict]:
    """Casos generados, cada uno con su versión de normas y su ficha esperada."""
    parametros = {v: cargar_parametros(kit / "normas" / v) for v in VERSIONES}
    casos = []
    for i, caso in enumerate(generar(semilla=semilla, n=n, prefijo="opt")):
        version = VERSIONES[i % len(VERSIONES)]
        casos.append({"caso": caso, "version": version, "esperada": esperada(caso, parametros[version])})
    return casos


class AdaptadorAdmision:
    """Conecta el agente con GEPA: ``evaluate`` juega un lote y ``make_reflective_dataset`` arma la devolución."""

    # None: GEPA usa su propuesta por defecto, que le pasa la devolución al reflector.
    propose_new_texts = None

    def __init__(self, modelo_lote, buscadores: dict):
        self.modelo_lote = modelo_lote
        self.buscadores = buscadores

    def evaluate(self, batch, candidate, capture_traces=False):
        entornos = [Entorno(d["caso"], self.buscadores[d["version"]]) for d in batch]
        vistas = [VistaDelAgente(e.paciente_id, e.paso) for e in entornos]
        AgenteConPrompt(self.modelo_lote, sistema_con(candidate["instrucciones"])).jugar_lote(vistas)
        resultados = [comparar(d["esperada"], e.decision, e.log) for d, e in zip(batch, entornos, strict=True)]
        trazas = [{"log": e.log, "resultado": r} for e, r in zip(entornos, resultados, strict=True)]
        return EvaluationBatch(outputs=resultados, scores=[r["parcial"] for r in resultados],
                               trajectories=trazas if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        registros = []
        for traza in eval_batch.trajectories:
            r = traza["resultado"]
            llamadas = [f"{x['herramienta']}({json.dumps(x['argumentos'], ensure_ascii=False)}) -> "
                        f"{str(x['observacion'])[:800]}" for x in traza["log"]]
            if r["obtenida"] is None:
                devolucion = "No registró la ficha: se quedó sin turnos o no respondió con JSON válido."
            else:
                fallas = [f"{k}: registró {r['obtenida'].get(k)!r}, correspondía {r['esperada'][k]!r}"
                          for k, ok in r["controles"].items() if not ok and k != "verificacion"]
                if not r["controles"]["verificacion"]:
                    fallas.append("verificacion: no verificó la afiliación con la entidad y el número correctos, "
                                  "o verificó una entidad que no correspondía")
                devolucion = "Todos los controles bien." if not fallas else "Errores:\n" + "\n".join(fallas)
            devolucion += NOTA_NUMEROS
            registros.append({"Inputs": {"llamadas": "\n".join(llamadas)},
                              "Generated Outputs": json.dumps(r["obtenida"], ensure_ascii=False),
                              "Feedback": devolucion})
        return {"instrucciones": registros}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--n-entrenamiento", type=int, default=60)
    ap.add_argument("--n-validacion", type=int, default=40)
    ap.add_argument("--max-llamadas", type=int, default=600, help="presupuesto de GEPA, en casos jugados")
    a = ap.parse_args()

    casos = armar_casos(a.kit, a.semilla, a.n_entrenamiento + a.n_validacion)
    entrenamiento, validacion = casos[:a.n_entrenamiento], casos[a.n_entrenamiento:]
    buscadores = {v: entrega.construir_buscador(a.kit / "normas" / v) for v in VERSIONES}
    llm = entrega.cargar_modelo()
    reflector_lote = entrega.modelo_lote_de(llm, max_tokens=4096)

    def reflector(prompt):
        mensajes = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
        return reflector_lote([mensajes])[0]

    inicial = sistema_con(INSTRUCCIONES_CATEDRA)
    resultado = gepa.optimize(
        seed_candidate={"instrucciones": INSTRUCCIONES_CATEDRA},
        trainset=entrenamiento,
        valset=validacion,
        adapter=AdaptadorAdmision(entrega.modelo_lote_de(llm), buscadores),
        reflection_lm=reflector,
        max_metric_calls=a.max_llamadas,
        run_dir=str(a.salida),
        seed=a.semilla,
    )

    ganador = sistema_con(resultado.best_candidate["instrucciones"])
    RUTA_PROMPT.write_text(ganador, encoding="utf-8")
    (a.salida / RUTA_PROMPT.name).write_text(ganador, encoding="utf-8")
    tokenizador = llm.get_tokenizer()
    resumen = {
        "semilla": a.semilla,
        "casos_entrenamiento": len(entrenamiento),
        "casos_validacion": len(validacion),
        "max_llamadas": a.max_llamadas,
        "puntaje_validacion_por_candidato": resultado.val_aggregate_scores,
        "mejor_candidato": resultado.best_idx,
        "tokens_prompt_inicial": len(tokenizador.encode(inicial)),
        "tokens_prompt_optimizado": len(tokenizador.encode(ganador)),
    }
    (a.salida / "resultado.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
