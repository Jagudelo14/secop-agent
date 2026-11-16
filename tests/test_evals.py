# ### Archivo: test_evals.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: Pruebas del calificador del set de evaluación

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

import run  # noqa: E402


# ### Números ###
def test_extrae_formato_colombiano():
    assert 1_234_567_890 in run.extraer_numeros("Total: $1.234.567.890")
    assert 3926 in run.extraer_numeros("firmó 3.926 contratos")
    assert 1_500_000.5 in run.extraer_numeros("$1.500.000,5")


def test_extrae_millones():
    assert 2_964_900_000_000 in run.extraer_numeros("unos 2.964.900 millones")


# ### Calificación ###
def test_cifra_dentro_de_tolerancia():
    ok, _ = run.calificar({"tipo": "conteo_suma"}, 2_964_907_448_466, "Fueron $2.964.907.448.466")
    assert ok


def test_cifra_equivocada():
    ok, _ = run.calificar({"tipo": "conteo_suma"}, 3926, "Firmó 3.500 contratos")
    assert not ok


def test_ranking_en_orden():
    correcta = [{"clave": str(i), "nombre": f"Empresa {l}", "total": 1} for i, l in enumerate("ABCDE")]
    texto = "| 1 | EMPRESA A |\n| 2 | Empresa B |\n| 3 | empresa c |\n| 4 | Empresa D |\n| 5 | Empresa E |"
    assert run.calificar({"tipo": "ranking"}, correcta, texto)[0]


def test_ranking_desordenado():
    correcta = [{"clave": None, "nombre": n, "total": 1} for n in ["Uno", "Dos", "Tres", "Cuatro", "Cinco"]]
    texto = "Dos, Uno, Tres, Cuatro, Cinco"
    assert not run.calificar({"tipo": "ranking"}, correcta, texto)[0]


def test_filtro_mismo_conjunto():
    correcta = ["CO1.PCCNTR.1", "CO1.PCCNTR.2"]
    assert run.calificar({"tipo": "filtro"}, correcta, "CO1.PCCNTR.2 y CO1.PCCNTR.1")[0]
    assert not run.calificar({"tipo": "filtro"}, correcta, "CO1.PCCNTR.2")[0]


def test_fuera_alcance():
    assert run.calificar({"tipo": "fuera_alcance"}, None, "No puedo responder eso con datos de SECOP II.")[0]
    assert not run.calificar({"tipo": "fuera_alcance"}, None, "El más corrupto recibió $5.000.000.000")[0]


def test_ranking_nombre_contenido_en_otro():
    # licitación pública dentro de obra pública
    nombres = ["Licitación pública Obra Publica", "Contratación directa", "Concurso de méritos abierto", "Licitación pública", "Mínima cuantía"]
    correcta = [{"clave": n, "nombre": None, "total": 1} for n in nombres]
    texto = "\n".join(f"| {i} | {n} |" for i, n in enumerate(nombres, 1))
    assert run.calificar({"tipo": "ranking"}, correcta, texto)[0]


def test_ranking_claves_cortas():
    nombres = ["Prestación de servicios", "Otro", "Decreto 092 de 2017", "Obra", "Compraventa"]
    correcta = [{"clave": n, "nombre": None, "total": 1} for n in nombres]
    texto = "\n".join(f"| {i} | {n} |" for i, n in enumerate(nombres, 1))
    assert run.calificar({"tipo": "ranking"}, correcta, texto)[0]


def test_fuera_alcance_con_codigos_no_es_cifra():
    texto = "Hay varias: SECRETARÍA GENERAL (Código: `700218068`, NIT: `899999061`). ¿Cuál deseas consultar?"
    assert run.calificar({"tipo": "fuera_alcance"}, None, texto)[0]


def test_fuera_alcance_no_se_puede():
    texto = "Esta pregunta no se puede responder con los datos de SECOP II."
    assert run.calificar({"tipo": "fuera_alcance"}, None, texto)[0]


# ### Reglas del set definitivo ###
def test_varias_cifras_deben_estar_todas():
    correcta = {"valores": [442_328_205_306, 291_147_505_222, 479_352_414_754], "mencionar": None}
    completo = "2023: $442.328.205.306; 2024: $291.147.505.222; 2025: $479.352.414.754"
    assert run.calificar({"tipo": "conteo_suma"}, correcta, completo)[0]
    assert not run.calificar({"tipo": "conteo_suma"}, correcta, "2023: $442.328.205.306")[0]


def test_cero_en_palabras():
    correcta = {"valores": [0.0], "mencionar": None}
    assert run.calificar({"tipo": "conteo_suma"}, correcta, "Ese NIT no registra contratos en 2025.")[0]
    assert not run.calificar({"tipo": "conteo_suma"}, correcta, "Tiene 12 contratos.")[0]


def test_diferencia_debe_nombrar_al_mayor():
    correcta = {"valores": [61_333_239_678], "mencionar": "CALDAS"}
    assert run.calificar({"tipo": "conteo_suma"}, correcta, "Caldas contrató más; diferencia de $61.333.239.678")[0]
    assert not run.calificar({"tipo": "conteo_suma"}, correcta, "La diferencia fue $61.333.239.678")[0]


def test_ranking_de_diez():
    correcta = [{"clave": None, "nombre": f"Empresa {c}", "total": 1} for c in "ABCDEFGHIJ"]
    texto = "\n".join(f"| {i} | Empresa {c} |" for i, c in enumerate("ABCDEFGHIJ", 1))
    assert run.calificar({"tipo": "ranking"}, correcta, texto)[0]
    assert not run.calificar({"tipo": "ranking"}, correcta, texto.replace("Empresa J", "Otra"))[0]


def test_ranking_clave_larga_por_inicio():
    objeto = "SUMINISTRO DE COMPLEMENTO ALIMENTARIO A LOS ESTUDIANTES MATRICULADOS EN LAS INSTITUCIONES EDUCATIVAS"
    correcta = [{"clave": objeto, "nombre": None, "total": 1}]
    texto = "1. Suministro de complemento alimentario a los estudiantes matriculados en las..."
    assert run.calificar({"tipo": "ranking"}, correcta, texto)[0]


def test_filtro_con_tope():
    ids = [f"CO1.PCCNTR.{i}" for i in range(100, 160)]
    correcta = {"ids": ids, "tope": 50}
    assert run.calificar({"tipo": "filtro"}, correcta, " ".join(ids[:50]))[0]
    assert not run.calificar({"tipo": "filtro"}, correcta, " ".join(ids[:49] + ["CO1.PCCNTR.9"]))[0]


def test_filtro_mas_de_cincuenta_pide_total():
    ids = [f"CO1.PCCNTR.{i}" for i in range(100, 204)]
    correcta = {"ids": ids, "tope": None}
    assert run.calificar({"tipo": "filtro"}, correcta, "Son 104 contratos. " + " ".join(ids[:50]))[0]
    assert not run.calificar({"tipo": "filtro"}, correcta, "Algunos: " + " ".join(ids[:50]))[0]


def test_ambigua():
    assert run.calificar({"tipo": "ambigua"}, None, "Hay varias entidades de la Policía. ¿Cuál quieres consultar?")[0]
    assert not run.calificar({"tipo": "ambigua"}, None, "La Policía contrató $5.000.000 en 2024.")[0]
