"""Genera los gráficos del INFORME a partir de los archivos del repo.

Lee solo archivos versionados (``historial_clasificado.csv``,
``evaluacion/corridas/*/resumen.json``, ``evaluacion/corridas/capacidad-*/capacidad.json`` y
``evaluacion/entrenamientos/*/perdida.json``) y escribe PNG en ``informe/figuras/``.

Todos comparten una estructura: el mismo tamaño, un título con la conclusión, un subtítulo con
lo que se mide y la fuente abajo. Los colores tienen un significado fijo en todos los gráficos:
gris para la referencia de la cátedra y una escala de azules que se oscurece a medida que avanza
el desarrollo (celeste sin entrenar, azul medio entrenado, azul oscuro el modelo final).

    uv run python -m evaluacion.graficos
"""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

CORRIDAS = Path("evaluacion/corridas")
ENTRENAMIENTOS = Path("evaluacion/entrenamientos")
SALIDA = Path("informe/figuras")
VERSIONES = ("original", "b", "c")

# Superficie y texto.
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_3 = "#8a8984"
GRILLA = "#e9e8e4"
# Significado fijo de cada color.
REFERENCIA = "#c9c7bf"      # la referencia de la cátedra
SIN_ENTRENAR = "#9ec5f4"    # nuestro modelo sin entrenar (con o sin prompt optimizado)
ENTRENADO = "#3987e5"       # entrenamientos intermedios
FINAL = "#184f95"           # el modelo final
APARTE = "#9b9a95"          # una variante que se compara (gris medio)
# Un color por entrenamiento, el mismo en la curva de pérdida y en los recursos. Validados para
# daltonismo con el final: naranja, verde y azul oscuro se distinguen entre sí.
COLOR_CORRIDA = {"sft-reales": APARTE, "sft-mixto": "#eb6834", "sft-mixto-catedra": "#1baf7a",
                 "sft-mixto-final": FINAL}
# Estados de la clasificación del historial (siempre con su nombre escrito).
CORRECTA, RUIDO, ERROR = "#0ca30c", "#fab219", "#d03b3b"
# Rampa secuencial para el mapa de calor.
AZULES = ["#e7f0fc", "#b7d3f6", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]

PRECIO_A100_SEGUNDO = 0.000583  # A100 de 40 GB en Modal (modal.com/pricing)
REF_SIN_ENTRENAR = (12, 15, 12)  # mission.md
REF_SFT = (25, 24, 25)


def estilo() -> None:
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
        "font.size": 10, "text.color": TINTA, "axes.labelcolor": TINTA_2, "xtick.color": TINTA_2,
        "ytick.color": TINTA_2, "axes.edgecolor": GRILLA, "axes.spines.top": False,
        "axes.spines.right": False, "axes.spines.left": False, "axes.grid": True, "grid.color": GRILLA,
        "grid.linewidth": 0.8, "axes.axisbelow": True, "legend.frameon": False, "xtick.major.size": 0,
        "ytick.major.size": 0,
    })


def figura(titulo: str, subtitulo: str, fuente: str, ncols: int = 1, alto: float = 4.4,
           izquierda: float = 0.1, abajo: int = 48, arriba: int = 0):
    """La estructura común: título y subtítulo arriba, fuente abajo, a distancia fija del gráfico.

    ``izquierda`` deja lugar a las etiquetas del eje y; ``abajo`` es la distancia en puntos de la
    fuente al borde inferior de los ejes (más si hay etiquetas o un título de eje abajo).
    """
    fig, ejes = plt.subplots(1, ncols, figsize=(9.5, alto), sharey=ncols > 1)
    fig.subplots_adjust(left=izquierda, right=0.97, wspace=0.12)
    primero = ejes[0] if ncols > 1 else ejes
    coords = ("figure fraction", "axes fraction")
    primero.annotate(titulo, (0.01, 1), xycoords=coords, xytext=(0, 34 + arriba), textcoords="offset points",
                     fontsize=13, fontweight="bold", color=TINTA, ha="left", va="bottom")
    primero.annotate(subtitulo, (0.01, 1), xycoords=coords, xytext=(0, 14 + arriba), textcoords="offset points",
                     fontsize=10, color=TINTA_2, ha="left", va="bottom")
    primero.annotate(f"Fuente: {fuente}", (0.01, 0), xycoords=coords, xytext=(0, -abajo),
                     textcoords="offset points", fontsize=8, color=TINTA_3, ha="left", va="top")
    return fig, ejes


def coma(decimales: int):
    """Formato de eje con coma decimal."""
    return FuncFormatter(lambda v, _: f"{v:.{decimales}f}".replace(".", ","))


def guardar(fig, nombre: str) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA / nombre, dpi=160, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(SALIDA / nombre)


def resumen(corrida: str, version: str) -> dict:
    return json.loads((CORRIDAS / f"{corrida}-{version}" / "resumen.json").read_text(encoding="utf-8"))


def resueltos(corrida: str) -> list[int]:
    return [resumen(corrida, v)["resueltos"] for v in VERSIONES]


def clasificacion() -> None:
    """Las 2.000 filas del historial por tipo."""
    filas = list(csv.DictReader(open("historial_clasificado.csv", encoding="utf-8")))
    tipos = [("Correcta", "correcta", CORRECTA, "sigue las normas y la costumbre"),
             ("Ruido", "ruido", RUIDO, "se aparta de una costumbre"),
             ("Error", "error", ERROR, "viola una norma escrita")]
    total = len(filas)
    fig, ax = figura("8 de cada 10 admisiones del historial son correctas",
                     f"Clasificación de las {total:,} filas del historial".replace(",", "."),
                     "historial_clasificado.csv (curado.clasificar)", alto=2.8, izquierda=0.12, abajo=14)
    y = [2, 1, 0]
    for yi, (nombre, clave, color, descripcion) in zip(y, tipos, strict=True):
        n = sum(f["tipo"] == clave for f in filas)
        ax.barh(yi, n, color=color, height=0.6, edgecolor=SUPERFICIE, linewidth=2)
        ax.text(n + 25, yi, f"{n:,}".replace(",", ".") + f"  ({n / total:.0%})  ·  {descripcion}",
                va="center", color=TINTA_2, fontsize=9.5)
    ax.set_yticks(y, [t[0] for t in tipos], fontsize=11)
    ax.set_xlim(0, 2600)
    ax.set_xticks([])
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    guardar(fig, "clasificacion.png")


def progreso() -> None:
    """Casos resueltos (de 150) en cada iteración del desarrollo."""
    pasos = [("Sin entrenar, prompt de la cátedra", "base", SIN_ENTRENAR),
             ("Sin entrenar, prompt reordenado", "ini", SIN_ENTRENAR),
             ("Sin entrenar, prompt de GEPA", "opt", SIN_ENTRENAR),
             ("SFT solo reales, prompt de GEPA", "sft-reales", ENTRENADO),
             ("SFT reales + sintéticas, prompt de GEPA", "sft-mixto", ENTRENADO),
             ("SFT reales + sintéticas, prompt de la cátedra", "gpu-catedra", ENTRENADO),
             ("SFT reales + sintéticas, prompt corregido (final)", "entrega", FINAL)]
    fig, ax = figura("De 21 a 149 casos resueltos", "Casos resueltos de 150 (50 de práctica × normas "
                     "original, b y c) en cada iteración del desarrollo",
                     "evaluacion/corridas/*/resumen.json", izquierda=0.36, abajo=30)
    y = list(range(len(pasos)))[::-1]
    for yi, (_, corrida, color) in zip(y, pasos, strict=True):
        total = sum(resueltos(corrida))
        ax.barh(yi, total, color=color, height=0.62, edgecolor=SUPERFICIE, linewidth=2)
        ax.text(total + 2, yi, str(total), va="center", color=TINTA, fontsize=10,
                fontweight="bold" if color == FINAL else "normal")
    # Una etiqueta abajo y otra arriba, para que no se pisen.
    for valor, texto, yt in [(sum(REF_SIN_ENTRENAR), "cátedra sin entrenar: 39", -0.75),
                             (sum(REF_SFT), "cátedra con SFT: 74", len(pasos) - 0.55)]:
        ax.axvline(valor, color=TINTA_3, linestyle=(0, (3, 3)), linewidth=1)
        ax.text(valor + 1.5, yt, texto, color=TINTA_3, fontsize=8)
    ax.set_yticks(y, [p[0] for p in pasos])
    ax.set_xlim(0, 160)
    ax.set_ylim(-0.95, len(pasos) - 0.4)
    ax.grid(axis="y", visible=False)
    guardar(fig, "progreso.png")


def tabla_parte4() -> None:
    """La tabla obligatoria de la Parte 4, un panel por versión de normas."""
    filas = [("Cátedra, sin entrenar", REF_SIN_ENTRENAR, REFERENCIA),
             ("Cátedra, con SFT", REF_SFT, REFERENCIA),
             ("Nuestro modelo, sin entrenar", resueltos("base"), SIN_ENTRENAR),
             ("Solo prompt", resueltos("opt"), SIN_ENTRENAR),
             ("Solo entrenamiento", resueltos("gpu-catedra"), ENTRENADO),
             ("Prompt + entrenamiento (final)", resueltos("entrega"), FINAL)]
    fig, ejes = figura("El modelo final resuelve casi todo con las tres versiones de normas",
                       "Casos resueltos de 50 por configuración (la tabla de la Parte 4)",
                       "evaluacion/corridas/{base,opt,gpu-catedra,entrega}-*/resumen.json y mission.md",
                       ncols=3, alto=3.9, izquierda=0.26, abajo=34, arriba=22)
    y = list(range(len(filas)))[::-1]
    for i, (ax, version) in enumerate(zip(ejes, VERSIONES, strict=True)):
        for yi, (_, valores, color) in zip(y, filas, strict=True):
            ax.barh(yi, valores[i], color=color, height=0.68, edgecolor=SUPERFICIE, linewidth=2)
            ax.text(valores[i] + 1, yi, str(valores[i]), va="center", fontsize=9, color=TINTA,
                    fontweight="bold" if color == FINAL else "normal")
        ax.set_title(f"Normas {version}", fontsize=10.5, color=TINTA, loc="left", fontweight="bold")
        ax.set_xlim(0, 58)
        ax.set_xticks([0, 25, 50])
        ax.grid(axis="y", visible=False)
    ejes[0].set_yticks(y, [f[0] for f in filas])
    guardar(fig, "tabla_parte4.png")


def perdida() -> None:
    """Curvas de pérdida de los cuatro entrenamientos."""
    corridas = [(n, e, COLOR_CORRIDA[n]) for n, e in [
        ("sft-reales", "Solo reales, 2 épocas"),
        ("sft-mixto", "Reales + sintéticas, prompt de GEPA"),
        ("sft-mixto-catedra", "Reales + sintéticas, prompt de la cátedra"),
        ("sft-mixto-final", "Reales + sintéticas, prompt corregido (final)")]]
    fig, ax = figura("La pérdida cae a casi cero antes de la mitad del entrenamiento",
                     "Pérdida sobre las respuestas del agente, en escala logarítmica",
                     "evaluacion/entrenamientos/*/perdida.json (bajado de W&B)", abajo=46)
    for nombre, etiqueta, color in corridas:
        puntos = json.loads((ENTRENAMIENTOS / nombre / "perdida.json").read_text(encoding="utf-8"))["puntos"]
        ax.plot([p["paso"] for p in puntos], [p["perdida"] for p in puntos], color=color,
                linewidth=2.4 if color == FINAL else 1.8, label=etiqueta)
    ax.set_yscale("log")
    ax.set_xlabel("Paso de entrenamiento (8 conversaciones por paso; 400 pasos = 3.200 conversaciones)")
    ax.legend(loc="upper right", fontsize=9)
    guardar(fig, "perdida.png")


def controles() -> None:
    """Acierto por control (promedio de las tres versiones de normas) en cada etapa."""
    etapas = [("Sin entrenar", "base"), ("Solo prompt", "opt"), ("SFT con prompt\nde GEPA", "sft-mixto"),
              ("Solo\nentrenamiento", "gpu-catedra"), ("Final", "entrega")]
    nombres = list(resumen("base", "original")["por_control"])
    matriz = [[sum(resumen(c, v)["por_control"][k] for v in VERSIONES) / 3 for _, c in etapas] for k in nombres]
    fig, ax = figura("El entrenamiento resuelve el oficio; el voluntariado necesitó el prompt corregido",
                     "Acierto por control en cada etapa (promedio de las normas original, b y c)",
                     "evaluacion/corridas/*/resumen.json", alto=5, izquierda=0.22, abajo=40)
    ax.imshow(matriz, cmap=LinearSegmentedColormap.from_list("azules", AZULES), vmin=0.5, vmax=1.0,
              aspect="auto")
    for i, fila in enumerate(matriz):
        for j, v in enumerate(fila):
            ax.text(j, i, f"{v:.2f}".replace(".", ","), ha="center", va="center", fontsize=9.5,
                    color=SUPERFICIE if v >= 0.85 else TINTA)
    ax.set_xticks(range(len(etapas)), [e for e, _ in etapas])
    ax.set_yticks(range(len(nombres)), nombres)
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    guardar(fig, "controles.png")


def capacidad() -> None:
    """Segundos por caso según cuántos casos se procesan a la vez."""
    series = [("capacidad-sft-catedra", "Buscador en CPU (modelo solo entrenamiento)", APARTE),
              ("capacidad-entrega", "Buscador en GPU (modelo final)", FINAL)]
    fig, ax = figura("Con el buscador en la GPU, una A100 escala hasta unos 200 casos a la vez",
                     "Segundos por caso según cuántos casos se procesan juntos, en una A100 de 40 GB",
                     "evaluacion/corridas/capacidad-*/capacidad.json", abajo=46)
    for carpeta, etiqueta, color in series:
        lotes = json.loads((CORRIDAS / carpeta / "capacidad.json").read_text(encoding="utf-8"))["lotes"]
        xs, ys = [l["casos"] for l in lotes], [l["segundos_por_caso"] for l in lotes]
        ax.plot(xs, ys, color=color, linewidth=2.4, marker="o", markersize=8, markeredgecolor=SUPERFICIE,
                markeredgewidth=2, label=etiqueta)
        ax.text(xs[-1] * 1.07, ys[-1], f"{ys[-1]:.2f} s".replace(".", ","), va="center", color=TINTA_2,
                fontsize=9)
    ax.set_xscale("log", base=2)
    ax.set_xticks([25, 50, 100, 200, 400], ["25", "50", "100", "200", "400"])
    ax.set_xlim(20, 560)
    ax.set_ylim(0, 1.8)
    ax.yaxis.set_major_formatter(coma(1))
    ax.set_xlabel("Casos procesados a la vez")
    ax.set_ylabel("Segundos por caso")
    ax.legend(loc="upper right", fontsize=9)
    guardar(fig, "capacidad.png")


def recursos() -> None:
    """Tiempo, costo y VRAM de cada entrenamiento en la A100 de 40 GB."""
    corridas = [(n, e, COLOR_CORRIDA[n]) for n, e in [
        ("sft-reales", "Solo reales, 2 épocas"),
        ("sft-mixto", "Reales + sintéticas, prompt de GEPA"),
        ("sft-mixto-catedra", "Reales + sintéticas, prompt de la cátedra"),
        ("sft-mixto-final", "Reales + sintéticas, prompt corregido (final)")]]
    datos = [json.loads((ENTRENAMIENTOS / n / "resumen.json").read_text(encoding="utf-8")) for n, _, _ in corridas]
    paneles = [("Tiempo (minutos)", [d["segundos"] / 60 for d in datos], 120, "{:.0f} min"),
               ("Costo de GPU (USD)", [d["segundos"] * PRECIO_A100_SEGUNDO for d in datos], 4.5, "USD {:.2f}"),
               ("Pico de VRAM (GB)", [d["vram_pico_gb"] for d in datos], 40, "{:.1f} GB")]
    fig, ejes = figura("Cada entrenamiento usa menos de la mitad de la GPU y cuesta menos de USD 4",
                       "Recursos de cada entrenamiento con LoRA en una A100 de 40 GB de Modal",
                       "evaluacion/entrenamientos/*/resumen.json; costo = tiempo × USD 0,000583 por segundo",
                       ncols=3, alto=3.2, izquierda=0.3, abajo=34, arriba=22)
    y = list(range(len(corridas)))[::-1]
    for ax, (titulo, valores, tope, formato) in zip(ejes, paneles, strict=True):
        for yi, v, (_, _, color) in zip(y, valores, corridas, strict=True):
            if titulo.startswith("Pico de VRAM"):  # la GPU entera de fondo, para ver qué parte se usa
                ax.barh(yi, 40, color=GRILLA, height=0.66, edgecolor=SUPERFICIE, linewidth=2)
            ax.barh(yi, v, color=color, height=0.66, edgecolor=SUPERFICIE, linewidth=2)
            ax.text(v + tope * 0.03, yi, formato.format(v).replace(".", ","), va="center", fontsize=8.5,
                    color=TINTA, fontweight="bold" if color == FINAL else "normal")
        ax.set_title(titulo, fontsize=10.5, color=TINTA, loc="left", fontweight="bold")
        ax.set_xlim(0, tope * 1.32)
        ax.set_xticks([])
        ax.grid(False)
        ax.spines["bottom"].set_visible(False)
    ejes[2].text(40, -0.62, "40 GB", color=TINTA_3, fontsize=8, ha="right", va="top")
    ejes[0].set_ylim(-0.95, len(corridas) - 0.45)
    ejes[0].set_yticks(y, [c[1] for c in corridas])
    guardar(fig, "recursos.png")


def main() -> None:
    estilo()
    clasificacion()
    progreso()
    tabla_parte4()
    perdida()
    controles()
    capacidad()
    recursos()


if __name__ == "__main__":
    main()
