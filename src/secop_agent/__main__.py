# ### Archivo: __main__.py ###
# Autor: Juan Camilo Agudelo (Jagudelo14)
# Correo: camiloagu1401@gmail.com
# Fecha: 2026-11-16
# Descripción: CLI, uso: python -m secop_agent "pregunta"

import argparse
import sys

from secop_agent.agent import responder


def main():
    parser = argparse.ArgumentParser(description="Pregúntale a SECOP II en lenguaje natural")
    parser.add_argument("pregunta", help="Pregunta entre comillas")
    parser.add_argument("--modelo", default=None, help="claude-sonnet-5-5, claude-haiku-5-5 o gemini-3.5-flash-lite")
    parser.add_argument("--traza", action="store_true", help="Mostrar llamadas a herramientas")
    args = parser.parse_args()

    # consola windows con tildes
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    resultado = responder(args.pregunta, modelo=args.modelo)
    print(resultado["respuesta"])

    if args.traza:
        print("\n--- Traza ---")
        for paso in resultado["traza"]:
            estado = f" ERROR: {paso['error']}" if paso["error"] else ""
            print(f"{paso['herramienta']}({paso['argumentos']}) {paso['segundos']}s{estado}")

    print(
        f"\n[{resultado['modelo']} · {resultado['llamadas_herramientas']} herramientas · "
        f"{resultado['latencia_seg']}s · ${resultado['costo_usd']:.4f} USD]"
    )


if __name__ == "__main__":
    main()
