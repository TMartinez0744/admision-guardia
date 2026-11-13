"""El agente de ejemplo de la cátedra con el mensaje de sistema como parámetro.

``admision.ejemplo.AgenteJSON`` arma siempre su propio mensaje de sistema. Para
probar y optimizar otros (Parte 3) se reemplaza solo ese mensaje; el resto del
protocolo (una llamada en JSON por turno, el resultado como mensaje del usuario)
queda igual al de la cátedra.
"""

from admision.ejemplo import AgenteJSON, _Partida, mensaje_de_sistema

# El mensaje de la cátedra tiene cuatro bloques separados por una línea en blanco:
# el rol, las herramientas con sus argumentos, el formato JSON y las normas que aplican.
_BLOQUES = mensaje_de_sistema().split("\n\n")
# Herramientas y formato: el contrato con el entorno. No se optimiza.
CONTRATO = "\n\n".join(_BLOQUES[1:3])
# Rol y estrategia: lo único que reescribe la optimización de prompt.
INSTRUCCIONES_CATEDRA = "\n\n".join([_BLOQUES[0], _BLOQUES[3]])


def sistema_con(instrucciones: str) -> str:
    """El mensaje de sistema completo: las instrucciones y después el contrato fijo."""
    return f"{instrucciones.strip()}\n\n{CONTRATO}"


class AgenteConPrompt(AgenteJSON):
    def __init__(self, modelo_lote, sistema: str | None = None, **kwargs):
        super().__init__(modelo_lote, **kwargs)
        self.sistema = sistema or mensaje_de_sistema()

    def jugar_lote(self, entornos: list) -> list[list[dict]]:
        partidas = [_Partida(e, self.max_turnos, self.max_sin_json) for e in entornos]
        for partida in partidas:
            partida.mensajes[0]["content"] = self.sistema
        while activas := [x for x in partidas if x.activa]:
            for partida, respuesta in zip(activas, self.modelo_lote([x.mensajes for x in activas]), strict=True):
                partida.recibir(respuesta)
        return [x.mensajes for x in partidas]
