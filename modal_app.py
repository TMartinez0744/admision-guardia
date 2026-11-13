"""Corre comandos del repo en una A100 de 40 GB de Modal.

La imagen tiene las dependencias de ``uv.lock`` (sin el grupo dev) y el kit de
la cátedra al lado del repo, en la misma ruta relativa que en local
(``../talksmith-ing/missions/TPFinal``). El código del repo se monta al
arrancar, así un cambio de código no reconstruye la imagen.

Los pesos de Hugging Face y las salidas quedan en el volumen ``admision-cache``:
los modelos se bajan una sola vez y los resultados se bajan después con
``modal volume get``.

    uv run modal run modal_app.py --comando "python -m admision.correr practica ... --salida /cache/corridas/base-original"
    uv run modal volume get admision-cache corridas/base-original corridas/

Requiere ``KIT`` apuntando a la carpeta del kit (por defecto, la de al lado del repo).
"""

import os
import subprocess
from pathlib import Path

import modal

REPO = Path(__file__).parent
KIT = Path(os.environ.get("KIT", REPO.parent / "talksmith-ing" / "missions" / "TPFinal"))
REMOTO_REPO = "/root/admision-guardia"
REMOTO_KIT = "/root/talksmith-ing/missions/TPFinal"
GPU = "A100-40GB"  # la consigna exige la de 40 GB; "A100" a secas puede dar la de 80 GB

volumen = modal.Volume.from_name("admision-cache", create_if_missing=True)

imagen = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("uv==0.12.13")
    .env({"UV_PROJECT_ENVIRONMENT": "/venv", "HF_HOME": "/cache/hf"})
    .add_local_dir(KIT, REMOTO_KIT, copy=True)
    .add_local_file(REPO / "pyproject.toml", f"{REMOTO_REPO}/pyproject.toml", copy=True)
    .add_local_file(REPO / "uv.lock", f"{REMOTO_REPO}/uv.lock", copy=True)
    .run_commands(f"cd {REMOTO_REPO} && uv sync --frozen --no-dev --no-install-project")
    .add_local_dir(REPO, REMOTO_REPO, ignore=[".venv", ".git", "corridas", "datos", "**/__pycache__"])
)

app = modal.App("admision-guardia", image=imagen)


@app.function(gpu=GPU, volumes={"/cache": volumen}, timeout=6 * 60 * 60)
def ejecutar(comando: str) -> int:
    """Corre ``comando`` desde la raíz del repo, con el Python del entorno."""
    print(f"$ {comando}", flush=True)
    resultado = subprocess.run(comando, shell=True, cwd=REMOTO_REPO,
                               env={**os.environ, "PATH": f"/venv/bin:{os.environ['PATH']}"})
    volumen.commit()
    return resultado.returncode


@app.local_entrypoint()
def main(comando: str):
    codigo = ejecutar.remote(comando)
    print(f"Terminó con código {codigo}")
    if codigo:
        raise SystemExit(codigo)
