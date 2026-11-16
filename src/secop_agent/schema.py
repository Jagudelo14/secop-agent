# ### Archivo: schema.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Columnas reales de SECOP II, normalización de textos y montos, validación de filtros y armado de SoQL

import os
import re
import unicodedata
from datetime import datetime

# ### Columnas confirmadas ###
COLUMNAS_CONTRATO = [
    "id_contrato",
    "referencia_del_contrato",
    "nombre_entidad",
    "nit_entidad",
    "codigo_entidad",
    "departamento",
    "ciudad",
    "proveedor_adjudicado",
    "documento_proveedor",
    "tipodocproveedor",
    "modalidad_de_contratacion",
    "tipo_de_contrato",
    "objeto_del_contrato",
    "valor_del_contrato",
    "valor_pagado",
    "fecha_de_firma",
    "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato",
    "estado_contrato",
    "urlproceso",
]

MODALIDADES = [
    "Contratación directa",
    "Contratación Directa (con ofertas)",
    "Contratación régimen especial",
    "Contratación régimen especial (con ofertas)",
    "Mínima cuantía",
    "Selección Abreviada de Menor Cuantía",
    "Selección abreviada subasta inversa",
    "Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes",
    "Concurso de méritos abierto",
    "Concurso de méritos con precalificación",
    "Licitación pública",
    "Licitación pública Obra Publica",
    "Licitación Pública Acuerdo Marco de Precios",
    "Enajenación de bienes con sobre cerrado",
    "Enajenación de bienes con subasta",
]

TIPOS_CONTRATO = [
    "Prestación de servicios", "Otro", "Decreto 092 de 2017", "Suministros", "Compraventa", "Obra",
    "Arrendamiento de inmuebles", "Interventoría", "Comodato", "Consultoría", "Seguros",
    "Arrendamiento de muebles", "Acuerdo Marco de Precios", "Servicios financieros",
    "Operaciones de Crédito Público", "Asociación Público Privada", "Venta muebles", "Negocio fiduciario",
    "Comisión", "Concesión", "No Especificado", "No Definido", "Venta inmuebles", "Acuerdo de cooperación",
]

MODALIDADES_DIRECTA = ["Contratación directa", "Contratación Directa (con ofertas)"]

# borradores y cancelados no cuentan
ESTADOS_EXCLUIDOS = ["Borrador", "Cancelado"]

FILTROS_PERMITIDOS = {
    "codigo_entidad",
    "nombre_entidad_empieza",
    "nit_entidad",
    "anio",
    "anio_desde",
    "anio_hasta",
    "objeto_contiene",
    "tipo_persona",
    "duracion_min_dias",
    "modalidades",
    "tipo_de_contrato",
    "departamento",
    "ciudad",
    "documento_proveedor",
    "valor_min",
    "valor_max",
    "estado_contrato",
}

AVISO_ALERTA = "patrón para revisar, no implica irregularidad"

# documentos de persona jurídica
DOCUMENTOS_JURIDICA = ["NIT"]
# sin tipo claro
DOCUMENTOS_SIN_TIPO = ["Otro", "No Definido"]


# ### Normalización ###
def quitar_tildes(texto):
    # separar letra y tilde
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def normalizar_texto(texto):
    if texto is None:
        return ""
    texto = quitar_tildes(str(texto)).upper()
    # signos a espacio
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_documento(documento):
    # solo dígitos
    if documento is None:
        return ""
    return re.sub(r"\D", "", str(documento))


def a_numero(valor):
    if valor is None or valor == "":
        return 0.0
    try:
        return float(valor)
    except (TypeError, ValueError):
        # quitar símbolos
        limpio = re.sub(r"[^\d.\-]", "", str(valor))
        return float(limpio) if limpio not in ("", "-", ".") else 0.0


def extraer_url(valor):
    # urlproceso llega como {"url": ...}
    if isinstance(valor, dict):
        return valor.get("url", "")
    return valor or ""


def es_persona_natural(tipo_documento):
    return "CEDULA" in normalizar_texto(tipo_documento)


def enmascarar_documento(documento, tipo_documento):
    ocultar = os.getenv("SECOP_OCULTAR_DOCUMENTOS", "0") == "1"
    if ocultar and es_persona_natural(tipo_documento) and documento:
        # últimos 3 dígitos
        return "***" + str(documento)[-3:]
    return documento


def limpiar_contrato(fila):
    return {
        "id_contrato": fila.get("id_contrato", ""),
        "referencia": fila.get("referencia_del_contrato", ""),
        "entidad": fila.get("nombre_entidad", ""),
        "nit_entidad": normalizar_documento(fila.get("nit_entidad")),
        "codigo_entidad": fila.get("codigo_entidad", ""),
        "proveedor": fila.get("proveedor_adjudicado", ""),
        "documento_proveedor": normalizar_documento(fila.get("documento_proveedor")),
        "tipo_documento_proveedor": fila.get("tipodocproveedor", ""),
        "modalidad": fila.get("modalidad_de_contratacion", ""),
        "tipo_de_contrato": fila.get("tipo_de_contrato", ""),
        "objeto": (fila.get("objeto_del_contrato") or "")[:200],
        "valor": a_numero(fila.get("valor_del_contrato")),
        "valor_pagado": a_numero(fila.get("valor_pagado")),
        "fecha_firma": (fila.get("fecha_de_firma") or "")[:10],
        "fecha_inicio": (fila.get("fecha_de_inicio_del_contrato") or "")[:10],
        "fecha_fin": (fila.get("fecha_de_fin_del_contrato") or "")[:10],
        "estado": fila.get("estado_contrato", ""),
        "url": extraer_url(fila.get("urlproceso")),
    }


def para_mostrar(contrato):
    # copia con documento oculto
    copia = dict(contrato)
    copia["documento_proveedor"] = enmascarar_documento(
        contrato.get("documento_proveedor"), contrato.get("tipo_documento_proveedor")
    )
    return copia


# ### Validación de filtros ###
def validar_filtros(filtros):
    filtros = dict(filtros or {})

    # rechazar filtros extra
    desconocidos = set(filtros) - FILTROS_PERMITIDOS
    if desconocidos:
        raise ValueError(f"Filtros no soportados: {sorted(desconocidos)}. Usa: {sorted(FILTROS_PERMITIDOS)}")

    limpios = {}
    # ids solo dígitos
    for campo in ("nit_entidad", "documento_proveedor"):
        if filtros.get(campo):
            valor = normalizar_documento(filtros[campo])
            if not valor:
                raise ValueError(f"{campo} debe tener dígitos")
            limpios[campo] = valor

    # una o varias entidades
    if filtros.get("codigo_entidad"):
        codigos = filtros["codigo_entidad"]
        codigos = codigos if isinstance(codigos, list) else [codigos]
        codigos = [normalizar_documento(c) for c in codigos]
        if not all(codigos):
            raise ValueError("codigo_entidad debe tener dígitos")
        limpios["codigo_entidad"] = codigos[0] if len(codigos) == 1 else codigos

    if filtros.get("nombre_entidad_empieza"):
        inicio = str(filtros["nombre_entidad_empieza"]).strip()
        if len(inicio) < 5:
            raise ValueError("nombre_entidad_empieza necesita al menos 5 letras")
        limpios["nombre_entidad_empieza"] = inicio

    # año único o rango
    for campo in ("anio", "anio_desde", "anio_hasta"):
        if filtros.get(campo) is not None:
            anio = int(filtros[campo])
            # secop ii desde 2015
            if not 2015 <= anio <= datetime.now().year:
                raise ValueError(f"Año fuera de rango: {anio}")
            limpios[campo] = anio
    if "anio" in limpios and ("anio_desde" in limpios or "anio_hasta" in limpios):
        raise ValueError("Usa anio para un solo año o anio_desde / anio_hasta para un rango, no ambos")
    if limpios.get("anio_desde", 0) > limpios.get("anio_hasta", 9999):
        raise ValueError("anio_desde no puede ser mayor que anio_hasta")

    if filtros.get("objeto_contiene"):
        palabras = filtros["objeto_contiene"]
        palabras = palabras if isinstance(palabras, list) else [palabras]
        palabras = [str(p).strip() for p in palabras if str(p).strip()]
        if not palabras or any(len(p) < 3 for p in palabras):
            raise ValueError("objeto_contiene necesita palabras de al menos 3 letras")
        limpios["objeto_contiene"] = palabras

    if filtros.get("tipo_persona"):
        tipo = normalizar_texto(filtros["tipo_persona"]).lower()
        if tipo not in ("natural", "juridica"):
            raise ValueError("tipo_persona debe ser 'natural' o 'juridica'")
        limpios["tipo_persona"] = tipo

    if filtros.get("duracion_min_dias") is not None:
        dias = int(filtros["duracion_min_dias"])
        if dias <= 0:
            raise ValueError("duracion_min_dias debe ser mayor que 0")
        limpios["duracion_min_dias"] = dias

    if filtros.get("modalidades"):
        modalidades = filtros["modalidades"]
        # texto suelto a lista
        if isinstance(modalidades, str):
            modalidades = [modalidades]
        invalidas = [m for m in modalidades if m not in MODALIDADES]
        if invalidas:
            raise ValueError(f"Modalidades no válidas: {invalidas}. Opciones: {MODALIDADES}")
        limpios["modalidades"] = modalidades

    if filtros.get("tipo_de_contrato"):
        if filtros["tipo_de_contrato"] not in TIPOS_CONTRATO:
            raise ValueError(f"tipo_de_contrato no válido. Opciones: {TIPOS_CONTRATO}")
        limpios["tipo_de_contrato"] = filtros["tipo_de_contrato"]

    for campo in ("departamento", "ciudad", "estado_contrato"):
        if filtros.get(campo):
            limpios[campo] = str(filtros[campo]).strip()

    # montos a número
    for campo in ("valor_min", "valor_max"):
        if filtros.get(campo) is not None:
            limpios[campo] = a_numero(filtros[campo])

    return limpios


# ### Armado de SoQL ###
def texto_soql(valor):
    # escapar comillas simples
    return "'" + str(valor).replace("'", "''") + "'"


def patron_like(texto):
    # vocales y ñ como comodín
    texto = quitar_tildes(texto).upper()
    return re.sub(r"[AEIOUN]", "_", texto)


def variantes_tilde(texto):
    # sin tilde y una tilde por posición
    base = quitar_tildes(texto).upper()
    acentos = {"A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú", "N": "Ñ"}
    variantes = [base]
    for i, letra in enumerate(base):
        if letra in acentos:
            variantes.append(base[:i] + acentos[letra] + base[i + 1:])
    return variantes


def _like_alguna(columna, textos, inicio="%", fin="%"):
    opciones = [f"upper({columna}) like {texto_soql(inicio + v + fin)}" for t in textos for v in variantes_tilde(t)]
    return "(" + " OR ".join(opciones) + ")"


def construir_where(filtros):
    filtros = validar_filtros(filtros)
    # siempre fuera borradores
    condiciones = [f"estado_contrato not in ({', '.join(texto_soql(e) for e in ESTADOS_EXCLUIDOS)})"]

    if "codigo_entidad" in filtros:
        codigos = filtros["codigo_entidad"]
        if isinstance(codigos, list):
            condiciones.append(f"codigo_entidad in ({', '.join(codigos)})")
        else:
            condiciones.append(f"codigo_entidad = {codigos}")
    if "nombre_entidad_empieza" in filtros:
        # sin importar tildes
        condiciones.append(_like_alguna("nombre_entidad", [filtros["nombre_entidad_empieza"]], inicio=""))
    if "nit_entidad" in filtros:
        condiciones.append(f"nit_entidad = {filtros['nit_entidad']}")
    if "documento_proveedor" in filtros:
        condiciones.append(f"documento_proveedor = {texto_soql(filtros['documento_proveedor'])}")
    if "anio" in filtros:
        condiciones.append(f"date_extract_y(fecha_de_firma) = {filtros['anio']}")
    if "anio_desde" in filtros:
        condiciones.append(f"date_extract_y(fecha_de_firma) >= {filtros['anio_desde']}")
    if "anio_hasta" in filtros:
        condiciones.append(f"date_extract_y(fecha_de_firma) <= {filtros['anio_hasta']}")
    if "objeto_contiene" in filtros:
        # alguna palabra, sin tildes
        condiciones.append(_like_alguna("objeto_del_contrato", filtros["objeto_contiene"]))
    if filtros.get("tipo_persona") == "juridica":
        condiciones.append(f"tipodocproveedor in ({', '.join(texto_soql(d) for d in DOCUMENTOS_JURIDICA)})")
    if filtros.get("tipo_persona") == "natural":
        excluidos = DOCUMENTOS_JURIDICA + DOCUMENTOS_SIN_TIPO
        condiciones.append(f"tipodocproveedor not in ({', '.join(texto_soql(d) for d in excluidos)})")
    if "duracion_min_dias" in filtros:
        condiciones.append(
            f"date_diff_d(fecha_de_fin_del_contrato, fecha_de_inicio_del_contrato) >= {filtros['duracion_min_dias']}"
        )
    if "modalidades" in filtros:
        lista = ", ".join(texto_soql(m) for m in filtros["modalidades"])
        condiciones.append(f"modalidad_de_contratacion in ({lista})")
    if "tipo_de_contrato" in filtros:
        condiciones.append(f"tipo_de_contrato = {texto_soql(filtros['tipo_de_contrato'])}")
    if "estado_contrato" in filtros:
        condiciones.append(f"estado_contrato = {texto_soql(filtros['estado_contrato'])}")

    # valor exacto ya resuelto en tools
    for campo in ("departamento", "ciudad"):
        if campo in filtros:
            condiciones.append(f"{campo} = {texto_soql(filtros[campo])}")

    if "valor_min" in filtros:
        condiciones.append(f"valor_del_contrato >= {filtros['valor_min']:.0f}")
    if "valor_max" in filtros:
        condiciones.append(f"valor_del_contrato <= {filtros['valor_max']:.0f}")

    return " AND ".join(condiciones)
