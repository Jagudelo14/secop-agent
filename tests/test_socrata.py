# ### Archivo: test_socrata.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Pruebas del cliente Socrata sin red, con respuestas grabadas

import httpx
import pytest

from secop_agent import socrata


def _respuesta(estado, cuerpo):
    peticion = httpx.Request("GET", socrata.URL_DATOS)
    return httpx.Response(estado, json=cuerpo, request=peticion)


# ### Caché ###
def test_segunda_consulta_sale_de_cache(monkeypatch, filas_reales):
    llamadas = []

    def falso_get(url, params, headers, timeout):
        llamadas.append(params)
        return _respuesta(200, filas_reales)

    monkeypatch.setattr(httpx, "get", falso_get)
    params = {"$limit": 25}

    assert socrata.consultar(params) == filas_reales
    assert socrata.consultar(params) == filas_reales
    assert len(llamadas) == 1


def test_modo_demo_sin_cache_falla(monkeypatch):
    monkeypatch.setenv("SECOP_MODO_DEMO", "1")
    with pytest.raises(ConnectionError):
        socrata.consultar({"$limit": 1})


# ### Reintentos ###
def test_reintenta_en_429_y_luego_responde(monkeypatch, filas_reales):
    respuestas = [_respuesta(429, {}), _respuesta(503, {}), _respuesta(200, filas_reales)]
    monkeypatch.setattr(httpx, "get", lambda *a, **k: respuestas.pop(0))
    monkeypatch.setattr(socrata.time, "sleep", lambda s: None)

    assert socrata.consultar({"$limit": 25}) == filas_reales


def test_se_rinde_tras_max_intentos(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _respuesta(500, {}))
    monkeypatch.setattr(socrata.time, "sleep", lambda s: None)

    with pytest.raises(ConnectionError):
        socrata.consultar({"$limit": 1})


def test_400_no_se_reintenta(monkeypatch):
    llamadas = []

    def falso_get(*a, **k):
        llamadas.append(1)
        return _respuesta(400, {"message": "query mal"})

    monkeypatch.setattr(httpx, "get", falso_get)
    with pytest.raises(ValueError):
        socrata.consultar({"$where": "x ="})
    assert len(llamadas) == 1


def test_envia_app_token(monkeypatch):
    vistos = {}

    def falso_get(url, params, headers, timeout):
        vistos.update(headers)
        return _respuesta(200, [])

    monkeypatch.setenv("SOCRATA_APP_TOKEN", "abc123")
    monkeypatch.setattr(httpx, "get", falso_get)
    socrata.consultar({"$limit": 1})
    assert vistos["X-App-Token"] == "abc123"


# ### Paginación ###
def test_paginacion_recorre_offsets(monkeypatch):
    total = [{"id_contrato": str(i)} for i in range(2500)]
    offsets = []

    def falso_get(url, params, headers, timeout):
        offsets.append(params["$offset"])
        return _respuesta(200, total[params["$offset"]: params["$offset"] + params["$limit"]])

    monkeypatch.setattr(httpx, "get", falso_get)
    filas = socrata.consultar_paginado({"$select": "id_contrato"})

    assert len(filas) == 2500
    assert offsets == [0, 1000, 2000]


def test_paginacion_respeta_maximo(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, params, headers, timeout: _respuesta(200, [{"x": 1}] * params["$limit"]))
    filas = socrata.consultar_paginado({}, max_filas=99_999)
    assert len(filas) == socrata.MAX_FILAS
