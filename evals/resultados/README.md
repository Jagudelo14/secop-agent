<!--
  ### Archivo: README.md ###
  Autor: Juan Camilo Agudelo (Jagudelo14)
  Correo: camiloagu1401@gmail.com
  Fecha: 2026-11-19
  Descripción: Guía de las corridas de evaluación que quedan en el repositorio
-->

# Resultados de la evaluación

Aquí dejo las corridas del set definitivo de 50 preguntas, con todo lo necesario para auditarlas. Las corridas del set de desarrollo no se versionan. El protocolo y el análisis están en [docs/evaluacion-definitiva.md](../../docs/evaluacion-definitiva.md).

## Corridas

| Corrida | Agente | Qué es | Resultado |
| --- | --- | --- | --- |
| `20261118-085949` | v7 | **Evaluación oficial, a ciegas** | 37/50 (74%) |
| `20261119-084906` | v8 | Primera corrección después de ver los fallos | 39/50 (78%) |
| `20261119-155020` | v9 | Prueba solo de las 5 preguntas corregidas (P03, P04, P11, P14 y P38) | 5/5 |
| `20261119-160009` | v9 | Corrida completa de la versión actual | 43/50 (86%) |

## Archivos de cada corrida

| Sufijo | Contenido |
| --- | --- |
| `.jsonl` | Una línea por pregunta: respuesta del agente, modelo, tokens, latencia y herramientas que usó, con sus enlaces |
| `-verificado.jsonl` | Lo mismo más la calificación: acierto o fallo y el detalle (cifra que falta, contratos que sobran) |
| `-manual.json` | Mi calificación a mano de P41–P50 (ambiguas y fuera de alcance), con la razón de cada una |
| `-metricas.md` | Resumen: acierto por tipo, enlaces inventados, latencia, tokens y costo estimado |
| `-respuestas.md` | Las 50 respuestas en texto legible, cada una con su calificación |

Solo la v7 tiene archivos intermedios, porque fue la medición oficial y quise poder reconstruir cada paso:

| Archivo | Qué guarda |
| --- | --- |
| `20261118-085949-pasada1.jsonl` | Estado después de la primera pasada por las 50, antes de repetir las que Gemini no respondió |
| `20261118-085949-antes-reintento-infra.jsonl` | Estado antes de repetir P18, P41 y P44, que fallaron porque datos.gov.co no respondió |
| `20261118-085949-antes-p44.jsonl` | Estado antes del último reintento de P44 |

## Registros

Los `.log` son la salida de consola de cada paso: `definitiva*.log` para la v7, `v8-*.log` y `v9-*.log` para las demás. Los que dicen `reintento` corresponden a preguntas repetidas porque Gemini o datos.gov.co no respondieron; los que dicen `verificacion`, a la calificación contra datos.gov.co.

Las cédulas de personas naturales están enmascaradas (`***123`), igual que en la demo.

Para recalificar una corrida con los datos de hoy:

```bash
uv run python evals/run.py --preguntas evals/preguntas_definitivas.jsonl --verificar evals/resultados/20261118-085949.jsonl
```

Ojo: el comando sobrescribe los archivos `-verificado.jsonl`, `-metricas.md` y `-respuestas.md` de esa corrida, y como SECOP cambia todos los días, puede dar cifras un poco distintas a las de la fecha original. Para conservar los archivos de la evaluación, recalifica sobre una copia del `.jsonl`.
