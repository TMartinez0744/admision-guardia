"""Baja de W&B la curva de pérdida de cada entrenamiento y la guarda en el repo.

Escribe ``evaluacion/entrenamientos/<corrida>/perdida.json`` con un punto por cada
registro de W&B (paso, época, pérdida, acierto de tokens y tasa de aprendizaje).
Así ``evaluacion.graficos`` puede dibujar las curvas sin acceso a W&B.

    uv run python -m evaluacion.historia_wandb   # necesita WANDB_API_KEY
"""

import json
from pathlib import Path

import wandb

PROYECTO = "pdelaguila-universidad-austral/admision-guardia"
CORRIDAS = ["sft-reales", "sft-mixto", "sft-mixto-catedra", "sft-mixto-final"]
CLAVES = {"train/global_step": "paso", "train/epoch": "epoca", "train/loss": "perdida",
          "train/mean_token_accuracy": "acierto_tokens", "train/learning_rate": "tasa"}


def main() -> None:
    corridas = {r.name: r for r in wandb.Api().runs(PROYECTO)}
    for nombre in CORRIDAS:
        historia = corridas[nombre].history(keys=list(CLAVES), pandas=False)
        puntos = [{CLAVES[k]: fila[k] for k in CLAVES} for fila in historia]
        salida = Path("evaluacion/entrenamientos") / nombre / "perdida.json"
        salida.write_text(json.dumps({"corrida": nombre, "wandb": corridas[nombre].url, "puntos": puntos},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
        print(nombre, len(puntos), "puntos")


if __name__ == "__main__":
    main()
