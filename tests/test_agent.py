# ### Archivo: test_agent.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Pruebas del bucle del agente con un cliente falso, sin gastar API

from datetime import date, datetime, timedelta
from types import SimpleNamespace as NS

from secop_agent import agent, tools


def _uso():
    return NS(input_tokens=100, output_tokens=50, cache_creation_input_tokens=0, cache_read_input_tokens=0)


def _texto(t):
    return NS(content=[NS(type="text", text=t)], stop_reason="end_turn", usage=_uso())


def _pide_herramienta(nombre, entrada, id_bloque="t1"):
    return NS(content=[NS(type="tool_use", id=id_bloque, name=nombre, input=entrada)], stop_reason="tool_use", usage=_uso())


def _cliente_falso(respuestas, peticiones):
    def crear(**kwargs):
        peticiones.append(kwargs)
        return respuestas.pop(0)

    mensajes = NS(create=crear)
    return NS(messages=mensajes, beta=NS(messages=mensajes))


def test_bucle_llama_herramienta_y_responde(monkeypatch):
    peticiones = []
    respuestas = [_pide_herramienta("detalle_contrato", {"id_contrato": "CO1.PCCNTR.1"}), _texto("Listo")]
    monkeypatch.setattr(agent, "crear_cliente", lambda api_key=None: _cliente_falso(respuestas, peticiones))
    monkeypatch.setattr(tools, "FUNCIONES", {**tools.FUNCIONES, "detalle_contrato": lambda id_contrato: {"ok": id_contrato}})

    r = agent.responder("hola", modelo="claude-haiku-5-5")

    assert r["respuesta"] == "Listo"
    assert r["llamadas_herramientas"] == 1
    assert r["tokens"]["entrada"] == 200
    # resultado vuelve al modelo
    ultimo = peticiones[1]["messages"][-2]["content"][0]
    assert ultimo["type"] == "tool_result" and "CO1.PCCNTR.1" in ultimo["content"]


def test_error_de_herramienta_va_como_is_error(monkeypatch):
    peticiones = []
    respuestas = [_pide_herramienta("agregar", {"filtros": {}, "agrupar_por": "color"}), _texto("No pude")]
    monkeypatch.setattr(agent, "crear_cliente", lambda api_key=None: _cliente_falso(respuestas, peticiones))

    r = agent.responder("x", modelo="claude-haiku-5-5")
    resultado = peticiones[1]["messages"][-2]["content"][0]

    assert resultado["is_error"] is True
    assert r["traza"][0]["error"]


def test_limite_de_llamadas_cierra_sin_herramientas(monkeypatch):
    peticiones = []
    respuestas = [_pide_herramienta("detalle_contrato", {"id_contrato": str(i)}, f"t{i}") for i in range(agent.MAX_LLAMADAS)]
    respuestas.append(_texto("Resumen final"))
    monkeypatch.setattr(agent, "crear_cliente", lambda api_key=None: _cliente_falso(respuestas, peticiones))
    monkeypatch.setattr(tools, "FUNCIONES", {**tools.FUNCIONES, "detalle_contrato": lambda id_contrato: {}})

    r = agent.responder("x", modelo="claude-haiku-5-5")

    assert r["llamadas_herramientas"] == agent.MAX_LLAMADAS
    assert peticiones[-1]["tool_choice"] == {"type": "none"}


def test_sonnet_usa_fallback_del_servidor(monkeypatch):
    peticiones = []
    monkeypatch.setattr(agent, "crear_cliente", lambda api_key=None: _cliente_falso([_texto("ok")], peticiones))

    agent.responder("x", modelo="claude-sonnet-5-5")

    assert peticiones[0]["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in peticiones[0]["betas"]


def test_costo_haiku():
    uso = {"entrada": 1_000_000, "salida": 1_000_000, "cache_escritura": 0, "cache_lectura": 0}
    assert agent.calcular_costo("claude-haiku-5-5", uso) == 0.60


def test_prompt_usa_la_fecha_de_colombia_al_preguntar(monkeypatch):
    # la fecha se arma en cada pregunta, no al importar
    monkeypatch.setattr(agent, "hoy_colombia", lambda: date(2030, 1, 2))
    assert "Hoy es 2030-01-02." in agent.prompt_sistema()


def test_hoy_colombia_va_cinco_horas_detras_de_utc():
    ahora = datetime.now(agent.ZONA_COLOMBIA)
    assert ahora.utcoffset() == timedelta(hours=-5)
