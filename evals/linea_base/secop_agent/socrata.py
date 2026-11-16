# ### Archivo: socrata.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Cliente de la API Socrata de datos.gov.co con paginación, reintentos y caché en disco

import hashlib
import json
import os
import time
from pathlib import Path

import httpx

# ### Configuración ###
DATASET = "jbjy-vk9h"
URL_DATOS = f"https://www.datos.gov.co/resource/{DATASET}.json"
URL_METADATOS = f"https://www.datos.gov.co/api/views/{DATASET}.json"
TAM_PAGINA = 1000
MAX_FILAS = 5000
MAX_INTENTOS = 4
TIMEOUT_SEG = 60


def _carpeta_cache():
    return Path(os.getenv("SECOP_CACHE_DIR", ".cache/socrata"))


def _horas_cache():
    return float(os.getenv("SECOP_CACHE_HORAS", "24"))


def _modo_demo():
    return os.getenv("SECOP_MODO_DEMO", "0") == "1"


# ### Caché en disco ###
def _llave_cache(params):
    # params a hash
    texto = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _leer_cache(params):
    ruta = _carpeta_cache() / f"{_llave_cache(params)}.json"
    # no hay caché
    if not ruta.exists():
        return None

    # horas desde que se guardó
    edad_horas = (time.time() - ruta.stat().st_mtime) / 3600
    # en demo no vence
    if edad_horas > _horas_cache() and not _modo_demo():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def _guardar_cache(params, filas):
    carpeta = _carpeta_cache()
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{_llave_cache(params)}.json"
    ruta.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")


# ### Peticiones HTTP ###
def _encabezados():
    encabezados = {"Accept": "application/json"}
    # token opcional
    token = os.getenv("SOCRATA_APP_TOKEN", "").strip()
    if token:
        encabezados["X-App-Token"] = token
    return encabezados


def _pedir(url, params):
    espera = 2
    for intento in range(1, MAX_INTENTOS + 1):
        try:
            response = httpx.get(url, params=params, headers=_encabezados(), timeout=TIMEOUT_SEG)

            # consulta mal armada
            if response.status_code == 400:
                raise ValueError(f"Consulta SoQL inválida: {response.text[:300]}")
            # límite o servidor caído
            if response.status_code == 429 or response.status_code >= 500:
                raise httpx.HTTPStatusError("reintentable", request=response.request, response=response)

            # token inválido u otro 4xx, sin reintento
            if not response.is_success:
                raise ConnectionError(f"datos.gov.co respondió {response.status_code}: {response.text[:300]}")
            return response.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as error:
            if intento == MAX_INTENTOS:
                raise ConnectionError(f"datos.gov.co no respondió tras {MAX_INTENTOS} intentos: {error}") from error
            time.sleep(espera)
            espera *= 2  # espera exponencial


# ### Consultas ###
def consultar(params):
    # quitar nulos
    params = {k: v for k, v in params.items() if v is not None}

    # primero caché
    filas = _leer_cache(params)
    if filas is not None:
        return filas

    # demo sin red
    if _modo_demo():
        raise ConnectionError("Modo demo activo y la consulta no está en caché.")

    # pedir y guardar
    filas = _pedir(URL_DATOS, params)
    _guardar_cache(params, filas)
    return filas


def consultar_paginado(params, max_filas=MAX_FILAS):
    # tope 5000
    max_filas = min(max_filas, MAX_FILAS)
    params = dict(params)
    # orden estable para paginar
    params.setdefault("$order", ":id")

    filas = []
    offset = 0
    while len(filas) < max_filas:
        limite = min(TAM_PAGINA, max_filas - len(filas))
        pagina = consultar({**params, "$limit": limite, "$offset": offset})
        filas.extend(pagina)
        # última página
        if len(pagina) < limite:
            break
        offset += limite
    return filas


def leer_metadatos():
    return _pedir(URL_METADATOS, {})
