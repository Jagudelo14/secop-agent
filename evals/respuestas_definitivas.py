# ### Archivo: respuestas_definitivas.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Consultas SoQL que dan la respuesta correcta de cada pregunta del set definitivo, sin tocar su redacción

import json
import sys
from pathlib import Path

ARCHIVO = Path(__file__).resolve().parent / "preguntas_definitivas.jsonl"

# ### Piezas comunes ###
E = "estado_contrato not in ('Borrador', 'Cancelado')"


def anio(a):
    return f"date_extract_y(fecha_de_firma) = {a}"


def anios(desde, hasta=None):
    if hasta is None:
        return f"date_extract_y(fecha_de_firma) >= {desde}"
    return f"date_extract_y(fecha_de_firma) between {desde} and {hasta}"


def w(*condiciones):
    return " AND ".join((E,) + condiciones)


def entidad(codigo):
    return f"codigo_entidad = {codigo}"


def texto(*palabras):
    # objeto contiene alguna
    return "(" + " OR ".join(f"upper(objeto_del_contrato) like '%{p}%'" for p in palabras) + ")"


# entidades con varias dependencias
CALI = "upper(nombre_entidad) like 'SANTIAGO DE CALI%'"
CUNDINAMARCA = "upper(nombre_entidad) like 'DEPARTAMENTO DE CUNDINAMARCA%'"
VALLE = ("(upper(nombre_entidad) like '%GOBERNACI_N DEL VALLE%' "
         "OR upper(nombre_entidad) like 'DEPARTAMENTO DEL VALLE DEL CAUCA%')")

DIRECTA = "modalidad_de_contratacion in ('Contratación directa', 'Contratación Directa (con ofertas)')"
SELECCION_ABREVIADA = ("modalidad_de_contratacion in ('Selección Abreviada de Menor Cuantía', "
                       "'Selección abreviada subasta inversa', 'Seleccion Abreviada Menor Cuantia Sin Manifestacion Interes')")
PERSONA_NATURAL = "tipodocproveedor not in ('NIT', 'Otro', 'No Definido')"
PERSONA_JURIDICA = "tipodocproveedor = 'NIT'"

# códigos confirmados en datos.gov.co
NARINO, MANIZALES, VILLAVICENCIO = 700694045, 705412617, 703915215
BOYACA, HUILA, META, IBAGUE = 702727819, 702349549, 700817075, 700787393
CORDOBA, ARMENIA, QUINDIO, PEREIRA = 705555407, 701365033, 702948183, 702259557
CALDAS, RISARALDA, ATLANTICO, MEDELLIN = 700613011, 702280165, 702589086, 700221021
SANTANDER, TOLIMA, MONTERIA = 701515082, 702192410, 702923731


def suma_por_anio(codigo, desde, hasta, columna="sum(valor_del_contrato)"):
    return {"$select": f"{columna} as respuesta", "$where": w(entidad(codigo), anios(desde, hasta)),
            "$group": "date_extract_y(fecha_de_firma)", "$order": "date_extract_y(fecha_de_firma)"}


def ranking(select, where, grupo, limite, orden="total DESC, clave"):
    return {"$select": select, "$where": where, "$group": grupo, "$order": orden, "$limit": limite}


def contratos_top(where, limite):
    return {"$select": "id_contrato as clave, valor_del_contrato as total", "$where": where,
            "$order": "valor_del_contrato DESC, id_contrato", "$limit": limite}


def lista(where, limite=1000):
    return {"$select": "id_contrato", "$where": where, "$limit": limite}


PROVEEDOR_SUMA = "documento_proveedor as clave, max(proveedor_adjudicado) as nombre, sum(valor_del_contrato) as total"
PROVEEDOR_CONTEO = "documento_proveedor as clave, max(proveedor_adjudicado) as nombre, count(*) as total"
ENTIDAD_CONTEO = "codigo_entidad as clave, max(nombre_entidad) as nombre, count(*) as total"
ENTIDAD_SUMA = "codigo_entidad as clave, max(nombre_entidad) as nombre, sum(valor_del_contrato) as total"

# ### Respuestas correctas ###
RESPUESTAS = {
    # conteo y suma
    "P01": {"soql": {"$select": "count(*) as respuesta", "$where": w("documento_proveedor = '900123456'", anio(2025))}},
    "P02": {"soql": suma_por_anio(NARINO, 2023, 2025)},
    "P03": {"soql": {"$select": "sum(valor_pagado) as respuesta_pagado, sum(valor_del_contrato) as respuesta_contratado",
                     "$where": w(entidad(MANIZALES), anio(2024))}},
    "P04": {"soql": {"$select": "count(*) as respuesta_contratos, sum(valor_del_contrato) as respuesta_valor",
                     "$where": w(entidad(VILLAVICENCIO), anio(2022))}},
    "P05": {"soql": {"$select": "sum(valor_del_contrato) as respuesta", "$where": w("departamento = 'Tolima'", anio(2023))}},
    "P06": {"soql": {"$select": "count(*) as respuesta", "$where": w(entidad(BOYACA), anio(2021), DIRECTA)}},
    "P07": {"soql": {"$select": "sum(valor_del_contrato) as respuesta", "$where": w(entidad(HUILA), anios(2020, 2024))}},
    "P08": {"soql": {"$select": "count(distinct documento_proveedor) as respuesta", "$where": w(CALI, anio(2023))}},
    "P09": {"soql": {"$select": "count(*) as respuesta_contratos, sum(valor_del_contrato) as respuesta_valor",
                     "$where": w(entidad(META), anio(2022), "tipo_de_contrato = 'Obra'")}},
    "P10": {"soql": suma_por_anio(IBAGUE, 2019, 2024)},
    "P11": {"soql": suma_por_anio(CORDOBA, 2020, 2022, columna="count(*)")},
    "P12": {"soql": {"$select": "count(*) as respuesta", "$where": w(entidad(ARMENIA), anio(2024), PERSONA_NATURAL)}},
    "P13": {"soql": {"$select": "avg(valor_del_contrato) as respuesta", "$where": w(entidad(QUINDIO), anio(2023))}},
    "P14": {"soql": {"$select": "count(*) as respuesta",
                     "$where": w(entidad(PEREIRA), anio(2021),
                                 "date_diff_d(fecha_de_fin_del_contrato, fecha_de_inicio_del_contrato) > 183")}},
    # mayor primero, diferencia y nombre
    "P15": {"soql": {"$select": "codigo_entidad, max(nombre_entidad) as nombre, sum(valor_del_contrato) as total",
                     "$where": w(f"codigo_entidad in ({CALDAS}, {RISARALDA})", anio(2024)),
                     "$group": "codigo_entidad", "$order": "total DESC"},
            "calculo": "diferencia", "debe_mencionar": "CALDAS"},
    # ranking
    "P16": {"soql": ranking(PROVEEDOR_SUMA, w(entidad(ATLANTICO), anios(2020)), "documento_proveedor", 10)},
    "P17": {"soql": ranking("modalidad_de_contratacion as clave, count(*) as total",
                            w(entidad(MEDELLIN), anios(2021, 2025)), "modalidad_de_contratacion", 5)},
    "P18": {"soql": ranking("departamento as clave, sum(valor_del_contrato) as total",
                            w(anio(2024), "departamento != 'No Definido'"), "departamento", 10)},
    "P19": {"soql": ranking(ENTIDAD_CONTEO, w("departamento = 'Valle del Cauca'", anio(2023)), "codigo_entidad", 10)},
    "P20": {"soql": ranking(PROVEEDOR_CONTEO, w(CUNDINAMARCA, anios(2020, 2024)), "documento_proveedor", 10)},
    "P21": {"soql": contratos_top(w("departamento = 'Magdalena'", anio(2022), "tipo_de_contrato = 'Obra'"), 10)},
    "P22": {"soql": ranking("ciudad as clave, sum(valor_del_contrato) as total",
                            w("departamento = 'Boyacá'", anio(2023), "ciudad != 'No Definido'"), "ciudad", 10)},
    "P23": {"soql": ranking(PROVEEDOR_SUMA, w(CALI, anio(2024), PERSONA_JURIDICA), "documento_proveedor", 10)},
    "P24": {"soql": ranking("objeto_del_contrato as clave, sum(valor_del_contrato) as total",
                            w(entidad(SANTANDER), anio(2021)), "objeto_del_contrato", 10)},
    "P25": {"soql": ranking(ENTIDAD_CONTEO, w("departamento = 'Meta'", anio(2022), DIRECTA), "codigo_entidad", 5)},
    "P26": {"soql": ranking(PROVEEDOR_CONTEO, w("departamento = 'Cesar'", anios(2019, 2024)), "documento_proveedor", 10)},
    "P27": {"soql": ranking("sector as clave, sum(valor_del_contrato) as total", w("departamento = 'Córdoba'", anio(2023)),
                            "sector", 5)},
    "P28": {"soql": contratos_top(w("departamento = 'Huila'", anio(2024), "tipo_de_contrato = 'Prestación de servicios'"), 10)},
    "P29": {"soql": ranking(ENTIDAD_SUMA, w("ciudad = 'Ibagué'", anio(2022)), "codigo_entidad", 5)},
    "P30": {"soql": ranking(PROVEEDOR_SUMA, w("departamento = 'Antioquia'", anio(2020)), "documento_proveedor", 10)},
    # filtro
    "P31": {"soql": lista(w("ciudad = 'Pereira'", anio(2025), "tipo_de_contrato = 'Obra'"))},
    "P32": {"soql": lista(w(VALLE, anios(2022, 2024), "tipo_de_contrato = 'Prestación de servicios'",
                            "valor_del_contrato > 500000000"))},
    "P33": {"soql": lista(w(entidad(ARMENIA), anio(2023), "modalidad_de_contratacion = 'Mínima cuantía'"))},
    "P34": {"soql": lista(w(entidad(TOLIMA), anio(2022), PERSONA_JURIDICA, "valor_del_contrato > 1000000000"))},
    "P35": {"soql": lista(w(CALI, anio(2024), texto("SOFTWARE", "LICENCIA", "LICENCIAMIENTO", "TECNOLOG"))), "tope": 50},
    "P36": {"soql": lista(w(entidad(CALDAS), anio(2024), "estado_contrato = 'En ejecución'"))},
    "P37": {"soql": lista(w("departamento = 'Risaralda'", anio(2023), "upper(objeto_del_contrato) like '%MANTENIMIENTO%'",
                            texto("VIA", "VÍA", "VIAL")))},
    "P38": {"soql": lista(w("departamento = 'Magdalena'", anio(2024),
                            "(upper(nombre_entidad) like '%ALCALD%' OR upper(nombre_entidad) like '%MUNICIPIO%')",
                            texto("ALIMENTACION ESCOLAR", "ALIMENTACIÓN ESCOLAR", "PAE")))},
    "P39": {"soql": lista(w(entidad(QUINDIO), anio(2022), SELECCION_ABREVIADA,
                            "valor_del_contrato between 100000000 and 300000000"))},
    "P40": {"soql": lista(w(entidad(MONTERIA), anio(2023), "tipo_de_contrato = 'Obra'",
                            texto("ESCENARIO", "DEPORTIV", "CANCHA", "POLIDEPORTIVO", "ESTADIO", "COLISEO")))},
}


# ### Escribir en el set ###
def main():
    filas = [json.loads(l) for l in ARCHIVO.read_text(encoding="utf-8").splitlines() if l.strip()]
    for f in filas:
        extra = RESPUESTAS.get(f["id"], {})
        f["soql"] = extra.get("soql")
        for clave in ("calculo", "tope", "debe_mencionar"):
            if clave in extra:
                f[clave] = extra[clave]
    with open(ARCHIVO, "w", encoding="utf-8", newline="\n") as salida:
        for f in filas:
            salida.write(json.dumps(f, ensure_ascii=False) + "\n")
    print(f"{sum(1 for f in filas if f['soql'])} consultas escritas")


if __name__ == "__main__":
    sys.exit(main())
