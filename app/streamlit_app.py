# ### Archivo: streamlit_app.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Demo web del agente SECOP II con límite de preguntas por sesión

import os

import streamlit as st

# cédulas ocultas en la demo
os.environ["SECOP_OCULTAR_DOCUMENTOS"] = "1"

from secop_agent.agent import responder, usa_gemini  # noqa: E402

# ### Configuración ###
MAX_PREGUNTAS_SESION = 5
# demo con el proveedor del .env o los secrets, el mismo de la evaluación
MODELO_DEMO = os.getenv("MODELGEMINI", "gemini-3.5-flash-lite") if usa_gemini() else os.getenv("MODEL", "claude-haiku-5-5")
MODELO_LLAVE_PROPIA = "claude-sonnet-5-5"

EJEMPLOS = [
    "¿Qué contratistas recibieron más dinero por contratación directa de la Secretaría General de la Alcaldía Mayor de Bogotá en 2025?",
    "¿Cuántos contratos firmó la Gobernación del Cauca en 2025?",
    "Corre las alertas para el INVIAS en 2025",
]

st.set_page_config(page_title="Analista SECOP II", layout="wide")

# ### Estados ###
if "chat" not in st.session_state:
    st.session_state.chat = []
if "historial" not in st.session_state:
    st.session_state.historial = []
if "preguntas_usadas" not in st.session_state:
    st.session_state.preguntas_usadas = 0

# ### Barra lateral ###
with st.sidebar:
    st.header("Analista SECOP II")
    st.caption("Contratos públicos de Colombia, conjunto jbjy-vk9h de datos.gov.co (CC BY-SA 4.0).")

    llave_visitante = st.text_input("Tu llave de Anthropic (opcional)", type="password",
                                    help="Con tu llave no hay límite y se usa Sonnet. No se guarda.")
    usa_llave_propia = bool(llave_visitante.strip())
    modelo = MODELO_LLAVE_PROPIA if usa_llave_propia else MODELO_DEMO

    if not usa_llave_propia:
        restantes = MAX_PREGUNTAS_SESION - st.session_state.preguntas_usadas
        st.info(f"Modo demo con {MODELO_DEMO}: te quedan {restantes} de {MAX_PREGUNTAS_SESION} preguntas.")
    else:
        st.success(f"Usando tu llave con {MODELO_LLAVE_PROPIA}.")

    if st.button("Nueva conversación"):
        st.session_state.chat = []
        st.session_state.historial = []
        st.rerun()

    st.divider()
    st.caption("Las alertas son patrones para revisar, no implican irregularidad. "
               "Los documentos de personas naturales se ocultan.")

# ### Encabezado ###
st.title("Pregúntale a SECOP II")
st.write("Cada cifra viene con el enlace al contrato del que salió.")

if not st.session_state.chat:
    columnas = st.columns(len(EJEMPLOS))
    for columna, ejemplo in zip(columnas, EJEMPLOS):
        if columna.button(ejemplo, use_container_width=True):
            st.session_state.pendiente = ejemplo
            st.rerun()

# ### Conversación ###
for turno in st.session_state.chat:
    with st.chat_message(turno["rol"]):
        st.markdown(turno["texto"])
        if turno.get("meta"):
            st.caption(turno["meta"])
        if turno.get("traza"):
            with st.expander("Herramientas usadas"):
                st.json(turno["traza"])

pregunta = st.chat_input("Escribe tu pregunta sobre contratos públicos") or st.session_state.pop("pendiente", None)

# ### Manejador de pregunta ###
if pregunta:
    # límite por sesión
    if not usa_llave_propia and st.session_state.preguntas_usadas >= MAX_PREGUNTAS_SESION:
        st.warning("Llegaste al límite de la demo. Pega tu propia llave en la barra lateral para seguir.")
        st.stop()

    st.session_state.chat.append({"rol": "user", "texto": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando SECOP II..."):
            try:
                resultado = responder(
                    pregunta,
                    modelo=modelo,
                    api_key=llave_visitante.strip() or None,
                    historial=st.session_state.historial,
                )
            except Exception as error:  # mostrar sin romper la app
                st.error(f"No se pudo responder: {error}")
                st.stop()

        meta = (f"{resultado['modelo']} · {resultado['llamadas_herramientas']} herramientas · "
                f"{resultado['latencia_seg']} s · ${resultado['costo_usd']:.4f} USD")
        st.markdown(resultado["respuesta"])
        st.caption(meta)

    st.session_state.historial = resultado["mensajes"]
    st.session_state.chat.append({"rol": "assistant", "texto": resultado["respuesta"], "meta": meta, "traza": resultado["traza"]})
    if not usa_llave_propia:
        st.session_state.preguntas_usadas += 1
    st.rerun()
