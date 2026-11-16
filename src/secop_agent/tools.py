# ### Archivo: tools.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Herramientas que usan el agente y el servidor MCP sobre SECOP II

import re

from secop_agent import alerts, socrata
from secop_agent.schema import (
    COLUMNAS_CONTRATO,
    MODALIDADES,
    TIPOS_CONTRATO,
    construir_where,
    enmascarar_documento,
    a_numero,
    limpiar_contrato,
    normalizar_texto,
    para_mostrar,
    patron_like,
    texto_soql,
)

MAX_CONTRATOS_POR_ALERTA = 20

AGRUPACIONES = {
    "proveedor": {"clave": "documento_proveedor", "nombre": "proveedor_adjudicado"},
    "entidad": {"clave": "codigo_entidad", "nombre": "nombre_entidad"},
    "modalidad": {"clave": "modalidad_de_contratacion", "nombre": None},
    "tipo_de_contrato": {"clave": "tipo_de_contrato", "nombre": None},
    "departamento": {"clave": "departamento", "nombre": None},
    "anio": {"clave": "date_extract_y(fecha_de_firma)", "nombre": None},
    "ciudad": {"clave": "ciudad", "nombre": None},
    "sector": {"clave": "sector", "nombre": None},
}

METRICAS = {
    "suma_valor": "total_valor",
    "conteo": "num_contratos",
    "suma_pagado": "total_pagado",
    "promedio_valor": "promedio_valor",
    "contratistas_distintos": "contratistas_distintos",
}

# columnas de cada métrica
COLUMNAS_METRICAS = [
    "count(*) as num_contratos",
    "sum(valor_del_contrato) as total_valor",
    "sum(valor_pagado) as total_pagado",
    "avg(valor_del_contrato) as promedio_valor",
    "count(distinct documento_proveedor) as contratistas_distintos",
]


# ### Resolver lugares ###
def _resolver_lugar(columna, texto):
    # valores reales de la columna
    valores = [f.get(columna) for f in socrata.consultar({
        "$select": f"{columna}, count(*) as n",
        "$group": columna,
        "$limit": 5000,
    }) if f.get(columna)]

    # comparar sin tildes
    buscado = normalizar_texto(texto)
    for valor in valores:
        if normalizar_texto(valor) == buscado:
            return valor

    # sugerir parecidos
    parecidos = [v for v in valores if buscado in normalizar_texto(v)][:10]
    raise ValueError(f"{columna} '{texto}' no existe. Parecidos: {parecidos}")


def _resolver_filtros(filtros):
    filtros = dict(filtros or {})
    for columna in ("departamento", "ciudad"):
        if filtros.get(columna):
            filtros[columna] = _resolver_lugar(columna, filtros[columna])
    return filtros


# ### buscar_entidad ###
def buscar_entidad(nombre, limite=10):
    # palabras útiles
    palabras = [p for p in re.split(r"\s+", nombre.strip()) if len(p) >= 3]
    if not palabras:
        raise ValueError("Escribe al menos una palabra de 3 letras del nombre de la entidad")

    # un like por palabra
    condiciones = [f"upper(nombre_entidad) like {texto_soql('%' + patron_like(p) + '%')}" for p in palabras]
    filas = socrata.consultar({
        "$select": "nombre_entidad, nit_entidad, codigo_entidad, departamento, ciudad, count(*) as num_contratos",
        "$where": " AND ".join(condiciones),
        "$group": "nombre_entidad, nit_entidad, codigo_entidad, departamento, ciudad",
        "$order": "num_contratos DESC",
        "$limit": 50,
    })

    # comodín trae ruido, filtrar exacto sin tildes
    buscadas = [normalizar_texto(p) for p in palabras]
    exactas = [f for f in filas if all(p in normalizar_texto(f.get("nombre_entidad")).split() for p in buscadas)]
    parciales = [f for f in filas if f not in exactas and all(p in normalizar_texto(f.get("nombre_entidad")) for p in buscadas)]
    filas = (exactas + parciales or filas)[: min(int(limite), 50)]

    return {
        "nota": "codigo_entidad identifica una sola entidad; varias entidades pueden compartir NIT",
        "sugerencia": None if filas else "Sin resultados: intenta con menos palabras o quita las palabras genéricas del tipo de entidad",
        "dependencias": _dependencias(filas),
        "candidatas": [
            {
                "nombre_entidad": f.get("nombre_entidad"),
                "codigo_entidad": f.get("codigo_entidad"),
                "nit_entidad": f.get("nit_entidad"),
                "departamento": f.get("departamento"),
                "ciudad": f.get("ciudad"),
                "num_contratos": int(a_numero(f.get("num_contratos"))),
            }
            for f in filas
        ],
    }


def _dependencias(filas):
    # inicio antes del guion
    grupos = {}
    for f in filas:
        nombre = f.get("nombre_entidad") or ""
        if "-" not in nombre:
            continue
        inicio = nombre.split("-")[0].strip()
        if len(inicio) >= 5:
            grupos.setdefault(inicio, set()).add(f.get("codigo_entidad"))
    # dos o más comparten inicio
    return [
        {
            "inicio_nombre": inicio,
            "num_entidades": len(codigos),
            "nota": "Parecen dependencias de una misma entidad; para tomarlas juntas usa el filtro nombre_entidad_empieza con este inicio",
        }
        for inicio, codigos in grupos.items() if len(codigos) >= 2
    ]


# ### consultar_contratos ###
def consultar_contratos(filtros, limite=50, orden="valor_desc"):
    ordenes = {
        "valor_desc": "valor_del_contrato DESC, id_contrato",
        "fecha_desc": "fecha_de_firma DESC, id_contrato",
        "fecha_asc": "fecha_de_firma ASC, id_contrato",
    }
    where = construir_where(_resolver_filtros(filtros))

    # total real antes de truncar
    conteo = socrata.consultar({
        "$select": "count(*) as num_contratos, sum(valor_del_contrato) as total_valor",
        "$where": where,
    })
    total = conteo[0] if conteo else {}

    # filas a devolver
    filas = socrata.consultar_paginado({
        "$select": ", ".join(COLUMNAS_CONTRATO),
        "$where": where,
        "$order": ordenes.get(orden, ordenes["valor_desc"]),
    }, max_filas=int(limite))

    contratos = [para_mostrar(limpiar_contrato(f)) for f in filas]
    num_total = int(a_numero(total.get("num_contratos")))
    return {
        "num_contratos_total": num_total,
        "valor_total": a_numero(total.get("total_valor")),
        "num_devueltos": len(contratos),
        "truncado": num_total > len(contratos),
        "contratos": contratos,
    }


# ### agregar ###
def agregar(filtros, agrupar_por, metrica="suma_valor", top=10, incluir_enlaces=True):
    # validar opciones
    if agrupar_por not in AGRUPACIONES:
        raise ValueError(f"agrupar_por debe ser uno de {list(AGRUPACIONES)}")
    if metrica not in METRICAS:
        raise ValueError(f"metrica debe ser una de {list(METRICAS)}")

    grupo = AGRUPACIONES[agrupar_por]
    where = construir_where(_resolver_filtros(filtros))
    columnas = [f"{grupo['clave']} as clave"]
    if grupo["nombre"]:
        # nombres varían, se toma uno
        columnas.append(f"max({grupo['nombre']}) as nombre")
    if agrupar_por == "proveedor":
        columnas.append("max(tipodocproveedor) as tipo_documento")
    columnas += COLUMNAS_METRICAS

    # ranking agrupado en servidor
    filas = socrata.consultar({
        "$select": ", ".join(columnas),
        "$where": where,
        "$group": grupo["clave"],
        "$order": f"{METRICAS[metrica]} DESC, clave",
        "$limit": min(int(top), 100),
    })

    # total sin agrupar
    general = socrata.consultar({
        "$select": ", ".join(COLUMNAS_METRICAS),
        "$where": where,
    })

    grupos = []
    for f in filas:
        clave = f.get("clave")
        if agrupar_por == "proveedor":
            # ocultar cédula si aplica
            clave = enmascarar_documento(clave, f.get("tipo_documento"))
        grupos.append({
            "clave": clave,
            "nombre": f.get("nombre"),
            "num_contratos": int(a_numero(f.get("num_contratos"))),
            "total_valor": a_numero(f.get("total_valor")),
            "total_pagado": a_numero(f.get("total_pagado")),
            "promedio_valor": round(a_numero(f.get("promedio_valor")), 2),
            "contratistas_distintos": int(a_numero(f.get("contratistas_distintos"))),
            "_clave_real": f.get("clave"),
        })

    if incluir_enlaces and grupos:
        if agrupar_por in ("proveedor", "entidad"):
            _agregar_enlaces(grupos, where, grupo["clave"])
        else:
            # pocos grupos, consulta por grupo
            _enlaces_por_grupo(grupos, where, grupo["clave"], numerica=agrupar_por == "anio")

    for g in grupos:
        # quitar clave interna
        g.pop("_clave_real", None)

    totales = general[0] if general else {}
    return {
        "agrupado_por": agrupar_por,
        "metrica": metrica,
        "total_general": {
            "num_contratos": int(a_numero(totales.get("num_contratos"))),
            "total_valor": a_numero(totales.get("total_valor")),
            "total_pagado": a_numero(totales.get("total_pagado")),
            "promedio_valor": round(a_numero(totales.get("promedio_valor")), 2),
            "contratistas_distintos": int(a_numero(totales.get("contratistas_distintos"))),
        },
        "grupos": grupos,
    }


def _agregar_enlaces(grupos, where, columna_clave, por_grupo=3):
    claves = ", ".join(texto_soql(g["_clave_real"]) for g in grupos if g["_clave_real"])
    if not claves:
        return

    filas = socrata.consultar_paginado({
        "$select": f"{columna_clave} as clave, id_contrato, valor_del_contrato, urlproceso",
        "$where": f"{where} AND {columna_clave} in ({claves})",
        "$order": "valor_del_contrato DESC, id_contrato",
    }, max_filas=2000)

    # top 3 contratos por grupo
    enlaces = {}
    for f in filas:
        lista = enlaces.setdefault(f.get("clave"), [])
        if len(lista) < por_grupo:
            lista.append({
                "id_contrato": f.get("id_contrato"),
                "valor": a_numero(f.get("valor_del_contrato")),
                "url": limpiar_contrato(f)["url"],
            })

    for g in grupos:
        g["contratos_mayores"] = enlaces.get(g["_clave_real"], [])


def _enlaces_por_grupo(grupos, where, columna_clave, numerica=False, por_grupo=3, max_grupos=20):
    for g in grupos[:max_grupos]:
        clave = g["_clave_real"]
        if clave is None:
            g["contratos_mayores"] = []
            continue
        valor = int(a_numero(clave)) if numerica else texto_soql(clave)
        # top 3 del grupo
        filas = socrata.consultar({
            "$select": "id_contrato, valor_del_contrato, urlproceso",
            "$where": f"{where} AND {columna_clave} = {valor}",
            "$order": "valor_del_contrato DESC, id_contrato",
            "$limit": por_grupo,
        })
        g["contratos_mayores"] = [
            {"id_contrato": f.get("id_contrato"), "valor": a_numero(f.get("valor_del_contrato")), "url": limpiar_contrato(f)["url"]}
            for f in filas
        ]


# ### detectar_alertas ###
def detectar_alertas(codigo_entidad, anio, parametros=None):
    filas = socrata.consultar_paginado({
        "$select": ", ".join(COLUMNAS_CONTRATO),
        "$where": construir_where({"codigo_entidad": codigo_entidad, "anio": anio}),
        "$order": "fecha_de_firma, id_contrato",
    })
    # limpiar y correr señales
    contratos = [limpiar_contrato(f) for f in filas]
    hallazgos = alerts.detectar(contratos, parametros)

    # recortar listas largas
    for h in hallazgos:
        h["num_contratos"] = len(h["contratos"])
        h["contratos"] = h["contratos"][:MAX_CONTRATOS_POR_ALERTA]

    return {
        "codigo_entidad": codigo_entidad,
        "anio": anio,
        "contratos_analizados": len(contratos),
        "analisis_truncado": len(contratos) >= socrata.MAX_FILAS,
        "parametros": {**alerts.PARAMETROS_DEFECTO, **(parametros or {})},
        "num_hallazgos": len(hallazgos),
        "hallazgos": hallazgos,
    }


# ### detalle_contrato ###
def detalle_contrato(id_contrato):
    filas = socrata.consultar({
        "$select": ", ".join(COLUMNAS_CONTRATO),
        "$where": f"id_contrato = {texto_soql(id_contrato)}",
        "$limit": 1,
    })
    if not filas:
        return {"encontrado": False, "id_contrato": id_contrato}
    return {"encontrado": True, "contrato": para_mostrar(limpiar_contrato(filas[0]))}


# ### Definiciones para Claude ###
ESQUEMA_FILTROS = {
    "type": "object",
    "description": "Filtros opcionales. Siempre se excluyen contratos en estado Borrador o Cancelado.",
    "properties": {
        "codigo_entidad": {
            "anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
            "description": "Código único de la entidad (sale de buscar_entidad), o una lista de códigos para tomar varias entidades juntas. Preferir sobre nit_entidad.",
        },
        "nombre_entidad_empieza": {"type": "string", "description": "Toma todas las entidades cuyo nombre empieza con este texto (sin importar tildes). Sirve cuando una entidad está registrada como varias dependencias que comparten el inicio del nombre."},
        "nit_entidad": {"type": "string", "description": "NIT de la entidad. Ojo: varias entidades pueden compartirlo."},
        "anio": {"type": "integer", "description": "Un solo año de la fecha de firma"},
        "anio_desde": {"type": "integer", "description": "Primer año de un rango de fechas de firma (incluido). No combinar con anio."},
        "anio_hasta": {"type": "integer", "description": "Último año de un rango de fechas de firma (incluido). No combinar con anio."},
        "objeto_contiene": {"type": "array", "items": {"type": "string"}, "description": "Palabras a buscar en el objeto del contrato, sin importar tildes. Basta con que aparezca una."},
        "tipo_persona": {"type": "string", "enum": ["natural", "juridica"], "description": "Tipo de contratista: natural (documento personal) o juridica (NIT)."},
        "duracion_min_dias": {"type": "integer", "description": "Duración mínima del contrato en días, calculada entre la fecha de inicio y la de fin."},
        "modalidades": {"type": "array", "items": {"type": "string", "enum": MODALIDADES}, "description": "Contratación directa = ['Contratación directa', 'Contratación Directa (con ofertas)']"},
        "tipo_de_contrato": {"type": "string", "enum": TIPOS_CONTRATO},
        "departamento": {"type": "string", "description": "Nombre completo del departamento, sin importar tildes; se compara contra los valores reales de SECOP"},
        "ciudad": {"type": "string", "description": "Nombre completo de la ciudad, sin importar tildes; se compara contra los valores reales de SECOP"},
        "documento_proveedor": {"type": "string", "description": "NIT o cédula del contratista, solo dígitos"},
        "valor_min": {"type": "number", "description": "Valor mínimo del contrato en pesos"},
        "valor_max": {"type": "number", "description": "Valor máximo del contrato en pesos"},
        "estado_contrato": {"type": "string"},
    },
    "additionalProperties": False,
}

HERRAMIENTAS = [
    {
        "name": "buscar_entidad",
        "description": "Busca entidades compradoras por nombre (sin importar tildes ni mayúsculas) y devuelve candidatas con codigo_entidad, NIT y número de contratos. Úsala antes de filtrar por entidad. Si hay varias candidatas que son entidades distintas, pide aclaración al usuario. Si el campo dependencias indica que son partes de una misma entidad, puedes tomarlas juntas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Palabras clave del nombre de la entidad"},
                "limite": {"type": "integer", "default": 10},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "consultar_contratos",
        "description": "Lista contratos que cumplen los filtros, con id_contrato, valor y enlace a SECOP. Devuelve también el conteo y la suma total reales aunque la lista se trunque. Máximo 5000 filas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filtros": ESQUEMA_FILTROS,
                "limite": {"type": "integer", "default": 50, "description": "Máximo de contratos a devolver (1 a 5000)"},
                "orden": {"type": "string", "enum": ["valor_desc", "fecha_desc", "fecha_asc"], "default": "valor_desc"},
            },
            "required": ["filtros"],
        },
    },
    {
        "name": "agregar",
        "description": "Suma, cuenta o promedia contratos agrupando en el servidor (rankings, totales por grupo). Devuelve el top de grupos, el total general y los contratos mayores de cada grupo con su enlace. El total sin agrupar viene en el campo total_general, con conteo, suma, pagado, promedio y contratistas distintos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filtros": ESQUEMA_FILTROS,
                "agrupar_por": {"type": "string", "enum": list(AGRUPACIONES)},
                "metrica": {
                    "type": "string",
                    "enum": list(METRICAS),
                    "description": (
                        "Cómo se ordena el ranking. conteo = número de contratos. "
                        "suma_valor = valor total contratado. suma_pagado = valor ya pagado. "
                        "promedio_valor = valor promedio por contrato. contratistas_distintos = número de contratistas diferentes."
                    ),
                },
                "top": {"type": "integer", "default": 10},
            },
            "required": ["filtros", "agrupar_por", "metrica"],
        },
    },
    {
        "name": "detectar_alertas",
        "description": "Corre las 4 señales deterministas (posible fraccionamiento, concentración en contratación directa, fechas inconsistentes, valor atípico) sobre los contratos de una entidad en un año. Las alertas son patrones para revisar, no irregularidades.",
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo_entidad": {"type": "string"},
                "anio": {"type": "integer"},
                "parametros": {
                    "type": "object",
                    "description": "Opcional: ventana_dias, umbral_fraccionamiento, min_contratos_fraccionamiento, porcentaje_concentracion, monto_minimo_entidad, percentil_atipico, min_grupo_atipico",
                },
            },
            "required": ["codigo_entidad", "anio"],
        },
    },
    {
        "name": "detalle_contrato",
        "description": "Trae un contrato por su id_contrato (formato CO1.PCCNTR.123) con su enlace a SECOP.",
        "input_schema": {
            "type": "object",
            "properties": {"id_contrato": {"type": "string"}},
            "required": ["id_contrato"],
        },
    },
]

FUNCIONES = {
    "buscar_entidad": buscar_entidad,
    "consultar_contratos": consultar_contratos,
    "agregar": agregar,
    "detectar_alertas": detectar_alertas,
    "detalle_contrato": detalle_contrato,
}


def ejecutar(nombre, argumentos):
    if nombre not in FUNCIONES:
        raise ValueError(f"Herramienta desconocida: {nombre}")
    return FUNCIONES[nombre](**argumentos)
