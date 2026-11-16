# ### Archivo: run.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Corre el set de evaluación, recalcula respuestas correctas y genera el reporte de métricas

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from secop_agent import socrata  # noqa: E402
from secop_agent.agent import MAX_LLAMADAS, VERSION_PROMPT  # noqa: E402
from secop_agent.schema import a_numero, normalizar_texto  # noqa: E402

CARPETA = Path(__file__).resolve().parent
ARCHIVO_PREGUNTAS = CARPETA / "preguntas.jsonl"
CARPETA_RESULTADOS = CARPETA / "resultados"
TOLERANCIA = 0.01
MAX_IDS_FILTRO = 50
# claves largas, como objetos
LARGO_CLAVE = 60
MARCAS_CERO = ["ningún contrato", "ningun contrato", "no tiene contratos", "no registra", "no se encontr",
               "no encontr", "no hay contratos", "0 contratos", "cero contratos"]

MARCAS_FUERA_ALCANCE = [
    "no puedo", "no se puede", "no es posible", "no tengo", "no cuento", "fuera de", "no está disponible",
    "no esta disponible", "aclar", "cuál de", "cual de", "precisar", "especificar", "no implica",
    "no dispongo", "secop i ", "no incluye", "no contiene",
]


# ### Carga ###
def cargar_preguntas(ids=None, limite=None):
    preguntas = [json.loads(l) for l in ARCHIVO_PREGUNTAS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if ids:
        preguntas = [p for p in preguntas if p["id"] in ids]
    if limite:
        preguntas = preguntas[:limite]
    return preguntas


# ### Respuesta correcta en vivo ###
def respuesta_correcta(pregunta):
    if not pregunta["soql"]:
        return None
    # sin caché, siempre fresca
    filas = socrata._pedir(socrata.URL_DATOS, pregunta["soql"])

    if pregunta["tipo"] == "conteo_suma":
        if pregunta.get("calculo") == "diferencia":
            # mayor menos menor
            totales = [a_numero(f.get("total")) for f in filas]
            return {"valores": [totales[0] - totales[1]], "mencionar": pregunta.get("debe_mencionar")}
        # todas las columnas respuesta
        valores = [a_numero(v) for f in filas for k, v in f.items() if k.startswith("respuesta")]
        return {"valores": valores or [0.0], "mencionar": pregunta.get("debe_mencionar")}
    if pregunta["tipo"] == "ranking":
        return [{"clave": f.get("clave"), "nombre": f.get("nombre"), "total": a_numero(f.get("total"))} for f in filas]
    if pregunta["tipo"] == "filtro":
        return {"ids": sorted(f["id_contrato"] for f in filas), "tope": pregunta.get("tope")}
    return None


# ### Lectura de números en texto ###
def extraer_numeros(texto):
    numeros = []
    patron = r"\d[\d.,]*(?:\s*(mil millones|millones|millón|billones|mil))?"
    for m in re.finditer(patron, texto, flags=re.IGNORECASE):
        crudo = m.group(0)
        escala_txt = (m.group(1) or "").lower()
        cifra = crudo[: len(crudo) - len(m.group(1))].strip() if m.group(1) else crudo
        cifra = cifra.rstrip(".,")

        valor = _a_float_colombiano(cifra)
        if valor is None:
            continue
        escala = {"mil millones": 1e9, "millones": 1e6, "millón": 1e6, "billones": 1e12, "mil": 1e3}.get(escala_txt, 1)
        numeros.append(valor * escala)
    return numeros


def _a_float_colombiano(cifra):
    if "." in cifra and "," in cifra:
        # el último separador es decimal
        if cifra.rfind(",") > cifra.rfind("."):
            cifra = cifra.replace(".", "").replace(",", ".")
        else:
            cifra = cifra.replace(",", "")
    elif "." in cifra or "," in cifra:
        sep = "." if "." in cifra else ","
        partes = cifra.split(sep)
        # grupos de 3 = miles
        if all(len(p) == 3 for p in partes[1:]):
            cifra = "".join(partes)
        else:
            cifra = cifra.replace(",", ".")
    try:
        return float(cifra)
    except ValueError:
        return None


# ### Calificación ###
def calificar(pregunta, correcta, texto):
    tipo = pregunta["tipo"]
    if tipo == "conteo_suma":
        return _calificar_cifra(correcta, texto)
    if tipo == "ranking":
        return _calificar_ranking(correcta, texto)
    if tipo == "filtro":
        return _calificar_filtro(correcta, texto)
    if tipo == "ambigua":
        return _calificar_ambigua(texto)
    return _calificar_fuera_alcance(texto)


def _aparece(valor, numeros, texto):
    if valor == 0:
        # cero dicho en palabras
        return 0 in numeros or any(m in texto.lower() for m in MARCAS_CERO)
    return any(abs(n - valor) / abs(valor) < TOLERANCIA for n in numeros)


def _calificar_cifra(correcta, texto):
    # compatible con una sola cifra
    if not isinstance(correcta, dict):
        correcta = {"valores": [correcta], "mencionar": None}
    numeros = extraer_numeros(texto)
    faltan = [v for v in correcta["valores"] if not _aparece(v, numeros, texto)]
    if faltan:
        return False, f"no aparece {', '.join(f'{v:,.0f}' for v in faltan)}"
    mencionar = correcta.get("mencionar")
    if mencionar and normalizar_texto(mencionar) not in normalizar_texto(texto):
        return False, f"no menciona {mencionar}"
    return True, f"{len(correcta['valores'])} cifra(s) correctas"


def _posicion(fila, texto_norm, texto_crudo):
    posiciones = []
    # claves cortas dan falsos positivos
    if fila["clave"] and len(str(fila["clave"])) >= 5:
        # textos largos, solo el inicio
        clave_norm = normalizar_texto(fila["clave"])[:LARGO_CLAVE]
        if clave_norm and clave_norm in texto_norm:
            posiciones.append(texto_norm.index(clave_norm))
        elif fila["clave"] in texto_crudo:
            posiciones.append(len(normalizar_texto(texto_crudo[: texto_crudo.index(fila["clave"])])))
    elif fila["clave"] and str(fila["clave"]).isalpha():
        # texto corto, palabra completa
        coincidencia = re.search(rf"\b{re.escape(normalizar_texto(fila['clave']))}\b", texto_norm)
        if coincidencia:
            posiciones.append(coincidencia.start())
    if fila["nombre"]:
        nombre_norm = normalizar_texto(fila["nombre"])
        if nombre_norm and nombre_norm in texto_norm:
            posiciones.append(texto_norm.index(nombre_norm))
    return min(posiciones) if posiciones else None


def _calificar_ranking(correcta, texto):
    texto_norm = normalizar_texto(texto)
    # todas las filas pedidas
    posiciones = [_posicion(f, texto_norm, texto) for f in correcta]
    faltan = [correcta[i]["nombre"] or correcta[i]["clave"] for i, p in enumerate(posiciones) if p is None]
    if faltan:
        return False, f"faltan: {[str(f)[:40] for f in faltan]}"
    # buscar en orden, evita subcadenas
    desde = 0
    for fila in correcta:
        posicion = _posicion(fila, texto_norm[desde:], "")
        if posicion is None:
            return False, "orden distinto"
        desde += posicion + 1
    return True, f"top {len(correcta)} en orden"


def _calificar_filtro(correcta, texto):
    # compatible con lista sola
    if not isinstance(correcta, dict):
        correcta = {"ids": correcta, "tope": None}
    encontrados = set(re.findall(r"CO1\.PCCNTR\.\d+", texto))
    esperados = set(correcta["ids"])
    sobran = encontrados - esperados
    tope = correcta.get("tope")

    # pide hasta un tope
    if tope and len(esperados) > tope:
        if not sobran and len(encontrados) == tope:
            return True, f"{tope} ids válidos de {len(esperados)}"
        return False, f"lista {len(encontrados)} de tope {tope}, sobran {len(sobran)}"
    # muchos, basta total y validez
    if len(esperados) > MAX_IDS_FILTRO:
        # números de ids no cuentan
        sin_ids = re.sub(r"CO1\.PCCNTR\.\d+", " ", texto)
        total_ok = _aparece(len(esperados), extraer_numeros(sin_ids), sin_ids)
        if total_ok and encontrados and not sobran:
            return True, f"total {len(esperados)} y {len(encontrados)} ids válidos"
        return False, f"total {'ok' if total_ok else 'no aparece'}, sobran {len(sobran)}, listados {len(encontrados)}"

    if encontrados == esperados:
        return True, f"{len(esperados)} ids iguales"
    return False, f"faltan {len(esperados - encontrados)}, sobran {len(sobran)}"


def _calificar_ambigua(texto):
    # sugerencia, se revisa a mano
    bajo = texto.lower()
    pregunta = "?" in texto and any(m in bajo for m in ("cuál", "cual", "cuáles", "especific", "precis", "aclar"))
    separa = any(m in bajo for m in ("varias entidades", "son varias", "distintas entidades", "diferentes entidades"))
    if pregunta or separa:
        return True, "pidió aclaración o separó entidades (revisar a mano)"
    return False, "no pidió aclaración ni separó (revisar a mano)"


def _calificar_fuera_alcance(texto):
    bajo = texto.lower()
    # solo pesos, no códigos ni nit
    montos = re.findall(r"\$\s*\d|\d\s*(?:millones|mil millones|billones)", bajo)
    marca = any(m in bajo for m in MARCAS_FUERA_ALCANCE) or "?" in texto
    if marca and not montos:
        return True, "pidió aclaración o declinó"
    return False, "dio cifras o no declinó"


# ### Estimación de precios ###
def _tokens_entrada(r):
    return r["tokens"]["entrada"] + r["tokens"]["cache_lectura"] + r["tokens"]["cache_escritura"]


def precios_referencia():
    from secop_agent.agent import PRECIOS
    precios = dict(PRECIOS)
    # gemini de pago, opcional
    entrada, salida = os.getenv("GEMINI_PRECIO_ENTRADA"), os.getenv("GEMINI_PRECIO_SALIDA")
    if entrada and salida:
        precios[os.getenv("MODELGEMINI", "gemini") + " (pago)"] = {"entrada": float(entrada), "salida": float(salida)}
    return precios


def estimar_precios(resultados):
    n = max(len(resultados), 1)
    entrada = sum(_tokens_entrada(r) for r in resultados)
    salida = sum(r["tokens"]["salida"] for r in resultados)

    lineas = [
        "",
        f"**Tokens totales:** {entrada:,} de entrada · {salida:,} de salida",
        "",
        "Costo estimado con los mismos tokens, sin caché (aproximado, cada proveedor tokeniza distinto):",
        "",
        "| Modelo | Costo total (USD) | Por pregunta (USD) | 1.000 preguntas (USD) |",
        "| --- | --- | --- | --- |",
    ]
    for modelo, precio in precios_referencia().items():
        # usd por millón
        total = (entrada * precio["entrada"] + salida * precio["salida"]) / 1_000_000
        lineas.append(f"| {modelo} | {total:.4f} | {total / n:.5f} | {total / n * 1000:.2f} |")
    return lineas


# ### Respuestas ###
def _bloque_codigo(texto):
    return "```\n" + (texto or "(vacía)").replace("```", "'''") + "\n```"


def escribir_respuestas(resultados, ruta):
    lineas = [f"## Respuestas del agente — {datetime.now():%Y-%m-%d %H:%M}", ""]
    for r in resultados:
        lineas += [
            f"### {r['id']} · {r['tipo']}",
            "",
            f"**Pregunta:** {r['pregunta']}",
            "",
            f"**Modelo:** {r['modelo']} · **Tokens:** {_tokens_entrada(r):,} entrada / {r['tokens']['salida']:,} salida · "
            f"**Latencia:** {r['latencia_seg']} s · **Herramientas:** {r['llamadas_herramientas']}",
            "",
        ]
        if r.get("error_agente"):
            lineas += [f"**Error del agente:** {r['error_agente']}", ""]
        # pasos del agente
        for paso in r["traza"]:
            estado = f" — error: {paso['error']}" if paso["error"] else ""
            lineas.append(f"- `{paso['herramienta']}` {json.dumps(paso['argumentos'], ensure_ascii=False)}{estado}")
        lineas += ["", _bloque_codigo(r["respuesta"]), ""]
        if "acierto" in r:
            lineas += [f"**Verificación:** {'acierto' if r['acierto'] else 'fallo'} — {r['detalle']}", ""]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


# ### Métricas ###
def _porcentaje(parte, total):
    return f"{parte}/{total} ({100 * parte / total:.1f}%)" if total else "0/0"


def _percentil(valores, p):
    if not valores:
        return 0
    ordenados = sorted(valores)
    # índice más cercano
    return ordenados[min(len(ordenados) - 1, round(p / 100 * (len(ordenados) - 1)))]


def escribir_metricas(resultados, ruta):
    n = len(resultados)
    aciertos = sum(r["acierto"] for r in resultados)
    errores_agente = sum(bool(r.get("error_agente")) for r in resultados)
    llamadas = sum(r["llamadas_herramientas"] for r in resultados)
    errores_herr = sum(1 for r in resultados for paso in r["traza"] if paso["error"])
    con_error_herr = sum(any(paso["error"] for paso in r["traza"]) for r in resultados)
    al_limite = sum(r["llamadas_herramientas"] >= MAX_LLAMADAS for r in resultados)
    # enlaces en preguntas con datos
    con_datos = [r for r in resultados if r["tipo"] not in ("fuera_alcance", "ambigua") and not r.get("error_agente")]
    con_enlace = sum("https://" in r["respuesta"] for r in con_datos)
    enlaces, inventados = 0, 0
    for r in resultados:
        # enlaces que no salieron de herramientas
        vistas = {u for paso in r["traza"] for u in paso.get("urls", [])}
        registro = any("urls" in paso for paso in r["traza"])
        for u in re.findall(r"https?://[^\s)\]|>]+", r["respuesta"]):
            enlaces += 1
            # corridas viejas sin registro
            inventados += (u not in vistas) if registro else not u.startswith("https://community.secop.gov.co")
    latencias = [r["latencia_seg"] for r in resultados if not r.get("error_agente")]
    modelos = {}
    for r in resultados:
        modelos[r["modelo"]] = modelos.get(r["modelo"], 0) + 1

    lineas = [
        f"## Métricas de evaluación — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"**Acierto: {_porcentaje(aciertos, n)}** · meta del SPEC: 24/30 (80%)",
        "",
        f"Prompt: {', '.join(sorted({r.get('version_prompt', 'sin registro') for r in resultados}))}",
        "",
        "| Métrica | Valor |",
        "| --- | --- |",
        f"| Aciertos | {_porcentaje(aciertos, n)} |",
        f"| Fallos (respuesta incorrecta) | {_porcentaje(n - aciertos - errores_agente, n)} |",
        f"| Errores del agente (no respondió) | {_porcentaje(errores_agente, n)} |",
        f"| Preguntas con algún error de herramienta | {_porcentaje(con_error_herr, n)} |",
        f"| Llamadas a herramientas con error | {_porcentaje(errores_herr, llamadas)} |",
        f"| Preguntas que llegaron al límite de {MAX_LLAMADAS} llamadas | {_porcentaje(al_limite, n)} |",
        f"| Respuestas con datos que incluyen enlace | {_porcentaje(con_enlace, len(con_datos))} |",
        f"| Enlaces inventados (no vienen de ninguna herramienta) | {_porcentaje(inventados, enlaces)} |",
        f"| Herramientas por pregunta (promedio) | {llamadas / max(n, 1):.1f} |",
        f"| Latencia promedio / mediana / p95 (s) | {sum(latencias) / max(len(latencias), 1):.1f} / "
        f"{_percentil(latencias, 50):.1f} / {_percentil(latencias, 95):.1f} |",
        f"| Modelos que respondieron | {', '.join(f'{m}: {k}' for m, k in modelos.items())} |",
        "",
        "### Por tipo de pregunta",
        "",
        "| Tipo | Acierto | Tokens entrada prom. | Tokens salida prom. | Latencia prom. (s) | Herramientas prom. |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for tipo in ("conteo_suma", "ranking", "filtro", "ambigua", "fuera_alcance", None):
        grupo = [r for r in resultados if tipo is None or r["tipo"] == tipo]
        if not grupo:
            continue
        k = len(grupo)
        lineas.append(
            f"| {tipo or '**Total**'} | {_porcentaje(sum(r['acierto'] for r in grupo), k)} | "
            f"{sum(_tokens_entrada(r) for r in grupo) / k:,.0f} | {sum(r['tokens']['salida'] for r in grupo) / k:,.0f} | "
            f"{sum(r['latencia_seg'] for r in grupo) / k:.1f} | {sum(r['llamadas_herramientas'] for r in grupo) / k:.1f} |"
        )

    lineas += ["", "### Consumo y costo estimado"]
    lineas += estimar_precios(resultados)

    lineas += ["", "### Detalle", "",
               "| Id | Tipo | Resultado | Detalle | Tokens entrada | Tokens salida | Latencia (s) | Herramientas |",
               "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in resultados:
        estado = "error" if r.get("error_agente") else ("acierto" if r["acierto"] else "fallo")
        lineas.append(
            f"| {r['id']} | {r['tipo']} | {estado} | {r['detalle']} | {_tokens_entrada(r):,} | "
            f"{r['tokens']['salida']:,} | {r['latencia_seg']} | {r['llamadas_herramientas']} |"
        )

    reporte = "\n".join(lineas) + "\n"
    ruta.write_text(reporte, encoding="utf-8")
    (CARPETA_RESULTADOS / "ultimo.md").write_text(reporte, encoding="utf-8")
    return reporte


# ### Paso 1: correr ###
def correr(preguntas, modelo, archivo, rehacer=()):
    from secop_agent.agent import responder

    # retomar, repetir errores y pedidas
    previas = leer_corrida(archivo) if archivo.exists() else []
    conservar = [r for r in previas if not r.get("error_agente") and r["id"] not in rehacer]
    archivo.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in conservar), encoding="utf-8")
    hechas = {r["id"] for r in conservar}
    for p in preguntas:
        if p["id"] in hechas:
            continue
        try:
            r = responder(p["pregunta"], modelo=modelo)
            error = None
        except Exception as fallo:  # una pregunta rota no tumba el set
            r = {"respuesta": "", "modelo": modelo or "sin respuesta", "tokens": {"entrada": 0, "salida": 0, "cache_lectura": 0, "cache_escritura": 0},
                 "costo_usd": 0, "latencia_seg": 0, "llamadas_herramientas": 0, "traza": []}
            error = str(fallo)

        fila = {
            "id": p["id"], "tipo": p["tipo"], "pregunta": p["pregunta"], "modelo": r["modelo"], "version_prompt": VERSION_PROMPT, "set": ARCHIVO_PREGUNTAS.stem,
            "respuesta": r["respuesta"], "error_agente": error, "tokens": r["tokens"], "costo_usd": r["costo_usd"],
            "latencia_seg": r["latencia_seg"], "llamadas_herramientas": r["llamadas_herramientas"], "traza": r["traza"],
        }
        # guardar al momento
        with open(archivo, "a", encoding="utf-8") as salida:
            salida.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")

        estado = f"ERROR {error[:80]}" if error else f"{r['latencia_seg']}s · {r['llamadas_herramientas']} herr."
        print(f"{p['id']} {r['modelo']} · {_tokens_entrada(fila):,}/{r['tokens']['salida']:,} tokens · {estado}")


def leer_corrida(archivo):
    return [json.loads(l) for l in archivo.read_text(encoding="utf-8").splitlines() if l.strip()]


# ### Paso 2: verificar ###
def verificar(archivo):
    preguntas = {p["id"]: p for p in cargar_preguntas()}
    # orden del set
    orden = list(preguntas)
    resultados = sorted(leer_corrida(archivo), key=lambda r: orden.index(r["id"]))
    # calificación a mano, si existe
    archivo_manual = Path(f"{archivo.with_suffix('')}-manual.json")
    manual = json.loads(archivo_manual.read_text(encoding="utf-8")) if archivo_manual.exists() else {}
    for r in resultados:
        if r.get("error_agente"):
            r["acierto"], r["detalle"], r["correcta"] = False, f"error del agente: {r['error_agente'][:80]}", None
            continue
        # respuesta correcta en vivo
        r["correcta"] = respuesta_correcta(preguntas[r["id"]])
        r["acierto"], r["detalle"] = calificar(preguntas[r["id"]], r["correcta"], r["respuesta"])
        # revisión manual manda
        if r["id"] in manual:
            r["acierto"], r["detalle"] = manual[r["id"]]["acierto"], "manual: " + manual[r["id"]]["razon"]
        print(f"{r['id']} {'OK ' if r['acierto'] else 'MAL'} {r['detalle']}")

    # guardar calificado
    base = archivo.with_suffix("")
    with open(f"{base}-verificado.jsonl", "w", encoding="utf-8") as salida:
        for r in resultados:
            salida.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    escribir_respuestas(resultados, Path(f"{base}-respuestas.md"))
    return escribir_metricas(resultados, Path(f"{base}-metricas.md"))


# ### Validar sin LLM ###
def validar(preguntas):
    ok = True
    for p in preguntas:
        correcta = respuesta_correcta(p)
        if p["tipo"] == "filtro":
            n = len(correcta["ids"])
            estado = "OK" if n > 0 else "REVISAR"
            ok &= estado == "OK"
            print(f"{p['id']} filtro: {n} contratos {estado}")
        elif p["tipo"] == "ranking":
            estado = "OK" if len(correcta) >= 3 else "REVISAR"
            ok &= estado == "OK"
            print(f"{p['id']} ranking: {[f['nombre'] or f['clave'] for f in correcta]} {estado}")
        elif p["tipo"] == "conteo_suma":
            print(f"{p['id']} cifras: {[f'{v:,.0f}' for v in correcta['valores']]} OK")
        else:
            print(f"{p['id']} {p['tipo']}, se califica a mano")
    return ok


# ### Principal ###
def main():
    parser = argparse.ArgumentParser(description="Evaluación del agente SECOP II")
    parser.add_argument("--modelo", default=None)
    parser.add_argument("--ids", nargs="*", help="Solo estas preguntas, ej: c01 r03")
    parser.add_argument("--limite", type=int, help="Solo las N primeras")
    parser.add_argument("--validar", action="store_true", help="Revisa las consultas SoQL sin llamar al LLM")
    parser.add_argument("--continuar", help="Retoma una corrida .jsonl cortada")
    parser.add_argument("--verificar", help="Solo califica una corrida .jsonl ya hecha")
    parser.add_argument("--sin-verificar", action="store_true", help="Solo corre, sin calificar")
    parser.add_argument("--preguntas", help="Archivo de preguntas, por defecto evals/preguntas.jsonl")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # set de desarrollo o de prueba
    global ARCHIVO_PREGUNTAS
    if args.preguntas:
        ARCHIVO_PREGUNTAS = Path(args.preguntas).resolve()
    preguntas = cargar_preguntas(args.ids, args.limite)

    if args.validar:
        sys.exit(0 if validar(preguntas) else 1)
    # caché vieja daría falsos errores
    os.environ["SECOP_CACHE_HORAS"] = "1"

    if args.verificar:
        print(verificar(Path(args.verificar)))
        return

    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    archivo = Path(args.continuar) if args.continuar else CARPETA_RESULTADOS / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    print(f"Corrida: {archivo}")
    # con --ids se rehacen esas
    correr(preguntas, args.modelo, archivo, rehacer=set(args.ids or []) if args.continuar else ())

    # respuestas sin calificar
    escribir_respuestas(leer_corrida(archivo), archivo.with_name(archivo.stem + "-respuestas.md"))
    if not args.sin_verificar:
        print()
        print(verificar(archivo))


if __name__ == "__main__":
    main()
