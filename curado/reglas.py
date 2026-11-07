"""Las normas escritas, como reglas, para derivar la ficha que corresponde a cada fila.

Cubre los siete campos que las normas determinan. El octavo,
``aviso_al_voluntariado``, no lo fija ninguna norma: se resuelve por costumbre
y se analiza aparte en ``curado.costumbres``.

Normas implementadas:
  NOR-ADM-01 §2-§4, NOR-ADM-02 §1, NOR-ADM-03 §1  -> registro, numero_documento,
                                                     box_antes_del_registro
  NOR-TDE-01 a NOR-TDE-04                         -> circuito, plazo_circuito_min
  NOR-COB-01 §3, NOR-COB-02 §2-§5, NOR-COB-03 §1 §4,
  NOR-COB-04 §1 §3 §4                             -> cobertura, entidad_a_notificar

Los valores de los parámetros salen siempre de la carpeta de normas que se
recibe, porque cambian entre versiones.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

MOTIVO_ECG = "dolor torácico"
MOTIVO_ACV = "signos neurológicos focales de inicio súbito"
SEPSIS_GRAVE = {"probable", "con signos de shock"}

TIPO_COBERTURA = {"obra social": "obra_social", "prepaga": "prepaga", "art": "art"}

PATRON_CREDENCIAL = re.compile(r"^(?P<nombre>.+?)\s*\((?P<tipo>[^)]+)\)\s*(?P<numero>\S+)$")
PATRON_ART = re.compile(r"^(?P<nombre>.+?)\s+CUIL\s+(?P<cuil>\S+)$")


def cargar_parametros(ruta_normas: Path) -> dict[str, int]:
    datos = yaml.safe_load((Path(ruta_normas) / "parametros.yaml").read_text(encoding="utf-8"))
    return {p["codigo"]: p["valor"] for p in datos["parametros"]}


def partir_credencial(texto: str) -> tuple[str, str, str] | None:
    """'Obra Social Bermejo (obra social) 18-876602-7' -> (nombre, tipo, número)."""
    texto = (texto or "").strip()
    if not texto or texto.lower() == "ninguna":
        return None
    m = PATRON_CREDENCIAL.match(texto)
    if not m:
        return None
    tipo = TIPO_COBERTURA.get(m.group("tipo").strip().lower())
    return (m.group("nombre").strip(), tipo, m.group("numero").strip()) if tipo else None


def nombre_de_art(texto: str) -> str | None:
    """'Pampa Laboral ART CUIL 23-28281926-3' -> 'Pampa Laboral ART'.

    En la ART el numero de afiliado es el CUIL del paciente (NOR-COB-02 §5).
    """
    texto = (texto or "").strip()
    if not texto:
        return None
    m = PATRON_ART.match(texto)
    return m.group("nombre").strip() if m else texto


def ultimo_digito(numero: str) -> int | None:
    digitos = [c for c in numero if c.isdigit()]
    return int(digitos[-1]) if digitos else None


def credenciales_de(fila: dict) -> list[tuple[str, str, str]]:
    """Las credenciales presentadas, o la cobertura declarada si no presentó ninguna."""
    crudas = (fila["credenciales"] or "").strip() or (fila["cobertura_declarada"] or "").strip()
    partidas = [partir_credencial(x) for x in crudas.split(";")]
    return [c for c in partidas if c]


def credencial_en_juego(fila: dict) -> tuple[str, str, str] | None:
    """La credencial sobre la que se resuelve la cobertura.

    Con una sola credencial no hay elección. Con varias, las normas no dicen
    cuál vale: la elección es una costumbre y se audita aparte, así que acá se
    toma la que la admisión efectivamente verificó.
    """
    credenciales = credenciales_de(fila)
    if not credenciales:
        return None
    verificada = (fila["entidad_verificada"] or "").strip()
    if verificada:
        for c in credenciales:
            if c[0] == verificada:
                return c
    return credenciales[0] if len(credenciales) == 1 else None


def _registro(fila: dict, p: dict[str, int]) -> tuple[str, str | None]:
    """NOR-ADM-01 §2 §3 y NOR-ADM-03 §1."""
    tipo = (fila["documento_tipo"] or "").strip().lower()
    numero = (fila["documento_numero"] or "").strip() or None
    if not tipo:
        return "provisorio", None
    if tipo in {"pasaporte", "cédula"} and int(fila["nivel"]) <= p["P-ADM-3"]:
        # El documento está a la vista, pero el nivel urgente manda registro
        # provisorio. El número se anota igual.
        return "provisorio", numero
    return "definitivo", numero


def _box_antes(fila: dict, p: dict[str, int]) -> bool:
    """NOR-ADM-02 §1 prevalece sobre NOR-ADM-01 §4."""
    return int(fila["edad"]) >= p["P-ADM-2"] or int(fila["nivel"]) <= p["P-ADM-1"]


def _circuito(fila: dict, p: dict[str, int]) -> tuple[str, int | None]:
    """NOR-TDE-01 a NOR-TDE-03, con el descuento por ambulancia de NOR-TDE-04 §1."""
    motivo = (fila["motivo"] or "").strip().lower()
    sepsis = (fila["sospecha_sepsis"] or "").strip().lower()
    if sepsis and sepsis != "no":
        circuito = "codigo_sepsis"
        plazo = p["P-TDE-3"] if sepsis in SEPSIS_GRAVE else p["P-TDE-4"]
    elif motivo == MOTIVO_ECG:
        circuito, plazo = "ecg", p["P-TDE-1"]
    elif motivo == MOTIVO_ACV:
        circuito, plazo = "codigo_acv", p["P-TDE-2"]
    else:
        return "ninguno", None
    if (fila["llegada"] or "").strip().lower() == "en ambulancia":
        plazo -= p["P-TDE-5"]
    return circuito, plazo


def _cobertura(fila: dict, p: dict[str, int]) -> tuple[str, str | None]:
    """NOR-COB-02 §5 (ART), NOR-COB-03 §1 §4 y NOR-COB-04 §1 §3 §4."""
    if (fila["lesion_trabajo"] or "").strip().lower() != "no":
        # Accidente de trabajo o en el trayecto: cubre la ART, y NOR-COB-04 no aplica.
        return "art", nombre_de_art(fila["art_declarada"])

    credencial = credencial_en_juego(fila)
    if credencial is None:
        # Declara no tener, o no pudo informarla (NOR-COB-01 §3).
        return "sin_cobertura", None

    nombre, tipo, numero = credencial
    reservada = ultimo_digito(numero) == p["P-COB-2"]
    activa = (fila["respuesta_verificacion"] or "").strip().lower() == "activa"

    if reservada:
        # NOR-COB-04 §1: sin cobertura, pero se notifica igual, este activa o no.
        return "sin_cobertura", nombre
    if activa:
        return tipo, nombre
    # NOR-COB-03 §1 y §4: inactiva es sin cobertura y no se notifica.
    return "sin_cobertura", None


def ficha_esperada(fila: dict, p: dict[str, int]) -> dict:
    """Los siete campos que las normas escritas determinan."""
    registro, numero = _registro(fila, p)
    circuito, plazo = _circuito(fila, p)
    cobertura, entidad = _cobertura(fila, p)
    return {
        "registro": registro,
        "numero_documento": numero,
        "box_antes_del_registro": _box_antes(fila, p),
        "circuito": circuito,
        "plazo_circuito_min": plazo,
        "cobertura": cobertura,
        "entidad_a_notificar": entidad,
    }
