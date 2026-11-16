# ### Archivo: test_alerts.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Las 4 señales sobre un caso armado a mano

from secop_agent import alerts
from secop_agent.schema import AVISO_ALERTA


def _contrato(id_contrato, documento, valor, firma, inicio=None, fin=None,
              modalidad="Contratación directa", tipo="Prestación de servicios", entidad="1"):
    return {
        "id_contrato": id_contrato,
        "codigo_entidad": entidad,
        "proveedor": f"Proveedor {documento}",
        "documento_proveedor": documento,
        "tipo_documento_proveedor": "NIT",
        "modalidad": modalidad,
        "tipo_de_contrato": tipo,
        "valor": valor,
        "fecha_firma": firma,
        "fecha_inicio": inicio or firma,
        "fecha_fin": fin or "2025-12-31",
        "url": f"https://secop/{id_contrato}",
    }


def _por_senal(hallazgos, senal):
    return [h for h in hallazgos if h["senal"] == senal]


# ### Fraccionamiento ###
def test_fraccionamiento_detecta_tres_contratos_en_ventana():
    contratos = [
        _contrato("A1", "900", 20_000_000, "2025-03-01"),
        _contrato("A2", "900", 20_000_000, "2025-03-10"),
        _contrato("A3", "900", 20_000_000, "2025-03-25"),
        # fuera de ventana
        _contrato("A4", "900", 20_000_000, "2025-06-01"),
    ]
    hallazgos = _por_senal(alerts.detectar(contratos), "posible_fraccionamiento")

    assert len(hallazgos) == 1
    assert {c["id_contrato"] for c in hallazgos[0]["contratos"]} == {"A1", "A2", "A3"}
    assert hallazgos[0]["aviso"] == AVISO_ALERTA


def test_fraccionamiento_no_salta_si_suma_bajo_umbral():
    contratos = [_contrato(f"B{i}", "901", 5_000_000, f"2025-03-0{i}") for i in range(1, 4)]
    assert _por_senal(alerts.detectar(contratos), "posible_fraccionamiento") == []


# ### Concentración ###
def test_concentracion_proveedor_sobre_20_por_ciento():
    contratos = [_contrato("C1", "800", 300_000_000, "2025-02-01")]
    contratos += [_contrato(f"C{i}", f"7{i}", 100_000_000, "2025-02-01") for i in range(2, 9)]
    hallazgos = _por_senal(alerts.detectar(contratos), "concentracion_contratacion_directa")

    # 300 de 1000 = 30 %
    assert len(hallazgos) == 1
    assert hallazgos[0]["participacion"] == 0.3
    assert hallazgos[0]["contratos"][0]["id_contrato"] == "C1"


def test_concentracion_ignora_entidad_pequena():
    contratos = [_contrato("D1", "800", 10_000_000, "2025-02-01")]
    assert _por_senal(alerts.detectar(contratos), "concentracion_contratacion_directa") == []


# ### Fechas ###
def test_fechas_inconsistentes_las_tres_reglas():
    contratos = [
        _contrato("E1", "1", 1, "2025-01-01", inicio="2025-02-01", fin="2025-01-15"),
        _contrato("E2", "2", 1, "2025-03-10", inicio="2025-03-01", fin="2025-05-01"),
        _contrato("E3", "3", 1, "2025-04-01", inicio="2025-04-02", fin="2025-04-02"),
        _contrato("E4", "4", 1, "2025-04-01", inicio="2025-04-02", fin="2025-08-02"),
    ]
    hallazgos = _por_senal(alerts.detectar(contratos), "fechas_inconsistentes")
    por_regla = {h["regla"]: {c["id_contrato"] for c in h["contratos"]} for h in hallazgos}

    assert por_regla == {
        "fin antes del inicio": {"E1"},
        "firma después del inicio": {"E2"},
        "duración de cero días": {"E3"},
    }


# ### Valor atípico ###
def test_valor_atipico_sobre_percentil():
    contratos = [_contrato(f"F{i}", str(i), 10_000_000, "2025-05-01") for i in range(30)]
    contratos.append(_contrato("F99", "99", 900_000_000, "2025-05-01"))
    hallazgos = _por_senal(alerts.detectar(contratos), "valor_atipico")

    assert len(hallazgos) == 1
    assert [c["id_contrato"] for c in hallazgos[0]["contratos"]] == ["F99"]


def test_valor_atipico_ignora_grupo_chico():
    contratos = [_contrato(f"G{i}", str(i), 1_000 * (i + 1), "2025-05-01") for i in range(5)]
    assert _por_senal(alerts.detectar(contratos), "valor_atipico") == []


def test_sin_contratos_no_hay_alertas():
    assert alerts.detectar([]) == []
