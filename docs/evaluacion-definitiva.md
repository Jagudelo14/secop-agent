<!--
  ### Archivo: evaluacion-definitiva.md ###
  Autor: Juan Camilo Agudelo (Jagudelo14)
  Correo: camiloagu1401@gmail.com
  Fecha: 2026-11-16
  Descripción: Protocolo y resultados de la evaluación definitiva del agente sobre el set de 50 preguntas
-->

# Evaluación definitiva

Esta es la evaluación que se presenta. Usa el set de 50 preguntas escrito por Juan Camilo Agudelo, que no se usó para desarrollar el agente. El proceso de desarrollo previo, con el set de 30 preguntas, está en [prompt-versiones.md](prompt-versiones.md).

## Set de preguntas

- **Archivo:** `evals/preguntas_definitivas.jsonl`, con la redacción exacta del autor. Solo se agregan las consultas SoQL que dan la respuesta correcta; el texto de las preguntas no se toca.
- **Autor:** Juan Camilo Agudelo. Las preguntas no las escribió quien desarrolló el agente.
- **Congelado:** 2026-11-16 15:22, antes de que el agente respondiera cualquiera de ellas.
- **Huella SHA-256** de las 50 líneas `id<TAB>pregunta`: `73cb07fc6e16bfbf2fb4998e444ef06c04c9abc06729c5f4dc639e750676b06c`

| Tipo | Preguntas | Cantidad |
| --- | --- | --- |
| Conteo o suma | P01–P15 | 15 |
| Ranking | P16–P30 | 15 |
| Filtro | P31–P40 | 10 |
| Ambigua | P41–P45 | 5 |
| Fuera de alcance | P46–P50 | 5 |

## Protocolo (registrado antes de cualquier corrida)

1. **Capacidades:** se implementa **solo** la lista cerrada de la sección siguiente. Se desarrolla y se prueba con pruebas unitarias y preguntas propias, **nunca** corriendo el agente sobre las 50 del set.
2. **Congelamiento:** se fija la versión final del código y del prompt y se registra el commit.
3. **Corrida final:** una sola vez sobre las 50 preguntas. Es la única vez que el agente ve este set. Las preguntas que no respondan por saturación o cuota de Gemini se repiten al final (ver cambio de protocolo del 2026-11-18).
4. **Reporte:** se presenta esa corrida con todas las métricas, sin excluir preguntas.

**Cambio de protocolo (2026-11-18, durante la corrida final y antes de calificar):** por decisión del autor, las preguntas que queden sin respuesta porque Gemini no respondió (saturación o cuota) **sí se repiten** al final de la corrida, con `--continuar`, hasta tener respuesta. Solo se repiten las que no tienen respuesta. Las que ya respondieron no se repiten, sean correctas o no. El reporte dice cuáles se repitieron y cuántos intentos necesitaron.

**Ampliación (2026-11-18, por decisión del autor):** la misma regla aplica cuando la caída es de datos.gov.co. En P18, P41 y P44 el agente respondió solo que el servidor de SECOP II no respondía, sin dar datos. Se repiten igual que las de Gemini, porque es una falla de infraestructura y no del agente. Esas respuestas se identificaron con una búsqueda automática de frases de error ("no responde", "timed out", "intenta de nuevo"), sin calificar el resto.

**Cambio de protocolo (2026-11-17):** el plan inicial incluía una línea base con el agente v5 sobre estas mismas 50 preguntas. El autor decidió que el set se use solo para la medición final. La línea base se canceló cuando había respondido 1 pregunta (P01); esa respuesta se borró sin leerla ni calificarla. La copia `evals/linea_base/` queda en el repositorio pero no se usa.

Después de la corrida final el agente no recibe más cambios. Si aparece un error del agente, se documenta como hallazgo, no se corrige para volver a medir.

### Decisiones tomadas por el autor antes de correr

| Tema | Decisión |
| --- | --- |
| Enfoque | Capacidades preregistradas y luego una sola corrida final. La línea base sobre este set se canceló el 2026-11-17 por decisión del autor |
| P05 "entidades territoriales" del Tolima | Cuentan todas las entidades ubicadas en Tolima |
| Preguntas de búsqueda por texto (P35, P37, P38, P40) | Las palabras clave que definen la respuesta correcta las propone el desarrollador y las aprueba el autor antes de congelar las respuestas correctas |
| Ambiguas (P41–P45) | Acierta si pide aclaración o si separa las entidades aclarando que son varias. Falla si elige una sola en silencio o suma todo como si fuera una entidad |

## Capacidades a agregar (lista cerrada)

Se decidió leyendo los **temas** de las preguntas, antes de ver cualquier respuesta del agente. No se agrega nada que no esté aquí.

| # | Capacidad | Para qué tipo de pregunta |
| --- | --- | --- |
| C1 | Filtro de rango de años (`anio_desde`, `anio_hasta`) en todas las herramientas | Periodos de varios años |
| C2 | Filtro de texto en el objeto del contrato (una o varias palabras clave) | Contratos sobre un tema |
| C3 | Agrupar por ciudad y por sector en `agregar` | Rankings por municipio o sector |
| C4 | Métricas `promedio_valor` y `contratistas_distintos` en `agregar` | Promedios y conteo de contratistas únicos |
| C5 | Filtro por tipo de contratista: persona natural o persona jurídica | Contratos con personas naturales o empresas |
| C6 | Filtro por duración mínima del contrato en días | Contratos de larga duración |
| C7 | Robustez: un tiempo agotado al consultar datos.gov.co se devuelve al modelo como error de herramienta en vez de tumbar la pregunta | Fallo observado en el set de desarrollo |

El prompt solo cambia para mencionar las capacidades nuevas en términos generales, sin ejemplos sacados de ninguna pregunta.

**Adición antes de la línea base (2026-11-16, al escribir las respuestas correctas):**

| # | Capacidad | Motivo |
| --- | --- | --- |
| C8 | Filtrar por varias entidades a la vez, o por las entidades cuyo nombre empieza igual | La Alcaldía de Cali (24 dependencias), la Gobernación del Valle y la de Cundinamarca están registradas en SECOP como una entidad distinta por cada secretaría. Se encontró revisando los datos, no por respuestas del agente, que todavía no ha corrido sobre este set. |

## Criterios de calificación (registrados antes de correr)

| Tipo | Acierta si |
| --- | --- |
| Conteo o suma | Aparecen **todas** las cifras pedidas, con tolerancia de 1%. Si la pregunta pide varios años o dos valores (pagado y contratado), deben estar todos |
| Ranking | Aparecen todos los elementos pedidos (5 o 10) en el orden correcto |
| Filtro | El conjunto de contratos listados es exactamente el esperado. Si la pregunta pone un tope ("hasta 50") y hay más, acierta si lista el tope y todos los listados cumplen el filtro |
| Ambigua | Criterio de la tabla de decisiones. Se califica a mano, dejando escrita la razón de cada una |
| Fuera de alcance | Dice que los datos no permiten responder lo que se pregunta y no afirma nada que no esté en los datos (por ejemplo, que una obra tuvo retrasos o sobrecostos). Puede mostrar datos de SECOP como contexto si aclara que no responden la pregunta. Se califica a mano, dejando escrita la razón |

**Cómo queda la calificación manual:** el calificador automático da una sugerencia para ambiguas y fuera de alcance. La decisión final y su razón se escriben en `evals/resultados/<corrida>-manual.json`, y esa decisión manda sobre la sugerencia. Los archivos manuales quedan en el repositorio para auditarlos.

Las preguntas de conteo, ranking y filtro se califican automáticamente con `evals/run.py`, contra la consulta SoQL de cada una ejecutada en vivo.

## Estado del agente

### Línea base (cancelada)

- **Copia congelada:** `evals/linea_base/secop_agent/`, guardada el 2026-11-16 a las 16:04, antes de tocar el código para las capacidades nuevas.
- **Huella SHA-256** del conjunto de archivos `.py`: `89086f8394611fbb1a13924701248c2bc843c9fd72eb0447f2305d9208ccd6a4`
- **No se usó:** se canceló antes de responder la segunda pregunta (ver cambio de protocolo). El comando que se iba a usar era:

```
PYTHONPATH=evals/linea_base python -m uv run python -u -X utf8 evals/run.py --preguntas evals/preguntas_definitivas.jsonl
```

### Capacidades implementadas (agente v6)

Implementadas el 2026-11-16 sin correr el agente sobre ninguna de las 50 preguntas. Se probaron con pruebas unitarias (76 en total) y con consultas reales a datos.gov.co sobre entidades del set de desarrollo.

| # | Implementación |
| --- | --- |
| C1 | Filtros `anio_desde` y `anio_hasta`, que no se combinan con `anio`. Para el valor de cada año se agrupa por `anio` |
| C2 | Filtro `objeto_contiene`: lista de palabras, basta que aparezca una. Busca con y sin tilde en cada vocal y en la ñ, sin comodines que traigan palabras parecidas |
| C3 | `agregar` agrupa también por `ciudad` y por `sector`, con los contratos mayores y su enlace en cada grupo |
| C4 | Métricas `promedio_valor` y `contratistas_distintos`, en cada grupo y en el total general |
| C5 | Filtro `tipo_persona`: `juridica` es NIT; `natural` es cualquier documento personal (todo menos NIT, "Otro" y "No Definido") |
| C6 | Filtro `duracion_min_dias`, calculado entre la fecha de inicio y la de fin |
| C7 | Los errores de red y los tiempos agotados llegan al modelo como error de herramienta. En Gemini, además, pasan al modelo de respaldo |
| C8 | `codigo_entidad` acepta una lista. Filtro `nombre_entidad_empieza`. `buscar_entidad` avisa cuando varias candidatas comparten el inicio del nombre antes de un guion (dependencias de una misma entidad) |

**Cambios en el prompt (v5 → v6),** sin ejemplos de ninguna pregunta:

- Si `buscar_entidad` indica que las candidatas son dependencias de una misma entidad, se toman juntas con `nombre_entidad_empieza` y se aclara en la respuesta. Si son entidades distintas, se sigue preguntando cuál.
- Para un periodo de varios años se usan `anio_desde` y `anio_hasta`; si piden cada año por separado, se agrupa por año.
- Si una lista de contratos se trunca, se da el total real y se aclara que se muestra solo una parte.

**Limitación conocida:** la detección de dependencias solo funciona cuando el nombre las separa con guion. Si una entidad está registrada con un nombre poco reconocible (como la Gobernación del Tolima, registrada como "GOBIERNO DEPARTAMENTAL"), el agente no la encuentra por nombre.

### Verificación de capacidades con el agente completo (2026-11-17)

Las pruebas de la v6 se habían hecho solo a nivel de herramienta. Antes de congelar se verificó el agente completo con Gemini, sin tocar el set definitivo:

1. **Prueba de humo** (pregunta propia sobre el INVIAS: contratos sobre puentes entre 2021 y 2023, año por año). Gemini aceptó las definiciones nuevas y el agente usó el rango de años, la búsqueda en el objeto y la agrupación por año. Hallazgos:
   - Buscó "puentes" en plural, lo que pierde contratos que dicen "puente". **Corrección:** la descripción de `objeto_contiene` pide usar la forma más corta de la palabra.
   - **Corrección:** la detección de dependencias compara los nombres sin tildes, porque una misma entidad aparece con y sin tilde.
2. **Set de verificación propio** (`evals/preguntas_capacidades.jsonl`): 10 preguntas, una o dos por capacidad, con entidades que no están en el set definitivo (Ministerio de Educación, ITM, INVIAS, La Guajira, Putumayo, Barranquilla, ICA). Corrida `20261117-202823`: **10/10**, 0 enlaces inventados de 119. Hallazgos:
   - **v04** (municipios de La Guajira) acertó apenas en la llamada 8 de 8: el modelo no relacionaba "municipios" con agrupar por ciudad. **Correcciones:**
     - La descripción de `agrupar_por` explica cada opción.
     - Una regla general en el prompt dice que los rankings de municipios, ciudades o departamentos se arman por ubicación.
     - `agregar` saca "No Definido" de los rankings por ciudad o departamento y lo reporta aparte en `sin_ubicacion`. Al repetirla, la pregunta había puesto "No Definido" de primero.
     - Después de las correcciones, v04 acierta con una sola llamada.
   - **v10** (ICA): el agente detectó las dependencias y usó `nombre_entidad_empieza`. `buscar_entidad` tardó 242 s por lentitud de datos.gov.co.

Con el cambio de texto, el prompt pasa a **v7**.

**Nota sobre la regla de municipios:** coincide con la definición que el autor aprobó para P22 (agrupar por ciudad). Se agregó porque falló una pregunta del set de verificación propio, no por respuestas del set definitivo, que el agente no ha visto.

### Regresión con la v7 y congelamiento

| Set | Corrida | Resultado | Enlaces inventados | Sin respuesta |
| --- | --- | --- | --- | --- |
| Capacidades (10) | `20261117-211801` | 10/10 | 0/105 | 0 |
| Desarrollo (30) | `20261117-204610` | 28/30, igual que la v5 | 0/260 | 0 |

Los dos fallos de desarrollo son los inestables conocidos:

- **f01:** filtra por ubicación en vez de resolver la entidad.
- **o01:** toma la Secretaría General como si fuera "la Alcaldía de Bogotá". Ha salido bien en v2, v3 y v5, y mal en 3b y v7, con prompts casi iguales. Es variación del modelo lite sin una causa nueva que corregir.

Se cumplió el criterio de parada:

- 28/30 o más en desarrollo.
- Dos corridas seguidas de capacidades en 10/10.
- Cero cifras sin respaldo.
- Enlaces inventados por debajo del 1%.
- Ningún tipo de fallo nuevo arreglable.

**El agente v7 queda congelado.** No recibe más cambios antes ni después de la corrida final.

### Corrida final

**Estado al cierre del 2026-11-18 (en curso, sin calificar):**

- **Corrida:** `evals/resultados/20261118-085949.jsonl`, con el agente v7 congelado (commit `v0.5.1`).
- **Pasada inicial:** 50 preguntas. Copia en `20261118-085949-pasada1.jsonl`.
- **Sin respuesta de Gemini:** P12, P21, P24, P28, P31, P34, P37 y P50.
  - Reintento 1: respondieron P12, P21, P24, P28, P37 y P50.
  - Reintentos 2 y 3: respondieron P31 y P34 en el tercero.
- **Caída de datos.gov.co:** en P18, P41 y P44 el agente respondió solo que el servidor no respondía. Copia del estado previo en `20261118-085949-antes-reintento-infra.jsonl`.
  - Al repetirlas, P18 y P41 respondieron.
  - P44 se detuvo sin terminar al cerrar la sesión y **falta repetirla**.
- **Archivos intermedios:** `-verificado.jsonl`, `-metricas.md` y `-respuestas.md` son de una verificación anterior a los reintentos y no son el resultado final.

**Pendiente:**

1. Repetir P44:

```
.venv/Scripts/python.exe -u -X utf8 evals/run.py --preguntas evals/preguntas_definitivas.jsonl --continuar evals/resultados/20261118-085949.jsonl --sin-verificar
```

2. Verificar las 50 una sola vez:

```
.venv/Scripts/python.exe -u -X utf8 evals/run.py --preguntas evals/preguntas_definitivas.jsonl --verificar evals/resultados/20261118-085949.jsonl
```

3. Calificar a mano P41 a P50 en `20261118-085949-manual.json`, con la razón de cada una, y volver a verificar.
4. Escribir las estadísticas finales en este documento.

## Respuestas correctas

Las consultas están en `evals/respuestas_definitivas.py`, que las escribe en el set sin tocar la redacción de las preguntas. Se calculan en vivo al calificar.

### Hallazgos en los datos

| Pregunta | Hallazgo |
| --- | --- |
| P01 | El NIT 900.123.456 no tiene ningún contrato en SECOP II. La respuesta correcta es 0 |
| P07 | La suma da $40.155.163.121.275.543 (unos 40.000 billones), un valor imposible para una gobernación. Hay contratos con valores mal digitados en los datos públicos |
| P18 | Primero aparece "No Definido" (contratos sin departamento) y Chocó suma más de $63.000 billones. Ambos son errores de los datos |
| P14, P34 | La Gobernación del Tolima está registrada como "GOBIERNO DEPARTAMENTAL" (código 702192410, NIT 800.113.672). Buscándola por nombre no aparece |
| P12, P33 | Hay dos "Municipio de Armenia": el de Quindío (701365033) y el de Antioquia (704868108). Se toma el de Quindío |
| P43 | No hay contratos de ninguna "Universidad Nacional" en SECOP II en 2022 |
| P08, P23, P35, P48 | La Alcaldía de Cali son 24 entidades en SECOP, una por dependencia ("SANTIAGO DE CALI DISTRITO ESPECIAL - ...") |
| P20 | Lo mismo con la Gobernación de Cundinamarca ("DEPARTAMENTO DE CUNDINAMARCA - SECRETARÍA ...") |
| P32 | Lo mismo con la Gobernación del Valle del Cauca |

### Decisiones (aprobadas por el autor el 2026-11-16, antes de la línea base)

| Pregunta | Propuesta | Resultado con la propuesta |
| --- | --- | --- |
| P07, P18 | Usar los datos tal como están, sin limpiar valores imposibles. Se califica que el agente reporte lo que dicen los datos | P07: $40.155.163.121.275.543 |
| P18 | Excluir "No Definido" del ranking, porque no es un departamento | Chocó, Bogotá, Antioquia, Valle… |
| P22 | Excluir "No Definido" de los municipios | Tunja, Aquitania, Sogamoso… |
| P14 | "Duración superior a seis meses" = más de 183 días entre la fecha de inicio y la de fin | 2.268 contratos |
| P12 | "Personas naturales" = contratista con cédula, pasaporte u otro documento personal (todo menos NIT, "Otro" y "No Definido") | 3.622 contratos |
| P23, P34 | "Empresas privadas" y "personas jurídicas" = contratista con NIT. Ojo: en P23 el NIT incluye entidades sin ánimo de lucro y algunas públicas, como hospitales o bomberos | — |
| P09, P21, P31, P40 | "Obra pública" = tipo de contrato "Obra" | P09: 10 contratos |
| P36 | "Estado de ejecución vigente" = estado "En ejecución" (en los datos no existe el estado "Vigente") | 62 contratos |
| P24 | "Objetos contractuales" = el texto del objeto del contrato, agrupado tal cual | — |
| P27 | "Sectores" = la columna `sector` de SECOP | Servicio Público, Salud… |
| P25 | No dice cuántas: se califican las 5 primeras | — |
| P27 | No dice cuántos: se califican los 5 primeros | — |
| P15 | Debe decir cuál contrató más y la diferencia | Caldas; diferencia $61.333.239.678 |
| P35 | Palabras clave: SOFTWARE, LICENCIA, LICENCIAMIENTO, TECNOLOG | 756 contratos (se piden hasta 50) |
| P37 | MANTENIMIENTO, y además VIA, VÍA o VIAL | 26 contratos |
| P38 | ALIMENTACION ESCOLAR o PAE, en entidades del Magdalena cuyo nombre tiene ALCALDÍA o MUNICIPIO | 48 contratos |
| P40 | ESCENARIO, DEPORTIV, CANCHA, POLIDEPORTIVO, ESTADIO o COLISEO, en contratos de obra | 2 contratos |
| P31, P32, P34, P36 | Tienen más de 50 contratos (104, 138, 67 y 62). Propuesta: acierta si da el total correcto y todos los contratos que lista cumplen el filtro, aunque no los liste todos | — |

## Resultados

Pendiente.
