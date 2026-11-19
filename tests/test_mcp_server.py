# ### Archivo: test_mcp_server.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-19
# Descripción: El servidor MCP publica las mismas herramientas, descripciones y esquemas que ve el agente

import asyncio

from secop_agent import mcp_server, tools


def _publicadas():
    return {h.name: h for h in asyncio.run(mcp_server.servidor.list_tools())}


def test_mismas_herramientas():
    assert set(_publicadas()) == {h["name"] for h in tools.HERRAMIENTAS}


def test_mismo_esquema_y_descripcion():
    publicadas = _publicadas()
    for herramienta in tools.HERRAMIENTAS:
        publicada = publicadas[herramienta["name"]]
        assert publicada.description == herramienta["description"]
        assert publicada.input_schema == herramienta["input_schema"]


def test_filtros_no_quedan_vacios():
    filtros = _publicadas()["consultar_contratos"].input_schema["properties"]["filtros"]
    assert {"codigo_entidad", "anio_desde", "objeto_contiene"} <= set(filtros["properties"])
