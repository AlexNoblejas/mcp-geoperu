# ¿Sirve un MCP sobre datos territoriales del Estado?

**MCP de GEOPERÚ · infraestructura de residuos sólidos del MINAM**
Alexander Noblejas · Diplomatura en Ciencia de Datos (QLAB) · sesión 04 · 28 de octubre de 2026

![Distribución territorial y aciertos por modo](grafico.png)

## Qué se midió

El proyecto del curso mide si un MCP evita que Claude invente **cifras macroeconómicas** del BCRP.
Aquí se mide algo distinto: si evita que invente **cifras territoriales**. La fuente es el servicio
ArcGIS `ServicioRRSS_MINAM` del geoservidor del Ministerio del Ambiente, publicado en GEOPERÚ, con
**76 infraestructuras de residuos sólidos georreferenciadas** en todo el país.

La diferencia importa porque el error cambia de forma. Una serie del BCRP tiene un valor correcto por
periodo, y equivocarse es dar un decimal distinto. Un registro territorial tiene una ubicación, y
equivocarse es **afirmar que existe infraestructura donde no hay registro de ella** — un error que en
planeamiento público se propaga a un diagnóstico y de ahí a una intervención.

Metodología idéntica a la del curso: las mismas 10 preguntas en dos modos (`memoria` y `mcp`),
con `claude -p`, Haiku, y la instrucción de responder `null` antes que estimar. Las verdades no salen
de este MCP: cada una se comprobó contra la URL del geoservidor que imprime
`cifras_para_verificar.py`, que es la fuente primaria.

## Resultados

<!-- Pegar aquí la tabla que imprime `python evaluar.py`, y volver a correr `python grafico.py`
     para que el gráfico incluya el tercer panel. -->

| modo | acierta | se equivoca | no sabe | segundos |
|---|---:|---:|---:|---:|
| memoria | | | | |
| mcp | | | | |

### Dos cifras comprobadas a mano

| Cifra | Valor | Verificada en |
|---|---:|---|
| Total nacional de infraestructuras registradas | **76** | [`where=1=1&returnCountOnly=true`](https://geoservidorperu.minam.gob.pe/arcgis/rest/services/Servicios_GeoPERU/ServicioRRSS_MINAM/MapServer/0/query?where=1%3D1&returnCountOnly=true&f=json) |
| Registros en el departamento de Piura | **8** | [`where=UPPER(DEPARTAMEN) LIKE '%PIURA%'`](https://geoservidorperu.minam.gob.pe/arcgis/rest/services/Servicios_GeoPERU/ServicioRRSS_MINAM/MapServer/0/query?where=UPPER%28DEPARTAMEN%29%20LIKE%20%27%25PIURA%25%27&returnCountOnly=true&f=json) |

Ambas se pueden volver a comprobar abriendo esas URLs: son consultas al servicio del MINAM, no a
este servidor.

## Lo que la capa reparte así

De los 76 registros, **57 son RSA**, 8 RSM, 6 RSE y 5 celdas transitorias. Territorialmente la
concentración es baja y pareja: Piura encabeza con 8, seguido de Ayacucho y Lima con 7, y Áncash con
6. Ningún departamento concentra más del 11 % del total.

Eso ya dice algo sobre el límite de la fuente: 76 puntos para 1,891 distritos del país no describen
la cobertura real de infraestructura de residuos. Describen **lo que está registrado en esta capa**,
que es otra cosa.

## Un hallazgo de calidad del dato

El campo `DEPARTAMEN` tiene el mismo departamento escrito de dos formas:

| Valor con tilde | Valor sin tilde |
|---|---|
| `JUNÍN` | `JUNIN` |
| `HUÁNUCO` | `HUANUCO` |
| `SAN MARTÍN` | `SAN MARTIN` |

Un `GROUP BY` ingenuo sobre ese campo devuelve **24 departamentos**; normalizando las tildes son
**21**. Es un error de digitación en el origen, no del MCP, y tiene una consecuencia práctica: quien
consulte el servicio con `DEPARTAMEN = 'JUNIN'` obtiene 1 registro cuando en realidad hay 5.

Por eso las herramientas de este servidor normalizan tildes y mayúsculas antes de filtrar, y por eso
las pruebas 3 a 5 verifican **invariantes** (que los desgloses sumen el total, que un filtro devuelva
un subconjunto) en vez de números clavados: una prueba atada a «24 departamentos» se rompería el día
que el MINAM corrija la tipografía, y lo haría pareciendo un error del código.

## Qué hace el servidor para no mentir

Tres decisiones deliberadas, más allá de lo que pedía la rúbrica:

1. **Cada respuesta trae su URL de consulta** en el campo `fuente`. La cifra es reproducible sin
   pasar por este MCP, que es la única forma de que alguien pueda desconfiar de él y comprobarlo.
2. **Python hace las cuentas, no el modelo.** `resumen_territorial` devuelve los desgloses ya
   calculados e `infraestructuras_cercanas` resuelve la distancia con haversine. El modelo nunca
   suma ni estima kilómetros.
3. **El recurso `geoperu://capa/rrss` declara lo que no se puede concluir**: que no hay serie de
   tiempo, y que la ausencia de un punto no prueba la ausencia de infraestructura, solo la ausencia
   de registro. El prompt `informe_territorial` le exige al modelo respetar esas advertencias. Un MCP
   que solo entrega datos invita a sobreinterpretarlos; este entrega los datos y sus límites.

## Conclusión

<!-- Ajustar las dos primeras frases según lo que salga en resultados.csv. -->

Vale la pena construir un MCP cuando la fuente es **autoritativa, consultable y el modelo no la tiene
memorizada**. Las tres condiciones se cumplen aquí: el servicio del MINAM es el registro oficial,
responde por HTTP sin clave, y son datos de nicho que ningún modelo aprendió de memoria.

La búsqueda web no es sustituto en este caso, y por una razón que no aplica al BCRP: las cifras del
BCRP están republicadas en notas de prensa y portales que un buscador encuentra, pero el conteo de
infraestructuras de residuos por departamento **solo existe dentro del servicio**. No hay página que
lo diga. Ahí el MCP no es más rápido que la web: es la única ruta.

Donde no vale la pena es cuando la pregunta es interpretativa. Esta capa no puede decir si la
infraestructura es suficiente, ni si mejoró, porque es una foto sin línea de tiempo. Un MCP hace que
el modelo deje de inventar el dato; no lo convierte en analista.

## Para reproducirlo

```bash
pip install fastmcp httpx pytest pandas matplotlib
pytest -q                         # 9 pruebas
python cifras_para_verificar.py   # cifras + URL del MINAM de cada una
python evaluar.py                 # memoria contra mcp
python grafico.py                 # grafico.png
```
