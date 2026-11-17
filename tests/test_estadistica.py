"""Las cuentas de ``evaluacion.estadistica`` y su lectura de las corridas guardadas."""

import math

import pytest

from evaluacion.estadistica import cargar, comparar, mcnemar_exacto, resueltos, wilson
from evaluacion.lectura import CORRIDAS, VERSIONES


def test_wilson_contiene_la_proporcion_y_queda_en_0_1():
    for exitos, n in [(0, 50), (13, 50), (50, 50), (149, 150)]:
        bajo, alto = wilson(exitos, n)
        assert 0 <= bajo <= exitos / n <= alto <= 1


def test_wilson_con_todo_resuelto_no_tiene_ancho_cero():
    bajo, alto = wilson(50, 50)
    assert alto == 1 and bajo < 0.95


def test_wilson_valor_conocido():
    # 13/50: [0.1587, 0.3955] (Wilson, z = 1.96).
    bajo, alto = wilson(13, 50)
    assert math.isclose(bajo, 0.1587, abs_tol=1e-3) and math.isclose(alto, 0.3955, abs_tol=1e-3)


def test_mcnemar_sin_discordancias_es_1():
    assert mcnemar_exacto(0, 0) == 1


def test_mcnemar_es_simetrico():
    assert mcnemar_exacto(3, 25) == mcnemar_exacto(25, 3)


def test_mcnemar_valores_conocidos():
    assert math.isclose(mcnemar_exacto(0, 5), 2 / 32)       # 2 * (1/2)^5
    assert math.isclose(mcnemar_exacto(1, 1), 1.0)
    assert math.isclose(mcnemar_exacto(2, 8), 0.109375)     # 2 * (1 + 10 + 45) / 1024


@pytest.mark.skipif(not (CORRIDAS / "entrega-original").exists(), reason="faltan las corridas guardadas")
def test_las_corridas_guardadas_coinciden_con_su_resumen():
    import json

    for version in VERSIONES:
        resumen = json.loads((CORRIDAS / f"entrega-{version}" / "resumen.json").read_text(encoding="utf-8"))
        res = cargar("entrega", version)
        assert len(res) == resumen["casos"]
        assert len(resueltos(res)) == resumen["resueltos"]


@pytest.mark.skipif(not (CORRIDAS / "gpu-final-original").exists(), reason="faltan las corridas guardadas")
def test_gpu_final_y_entrega_resuelven_los_mismos_casos():
    datos = {(c, v): cargar(c, v) for c in ("gpu-final", "entrega") for v in VERSIONES}
    assert comparar("gpu-final", "entrega", datos) == (0, 0, 1.0)
