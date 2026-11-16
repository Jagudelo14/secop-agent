# ### Archivo: test_tools.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Pruebas de herramientas con respuestas grabadas de la API

import pytest

from secop_agent import socrata, tools


@pytest.fixture
def api_grabada(monkeypatch, filas_reales):
    consultas = []

    def falso_consultar(params):
        consultas.append(params)
        if "count(*)" in params.get("$select", "") and "$group" not in params:
            return [{"num_contratos": "25", "total_valor": "123456789"}]
        return filas_reales[: params.get("$limit", 1000)]

    monkeypatch.setattr(socrata, "consultar", falso_consultar)
    return consultas


def test_consultar_contratos_limpia_y_cuenta(api_grabada):
    r = tools.consultar_contratos({"anio": 2024}, limite=10)
    assert r["num_contratos_total"] == 25
    assert r["num_devueltos"] == 10
    assert r["truncado"] is True
    assert all(c["url"].startswith("https://") for c in r["contratos"])


def test_detectar_alertas_corre_con_datos_reales(api_grabada):
    r = tools.detectar_alertas("700218068", 2024)
    assert r["contratos_analizados"] == 25
    assert all(h["aviso"] for h in r["hallazgos"])


def test_detalle_contrato_no_encontrado(monkeypatch):
    monkeypatch.setattr(socrata, "consultar", lambda params: [])
    assert tools.detalle_contrato("CO1.PCCNTR.0")["encontrado"] is False


def test_agregar_valida_agrupacion():
    with pytest.raises(ValueError):
        tools.agregar({}, "color")


def test_ejecutar_herramienta_desconocida():
    with pytest.raises(ValueError):
        tools.ejecutar("borrar_todo", {})


def test_definiciones_coinciden_con_funciones():
    nombres = {h["name"] for h in tools.HERRAMIENTAS}
    assert nombres == set(tools.FUNCIONES)
