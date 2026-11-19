# ### Archivo: streamlit_app.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Demo web del agente SECOP II con límite de preguntas por sesión y por día

import logging
import os
import sys
import threading
from pathlib import Path

import streamlit as st

# paquete desde src, aunque la nube no lo instale
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# secrets de Streamlit Cloud como variables de entorno
try:
    for clave, valor in st.secrets.items():
        if isinstance(valor, (str, int, float)):
            os.environ.setdefault(clave, str(valor))
except Exception:  # en local no hay secrets.toml
    pass

# cédulas ocultas en la demo
os.environ["SECOP_OCULTAR_DOCUMENTOS"] = "1"

from secop_agent.agent import hoy_colombia, responder  # noqa: E402

# ### Configuración ###
MAX_PREGUNTAS_SESION = 5
# tope de toda la app por día, protege la cuota gratuita de gemini
MAX_PREGUNTAS_DIA = int(os.getenv("DEMO_MAX_PREGUNTAS_DIA", "60"))
# solo gemini, el mismo de la evaluación; los visitantes no ponen llaves
MODELO_DEMO = os.getenv("MODELGEMINI", "gemini-3.5-flash-lite")

EJEMPLOS = [
    "¿Qué contratistas recibieron más dinero por contratación directa de la Secretaría General de la Alcaldía Mayor de Bogotá en 2025?",
    "¿Cuántos contratos firmó la Gobernación del Cauca en 2025?",
    "Corre las alertas para el INVIAS en 2025",
]

st.set_page_config(page_title="Analista SECOP II", layout="wide")


# ### Tope diario ###
@st.cache_resource
def contador_diario():
    # compartido por todas las sesiones mientras la app esté encendida
    return {"fecha": hoy_colombia(), "usadas": 0, "candado": threading.Lock()}


def reservar_pregunta_del_dia():
    contador = contador_diario()
    with contador["candado"]:
        # el día cambia a medianoche de Colombia, no de UTC
        if contador["fecha"] != hoy_colombia():
            contador["fecha"], contador["usadas"] = hoy_colombia(), 0
        if contador["usadas"] >= MAX_PREGUNTAS_DIA:
            return False
        contador["usadas"] += 1
        return True


def devolver_pregunta_del_dia():
    # una pregunta que falló no gasta cupo
    contador = contador_diario()
    with contador["candado"]:
        contador["usadas"] = max(contador["usadas"] - 1, 0)


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

    restantes = MAX_PREGUNTAS_SESION - st.session_state.preguntas_usadas
    st.info(f"Demo con {MODELO_DEMO}: te quedan {restantes} de {MAX_PREGUNTAS_SESION} preguntas.")

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
    if st.session_state.preguntas_usadas >= MAX_PREGUNTAS_SESION:
        st.warning("Llegaste al límite de la demo. Para seguir, puedes correr el proyecto en tu equipo: las instrucciones están en el README del repositorio.")
        st.stop()
    # tope global del día
    if not reservar_pregunta_del_dia():
        st.warning("La demo ya respondió todas las preguntas que tiene disponibles por hoy. Vuelve mañana o corre el proyecto en tu equipo: las instrucciones están en el README del repositorio.")
        st.stop()

    st.session_state.chat.append({"rol": "user", "texto": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando SECOP II..."):
            try:
                resultado = responder(
                    pregunta,
                    modelo=MODELO_DEMO,
                    historial=st.session_state.historial,
                )
            except Exception:  # detalle al log, mensaje simple al visitante
                logging.getLogger("demo").exception("Falló la pregunta: %s", pregunta)
                devolver_pregunta_del_dia()
                st.error("No pude responder en este momento: el modelo o datos.gov.co no respondieron. Intenta de nuevo en un minuto.")
                st.stop()

        meta = (f"{resultado['modelo']} · {resultado['llamadas_herramientas']} herramientas · "
                f"{resultado['latencia_seg']} s · ${resultado['costo_usd']:.4f} USD")
        st.markdown(resultado["respuesta"])
        st.caption(meta)

    st.session_state.historial = resultado["mensajes"]
    st.session_state.chat.append({"rol": "assistant", "texto": resultado["respuesta"], "meta": meta, "traza": resultado["traza"]})
    st.session_state.preguntas_usadas += 1
    st.rerun()
