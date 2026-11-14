"""Sube los puntos de control intermedios de cada corrida a Hugging Face.

Trainer guardó un adaptador LoRA cada 100 pasos en ``<salida>/checkpoint-N``,
pero no los subió: la rama ``<corrida>-checkpoints`` no existía. Este script la
crea y sube cada ``checkpoint-N`` como carpeta, en un commit propio, y deja una
etiqueta ``<corrida>-checkpoint-N`` por punto de control.

    uv run modal run modal_app.py --comando "python -m entrenamiento.subir_checkpoints \
        --hub grupo11-admision-guardia/admision-gemma4-e4b --modelos /cache/modelos"

Necesita ``HF_TOKEN`` con permiso de escritura.
"""

import argparse
import json
from pathlib import Path

from huggingface_hub import HfApi

CORRIDAS = ["sft-reales", "sft-mixto", "sft-mixto-catedra", "sft-mixto-final"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hub", required=True)
    ap.add_argument("--modelos", type=Path, required=True)
    a = ap.parse_args()
    api = HfApi()
    subidos = {}
    for corrida in CORRIDAS:
        rama = f"{corrida}-checkpoints"
        api.create_branch(a.hub, branch=rama, exist_ok=True)
        puntos = sorted((a.modelos / corrida).glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
        for punto in puntos:
            commit = api.upload_folder(repo_id=a.hub, folder_path=str(punto), path_in_repo=punto.name,
                                       revision=rama, commit_message=f"{corrida}: {punto.name} (adaptador LoRA)",
                                       ignore_patterns=["optimizer.pt", "scheduler.pt", "rng_state.pth"])
            api.create_tag(a.hub, tag=f"{corrida}-{punto.name}", revision=commit.oid, exist_ok=True)
            subidos.setdefault(corrida, {})[punto.name] = commit.oid
            print(corrida, punto.name, commit.oid, flush=True)
    print(json.dumps(subidos, indent=2))


if __name__ == "__main__":
    main()
