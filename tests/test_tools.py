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


def test_agregar_por_modalidad_trae_enlaces(monkeypatch, filas_reales):
    consultas = []

    def falso_consultar(params):
        consultas.append(params)
        if "$group" in params:
            return [{"clave": "Contratación directa", "num_contratos": "5", "total_valor": "100", "total_pagado": "0"}]
        if "count(*)" in params.get("$select", ""):
            return [{"num_contratos": "5", "total_valor": "100", "total_pagado": "0"}]
        return filas_reales[: params.get("$limit", 1000)]

    monkeypatch.setattr(socrata, "consultar", falso_consultar)
    r = tools.agregar({"anio": 2024}, "modalidad", top=5)

    mayores = r["grupos"][0]["contratos_mayores"]
    assert len(mayores) == 3
    assert all(c["url"].startswith("https://") for c in mayores)
    # filtro del grupo en la consulta
    assert "modalidad_de_contratacion = 'Contratación directa'" in consultas[-1]["$where"]


def test_agregar_promedio_y_contratistas_distintos(monkeypatch):
    consultas = []

    def falso_consultar(params):
        consultas.append(params)
        fila = {"clave": "Bogotá", "num_contratos": "4", "total_valor": "400", "total_pagado": "0",
                "promedio_valor": "100", "contratistas_distintos": "3"}
        if "$group" in params:
            return [fila]
        if "avg(" in params.get("$select", ""):
            return [fila]
        return []

    monkeypatch.setattr(socrata, "consultar", falso_consultar)
    r = tools.agregar({}, "ciudad", metrica="contratistas_distintos", top=5)

    assert r["total_general"]["promedio_valor"] == 100
    assert r["total_general"]["contratistas_distintos"] == 3
    assert r["grupos"][0]["contratistas_distintos"] == 3
    assert consultas[0]["$order"].startswith("contratistas_distintos DESC")


def test_buscar_entidad_marca_dependencias(monkeypatch):
    filas = [
        {"nombre_entidad": "ENTIDAD EJEMPLO - SECRETARIA UNO", "codigo_entidad": "1", "num_contratos": "5"},
        {"nombre_entidad": "ENTIDAD EJEMPLO - SECRETARIA DOS", "codigo_entidad": "2", "num_contratos": "4"},
        {"nombre_entidad": "OTRA ENTIDAD", "codigo_entidad": "3", "num_contratos": "3"},
    ]
    monkeypatch.setattr(socrata, "consultar", lambda params: filas)
    r = tools.buscar_entidad("entidad")

    assert r["dependencias"][0]["inicio_nombre"] == "ENTIDAD EJEMPLO"
    assert r["dependencias"][0]["num_entidades"] == 2
