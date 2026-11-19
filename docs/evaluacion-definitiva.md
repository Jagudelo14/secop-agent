<!--
  ### Archivo: evaluacion-definitiva.md ###
  Autor: Juan Camilo Agudelo (Jagudelo14)
  Correo: camiloagu1401@gmail.com
  Fecha: 2026-11-16
  Descripción: Protocolo y resultados de la evaluación definitiva del agente sobre el set de 50 preguntas
-->

# Evaluación definitiva

Esta es la evaluación que presento. Usa un set de 50 preguntas que escribí yo, distinto del que usé para desarrollar el agente. El proceso de desarrollo previo, con el set de 30 preguntas, está en [prompt-versiones.md](prompt-versiones.md).

## Set de preguntas

- **Archivo:** `evals/preguntas_definitivas.jsonl`, con mi redacción exacta. Solo agregué las consultas SoQL que dan la respuesta correcta; el texto de las preguntas no se toca.
- **Quién las escribió:** yo. No salieron del proceso de ajuste del prompt, que hice con Claude sobre el set de desarrollo de 30.
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
3. **Corrida final:** una sola vez sobre las 50 preguntas. Es la única vez que el agente ve este set. Las preguntas que queden sin respuesta por una caída de Gemini o de datos.gov.co se repiten al final con `--continuar`. Las que ya respondieron no se repiten, sean correctas o no.
4. **Reporte:** se presenta esa corrida con todas las métricas, sin excluir preguntas.

La versión que se mide (v7) no recibe cambios después de la corrida final: sus errores se documentan como hallazgos. Las correcciones posteriores (v8 y v9) se reportan aparte, al final.

## Capacidades a agregar (lista cerrada)

La decidí leyendo los **temas** de las preguntas, antes de ver cualquier respuesta del agente. No se agrega nada que no esté aquí.

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
| Ambigua | Pide aclaración, o separa las entidades aclarando que son varias. Falla si elige una sola en silencio o suma todo como si fuera una entidad. Se califica a mano, dejando escrita la razón de cada una |
| Fuera de alcance | Dice que los datos no permiten responder lo que se pregunta y no afirma nada que no esté en los datos (por ejemplo, que una obra tuvo retrasos o sobrecostos). Puede mostrar datos de SECOP como contexto si aclara que no responden la pregunta. Se califica a mano, dejando escrita la razón |

**Cómo queda la calificación manual:** el calificador automático da una sugerencia para ambiguas y fuera de alcance. La decisión final y su razón se escriben en `evals/resultados/<corrida>-manual.json`, y esa decisión manda sobre la sugerencia. Los archivos manuales quedan en el repositorio para auditarlos.

Las preguntas de conteo, ranking y filtro se califican automáticamente con `evals/run.py`, contra la consulta SoQL de cada una ejecutada en vivo.

## Estado del agente

### Línea base (cancelada)

Antes de agregar las capacidades nuevas guardé una copia del agente v5 para correrla como línea base sobre este set. La cancelé antes de que respondiera la segunda pregunta, para que el set se usara solo en la medición final, y borré esa respuesta sin leerla ni calificarla. La copia ya no está en el repositorio; queda en el historial de git, en `v0.5.0`.

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

**Nota sobre la regla de municipios:** coincide con la definición que aprobé para P22 (agrupar por ciudad). Se agregó porque falló una pregunta del set de verificación propio, no por respuestas del set definitivo, que el agente no ha visto.

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

**Estado final (2026-11-19): corrida completa, verificada y calificada.** Los resultados están en la sección [Resultados](#resultados). Lo que sigue es el registro de cómo se llegó ahí.

- **2026-11-19:** P44 se repitió con el mismo agente congelado (el código de `src/` no cambió desde `v0.5.1`). Respondió en 818 s con 8 herramientas. La primera llamada volvió a agotar el tiempo de datos.gov.co, pero el agente siguió con otras consultas. Copia del estado previo en `20261118-085949-antes-p44.jsonl` y registro en `definitiva-reintento-p44.log`.
- **2026-11-19:** verificación de las 50 (`definitiva-verificacion.log`), con la calificación manual de P41–P50 en `20261118-085949-manual.json`. Los archivos `-verificado.jsonl`, `-metricas.md` y `-respuestas.md` quedan reemplazados por esta verificación y son el resultado final.

**Registro al cierre del 2026-11-18:**

- **Corrida:** `evals/resultados/oficiales/20261118-085949.jsonl`, con el agente v7 congelado (commit `v0.5.1`).
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
.venv/Scripts/python.exe -u -X utf8 evals/run.py --preguntas evals/preguntas_definitivas.jsonl --continuar evals/resultados/oficiales/20261118-085949.jsonl --sin-verificar
```

2. Verificar las 50 una sola vez:

```
.venv/Scripts/python.exe -u -X utf8 evals/run.py --preguntas evals/preguntas_definitivas.jsonl --verificar evals/resultados/oficiales/20261118-085949.jsonl
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

### Decisiones (las aprobé el 2026-11-16, antes de la línea base)

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

Corrida `20261118-085949`, agente v7 congelado (commit `v0.5.1`), verificada el 2026-11-19 contra datos.gov.co en vivo. Detalle por pregunta en `evals/resultados/oficiales/20261118-085949-metricas.md` y respuestas completas en `20261118-085949-respuestas.md`.

**Acierto: 37/50 (74%).**

### Acierto por tipo

| Tipo | Acierto | Calificación |
| --- | --- | --- |
| Conteo o suma | 13/15 (86,7%) | Automática |
| Ranking | 12/15 (80,0%) | Automática |
| Filtro | 3/10 (30,0%) | Automática |
| Ambigua | 4/5 (80,0%) | Manual |
| Fuera de alcance | 5/5 (100%) | Manual |
| **Total** | **37/50 (74,0%)** | |

### Confiabilidad

| Métrica | Valor |
| --- | --- |
| Errores del agente (no respondió) | 0/50 |
| Enlaces inventados (no vienen de ninguna herramienta) | **0/453 (0%)** |
| Respuestas con datos que incluyen enlace | 36/40 (90%) |
| Llamadas a herramientas con error | 1/136 (0,7%), el tiempo agotado en P44 |
| Preguntas que llegaron al límite de 8 llamadas | 4/50 (8%) |
| Herramientas por pregunta (promedio) | 2,7 |

**Reintentos por infraestructura:** 11 preguntas se repitieron porque no hubo respuesta.

- **Por Gemini (8):**
  - P12, P21, P24, P28, P37 y P50 respondieron en el primer reintento.
  - P31 y P34 respondieron en el tercero.
- **Por datos.gov.co (3):**
  - P18 y P41 respondieron en el primer reintento.
  - P44 respondió el 2026-11-19, después de un reintento que se detuvo sin terminar.

Ninguna respuesta que ya existiera se repitió.

### Latencia, tokens y costo

| Métrica | Valor |
| --- | --- |
| Latencia promedio / mediana / p95 | 135,5 s / 87,0 s / 342,5 s |
| Latencia más alta | 818 s (P44) |
| Tokens totales | 1.675.747 de entrada · 64.790 de salida |
| Tokens por pregunta (promedio) | 33.515 de entrada · 1.296 de salida |
| Modelos que respondieron | gemini-3.5-flash-lite: 35 · gemini-3.1-flash-lite (respaldo): 15 |
| Costo real | USD 0 (cuota gratuita de Gemini) |
| Costo estimado con los mismos tokens, sin caché | claude-haiku-5-5: USD 0,20 (USD 4,00 por 1.000 preguntas) · claude-sonnet-5-5: USD 4,00 (USD 79,99 por 1.000 preguntas) |

La latencia la domina datos.gov.co, no el modelo. Algunas llamadas a `buscar_entidad` tardaron más de 200 s. Las ambiguas son las más lentas (337 s en promedio, 6 herramientas) porque el agente busca varias entidades candidatas.

| Tipo | Tokens entrada prom. | Tokens salida prom. | Latencia prom. (s) | Herramientas prom. |
| --- | --- | --- | --- | --- |
| Conteo o suma | 20.380 | 855 | 142,7 | 2,5 |
| Ranking | 23.430 | 1.266 | 103,5 | 1,7 |
| Filtro | 49.838 | 2.682 | 113,0 | 3,1 |
| Ambigua | 65.556 | 632 | 337,1 | 6,0 |
| Fuera de alcance | 38.487 | 600 | 53,2 | 2,4 |

### Errores (13)

Según el protocolo, los errores se documentan como hallazgos y el agente v7 no se corrige. Las correcciones posteriores (v8 y v9) están al final, en una sección aparte.

| Pregunta | Tipo | Qué pasó |
| --- | --- | --- |
| P08 | Conteo | Dio 10.515 contratistas distintos; la respuesta correcta es 11.155. Filtró por "SANTIAGO DE CALI DISTRITO ESPECIAL", pero la Secretaría de Cultura está registrada con doble espacio ("SANTIAGO DE CALI  DISTRITO ESPECIAL - ...", 2.615 contratos en 2023–2024) y el filtro por inicio de nombre no la toma |
| P14 | Conteo | Dio 2.441; la respuesta correcta es 2.268. `duracion_min_dias` incluye el límite (≥ 183) y la pregunta dice "superior a seis meses" (> 183). Hay exactamente 173 contratos de 183 días: 2.441 − 173 = 2.268. El agente debió pasar 184 |
| P20 | Ranking | Filtró por nombres que empiezan con "GOBERNACION DE CUNDINAMARCA", pero la entidad está registrada como "DEPARTAMENTO DE CUNDINAMARCA - ...". El top 10 es de otra entidad |
| P23 | Ranking | La misma causa de P08: el filtro no toma la Secretaría de Cultura (registrada con doble espacio). Por eso faltan la Corporación de Eventos y el Fondo Mixto de Cultura, que contratan con esa secretaría, y el valor del primero no coincide |
| P24 | Ranking | Listó los 10 contratos de mayor valor resumiendo su objeto, en vez de agrupar por el texto del objeto como se decidió para P24 |
| P31 | Filtro | El total (104) es correcto, pero listó los contratos con enlaces "Ver contrato" sin el id `CO1.PCCNTR`, así que el calificador no pudo comprobarlos. **Posible falso negativo del calificador**; se mantiene la nota automática |
| P32 | Filtro | Dio 76 contratos; la respuesta correcta es 138. Filtró por "GOBERNACION DEL VALLE DEL CAUCA", pero muchas dependencias están registradas con otros nombres: "DEPARTAMENTO DEL VALLE DEL CAUCA - ...", "GOBERNACION DEL VALLE - ..." (sin "del Cauca") o con la gobernación al final ("SECRETARIA DE INFRAESTRUCTURA - GOBERNACION DEL VALLE") |
| P33 | Filtro | Juntó los dos "Municipio de Armenia" (Quindío y Antioquia) sin avisar; sobran 4 contratos |
| P34 | Filtro | Encontró la Gobernación del Tolima ("GOBIERNO DEPARTAMENTAL"), pero dio 68 en vez de 67. Es el mismo caso de P14: `valor_min` incluye el límite (≥) y la pregunta dice "superiores a 1.000 millones" (>). Hay exactamente 1 contrato de $1.000.000.000. Además listó solo 10 de los 67 |
| P35 | Filtro | Agregó "tecnologico" a las palabras clave aprobadas: 807 contratos en vez de 756, y 11 de los 50 listados no cumplen el filtro |
| P37 | Filtro | Usó palabras clave distintas a las aprobadas ("mantenimiento de vias", "vias"): faltan 25 y sobran 9 |
| P38 | Filtro | Restringió a tipo "Suministros" y no filtró por alcaldías: faltan 45 de 48 |
| P44 | Ambigua | Ver la calificación manual: un ranking de 3 subredes de Bogotá que solo cuenta contratos con "salud" en el objeto, sin decirlo |

**Patrones:**

1. **Filtros por texto (P35, P37, P38):** el agente elige sus propias palabras clave y no coinciden con las aprobadas. Son 3 de los 7 fallos de filtro.
2. **Resolución de entidades (P08, P20, P23, P32, P33):** el filtro por inicio de nombre depende de cómo esté registrada la entidad: un doble espacio, otro prefijo o dos entidades con el mismo nombre cambian el resultado sin que el agente lo note. Es la causa más frecuente: 5 fallos.
3. **Límite incluido o excluido (P14, P34):** `duracion_min_dias` y `valor_min` incluyen el límite y el agente no lo ajusta cuando la pregunta dice "superior a". En las dos preguntas la diferencia es exactamente la de los contratos que caen en el límite.
4. **Formato (P24, P31):** la respuesta tiene los datos, pero no en la forma que se pidió o que el calificador puede leer.

Las preguntas fuera de alcance (5/5) y los enlaces (0 inventados de 453) muestran que el agente no inventa: cuando falla, falla en cómo arma la consulta, no en afirmar cosas que no están en los datos.

### Calificación manual (P41–P50)

Las razones completas están en `evals/resultados/oficiales/20261118-085949-manual.json`. Resumen:

| Pregunta | Resultado | Razón resumida |
| --- | --- | --- |
| P41 Policía | Acierto | Aclara que son varias unidades; da el agregado de las 17 entidades "POLICIA…" diciendo que es un agregado y ofrece consultar una |
| P42 Fiscalía | Acierto | Aclara que hay varias regionales (son 9); da solo el Nivel Central, lo dice y ofrece las demás |
| P43 Universidad Nacional | Acierto (límite) | Separa la Universidad Nacional ($0) de la Pedagógica Nacional sin sumarlas; no pide aclaración explícita |
| P44 Hospitales públicos | **Fallo** | Resuelve la ambigüedad con un criterio que no explica (solo contratos con "salud") y presenta 3 subredes como los hospitales que más contrataron |
| P45 Ministerio de Transporte | Acierto (límite) | Es una sola entidad en SECOP; deja explícito que "principales" es por valor. Cifras verificadas |
| P46 Calidad de obras | Acierto | Declina primero; muestra contratistas solo como contexto |
| P47 Retrasos | Acierto | Declina; los estados "Suspendido" que muestra son reales y advierte que no implican irregularidad |
| P48 Sanciones | Acierto | Declina sin dar datos |
| P49 Sobrecostos | Acierto (límite) | Muestra con datos verificados que no hubo contratos de construcción de hospitales; no dice de forma explícita que SECOP tampoco mide sobrecostos |
| P50 Cumplimiento | Acierto | Declina sin dar datos |

Todas las cifras que citan las respuestas de P41–P50 se contrastaron contra datos.gov.co. Los tres casos marcados como límite son los que revisé con más cuidado. Si se cambian a fallo, el acierto baja a 34/50 (68%).

## Después de la evaluación: v8 y v9 (no son medición a ciegas)

El resultado de la evaluación definitiva es el de la v7: **37/50 (74%)**. Lo que sigue lo hice después, para corregir los fallos que encontró esa evaluación. Las dos versiones se ajustaron mirando las respuestas de este mismo set, así que sus números son optimistas y no reemplazan al 74%: miden cuánto mejora el agente cuando se corrigen fallos conocidos, no cómo le va con preguntas nuevas.

| Corrida | Prompt | Acierto | Conteo | Ranking | Filtro | Ambigua | Fuera de alcance | Enlaces inventados |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `20261118-085949` | v7 (a ciegas, oficial) | 37/50 (74%) | 13/15 | 12/15 | 3/10 | 4/5 | 5/5 | 0/453 |
| `20261119-084906` | v8 | 39/50 (78%) | 11/15 | 15/15 | 5/10 | 3/5 | 5/5 | 2/425 |
| `20261119-160009` | v9 | 43/50 (86%) | 14/15 | 15/15 | 5/10 | 4/5 | 5/5 | 0/652 |

Las preguntas que Gemini o datos.gov.co dejaron sin respuesta se repitieron igual que en la v7. En la v8 fueron 16 (P01, P13, P14, P16, P17, P23, P25, P28, P33, P35, P40, P43, P46, P47, P48 y P50; P14, P16 y P17 dos veces) y P43 una vez más porque datos.gov.co no respondió a ninguna consulta. En la v9 solo P06. Las calificaciones manuales de P41–P50 están en `evals/resultados/<corrida>-manual.json`, con la razón de cada una y las cifras contrastadas en vivo.

### v8: cambios generales a partir de los errores

| Cambio | Errores que apunta |
| --- | --- |
| `buscar_entidad` devuelve `entidad_completa`: la gobernación o alcaldía con todas sus dependencias, aunque estén registradas con otro prefijo o con doble espacio | P08, P20, P23, P32 |
| Aviso de municipios homónimos en varios departamentos (`homonimas`) | P33 |
| Filtros estrictos `valor_mayor_que` y `duracion_mayor_que_dias` para "superior a" | P14, P34 |
| `objeto_contiene_todas` para temas que juntan dos ideas | P37 |
| `nombre_entidad_contiene` para "las alcaldías de un departamento" | P38 |
| Agrupar por objeto del contrato | P24 |
| El texto de cada enlace es el id del contrato | P31 |

Resultado: arregló P08, P20, P23, P24, P31 y P37, pero dañó P03, P04 y P11 (ver v9) y P43, y por primera vez aparecieron enlaces inventados (2, uno en P50: un enlace de búsqueda de SECOP que no salió de ninguna herramienta).

### v9: corrección de la v8

| Cambio | Errores que apunta |
| --- | --- |
| `entidad_completa` solo toma nombres en los que el tipo abre un tramo del nombre seguido del lugar ("MUNICIPIO DE MANIZALES", "DEPARTAMENTO DE CUNDINAMARCA - SECRETARÍA…"). En la v8 sumaba entidades autónomas que tienen el lugar en el nombre: la Contraloría de Manizales, la ESE de Villavicencio, la Contraloría de Córdoba, un sindicato del Valle y una asociación de municipios del Tolima | P03, P04, P11 |
| `nombre_entidad_contiene` con ALCALDIA también busca MUNICIPIO | P38 |
| Prompt: meses a días con 30,44 días por mes (6 meses = 183) | P14 |
| Prompt: un programa con sigla conocida se busca por nombre completo y sigla. El ejemplo de la regla ("alimentación escolar es PAE") es el de la propia pregunta P38, así que esta regla está ajustada a la respuesta correcta | P38 |

Antes de correr las 50 se probaron solo P03, P04, P11, P14 y P38: 5/5 (`20261119-155020`). En la corrida completa la v9 arregló esas cinco, P33 y P44, y falló P07, P37 y P40, que la v8 tenía bien.

### Errores de la v9 (7)

| Pregunta | Tipo | Qué pasó |
| --- | --- | --- |
| P07 | Conteo | Resolvió bien la entidad, pero por su cuenta excluyó un contrato de 2021 que consideró atípico. La respuesta correcta lo incluye |
| P32 | Filtro | La respuesta correcta deja por fuera "GOBERNACIÓN VALLE DEL CAUCA -SECRETARIA DE SALUD" (sin "del"); el agente la incluye |
| P34 | Filtro | La Gobernación del Tolima está registrada como "GOBIERNO DEPARTAMENTAL", sin el lugar en el nombre, y el agente no la encontró |
| P35 | Filtro | La búsqueda sin tildes también encuentra "TECNÓLOGO" y la respuesta correcta no; sobran 16 |
| P37 | Filtro | Buscó "vías" con O en vez de exigir "mantenimiento" y "vía" juntas. Probablemente lo causó la regla nueva de buscar por frase completa |
| P40 | Filtro | Mezcló palabras genéricas ("construcción", "adecuación") con las deportivas; sobran 15 |
| P43 | Ambigua | Eligió en silencio la Universidad Nacional de Colombia y respondió $0 sin mencionar otras candidatas |

La v9 no llegó a la meta de 90% que me propuse. No hice otra ronda: cada regla nueva del prompt arregla una pregunta y puede dañar otra (P37 es el ejemplo), y seguir ajustando sobre este mismo set haría el número cada vez menos creíble.
