# ### Archivo: agent_gemini.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Bucle del agente con Gemini (nivel gratuito), mismas herramientas y misma salida que agent.py

import json
import os
import time

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors

from secop_agent import tools
from secop_agent.agent import (
    AVISO_SIN_RESPALDO,
    MAX_CARACTERES_RESULTADO,
    MAX_LLAMADAS,
    PROMPT_SISTEMA,
    cifras_sin_respaldo,
    urls_en,
)

load_dotenv()

# ### Configuración ###
MODELO_GEMINI = "gemini-3.8-flash"
# si el principal está saturado
MODELOS_RESPALDO = "gemini-3.5-flash,gemini-3.5-flash-lite"
# nivel gratuito, ajustable
RPM_DEFECTO = 5
MAX_REINTENTOS = 3
TIEMPO_MAXIMO_MS = 60_000

# marcas de tiempo últimas peticiones
_peticiones = []


# ### Límite por minuto ###
def _esperar_turno():
    rpm = int(os.getenv("GEMINI_RPM", RPM_DEFECTO))
    ahora = time.monotonic()
    # solo último minuto
    _peticiones[:] = [t for t in _peticiones if ahora - t < 60]
    if len(_peticiones) >= rpm:
        # esperar al más viejo
        time.sleep(60 - (ahora - _peticiones[0]) + 0.5)
    _peticiones.append(time.monotonic())


def _respaldos():
    texto = os.getenv("GEMINI_RESPALDO", MODELOS_RESPALDO)
    return [m.strip() for m in texto.split(",") if m.strip()]


def _cuota_diaria_agotada(error):
    texto = str(error).lower()
    return "perday" in texto or "per day" in texto or "requests_per_day" in texto


# ### Cliente ###
def crear_cliente(api_key=None):
    return genai.Client(
        api_key=api_key or os.getenv("GEMINI_API_KEY"),
        # tope en ms, reintentos propios
        http_options={"timeout": TIEMPO_MAXIMO_MS, "retry_options": {"attempts": 1}},
    )


def _declaraciones():
    # mismo esquema json que claude
    return [
        {"name": h["name"], "description": h["description"], "parameters_json_schema": h["input_schema"]}
        for h in tools.HERRAMIENTAS
    ]


def _pedir_respuesta(cliente, modelo, contenidos, permitir_herramientas=True):
    configuracion = {
        "system_instruction": PROMPT_SISTEMA,
        "tools": [{"function_declarations": _declaraciones()}],
        # bucle manual, no automático
        "automatic_function_calling": {"disable": True},
        "tool_config": {"function_calling_config": {"mode": "AUTO" if permitir_herramientas else "NONE"}},
    }

    # principal y respaldos en orden
    candidatos = [modelo] + [m for m in _respaldos() if m != modelo]
    ultimo_error = None

    for candidato in candidatos:
        for intento in range(MAX_REINTENTOS):
            _esperar_turno()
            try:
                respuesta = cliente.models.generate_content(model=candidato, contents=contenidos, config=configuracion)
                return respuesta, candidato
            except (httpx.TimeoutException, httpx.TransportError, TimeoutError) as error:
                # lento o sin red, siguiente modelo
                ultimo_error = error
                break
            except errors.APIError as error:
                ultimo_error = error
                if error.code == 429 and _cuota_diaria_agotada(error):
                    raise ConnectionError("Cuota diaria gratuita de Gemini agotada, intenta mañana") from error
                # saturado, siguiente modelo
                if error.code in (500, 503, 504):
                    break
                # límite por minuto, esperar
                if error.code == 429:
                    time.sleep(20 * (intento + 1))
                    continue
                raise

    raise ConnectionError(f"Ningún modelo de Gemini respondió ({', '.join(candidatos)}): {ultimo_error}")


# ### Herramientas ###
def _correr_herramienta(llamada):
    argumentos = dict(llamada.args or {})
    try:
        resultado = tools.ejecutar(llamada.name, argumentos)
        texto = json.dumps(resultado, ensure_ascii=False, default=str)
        # resultado demasiado largo
        if len(texto) > MAX_CARACTERES_RESULTADO:
            texto = texto[:MAX_CARACTERES_RESULTADO] + '... [recortado: pide menos filas o usa agregar]'
        return {"resultado": texto}, None
    # red caída o tiempo agotado incluidos
    except (ValueError, TypeError, OSError, httpx.HTTPError) as error:
        return {"error": str(error)}, str(error)


def _parte_respuesta(llamada, contenido):
    return {"function_response": {"id": llamada.id, "name": llamada.name, "response": contenido}}


def _sumar_uso(acumulado, uso):
    if uso is None:
        return
    acumulado["entrada"] += uso.prompt_token_count or 0
    # razonamiento cuenta como salida
    acumulado["salida"] += (uso.candidates_token_count or 0) + (uso.thoughts_token_count or 0)
    acumulado["cache_lectura"] += uso.cached_content_token_count or 0


# ### Bucle del agente ###
def responder(pregunta, modelo=None, api_key=None, historial=None):
    modelo = modelo or os.getenv("MODELGEMINI", MODELO_GEMINI)
    cliente = crear_cliente(api_key)
    # historial + pregunta nueva
    contenidos = list(historial or []) + [{"role": "user", "parts": [{"text": pregunta}]}]

    uso = {"entrada": 0, "salida": 0, "cache_escritura": 0, "cache_lectura": 0}
    traza = []
    corregida = False
    inicio = time.perf_counter()

    while True:
        # límite alcanzado, cerrar sin herramientas
        permitir = len(traza) < MAX_LLAMADAS
        # seguir con el que respondió
        respuesta, modelo = _pedir_respuesta(cliente, modelo, contenidos, permitir_herramientas=permitir)
        _sumar_uso(uso, respuesta.usage_metadata)
        usado = modelo

        # sin candidato, bloqueado
        if not respuesta.candidates or respuesta.candidates[0].content is None:
            texto = "El modelo no pudo responder esta pregunta."
            break
        # contenido completo, conserva firmas
        contenidos.append(respuesta.candidates[0].content)

        llamadas = respuesta.function_calls or []
        if not llamadas:
            texto = (respuesta.text or "").strip()
            # cifras inventadas, una corrección
            if not corregida and cifras_sin_respaldo(texto, traza):
                corregida = True
                contenidos.append({"role": "user", "parts": [{"text": AVISO_SIN_RESPALDO}]})
                continue
            if str(respuesta.candidates[0].finish_reason).endswith("MAX_TOKENS"):
                texto += "\n\n[respuesta cortada por longitud]"
            break

        partes = []
        for llamada in llamadas:
            # sobre el límite, error
            if len(traza) >= MAX_LLAMADAS:
                partes.append(_parte_respuesta(llamada, {
                    "error": f"límite de {MAX_LLAMADAS} llamadas alcanzado. Responde con lo que ya tienes."
                }))
                continue

            # correr y medir
            t0 = time.perf_counter()
            contenido, error = _correr_herramienta(llamada)
            partes.append(_parte_respuesta(llamada, contenido))
            traza.append({
                "herramienta": llamada.name,
                "argumentos": dict(llamada.args or {}),
                "error": error,
                "segundos": round(time.perf_counter() - t0, 2),
                "urls": [] if error else urls_en(contenido["resultado"]),
            })

        # todos los resultados en un solo mensaje
        contenidos.append({"role": "user", "parts": partes})

    return {
        "respuesta": texto,
        "modelo": usado,
        "llamadas_herramientas": len(traza),
        "traza": traza,
        "tokens": uso,
        # nivel gratuito
        "costo_usd": 0.0,
        "latencia_seg": round(time.perf_counter() - inicio, 2),
        "mensajes": contenidos,
    }
