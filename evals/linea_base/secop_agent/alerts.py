# ### Archivo: alerts.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Las 4 señales de alerta calculadas con pandas, sin LLM

import pandas as pd

from secop_agent.schema import AVISO_ALERTA, MODALIDADES_DIRECTA, para_mostrar

# ### Parámetros por defecto ###
PARAMETROS_DEFECTO = {
    "ventana_dias": 30,
    "umbral_fraccionamiento": 50_000_000,
    "min_contratos_fraccionamiento": 3,
    "porcentaje_concentracion": 0.20,
    "monto_minimo_entidad": 100_000_000,
    "percentil_atipico": 99,
    "min_grupo_atipico": 20,
}


# ### Preparación ###
def preparar_df(contratos):
    df = pd.DataFrame(contratos)
    if df.empty:
        return df

    # texto a fecha
    for columna in ("fecha_firma", "fecha_inicio", "fecha_fin"):
        df[columna] = pd.to_datetime(df[columna], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    # año de firma
    df["anio"] = df["fecha_firma"].dt.year
    return df


def _resumen_contratos(filas):
    columnas = ["id_contrato", "proveedor", "documento_proveedor", "tipo_documento_proveedor", "valor", "fecha_firma", "url"]
    salida = []
    for fila in filas[columnas].to_dict("records"):
        # fecha a texto
        fila["fecha_firma"] = fila["fecha_firma"].strftime("%Y-%m-%d") if pd.notna(fila["fecha_firma"]) else ""
        salida.append(para_mostrar(fila))
    return salida


def _hallazgo(senal, descripcion, filas, **extra):
    return {
        "senal": senal,
        "descripcion": descripcion,
        "aviso": AVISO_ALERTA,
        **extra,
        "contratos": _resumen_contratos(filas),
    }


# ### Señal 1: posible fraccionamiento ###
def senal_fraccionamiento(df, ventana_dias, umbral, min_contratos):
    hallazgos = []
    # solo contratos bajo umbral
    candidatos = df[(df["valor"] < umbral) & df["fecha_firma"].notna() & (df["documento_proveedor"] != "")]

    for (_, documento), grupo in candidatos.groupby(["codigo_entidad", "documento_proveedor"]):
        # orden por fecha
        grupo = grupo.sort_values("fecha_firma").reset_index(drop=True)
        i = 0
        while i < len(grupo):
            # ventana desde contrato i
            fin_ventana = grupo.loc[i, "fecha_firma"] + pd.Timedelta(days=ventana_dias)
            resto = grupo.iloc[i:]
            ventana = resto[resto["fecha_firma"] <= fin_ventana]

            if len(ventana) >= min_contratos and ventana["valor"].sum() > umbral:
                hallazgos.append(_hallazgo(
                    "posible_fraccionamiento",
                    f"{len(ventana)} contratos con el mismo proveedor en {ventana_dias} días, "
                    f"cada uno bajo ${umbral:,.0f} y suma ${ventana['valor'].sum():,.0f}",
                    ventana,
                    suma=float(ventana["valor"].sum()),
                ))
                # saltar ventana ya reportada
                i += len(ventana)
            else:
                i += 1
    return hallazgos


# ### Señal 2: concentración en contratación directa ###
def senal_concentracion_directa(df, porcentaje, monto_minimo_entidad):
    hallazgos = []
    # solo contratación directa
    directa = df[df["modalidad"].isin(MODALIDADES_DIRECTA) & (df["documento_proveedor"] != "")]

    for (_, anio), grupo in directa.groupby(["codigo_entidad", "anio"]):
        # total directo de la entidad
        total = grupo["valor"].sum()
        if total < monto_minimo_entidad:
            continue

        por_proveedor = grupo.groupby("documento_proveedor")["valor"].sum()
        for documento, valor in por_proveedor.items():
            # porcentaje del proveedor
            participacion = valor / total
            if participacion > porcentaje:
                filas = grupo[grupo["documento_proveedor"] == documento]
                hallazgos.append(_hallazgo(
                    "concentracion_contratacion_directa",
                    f"Un proveedor recibe el {participacion:.1%} del valor de contratación directa "
                    f"de la entidad en {int(anio)} (${valor:,.0f} de ${total:,.0f})",
                    filas,
                    participacion=round(float(participacion), 4),
                ))
    return hallazgos


# ### Señal 3: fechas inconsistentes ###
def senal_fechas_inconsistentes(df):
    # solo día, sin hora
    firma = df["fecha_firma"].dt.normalize()
    inicio = df["fecha_inicio"].dt.normalize()
    fin = df["fecha_fin"].dt.normalize()

    reglas = [
        ("fin antes del inicio", fin < inicio),
        ("firma después del inicio", firma > inicio),
        ("duración de cero días", fin == inicio),
    ]

    hallazgos = []
    for nombre, mascara in reglas:
        filas = df[mascara.fillna(False)]
        if not filas.empty:
            hallazgos.append(_hallazgo(
                "fechas_inconsistentes",
                f"{len(filas)} contratos con {nombre}",
                filas,
                regla=nombre,
            ))
    return hallazgos


# ### Señal 4: valor atípico ###
def senal_valor_atipico(df, percentil, min_grupo):
    hallazgos = []
    for (_, tipo, modalidad), grupo in df.groupby(["codigo_entidad", "tipo_de_contrato", "modalidad"]):
        # grupo chico no da percentil
        if len(grupo) < min_grupo:
            continue

        # valor del percentil
        corte = grupo["valor"].quantile(percentil / 100)
        filas = grupo[grupo["valor"] > corte]
        if not filas.empty:
            hallazgos.append(_hallazgo(
                "valor_atipico",
                f"{len(filas)} contratos de {tipo} por {modalidad} superan el percentil {percentil} "
                f"(${corte:,.0f}) de {len(grupo)} contratos comparables",
                filas,
                percentil_corte=float(corte),
            ))
    return hallazgos


# ### Todas las señales ###
def detectar(contratos, parametros=None):
    # defecto + usuario
    p = {**PARAMETROS_DEFECTO, **(parametros or {})}
    df = preparar_df(contratos)
    if df.empty:
        return []

    return [
        *senal_fraccionamiento(df, p["ventana_dias"], p["umbral_fraccionamiento"], p["min_contratos_fraccionamiento"]),
        *senal_concentracion_directa(df, p["porcentaje_concentracion"], p["monto_minimo_entidad"]),
        *senal_fechas_inconsistentes(df),
        *senal_valor_atipico(df, p["percentil_atipico"], p["min_grupo_atipico"]),
    ]
