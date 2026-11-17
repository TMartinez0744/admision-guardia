"""``evaluacion.lectura`` y ``evaluacion.tabla`` sobre los archivos guardados en el repo."""

import pytest

from evaluacion import lectura
from evaluacion.tabla import fila

hay_corridas = pytest.mark.skipif(not (lectura.CORRIDAS / "entrega-original").exists(),
                                  reason="faltan las corridas guardadas")


@hay_corridas
def test_resumenes_vienen_en_el_orden_de_las_versiones():
    assert [r["casos"] for r in lectura.resumenes("entrega")] == [50, 50, 50]
    assert lectura.resueltos("entrega") == [49, 50, 50]


@hay_corridas
def test_resultados_por_caso_coinciden_con_el_resumen():
    for version in lectura.VERSIONES:
        res = lectura.resultados("base", version)
        assert len(res) == lectura.resumen("base", version)["casos"]
        assert sum(f["resuelto"] for f in res.values()) == lectura.resumen("base", version)["resueltos"]


@hay_corridas
def test_tabla_acepta_un_prefijo_con_carpeta():
    linea = fila(str(lectura.CORRIDAS / "entrega"))
    assert linea.startswith("| entrega | 49 / 50 | 50 / 50 | 50 / 50 |")


def test_entrenamientos_y_capacidad():
    if not (lectura.ENTRENAMIENTOS / "sft-mixto-final").exists():
        pytest.skip("faltan los entrenamientos guardados")
    assert lectura.perdida("sft-mixto-final")[0].keys() >= {"paso", "perdida"}
    assert "segundos" in lectura.entrenamiento("sft-mixto-final")
    assert [l["casos"] for l in lectura.capacidad("capacidad-entrega")] == [25, 50, 100, 200, 400]
