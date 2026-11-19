# ### Archivo: test_agent_gemini.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Pruebas del bucle con Gemini usando un cliente falso, sin gastar cuota

from types import SimpleNamespace as NS

from secop_agent import agent, agent_gemini, tools


def _uso():
    return NS(prompt_token_count=100, candidates_token_count=50, thoughts_token_count=0, cached_content_token_count=0)


def _respuesta(texto=None, llamadas=None):
    contenido = NS(role="model", parts=[])
    return NS(
        candidates=[NS(content=contenido, finish_reason="STOP")],
        function_calls=llamadas,
        text=texto,
        usage_metadata=_uso(),
    )


def _cliente(respuestas, vistos):
    def generar(model, contents, config):
        vistos.append({"contents": list(contents), "config": config})
        return respuestas.pop(0)
    return NS(models=NS(generate_content=generar))


def _preparar(monkeypatch, respuestas):
    vistos = []
    monkeypatch.setattr(agent_gemini, "crear_cliente", lambda api_key=None: _cliente(respuestas, vistos))
    # sin esperas
    monkeypatch.setattr(agent_gemini, "_esperar_turno", lambda: None)
    return vistos


def test_corre_herramienta_y_responde(monkeypatch):
    monkeypatch.setattr(tools, "ejecutar", lambda nombre, args: {"num_contratos_total": 3})
    llamada = NS(id="f1", name="consultar_contratos", args={"filtros": {"anio": 2024}})
    vistos = _preparar(monkeypatch, [_respuesta(llamadas=[llamada]), _respuesta(texto="Son 3 contratos.")])

    r = agent_gemini.responder("¿cuántos?", modelo="gemini-3.5-flash-lite")

    assert r["respuesta"] == "Son 3 contratos."
    assert r["llamadas_herramientas"] == 1
    assert r["costo_usd"] == 0.0
    # resultado devuelto al modelo
    parte = vistos[1]["contents"][-1]["parts"][0]["function_response"]
    assert parte["name"] == "consultar_contratos" and "3" in parte["response"]["resultado"]


def test_error_de_herramienta_vuelve_al_modelo(monkeypatch):
    def falla(nombre, args):
        raise ValueError("filtro malo")
    monkeypatch.setattr(tools, "ejecutar", falla)
    llamada = NS(id="f1", name="agregar", args={})
    vistos = _preparar(monkeypatch, [_respuesta(llamadas=[llamada]), _respuesta(texto="No pude.")])

    r = agent_gemini.responder("x", modelo="gemini-3.5-flash-lite")

    assert r["traza"][0]["error"] == "filtro malo"
    assert vistos[1]["contents"][-1]["parts"][0]["function_response"]["response"] == {"error": "filtro malo"}


def test_cierra_sin_herramientas_al_limite(monkeypatch):
    monkeypatch.setattr(tools, "ejecutar", lambda nombre, args: {})
    llamada = NS(id="f", name="buscar_entidad", args={"nombre": "x"})
    respuestas = [_respuesta(llamadas=[llamada]) for _ in range(agent.MAX_LLAMADAS)] + [_respuesta(texto="fin")]
    vistos = _preparar(monkeypatch, respuestas)

    r = agent_gemini.responder("x", modelo="gemini-3.5-flash-lite")

    assert r["llamadas_herramientas"] == agent.MAX_LLAMADAS
    assert vistos[-1]["config"]["tool_config"]["function_calling_config"]["mode"] == "NONE"


def test_desvio_por_proveedor(monkeypatch):
    monkeypatch.setenv("PROVEEDOR", "gemini")
    assert agent.usa_gemini() is True
    assert agent.usa_gemini("claude-haiku-5-5") is False
    monkeypatch.setenv("PROVEEDOR", "anthropic")
    assert agent.usa_gemini() is False


def test_pasa_al_respaldo_si_esta_saturado(monkeypatch):
    from google.genai import errors
    monkeypatch.setenv("GEMINI_RESPALDO", "respaldo-a,respaldo-b")
    monkeypatch.setattr(agent_gemini, "_esperar_turno", lambda: None)
    pedidos = []

    def generar(model, contents, config):
        pedidos.append(model)
        # solo el último responde
        if model != "respaldo-b":
            raise errors.ServerError(503, {"error": {"code": 503, "message": "saturado", "status": "UNAVAILABLE"}})
        return _respuesta(texto="hola")

    cliente = NS(models=NS(generate_content=generar))
    _, usado = agent_gemini._pedir_respuesta(cliente, "principal", [])
    assert pedidos == ["principal", "respaldo-a", "respaldo-b"]
    assert usado == "respaldo-b"


def test_rechaza_cifras_sin_herramienta_de_datos(monkeypatch):
    monkeypatch.setattr(tools, "ejecutar", lambda nombre, args: {"candidatas": []})
    llamada = NS(id="f1", name="buscar_entidad", args={"nombre": "Alcaldía de Bogotá"})
    respuestas = [
        _respuesta(llamadas=[llamada]),
        _respuesta(texto="Contrató $547.410.970.672 en 460 contratos."),
        _respuesta(texto="¿Cuál de estas entidades quieres consultar?"),
    ]
    vistos = _preparar(monkeypatch, respuestas)

    r = agent_gemini.responder("¿Cuánto contrató la Alcaldía de Bogotá?", modelo="gemini-3.5-flash-lite")

    # se le devolvió una vez
    assert r["respuesta"] == "¿Cuál de estas entidades quieres consultar?"
    assert vistos[2]["contents"][-1]["parts"][0]["text"] == agent.AVISO_SIN_RESPALDO


def test_cifras_con_herramienta_de_datos_pasan():
    traza = [{"herramienta": "agregar", "error": None}]
    assert not agent.cifras_sin_respaldo("Total: $1.000", traza)
    assert agent.cifras_sin_respaldo("Total: $1.000", [{"herramienta": "buscar_entidad", "error": None}])
    assert not agent.cifras_sin_respaldo("Firmó 3 contratos", [])


def test_tiempo_agotado_en_herramienta_vuelve_al_modelo(monkeypatch):
    def lento(nombre, args):
        raise TimeoutError("The read operation timed out")
    monkeypatch.setattr(tools, "ejecutar", lento)
    llamada = NS(id="f1", name="agregar", args={})
    vistos = _preparar(monkeypatch, [_respuesta(llamadas=[llamada]), _respuesta(texto="No pude consultar.")])

    r = agent_gemini.responder("x", modelo="gemini-3.5-flash-lite")

    # no tumba la pregunta
    assert r["respuesta"] == "No pude consultar."
    assert "timed out" in vistos[1]["contents"][-1]["parts"][0]["function_response"]["response"]["error"]
