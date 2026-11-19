# ### Archivo: fase0_esquema.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Fase 0, baja metadatos y 1000 filas de jbjy-vk9h y genera docs/schema.json y docs/esquema.md

import json
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from secop_agent import socrata
from secop_agent.schema import COLUMNAS_CONTRATO

load_dotenv()

CARPETA_DOCS = Path(__file__).resolve().parent.parent / "docs"
FILAS_MUESTRA = 1000
# columnas con nombres, documentos o cuentas de personas; no van de ejemplo en docs
PATRON_PERSONAL = re.compile(r"documento|proveedor_adjudicado|nombre_(representante|ordenador|supervisor)|identificaci|domicilio|cuenta")


# ### Formato por columna ###
def detectar_formato(valores):
    if not valores:
        return "vacío"
    muestra = [v for v in valores if v is not None][:200]
    if all(isinstance(v, dict) for v in muestra):
        return "objeto " + ",".join(sorted(muestra[0].keys()))
    textos = [str(v) for v in muestra]
    if all(re.fullmatch(r"-?\d+(\.\d+)?", t) for t in textos):
        return "número como texto"
    if all(re.fullmatch(r"\d{4}-\d{2}-\d{2}T[\d:.]+", t) for t in textos):
        return "fecha ISO como texto"
    return "texto"


def perfilar(metadatos, filas):
    columnas = []
    for col in metadatos["columns"]:
        nombre = col["fieldName"]
        if nombre.startswith(":"):
            continue

        valores = [f.get(nombre) for f in filas]
        presentes = [v for v in valores if v not in (None, "", "No Definido")]
        distintos = {json.dumps(v, ensure_ascii=False) for v in presentes}
        columnas.append({
            "nombre": nombre,
            "titulo": col.get("name"),
            "tipo_socrata": col.get("dataTypeName"),
            "descripcion": (col.get("description") or "").strip(),
            "formato_json": detectar_formato(presentes),
            "pct_nulos": round(100 * (1 - len(presentes) / max(len(filas), 1)), 1),
            "valores_distintos_muestra": len(distintos),
            "ejemplo": ("[dato personal oculto]" if PATRON_PERSONAL.search(nombre) else presentes[0]) if presentes else None,
            "usada_por_el_agente": nombre in COLUMNAS_CONTRATO,
        })
    return columnas


# ### Informe markdown ###
def escribir_informe(columnas, total_filas):
    lineas = [
        "<!--",
        "  ### Archivo: esquema.md ###",
        "  Autor: Juan Camilo Agudelo (Jagudelo14)",
        "  Correo: camiloagu1401@gmail.com",
        f"  Fecha: {date.today().isoformat()}",
        "  Descripción: Informe generado por scripts/fase0_esquema.py",
        "-->",
        "",
        "# Esquema real de SECOP II – Contratos Electrónicos (jbjy-vk9h)",
        "",
        f"Generado el {date.today().isoformat()} con {total_filas} filas de muestra.",
        "",
        "## Columnas que usa el agente",
        "",
        "| Columna | Tipo Socrata | Formato en JSON | % nulos | Ejemplo |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in columnas:
        if c["usada_por_el_agente"]:
            ejemplo = str(c["ejemplo"])[:60].replace("|", "/")
            lineas.append(f"| `{c['nombre']}` | {c['tipo_socrata']} | {c['formato_json']} | {c['pct_nulos']} | {ejemplo} |")

    lineas += [
        "",
        "## Resto de columnas",
        "",
        "| Columna | Tipo Socrata | % nulos |",
        "| --- | --- | --- |",
    ]
    for c in columnas:
        if not c["usada_por_el_agente"]:
            lineas.append(f"| `{c['nombre']}` | {c['tipo_socrata']} | {c['pct_nulos']} |")

    (CARPETA_DOCS / "esquema.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    CARPETA_DOCS.mkdir(exist_ok=True)

    print("Bajando metadatos...")
    metadatos = socrata.leer_metadatos()
    print(f"Bajando {FILAS_MUESTRA} filas de muestra...")
    filas = socrata.consultar({"$limit": FILAS_MUESTRA, "$order": ":id"})

    columnas = perfilar(metadatos, filas)
    faltantes = [c for c in COLUMNAS_CONTRATO if c not in {col["nombre"] for col in columnas}]

    esquema = {
        "dataset": socrata.DATASET,
        "nombre": metadatos.get("name"),
        "fecha_generado": date.today().isoformat(),
        "filas_muestra": len(filas),
        "columnas": columnas,
    }
    (CARPETA_DOCS / "schema.json").write_text(json.dumps(esquema, ensure_ascii=False, indent=2), encoding="utf-8")
    (CARPETA_DOCS / "muestra.json").write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
    escribir_informe(columnas, len(filas))

    print(f"{len(columnas)} columnas guardadas en docs/schema.json")
    if faltantes:
        print(f"OJO, columnas esperadas que no existen: {faltantes}")
        sys.exit(1)
    print("Todas las columnas que usa el agente existen.")


if __name__ == "__main__":
    main()
