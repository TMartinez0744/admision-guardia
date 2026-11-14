"""Genera los gráficos del INFORME a partir de las corridas guardadas en el repo.

Lee solo archivos versionados (``evaluacion/corridas/*/resumen.json``,
``evaluacion/corridas/capacidad-*/capacidad.json`` y
``evaluacion/entrenamientos/*/perdida.json``) y escribe PNG en ``informe/figuras/``.

    uv run python -m evaluacion.graficos
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CORRIDAS = Path("evaluacion/corridas")
ENTRENAMIENTOS = Path("evaluacion/entrenamientos")
SALIDA = Path("informe/figuras")
VERSIONES = ("original", "b", "c")

# Paleta categórica validada (orden fijo) y tokens de texto y superficie.
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRILLA = "#e4e3df"
REFERENCIA = "#8a8984"
# Rampa secuencial azul para el mapa de calor.
AZULES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Referencia de la cátedra (mission.md).
REF_SIN_ENTRENAR = (12, 15, 12)
REF_SFT = (25, 24, 25)


def estilo() -> None:
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
        "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "text.color": TINTA, "axes.labelcolor": TINTA_2, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
        "axes.edgecolor": GRILLA, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRILLA, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "legend.frameon": False,
    })


def resumen(corrida: str, version: str) -> dict:
    return json.loads((CORRIDAS / f"{corrida}-{version}" / "resumen.json").read_text(encoding="utf-8"))


def resueltos(corrida: str) -> list[int]:
    return [resumen(corrida, v)["resueltos"] for v in VERSIONES]


def guardar(fig, nombre: str) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA / nombre, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(SALIDA / nombre)


def progreso() -> None:
    """Casos resueltos (de 150) en cada iteración del desarrollo."""
    pasos = [("Línea base: sin entrenar, prompt de la cátedra", "base"),
             ("Prompt reordenado", "ini"),
             ("Prompt optimizado con GEPA", "opt"),
             ("SFT solo reales (prompt GEPA)", "sft-reales"),
             ("SFT reales + sintéticas (prompt GEPA)", "sft-mixto"),
             ("SFT reales + sintéticas (prompt cátedra)", "gpu-catedra"),
             ("SFT reales + sintéticas (prompt corregido): final", "entrega")]
    totales = [sum(resueltos(c)) for _, c in pasos]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    y = list(range(len(pasos)))[::-1]
    ax.barh(y, totales, color=SERIE[0], height=0.62, edgecolor=SUPERFICIE, linewidth=2)
    for yi, t in zip(y, totales, strict=True):
        ax.text(t + 2, yi, f"{t}", va="center", color=TINTA, fontsize=10)
    for valor, texto in [(sum(REF_SIN_ENTRENAR), "Referencia cátedra\nsin entrenar (39)"),
                         (sum(REF_SFT), "Referencia cátedra\ncon SFT (74)")]:
        ax.axvline(valor, color=REFERENCIA, linestyle="--", linewidth=1.2)
        ax.text(valor + 1.5, len(pasos) - 0.35, texto, color=TINTA_2, fontsize=8, va="top")
    ax.set_yticks(y, [p for p, _ in pasos])
    ax.set_xlim(0, 160)
    ax.set_xlabel("Casos resueltos de 150 (50 de práctica × normas original, b y c)")
    ax.grid(axis="y", visible=False)
    ax.set_title("De 21 a 149 casos resueltos: cada iteración del desarrollo")
    guardar(fig, "progreso.png")


def tabla_parte4() -> None:
    """La tabla obligatoria de la Parte 4, por versión de normas."""
    filas = [("Referencia\nsin entrenar", REF_SIN_ENTRENAR), ("Referencia\ncon SFT", REF_SFT),
             ("Nuestro modelo\nsin entrenar", resueltos("base")), ("Solo\nprompt", resueltos("opt")),
             ("Solo\nentrenamiento", resueltos("gpu-catedra")),
             ("Prompt +\nentrenamiento", resueltos("entrega"))]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ancho = 0.26
    for i, version in enumerate(VERSIONES):
        xs = [k + (i - 1) * ancho for k in range(len(filas))]
        valores = [f[1][i] for f in filas]
        ax.bar(xs, valores, width=ancho, color=SERIE[i], edgecolor=SUPERFICIE, linewidth=2,
               label=f"normas {version}")
        for x, v in zip(xs, valores, strict=True):
            ax.text(x, v + 0.8, str(v), ha="center", fontsize=7.5, color=TINTA_2)
    ax.set_xticks(range(len(filas)), [f[0] for f in filas])
    ax.set_ylim(0, 55)
    ax.set_ylabel("Casos resueltos de 50")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", ncols=3)
    ax.set_title("Casos resueltos por configuración y versión de normas (Parte 4)")
    guardar(fig, "tabla_parte4.png")


def perdida() -> None:
    """Curvas de pérdida de los cuatro entrenamientos (de W&B, guardadas en el repo)."""
    corridas = [("sft-reales", "Solo reales (2 épocas)"), ("sft-mixto", "Reales + sintéticas, prompt GEPA"),
                ("sft-mixto-catedra", "Reales + sintéticas, prompt cátedra"),
                ("sft-mixto-final", "Reales + sintéticas, prompt corregido (final)")]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for i, (nombre, etiqueta) in enumerate(corridas):
        puntos = json.loads((ENTRENAMIENTOS / nombre / "perdida.json").read_text(encoding="utf-8"))["puntos"]
        ax.plot([p["paso"] for p in puntos], [p["perdida"] for p in puntos], color=SERIE[i], linewidth=2,
                label=etiqueta)
    ax.set_yscale("log")
    ax.set_xlabel("Paso de entrenamiento (8 conversaciones por paso; 400 pasos = 3.200 conversaciones)")
    ax.set_ylabel("Pérdida (escala logarítmica)")
    ax.legend(loc="upper right")
    ax.set_title("Pérdida de entrenamiento: cae a casi cero antes de la mitad")
    guardar(fig, "perdida.png")


def controles() -> None:
    """Acierto por control (promedio de las tres versiones de normas) en cada etapa."""
    etapas = [("Sin entrenar", "base"), ("Solo prompt", "opt"), ("SFT, prompt\nGEPA", "sft-mixto"),
              ("Solo\nentrenamiento", "gpu-catedra"), ("Final", "entrega")]
    nombres = list(resumen("base", "original")["por_control"])
    matriz = [[sum(resumen(c, v)["por_control"][k] for v in VERSIONES) / 3 for _, c in etapas] for k in nombres]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    from matplotlib.colors import LinearSegmentedColormap

    mapa = LinearSegmentedColormap.from_list("azules", AZULES)
    ax.imshow(matriz, cmap=mapa, vmin=0.5, vmax=1.0, aspect="auto")
    for i, fila in enumerate(matriz):
        for j, v in enumerate(fila):
            ax.text(j, i, f"{v:.2f}".replace(".", ","), ha="center", va="center", fontsize=9,
                    color=SUPERFICIE if v >= 0.85 else TINTA)
    ax.set_xticks(range(len(etapas)), [e for e, _ in etapas])
    ax.set_yticks(range(len(nombres)), nombres)
    ax.grid(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Acierto por control: qué arregló cada etapa")
    guardar(fig, "controles.png")


def capacidad() -> None:
    """Segundos por caso según cuántos casos se procesan a la vez."""
    series = [("capacidad-entrega", "Buscador en GPU (modelo final)"),
              ("capacidad-sft-catedra", "Buscador en CPU (modelo solo entrenamiento)")]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for i, (carpeta, etiqueta) in enumerate(series):
        lotes = json.loads((CORRIDAS / carpeta / "capacidad.json").read_text(encoding="utf-8"))["lotes"]
        xs, ys = [l["casos"] for l in lotes], [l["segundos_por_caso"] for l in lotes]
        ax.plot(xs, ys, color=SERIE[i], linewidth=2, marker="o", markersize=7, markeredgecolor=SUPERFICIE,
                markeredgewidth=2, label=etiqueta)
        ax.text(xs[-1] * 1.06, ys[-1], f"{ys[-1]:.2f} s".replace(".", ","), va="center", color=TINTA_2, fontsize=9)
    ax.set_xscale("log", base=2)
    ax.set_xticks([25, 50, 100, 200, 400], ["25", "50", "100", "200", "400"])
    ax.set_xlim(20, 560)
    ax.set_ylim(0, 1.8)
    ax.set_xlabel("Casos procesados a la vez")
    ax.set_ylabel("Segundos por caso")
    ax.legend(loc="upper right")
    ax.set_title("Capacidad en una A100 de 40 GB: con el buscador en GPU escala hasta unos 200 casos")
    guardar(fig, "capacidad.png")


def main() -> None:
    estilo()
    progreso()
    tabla_parte4()
    perdida()
    controles()
    capacidad()


if __name__ == "__main__":
    main()
