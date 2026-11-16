# ### Archivo: conftest.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Fixtures compartidas, caché temporal y bloqueo de red

import json
from pathlib import Path

import pytest

CARPETA_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def entorno_aislado(tmp_path, monkeypatch):
    # caché limpia por test
    monkeypatch.setenv("SECOP_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SECOP_MODO_DEMO", "0")
    monkeypatch.setenv("SECOP_OCULTAR_DOCUMENTOS", "0")
    monkeypatch.delenv("SOCRATA_APP_TOKEN", raising=False)

    # sin red en tests
    def sin_red(*args, **kwargs):
        raise AssertionError("Un test intentó salir a internet")

    monkeypatch.setattr("httpx.get", sin_red)


@pytest.fixture
def filas_reales():
    return json.loads((CARPETA_FIXTURES / "contratos_reales.json").read_text(encoding="utf-8"))
