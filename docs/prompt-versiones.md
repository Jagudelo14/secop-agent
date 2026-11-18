<!--
  ### Archivo: prompt-versiones.md ###
  Autor: Juan Camilo Agudelo (Jagudelo14)
  Correo: camiloagu1401@gmail.com
  Fecha: 2026-11-16
  Descripción: Proceso de evaluación del agente, iteración por iteración, con cada corrida, sus cambios y sus resultados
-->

# Proceso de evaluación del agente

Este documento registra cada iteración del agente: qué se cambió, por qué, con qué corrida se midió y qué dio. Incluye los errores del proceso, no solo los aciertos, para que los números finales se puedan auditar.

**Resumen para presentar:** las cifras válidas son solo las de la **v5**, la primera versión sin contenido derivado de las preguntas del set (ver [Auditoría de contaminación](#auditoría-de-contaminación)). Las corridas v1 a v4 sirven para entender el proceso, pero sus porcentajes están inflados y no se deben presentar como resultado.

## Cómo se mide

| Elemento | Detalle |
| --- | --- |
| Set de desarrollo | `evals/preguntas.jsonl`, 30 preguntas: 10 de conteo o suma, 8 de ranking, 8 de filtro, 4 fuera de alcance o ambiguas. Se usó para encontrar fallos y ajustar. |
| Set de prueba | `evals/preguntas_prueba.jsonl`, 10 preguntas con entidades que no están en el set de desarrollo. Escrito y congelado antes de correr la v5 (ver [Set de prueba](#set-de-prueba)). Nunca se usa para ajustar. |
| Respuesta correcta | Cada pregunta tiene su consulta SoQL escrita a mano. Se ejecuta en vivo contra datos.gov.co al calificar, así la respuesta correcta y la del agente se comparan con los datos del mismo día. |
| Calificación | Automática (`evals/run.py`). Conteo o suma: la cifra correcta aparece en la respuesta con tolerancia de 1%. Ranking: los 5 primeros aparecen y en orden. Filtro: el conjunto de `id_contrato` es exactamente el esperado. Fuera de alcance: el agente declina o pide aclaración sin dar montos en pesos. |
| Modelo | `gemini-3.5-flash-lite`, nivel gratuito, con `gemini-3.1-flash-lite` de respaldo cuando el primero está saturado. El reporte de cada corrida dice cuál respondió cada pregunta. |
| Métricas extra | Preguntas sin respuesta (el modelo saturado no contestó), errores de herramientas, enlaces inventados (enlaces de la respuesta que no salieron de ninguna herramienta, medido desde la v3), latencia, tokens y costo estimado con Claude. |

**Archivos de cada corrida** en `evals/resultados/`: `<fecha>.jsonl` (respuestas crudas), `<fecha>-respuestas.md` (cada pregunta con su respuesta, herramientas usadas y consumo), `<fecha>-verificado.jsonl` y `<fecha>-metricas.md` (calificación y métricas).

## Todas las corridas

| # | Corrida | Prompt | Set | Calificación original | Recalificada¹ | Fallos reales | Sin respuesta | Enlaces inventados | Presentable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `20261116-125248` | v1 | desarrollo | 24/30 | 25/30 | o01 | 4 (c08, r07, f05, f08) | no medido² | No |
| 2 | `20261116-132623` | v2 | desarrollo | 26/30 | 28/30 | f01 | 1 (f06) | no medido² | No |
| 3 | `20261116-135339` | v3 | desarrollo | 30/30 | 30/30 | ninguno | 0 | 10/257 (3,9%) | No |
| 4 | `20261116-142700` | v3 + arreglo en `agregar` | desarrollo | 28/30 | 28/30 | r05, o01 | 0 | 1/202 (0,5%) | No |
| 5 | `20261116-145905` | v4 | desarrollo | interrumpida en 7/30 | — | — | — | — | No |
| 6 | `20261116-151047` | v5 | desarrollo | 27/30 | 28/30 | f01 | 1 (c08, tiempo agotado consultando datos) | 0/202 (0%) | Sí, como referencia de desarrollo |
| 7 | `20261116-153720` | v5 | desarrollo (repetición) | inválida | — | — | 15, cuota diaria de Gemini agotada desde r06 | — | No |
| 8 | `20261116-155616` | v5 | prueba propia (10) | inválida | — | — | 8, cuota diaria agotada | — | No |

¹ Recalificada con el calificador corregido (ver [Correcciones al calificador](#correcciones-al-calificador)), sin volver a llamar al modelo.
² Antes de la v3 la traza no guardaba los enlaces que devolvía cada herramienta, así que no se podía saber si un enlace era real.

## Iteración 1 — prompt v1

**Corrida 1** · `20261116-125248` · desarrollo · 24/30 original, 25/30 recalificada

Prompt inicial con las reglas del SPEC: toda cifra sale de una herramienta, cada cifra lleva su enlace, resolver la entidad con `buscar_entidad` antes de filtrar, formato de montos colombiano, tablas en rankings, alertas solo desde `detectar_alertas`, y declinar lo que está fuera de alcance.

**Resultados:**

- 4 preguntas sin respuesta porque Gemini estaba saturado (c08, r07, f05, f08). No son fallos del agente, pero cuentan en contra del 30.
- **o01** "¿Cuánto contrató la Alcaldía de Bogotá en 2025?": fallo real. La pregunta es ambigua (la Alcaldía son muchas entidades) y el agente eligió la Secretaría General por su cuenta y dio cifras.
- **r04**: la calificación original lo marcó como fallo, pero era un error del calificador (ver correcciones). Al revisarlo se vio otro problema que el calificador no medía: todos los enlaces de la tabla eran inventados (`https://www.colombiacompra.gov.co/secop-ii`).

Tokens: 246.632 de entrada y 17.973 de salida. Latencia promedio 52,7 s.

## Iteración 2 — prompt v2

**Corrida 2** · `20261116-132623` · desarrollo · 26/30 original, 28/30 recalificada

**Cambios en el prompt:**

1. Copiar los enlaces tal como vienen en el campo `url` de los resultados y nunca construirlos.
2. Si `buscar_entidad` devuelve varias candidatas y ninguna coincide exactamente, listar las candidatas y preguntar sin dar cifras. Esta regla incluía como ejemplos "Alcaldía de Bogotá", "Gobernación" y "Ministerio de Salud" (contaminación, se quitó en la v5).

**Resultados:**

- o01 ahora pregunta cuál entidad. r04 ahora usa enlaces reales.
- 1 sin respuesta por saturación (f06).
- **f01** "Lista los contratos de obra del Departamento de Antioquia firmados en 2025 por más de 5.000 millones": fallo real. Filtró por ubicación (`departamento = Antioquia`) en vez de resolver la entidad Departamento de Antioquia, y trajo 83 contratos de todas las entidades ubicadas allí en vez de los 13 de la Gobernación.
- **r07** y **o01**: la calificación original los marcó como fallos, pero eran errores del calificador (ver correcciones). En r07 los enlaces eran inventados, con el dominio correcto y ids falsos; la métrica de esta corrida no podía detectarlo.

Tokens: 343.516 de entrada y 31.203 de salida. Latencia promedio 36,3 s.

## Iteración 3 — prompt v3

**Corrida 3** · `20261116-135339` · desarrollo · 30/30

**Cambio en el prompt:** "Contratos del Departamento de X" habla de la entidad que contrata y se resuelve con `buscar_entidad`; los filtros de departamento y ciudad son solo para ubicación. La regla tenía como ejemplo "Antioquia", que está en las preguntas c07 y f01 (contaminación, se quitó en la v5).

**Cambio en el código:** desde aquí cada paso de la traza guarda los enlaces que devolvió la herramienta, y la métrica "enlaces inventados" compara contra esos.

**Resultados:** 30/30, ninguna sin respuesta, 0 errores de herramientas. f01 ya resuelve la entidad correcta. Pero 10 de 257 enlaces (3,9%) eran inventados, todos en r04 y r07.

**Causa de los enlaces inventados:** estaba en la herramienta, no en el modelo. `agregar` solo devolvía enlaces al agrupar por proveedor o por entidad. Al agrupar por modalidad o tipo de contrato no traía ninguno, y como el prompt exige un enlace por fila, el modelo los fabricaba.

Tokens: 385.647 de entrada y 34.285 de salida. Latencia promedio 48,9 s.

## Iteración 3b — mismo prompt v3, arreglo en `agregar`

**Corrida 4** · `20261116-142700` · desarrollo · 28/30

**Qué se cambió:** solo la herramienta `agregar`, que ahora trae los 3 contratos mayores con su enlace real en todas las agrupaciones (modalidad, tipo de contrato, departamento, año). El prompt quedó exactamente igual que en la corrida 3.

**Resultados:**

- Los enlaces inventados bajaron de 10/257 (3,9%) a **1/202 (0,5%)**: el arreglo funcionó.
- El acierto bajó de 30/30 a **28/30**, con el mismo prompt.

**Por qué bajó el resultado con el mismo prompt:** los dos fallos nuevos no tienen que ver con el arreglo de enlaces.

- **r05** "¿En qué 5 departamentos se firmaron más contratos de obra en 2025?": ordenó por valor total en vez de por número de contratos. Dejó la métrica por defecto de `agregar` (`suma_valor`), que no tenía ninguna descripción. En la corrida 3 la misma pregunta con el mismo prompt había salido bien.
- **o01**: inventó las cifras completas. Llamó a `buscar_entidad` dos veces, nunca a una herramienta de datos, y respondió "$547.410.970.672 en 460 contratos" con un enlace inventado (el único de la corrida). En la corrida 3 había preguntado cuál entidad, como debía.

La conclusión es que **el modelo lite no responde igual dos veces**: con el mismo prompt, la misma pregunta puede salir bien en una corrida y mal en la siguiente. El 30/30 de la corrida 3 no era un resultado estable. Por eso desde la v5 cada versión se corre al menos dos veces y se reporta el rango, no una sola cifra.

Tokens: 332.571 de entrada y 28.356 de salida. Latencia promedio 52,3 s.

## Iteración 4 — v4 (interrumpida)

**Corrida 5** · `20261116-145905` · desarrollo · detenida en la pregunta 7 de 30

**Cambios:**

1. En `agregar`, la métrica pasó a ser obligatoria y con descripción. La descripción tenía frases sacadas de las preguntas ("más contratos", "más usados", "cuánto dinero"), contaminación que se quitó en la v5.
2. **Control de cifras en el código** (`cifras_sin_respaldo` en `agent.py`, usado por Gemini y por Claude): si la respuesta final trae montos en pesos y el agente no llamó ninguna herramienta de datos (`consultar_contratos`, `agregar`, `detectar_alertas` o `detalle_contrato`), la respuesta no se acepta y se le devuelve al modelo una sola vez para que consulte o pregunte. Es una regla determinista que no depende de que el modelo obedezca el prompt. Este cambio sí se conserva en la v5.

**Por qué se detuvo:** durante la corrida se revisó todo el código contra las preguntas del set y se encontraron ejemplos copiados de ellas (siguiente sección). No tenía sentido terminar de medir una versión contaminada.

## Auditoría de contaminación

Al revisar el prompt y las descripciones de las herramientas contra las 30 preguntas del set de desarrollo se encontraron nombres y frases que venían directamente de esas preguntas. Eso le da al modelo pistas que no tendría con preguntas nuevas e infla el resultado.

| Dónde | Texto | Pregunta que favorece | Desde |
| --- | --- | --- | --- |
| Prompt, fuera de alcance | "por ejemplo SECOP I, contratos antes de 2015, opiniones políticas o datos personales" | o02, o03, o04 | v1 |
| `buscar_entidad`, descripción de `nombre` | `ej: 'secretaria general alcaldia bogota'` | c03, r01 | v1 |
| `buscar_entidad`, sugerencia sin resultados | `ej: 'medellin', 'distrito medellin', 'departamento antioquia'` | c07, f01 | v1 |
| Filtros `departamento` y `ciudad` | `Ej: 'Antioquia', 'Valle del Cauca', 'Distrito Capital de Bogotá'`, `'Medellín', 'Bogotá'` | r03, r05 y otras | v1 |
| Prompt, entidad ambigua | "como 'Alcaldía de Bogotá', 'Gobernación' o 'Ministerio de Salud'" | o01 | v2 |
| Prompt, entidad o ubicación | "'Contratos del Departamento de X'... ('contratos firmados en Antioquia', 'entidades de Cali')" | c07, f01 | v3 |
| `agregar`, descripción de `metrica` | "más contratos", "más usados", "cuánto dinero", "más plata" | r05, r07, c02 | v4 |
| `agregar`, descripción | "Para cuántos contratos o cuánto dinero en total usa el campo total_general" | c02 | v1 |

Como varios puntos estaban desde la v1, **ninguna corrida de la v1 a la v4 es presentable**.

**Lo que se dejó a propósito:** la descripción del filtro `modalidades` dice que "contratación directa" corresponde a dos valores de SECOP (`Contratación directa` y `Contratación Directa (con ofertas)`). No es un ejemplo sacado de las preguntas sino un hecho de los datos, confirmado en la fase 0 al revisar los valores reales de la columna, y lo necesita cualquier pregunta sobre contratación directa.

## Iteración 5 — v5, versión limpia

**Cambios:** se quitó todo lo de la tabla anterior y cada regla quedó en términos generales, sin nombres propios ni frases parecidas a las preguntas:

- Entidad o ubicación: "Cuando la pregunta nombra una entidad pública como quien contrata, resuélvela con buscar_entidad y filtra por codigo_entidad, aunque su nombre incluya un lugar. Usa los filtros departamento y ciudad solo cuando la pregunta pide contratos según la ubicación y no según quién contrata."
- Entidad ambigua: "Si buscar_entidad devuelve varias candidatas y ninguna coincide exactamente con el nombre que pidió el usuario, no elijas tú: lista las candidatas y pregunta cuál quiere, sin dar cifras."
- Fuera de alcance: "Si la pregunta pide algo que estos datos no contienen o que no se puede verificar con ellos, dilo y no respondas de memoria."
- `metrica` en `agregar`: "conteo = número de contratos. suma_valor = valor total contratado. suma_pagado = valor ya pagado."
- Descripciones de `buscar_entidad` y de los filtros sin ejemplos de nombres.

Se conservan los cambios que no son contaminación: copiar enlaces sin inventarlos, `agregar` con enlaces en todas las agrupaciones y el control de cifras sin respaldo.

**Corridas:** se programaron dos en el set de desarrollo y una en el set de prueba propio.

- **Corrida 6** (desarrollo): 27/30 original y **28/30 (93,3%)** recalificada. **0 enlaces inventados de 202.**
  - c08 no se respondió: se agotó el tiempo de espera al consultar datos.gov.co y el error tumbó la pregunta en vez de llegarle al modelo (corrección C7 de la evaluación definitiva).
  - **f01 falló de nuevo:** sin el ejemplo de "Antioquia" en el prompt, el agente volvió a filtrar por ubicación en vez de por la entidad Departamento de Antioquia. Es la señal más clara de que el 30/30 de la v3 dependía en parte de ese ejemplo.
  - o03 la marcó mal el calificador (ver correcciones).
- **Corridas 7 y 8:** inválidas. La cuota diaria gratuita de Gemini se agotó a mitad de la corrida 7 (unas 5 corridas completas en el mismo día) y casi todas las preguntas quedaron sin respuesta por cuota, no por el agente.

Comparación honesta: la v3 sacó 30/30 con ejemplos del set en el prompt, y la v5 sin ellos sacó 28/30 en desarrollo. La diferencia está en f01, la pregunta que tenía su ejemplo.

**Lección para la evaluación definitiva:** las 50 preguntas necesitan unas 200 peticiones a Gemini, así que la línea base y la corrida final deben hacerse en días distintos, cada una con la cuota diaria completa.

## Iteración 6 — v6, capacidades para la evaluación definitiva

La v6 agrega las capacidades C1 a C8 (rangos de años, búsqueda en el objeto, agrupar por ciudad y sector, promedio, contratistas distintos, tipo de persona, duración, varias entidades y robustez ante errores de red). Se decidieron leyendo los temas del set definitivo de 50 preguntas, antes de correr el agente sobre él. El detalle, el protocolo y los resultados están en [evaluacion-definitiva.md](evaluacion-definitiva.md).

Antes de los cambios se guardó una copia exacta de la v5 en `evals/linea_base/` para correr la línea base. Esa línea base se canceló después por decisión del autor.

## Iteración 7 — v7, verificación con el agente completo

La v6 solo se había probado a nivel de herramienta. Al correr el agente completo sobre un set de verificación propio de 10 preguntas (`evals/preguntas_capacidades.jsonl`) aparecieron tres problemas, que se corrigieron en términos generales:

1. **Plural en la búsqueda por objeto.** El agente buscaba "puentes" y perdía los contratos con "puente". La descripción del filtro ahora pide usar la forma más corta.
2. **Rankings de municipios.** El modelo los armaba por entidad (alcaldías) en vez de por ubicación, y además ponía "No Definido" como si fuera un municipio. Correcciones:
   - Se describió cada opción de `agrupar_por`.
   - Se agregó una regla general de ubicación al prompt.
   - `agregar` saca "No Definido" de los rankings por ciudad o departamento y lo reporta aparte.
3. **Dependencias con y sin tilde.** Se agrupan sin tildes.

| Corrida | Prompt | Set | Resultado | Enlaces inventados |
| --- | --- | --- | --- | --- |
| `20261117-202823` | v6 | capacidades (10) | 10/10 (v04 acertó apenas en la llamada 8 de 8) | 0/119 |
| `20261117-211801` | v7 | capacidades (10) | 10/10 | 0/105 |
| `20261117-204610` | v7 | desarrollo (30) | 28/30 (f01 y o01) | 0/260 |

Con eso se cumplió el criterio de parada y **la v7 quedó congelada** para la evaluación definitiva.

## Set de prueba

- **Archivo:** `evals/preguntas_prueba.jsonl`, 10 preguntas: 3 de conteo o suma, 3 de ranking, 2 de filtro y 2 fuera de alcance.
- **Entidades:** Departamento de Santander, Municipio de Bucaramanga, Agencia Nacional de Infraestructura, SENA Regional Córdoba e ICBF Regional Bolívar. Ninguna aparece en el set de desarrollo.
- **Congelado:** 2026-11-16 15:10, antes de correr la v5. SHA-256 del archivo: `6721936f9fea36ccf284ef7e1e1819c35ce62372cde16304d0a92a0e8c3c19bc`. Si el archivo cambia, la huella cambia.
- **Quién lo escribió:** Claude, el mismo asistente que ajustó el prompt, aunque antes de ver cualquier resultado de la v5 y sin que el prompt se haya ajustado a estas preguntas. Para una evaluación más independiente, conviene que otra persona escriba un set adicional.
- **Validación:** las consultas SoQL se ejecutaron con `--validar` antes de congelar. h05 se reescribió en ese momento porque pedía "las 5 primeras" modalidades y la entidad solo usó 3.

## Correcciones al calificador

No son cambios del agente, pero movieron los números y por eso las corridas 1 y 2 tienen dos calificaciones.

| Caso | Problema | Corrección |
| --- | --- | --- |
| r04 (corrida 1) | "Licitación pública" está dentro de "Licitación pública Obra Publica" y el calificador creía que el orden estaba mal | Busca cada fila después de la anterior, en orden |
| r07 (corrida 2) | Ignoraba las claves de menos de 5 letras, como "Otro" y "Obra" | Las claves cortas de texto se buscan como palabra completa |
| o01 (corrida 2) | Tomaba el código de entidad y el NIT como montos, y creía que el agente había dado cifras cuando en realidad preguntó cuál entidad | Solo cuenta como cifra un monto con `$` o con "millones" / "billones" |
| o03 (corrida 6) | No reconocía "no se puede responder" como declinar | Se agregó "no se puede" a las frases de declinar |

Cada corrección tiene su prueba en `tests/test_evals.py`. Todas se hicieron revisando a mano respuestas que el calificador marcó mal, nunca para que una respuesta incorrecta pasara.

## Limitaciones conocidas

- **Variabilidad del modelo:** el modelo lite da respuestas distintas a la misma pregunta entre corridas (ver iteración 3b). Una diferencia de 1 o 2 preguntas entre corridas puede ser azar.
- **Saturación:** en el nivel gratuito, Gemini a veces no responde. Esas preguntas cuentan como no respondidas, no se repiten para mejorar la cifra.
- **Calificador automático:** revisa cifras, orden e ids, pero no si el texto alrededor es correcto. Por eso los enlaces inventados se miden aparte.
- **Modelo:** todas las cifras son con Gemini lite. Con Claude Haiku o Sonnet los resultados pueden ser distintos y habría que medirlos aparte.
