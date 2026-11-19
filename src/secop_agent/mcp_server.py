# ### Archivo: mcp_server.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Servidor MCP (SDK mcp 2.x, antes FastMCP) con las mismas herramientas de tools.py

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

from secop_agent import tools

load_dotenv()

servidor = MCPServer(
    "secop-ii",
    instructions="Consulta contratos públicos colombianos de SECOP II. Las alertas son patrones para revisar, no implican irregularidad.",
)

# misma descripción que ve el agente
DESCRIPCIONES = {h["name"]: h["description"] for h in tools.HERRAMIENTAS}


# ### Herramientas MCP ###
@servidor.tool(description=DESCRIPCIONES["buscar_entidad"])
def buscar_entidad(nombre: str, limite: int = 10) -> dict:
    return tools.buscar_entidad(nombre, limite)


@servidor.tool(description=DESCRIPCIONES["consultar_contratos"])
def consultar_contratos(filtros: dict, limite: int = 50, orden: str = "valor_desc") -> dict:
    return tools.consultar_contratos(filtros, limite, orden)


@servidor.tool(description=DESCRIPCIONES["agregar"])
def agregar(filtros: dict, agrupar_por: str, metrica: str, top: int = 10) -> dict:
    return tools.agregar(filtros, agrupar_por, metrica, top)


@servidor.tool(description=DESCRIPCIONES["detectar_alertas"])
def detectar_alertas(codigo_entidad: str, anio: int, parametros: dict | None = None) -> dict:
    return tools.detectar_alertas(codigo_entidad, anio, parametros)


@servidor.tool(description=DESCRIPCIONES["detalle_contrato"])
def detalle_contrato(id_contrato: str) -> dict:
    return tools.detalle_contrato(id_contrato)


# ### Esquemas ###
# mismo esquema que ve el agente; sin esto filtros sale vacío
for herramienta in tools.HERRAMIENTAS:
    servidor._tool_manager.get_tool(herramienta["name"]).parameters = herramienta["input_schema"]


def main():
    servidor.run()


if __name__ == "__main__":
    main()
