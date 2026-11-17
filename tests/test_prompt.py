"""``prompt``: los archivos de prompt guardados y el agente con el mensaje de sistema como parámetro.

Necesita el kit instalado. El agente se prueba con un modelo de juguete que contesta llamadas fijas.
"""

import json
import re
from pathlib import Path

import pytest

pytest.importorskip("admision")

from admision.ejemplo import HERRAMIENTAS, mensaje_de_sistema, primer_mensaje  # noqa: E402

from curado.costumbres import EDAD_VOLUNTARIADO  # noqa: E402
from prompt import archivos  # noqa: E402
from prompt.agente import CONTRATO, INSTRUCCIONES_CATEDRA, AgenteConPrompt, sistema_con  # noqa: E402

CARPETA = Path(archivos.__file__).parent


def leer(nombre: str) -> str:
    return (CARPETA / nombre).read_text(encoding="utf-8")


# --- El contrato y los archivos guardados ---------------------------------------------------------

def test_el_contrato_tiene_las_cinco_herramientas_y_sus_argumentos():
    for herramienta in HERRAMIENTAS:
        assert f"- {herramienta['nombre']}:" in CONTRATO
        for argumento in herramienta["argumentos"]:
            assert f'"{argumento}"' in CONTRATO


def test_contrato_e_instrucciones_reparten_el_mensaje_de_la_catedra_sin_perder_nada():
    bloques = mensaje_de_sistema().split("\n\n")
    assert sorted(f"{INSTRUCCIONES_CATEDRA}\n\n{CONTRATO}".split("\n\n")) == sorted(bloques)


def test_sistema_con_pone_las_instrucciones_antes_del_contrato():
    assert sistema_con("  Sos un operador.\n") == f"Sos un operador.\n\n{CONTRATO}"


@pytest.mark.parametrize("nombre", ["sistema_inicial.txt", "sistema_optimizado.txt", "sistema_final.txt"])
def test_los_prompts_conservan_el_contrato_fijo_al_final(nombre):
    # GEPA solo reescribe las instrucciones: el contrato con el entorno no puede cambiar.
    assert leer(nombre).endswith(CONTRATO)


def test_los_archivos_guardados_coinciden_con_los_que_genera_archivos():
    """Si alguien edita un prompt a mano o cambia el kit, ``uv run python -m prompt.archivos`` los regenera."""
    assert leer("sistema_catedra.txt") == mensaje_de_sistema()
    assert leer("sistema_inicial.txt") == sistema_con(INSTRUCCIONES_CATEDRA)
    assert leer("sistema_final.txt") == leer("sistema_optimizado.txt").replace(archivos.REGLA_GEPA, archivos.COSTUMBRE)


def test_el_prompt_final_cambia_solo_la_regla_del_voluntariado():
    optimizado, final = leer("sistema_optimizado.txt"), leer("sistema_final.txt")
    assert optimizado.count(archivos.REGLA_GEPA) == 1
    assert archivos.REGLA_GEPA not in final and archivos.COSTUMBRE in final
    assert optimizado.replace(archivos.REGLA_GEPA, "") == final.replace(archivos.COSTUMBRE, "")


def test_la_costumbre_del_prompt_usa_la_misma_edad_que_el_curado():
    assert re.findall(r"(\d+) años", archivos.COSTUMBRE) == [str(EDAD_VOLUNTARIADO)]


def test_archivos_rechaza_un_optimizado_sin_la_regla_de_gepa(tmp_path, monkeypatch):
    (tmp_path / "sistema_optimizado.txt").write_text("otro prompt", encoding="utf-8")
    monkeypatch.setattr(archivos, "CARPETA", tmp_path)
    with pytest.raises(ValueError, match="regla de GEPA"):
        archivos.main()


def test_entrega_usa_el_prompt_final():
    entrega = pytest.importorskip("entrega")
    assert Path(entrega.RUTA_PROMPT) == CARPETA / "sistema_final.txt"


# --- El agente ------------------------------------------------------------------------------------

class Entorno:
    def __init__(self, paciente_id):
        self.paciente_id = paciente_id
        self.llamadas = []

    def paso(self, herramienta, argumentos):
        self.llamadas.append(herramienta)
        return f"ok {herramienta}", herramienta == "registrar_decision"


def llamada(herramienta, **argumentos):
    return json.dumps({"herramienta": herramienta, "argumentos": argumentos})


class Modelo:
    """Contesta según cuántos mensajes tiene la conversación: lee el triage y después registra."""

    def __init__(self):
        self.lotes = []

    def __call__(self, conversaciones):
        self.lotes.append(conversaciones)
        return [llamada("leer_triage", paciente_id="P-1") if len(c) == 2 else llamada("registrar_decision")
                for c in conversaciones]


def test_el_agente_usa_el_mensaje_de_sistema_que_recibe():
    modelo = Modelo()
    conversaciones = AgenteConPrompt(modelo, "mi prompt").jugar_lote([Entorno("P-1"), Entorno("P-2")])
    assert all(c[0] == {"role": "system", "content": "mi prompt"} for c in conversaciones)
    assert all(c[0]["content"] == "mi prompt" for c in modelo.lotes[0])
    assert [c[1]["content"] for c in conversaciones] == [primer_mensaje("P-1"), primer_mensaje("P-2")]


def test_sin_mensaje_de_sistema_usa_el_de_la_catedra():
    conversacion, = AgenteConPrompt(Modelo()).jugar_lote([Entorno("P-1")])
    assert conversacion[0]["content"] == mensaje_de_sistema()


def test_el_agente_juega_hasta_registrar_la_ficha_y_devuelve_la_conversacion_completa():
    entorno = Entorno("P-1")
    conversacion, = AgenteConPrompt(Modelo(), "s").jugar_lote([entorno])
    assert entorno.llamadas == ["leer_triage", "registrar_decision"]
    assert [m["role"] for m in conversacion] == ["system", "user", "assistant", "user", "assistant"]
    assert conversacion[3]["content"] == "Resultado de leer_triage:\nok leer_triage"


def test_una_respuesta_sin_json_se_corrige_y_tres_seguidas_cortan_el_caso():
    entorno = Entorno("P-1")
    conversacion, = AgenteConPrompt(lambda cs: ["no sé"] * len(cs), "s").jugar_lote([entorno])
    assert entorno.llamadas == []
    assert sum(m["role"] == "assistant" for m in conversacion) == 3
