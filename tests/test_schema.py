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


# ### Capacidades nuevas ###
def test_rango_de_anios():
    where = schema.construir_where({"anio_desde": 2020, "anio_hasta": 2024})
    assert "date_extract_y(fecha_de_firma) >= 2020" in where
    assert "date_extract_y(fecha_de_firma) <= 2024" in where


def test_anio_y_rango_no_se_combinan():
    with pytest.raises(ValueError):
        schema.validar_filtros({"anio": 2022, "anio_desde": 2020})
    with pytest.raises(ValueError):
        schema.validar_filtros({"anio_desde": 2024, "anio_hasta": 2020})


def test_objeto_contiene_con_y_sin_tilde():
    where = schema.construir_where({"objeto_contiene": ["vía"]})
    assert "like '%VIA%'" in where and "like '%VÍA%'" in where
    # no comodines en vocales
    assert "V__" not in where


def test_tipo_persona():
    assert "tipodocproveedor in ('NIT')" in schema.construir_where({"tipo_persona": "jurídica"})
    natural = schema.construir_where({"tipo_persona": "natural"})
    assert "tipodocproveedor not in ('NIT', 'Otro', 'No Definido')" in natural
    with pytest.raises(ValueError):
        schema.validar_filtros({"tipo_persona": "empresa"})


def test_duracion_minima():
    where = schema.construir_where({"duracion_min_dias": 184})
    assert "date_diff_d(fecha_de_fin_del_contrato, fecha_de_inicio_del_contrato) >= 184" in where


def test_varias_entidades_y_nombre_que_empieza():
    where = schema.construir_where({"codigo_entidad": ["700221021", "712170091"]})
    assert "codigo_entidad in (700221021, 712170091)" in where
    where = schema.construir_where({"nombre_entidad_empieza": "Distrito Especial"})
    # espacio como comodín, por nombres con espacios dobles
    assert "upper(nombre_entidad) like 'DISTRITO%ESPECIAL%'" in where
    with pytest.raises(ValueError):
        schema.validar_filtros({"nombre_entidad_empieza": "abc"})


def test_limites_estrictos():
    where = schema.construir_where({"valor_mayor_que": 1_000_000_000, "duracion_mayor_que_dias": 183})
    assert "valor_del_contrato > 1000000000" in where
    assert "fecha_de_inicio_del_contrato) > 183" in where


def test_objeto_con_todas_las_palabras():
    where = schema.construir_where({"objeto_contiene_todas": ["mantenimiento", "via"]})
    assert where.count(" AND (upper(objeto_del_contrato) like") == 2


def test_nombre_entidad_contiene():
    where = schema.construir_where({"nombre_entidad_contiene": ["alcald", "municipio"]})
    assert "upper(nombre_entidad) like '%ALCALD%'" in where and "'%MUNICIPIO%'" in where
    # alcaldía sola también trae municipio
    where = schema.construir_where({"nombre_entidad_contiene": ["ALCALDIA"]})
    assert "'%MUNICIPIO%'" in where
