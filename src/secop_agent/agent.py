# ### Archivo: agent.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Bucle del agente con tool use nativo del SDK anthropic, sin frameworks

import json
import os
import re
import time
from datetime import date

import anthropic
import httpx
from dotenv import load_dotenv

from secop_agent import tools

load_dotenv()

# ### Configuración ###
MODELO_DEFECTO = "claude-sonnet-5-5"
MAX_LLAMADAS = 8
MAX_TOKENS = 16000
MAX_CARACTERES_RESULTADO = 60_000

# USD por millón de tokens
PRECIOS = {
    "claude-sonnet-5-5": {"entrada": 2.00, "salida": 10.00},
    "claude-haiku-5-5": {"entrada": 0.10, "salida": 0.50},
}

# fallback del servidor si hay rechazo
MODELOS_CON_FALLBACK = {"claude-sonnet-5-5"}

# historial en docs/prompt-versiones.md
VERSION_PROMPT = "v9"

PROMPT_SISTEMA = f"""Eres un analista de contratación pública colombiana. Respondes preguntas sobre contratos de SECOP II (conjunto jbjy-vk9h de datos.gov.co) usando solo las herramientas disponibles. Hoy es {date.today().isoformat()}.

Reglas:
- Toda cifra que des (montos, conteos, porcentajes) tiene que venir de un resultado de herramienta en esta conversación. Si una herramienta falla o no devuelve datos, dilo y no estimes.
- Cada cifra va acompañada del enlace (url) al contrato o contratos de los que sale. En rankings, pon el enlace de al menos el contrato mayor de cada fila.
- Copia los enlaces tal como vienen en el campo url de los resultados (empiezan por https://community.secop.gov.co). Nunca construyas ni inventes un enlace; si una fila no trae url, pon solo el id_contrato.
- Antes de filtrar por una entidad, resuélvela con buscar_entidad y filtra por codigo_entidad.
- Cuando la pregunta nombra una entidad pública como quien contrata, resuélvela con buscar_entidad y filtra por codigo_entidad, aunque su nombre incluya un lugar. Usa los filtros departamento y ciudad solo cuando la pregunta pide contratos según la ubicación y no según quién contrata.
- Si buscar_entidad devuelve varias candidatas y ninguna coincide exactamente con el nombre que pidió el usuario, no elijas tú: lista las candidatas y pregunta cuál quiere, sin dar cifras. La excepción es cuando el campo dependencias indica que las candidatas son partes de una misma entidad: entonces tómalas juntas con nombre_entidad_empieza y dilo en la respuesta.
- Si buscar_entidad devuelve entidad_completa (una gobernación o alcaldía con todas sus dependencias), filtra con codigo_entidad igual a esa lista de códigos, aunque los nombres sean distintos, y di en la respuesta que incluye todas sus dependencias. Si además trae homonimas y la pregunta no dice el departamento, usa los códigos del primer grupo (el de más contratos) y aclara que existe otro municipio con el mismo nombre.
- Un ranking de municipios, ciudades o departamentos se arma por ubicación: agrupa por ciudad o por departamento, que suma todas las entidades ubicadas allí. Agrupa por entidad solo si preguntan por las alcaldías, gobernaciones u otras entidades.
- Límites: "superior a", "mayor a" o "más de" no incluyen el límite: usa valor_mayor_que o duracion_mayor_que_dias. "Desde", "mínimo" o "al menos" sí lo incluyen: usa valor_min o duracion_min_dias. Para pasar meses a días usa 30,44 días por mes y redondea (6 meses = 183 días, 1 año = 365).
- Si el tema es el nombre de un programa público con sigla conocida (alimentación escolar es PAE), usa objeto_contiene con el nombre completo y la sigla, no palabras sueltas.
- Para buscar un tema en el objeto, si el tema junta una actividad y una cosa, usa objeto_contiene_todas con la raíz de cada una. No agregues filtros que la pregunta no pide (por ejemplo, un tipo de contrato que no menciona).
- Si la pregunta habla de un tipo de entidades en un lugar (las alcaldías de un departamento, los hospitales de una ciudad), combina departamento o ciudad con nombre_entidad_contiene y las raíces con que se nombran esas entidades.
- Para "objetos contractuales" o "conceptos" que más acumulan, agrupa por objeto.
- Para un periodo de varios años usa anio_desde y anio_hasta. Si piden el valor de cada año por separado, agrupa por anio.
- Cuando listes contratos y el total supere los que devolvió la herramienta, di el total real y aclara que muestras solo una parte.
- Escribe los montos en pesos completos con separador de miles con punto, ej: $1.234.567.890. Los conteos como enteros.
- Para rankings usa una tabla markdown con posición, nombre, documento, número de contratos, total y enlace.
- Cuando listes contratos de un filtro, incluye todos los id_contrato devueltos (formato CO1.PCCNTR.123) si son 50 o menos. El texto de cada enlace es el id_contrato, nunca "Ver contrato".
- Las alertas solo las decide detectar_alertas. Nunca califiques algo como irregular por tu cuenta y repite siempre el aviso: "patrón para revisar, no implica irregularidad".
- Si la pregunta pide algo que estos datos no contienen o que no se puede verificar con ellos, dilo y no respondas de memoria.
- Responde en español, breve y directo."""


# ### Cliente ###
def crear_cliente(api_key=None):
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


def _pedir_respuesta(cliente, modelo, mensajes, permitir_herramientas=True):
    # sistema y herramientas en caché
    herramientas = [dict(h) for h in tools.HERRAMIENTAS]
    herramientas[-1]["cache_control"] = {"type": "ephemeral"}

    parametros = {
        "model": modelo,
        "max_tokens": MAX_TOKENS,
        "system": [{"type": "text", "text": PROMPT_SISTEMA, "cache_control": {"type": "ephemeral"}}],
        "tools": herramientas,
        "tool_choice": {"type": "auto"} if permitir_herramientas else {"type": "none"},
        "output_config": {"effort": os.getenv("EFFORT", "medium")},
        "messages": mensajes,
    }

    # sonnet con respaldo
    if modelo in MODELOS_CON_FALLBACK:
        return cliente.beta.messages.create(
            **parametros,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    return cliente.messages.create(**parametros)


# ### Costos ###
def _sumar_uso(acumulado, uso):
    acumulado["entrada"] += uso.input_tokens or 0
    acumulado["salida"] += uso.output_tokens or 0
    acumulado["cache_escritura"] += getattr(uso, "cache_creation_input_tokens", 0) or 0
    acumulado["cache_lectura"] += getattr(uso, "cache_read_input_tokens", 0) or 0


def calcular_costo(modelo, uso):
    precio = PRECIOS.get(modelo, PRECIOS[MODELO_DEFECTO])
    entrada = (
        uso["entrada"]
        + uso["cache_escritura"] * 1.25
        + uso["cache_lectura"] * 0.10
    ) * precio["entrada"]
    # costo salida
    salida = uso["salida"] * precio["salida"]
    return round((entrada + salida) / 1_000_000, 6)


# ### Control de cifras ###
HERRAMIENTAS_DATOS = {"consultar_contratos", "agregar", "detectar_alertas", "detalle_contrato"}
AVISO_SIN_RESPALDO = (
    "Tu respuesta trae montos en pesos pero no llamaste ninguna herramienta de datos "
    "(consultar_contratos, agregar, detectar_alertas o detalle_contrato), así que esas cifras no tienen respaldo. "
    "Consulta los datos con una herramienta o, si la entidad es ambigua, pregunta cuál quiere el usuario sin dar cifras."
)


def cifras_sin_respaldo(texto, traza):
    # montos sin herramienta de datos
    usadas = {paso["herramienta"] for paso in traza if not paso["error"]}
    return bool(re.search(r"\$\s*\d", texto or "")) and not usadas & HERRAMIENTAS_DATOS


# ### Herramientas ###
def urls_en(texto):
    # enlaces reales del resultado
    return sorted(set(re.findall(r'https?://[^\s"\\]+', texto or "")))


def _correr_herramienta(bloque):
    try:
        resultado = tools.ejecutar(bloque.name, dict(bloque.input))
        texto = json.dumps(resultado, ensure_ascii=False, default=str)
        # resultado demasiado largo
        if len(texto) > MAX_CARACTERES_RESULTADO:
            texto = texto[:MAX_CARACTERES_RESULTADO] + '... [recortado: pide menos filas o usa agregar]'
        return {"type": "tool_result", "tool_use_id": bloque.id, "content": texto}, None
    # red caída o tiempo agotado incluidos
    except (ValueError, TypeError, OSError, httpx.HTTPError) as error:
        return {
            "type": "tool_result",
            "tool_use_id": bloque.id,
            "content": f"Error: {error}",
            "is_error": True,
        }, str(error)


def _texto_final(respuesta):
    return "\n".join(b.text for b in respuesta.content if b.type == "text").strip()


# ### Proveedor ###
def usa_gemini(modelo=None):
    if modelo:
        return modelo.startswith("gemini")
    return os.getenv("PROVEEDOR", "anthropic").lower() == "gemini"


# ### Bucle del agente ###
def responder(pregunta, modelo=None, api_key=None, historial=None):
    # desvío a gemini
    if usa_gemini(modelo):
        from secop_agent import agent_gemini
        return agent_gemini.responder(pregunta, modelo=modelo, api_key=api_key, historial=historial)

    modelo = modelo or os.getenv("MODEL", MODELO_DEFECTO)
    cliente = crear_cliente(api_key)
    # historial + pregunta nueva
    mensajes = list(historial or []) + [{"role": "user", "content": pregunta}]

    uso = {"entrada": 0, "salida": 0, "cache_escritura": 0, "cache_lectura": 0}
    traza = []
    corregida = False
    inicio = time.perf_counter()

    while True:
        # límite alcanzado, cerrar sin herramientas
        permitir = len(traza) < MAX_LLAMADAS
        respuesta = _pedir_respuesta(cliente, modelo, mensajes, permitir_herramientas=permitir)
        # acumular tokens
        _sumar_uso(uso, respuesta.usage)
        mensajes.append({"role": "assistant", "content": respuesta.content})

        # modelo rechazó
        if respuesta.stop_reason == "refusal":
            texto = "El modelo no pudo responder esta pregunta."
            break
        # terminó, sin más herramientas
        if respuesta.stop_reason != "tool_use":
            texto = _texto_final(respuesta)
            # cifras inventadas, una corrección
            if not corregida and cifras_sin_respaldo(texto, traza):
                corregida = True
                mensajes.append({"role": "user", "content": AVISO_SIN_RESPALDO})
                continue
            if respuesta.stop_reason == "max_tokens":
                texto += "\n\n[respuesta cortada por longitud]"
            break

        # herramientas pedidas
        bloques = [b for b in respuesta.content if b.type == "tool_use"]
        resultados = []
        for bloque in bloques:
            # sobre el límite, error
            if len(traza) >= MAX_LLAMADAS:
                resultados.append({
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": f"Error: límite de {MAX_LLAMADAS} llamadas alcanzado. Responde con lo que ya tienes.",
                    "is_error": True,
                })
                continue

            # correr y medir
            t0 = time.perf_counter()
            resultado, error = _correr_herramienta(bloque)
            resultados.append(resultado)
            traza.append({
                "herramienta": bloque.name,
                "argumentos": dict(bloque.input),
                "error": error,
                "segundos": round(time.perf_counter() - t0, 2),
                "urls": [] if error else urls_en(resultado["content"]),
            })

        # todos los resultados en un solo mensaje
        mensajes.append({"role": "user", "content": resultados})

    return {
        "respuesta": texto,
        "modelo": modelo,
        "llamadas_herramientas": len(traza),
        "traza": traza,
        "tokens": uso,
        "costo_usd": calcular_costo(modelo, uso),
        "latencia_seg": round(time.perf_counter() - inicio, 2),
        "mensajes": mensajes,
    }
