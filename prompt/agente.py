"""El agente de ejemplo de la cátedra con el mensaje de sistema como parámetro.

``admision.ejemplo.AgenteJSON`` arma siempre su propio mensaje de sistema. Para
probar y optimizar otros (Parte 3) se reemplaza solo ese mensaje; el resto del
protocolo (una llamada en JSON por turno, el resultado como mensaje del usuario)
queda igual al de la cátedra.
"""

from admision.ejemplo import AgenteJSON, _Partida, mensaje_de_sistema


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
