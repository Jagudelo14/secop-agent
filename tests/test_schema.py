# ### Archivo: test_schema.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Pruebas de normalización, validación de filtros y armado de SoQL

import pytest

from secop_agent import schema


# ### Normalización ###
def test_normalizar_texto_quita_tildes_y_signos():
    assert schema.normalizar_texto("  Alcaldía  de Bogotá D.C. ") == "ALCALDIA DE BOGOTA D C"


def test_normalizar_documento():
    assert schema.normalizar_documento("899.999.061-9") == "8999990619"
    assert schema.normalizar_documento(None) == ""


def test_a_numero_tolera_basura():
    assert schema.a_numero("26800000") == 26_800_000
    assert schema.a_numero("$ 1,500") == 1500
    assert schema.a_numero(None) == 0
    assert schema.a_numero("") == 0


def test_extraer_url_de_objeto():
    assert schema.extraer_url({"url": "https://x"}) == "https://x"
    assert schema.extraer_url(None) == ""


def test_limpiar_contrato_real(filas_reales):
    contrato = schema.limpiar_contrato(filas_reales[0])
    assert contrato["id_contrato"].startswith("CO1.PCCNTR.")
    assert isinstance(contrato["valor"], float)
    assert contrato["url"].startswith("https://")


def test_enmascara_cedulas(monkeypatch):
    monkeypatch.setenv("SECOP_OCULTAR_DOCUMENTOS", "1")
    assert schema.enmascarar_documento("1234567088", "Cédula de Ciudadanía") == "***088"
    assert schema.enmascarar_documento("899999115", "NIT") == "899999115"


# ### Validación ###
def test_filtro_desconocido_falla():
    with pytest.raises(ValueError):
        schema.validar_filtros({"entidad": "x"})


def test_modalidad_invalida_falla():
    with pytest.raises(ValueError):
        schema.validar_filtros({"modalidades": ["directa"]})


def test_anio_fuera_de_rango():
    with pytest.raises(ValueError):
        schema.validar_filtros({"anio": 1990})


# ### SoQL ###
def test_where_completo():
    where = schema.construir_where({
        "codigo_entidad": "700218068",
        "anio": 2025,
        "modalidades": ["Contratación directa"],
        "valor_min": 1000,
    })
    assert "codigo_entidad = 700218068" in where
    assert "date_extract_y(fecha_de_firma) = 2025" in where
    assert "modalidad_de_contratacion in ('Contratación directa')" in where
    assert "valor_del_contrato >= 1000" in where
    assert "estado_contrato not in ('Borrador', 'Cancelado')" in where


def test_where_escapa_comillas():
    where = schema.construir_where({"ciudad": "Bogotá' OR 1=1 --"})
    assert "''" in where


def test_patron_like_ignora_tildes():
    assert schema.patron_like("Bogotá") == "B_G_T_"
