**MCP de GEOPERÚ / ArcGIS del Estado peruano**

https://github.com/AlexNoblejas/mcp-geoperu

Alternativa institucional al MCP del BCRP. En vez de 17,167 series macroeconómicas,
un catálogo de **capas georreferenciadas** de servidores ArcGIS REST del Estado,
empezando por el geoservidor del MINAM que publica las capas de GEOPERÚ.

| | |
|---|---|
| Pruebas | 15 en verde, con datos reales. La tabla de equivalencia con las 8 del proyecto original está en el README |
| Herramientas | 7 · dos genéricas (`buscar_capas`, `consultar_capa`) + `listar_servidores` + cuatro dedicadas a residuos sólidos |
| Herramienta propia | `infraestructuras_cercanas`: radio en km desde una coordenada, con haversine en Python |
| Evaluación | memoria **0/10** · MCP **10/10** |

**La arquitectura es la del profesor, sobre otro catálogo:**

| Proyecto del BCRP | Este |
|---|---|
| `catalogo()` · 17,167 series, cacheado en `datos/` | `catalogo()` · 4,708 capas de 2 entidades, cacheado en `datos/` |
| `buscar_series("ipc 12 meses")` | `buscar_capas("riesgo distrital")` |
| `serie(codigo, desde, hasta)` | `consultar_capa(servidor, servicio, capa, where)` |

**Tres hallazgos:**

1. **Error en la fuente oficial.** El campo `DEPARTAMEN` tiene el mismo departamento
   escrito de dos formas (`JUNÍN`/`JUNIN`, `HUÁNUCO`/`HUANUCO`, `SAN MARTÍN`/`SAN MARTIN`).
   Un `GROUP BY` ingenuo devuelve 24 departamentos; normalizando tildes son 21. Quien
   consulte `DEPARTAMEN = 'JUNIN'` obtiene 1 registro cuando hay 5.

2. **Un bug mío que encontró la evaluación.** Ica devolvía 6 en vez de 4, porque el filtro
   hacía coincidencia por subcadena e "ica" también está dentro de HUANCAVELICA. Las pruebas
   pasaban con el bug dentro: verificaban invariantes, y 6 es un subconjunto válido de 76.
   Lo delató comparar contra una cifra verificada a mano en la fuente. Un MCP puede estar
   en verde y mentir.

3. **1,177 capas invisibles por una URL sin escapar.** 62 servicios fallaban porque sus
   nombres llevan tildes (`02_CARACTERIZACIÓN_DEL_TERRITORIO_TUMBES`). Con
   `urllib.parse.quote` el catálogo pasó de 3,482 a 4,659 capas. No daba ningún error:
   simplemente una cuarta parte del catálogo no existía para quien consultaba.

**Auditoría propia.** Ejercitando el servidor con entradas límite salieron seis defectos
más, todos corregidos y fijados con pruebas: `limite=0` devolvía 1 registro en silencio;
un servidor mal escrito devolvía 0 capas en vez de error; la búsqueda vacía volcaba las
4,708 capas al contexto; el recurso con entrada no numérica lanzaba un `ValueError` de
Python en vez de un `ToolError` util; `SampleWorldCities` —el servicio de demostración que
ArcGIS instala por defecto y quedó publicado en CENEPRED— se contaba como dato oficial
(46 capas útiles, no 49); y el catálogo no declaraba su fecha de descarga. Los seis
devolvían respuestas plausibles sin lanzar ningún error.

**Qué es y qué no es GEOPERÚ.** Es un visor que agrega capas publicadas por varias
entidades, cada una en su propio ArcGIS; no hay una API única. Por eso el servidor tiene un
registro de servidores (`servidores.py`) y un probador que decide cuáles entran por
evidencia, no por suposición: prueba varias rutas de montaje por host y marca vivo solo al
que devolvió su catálogo. Confirmados: **MINAM** (4,659 capas) y **CENEPRED/SIGRID** (49).
Registrados sin responder: SERNANP, ANA, MIDAGRI, IGN, SENAMHI, MTC. Agregar una entidad es una entrada en un
diccionario.

**Nota metodológica.** Esta máquina no tiene el CLI de Claude Code, así que `evaluar.py`
quedó en el repo (funcional, con `--claude`) y la comparación efectiva está en
`evaluar_manual.py`: mismas 10 preguntas, modo memoria sin herramientas, n=1 por celda y
Opus 5 en vez de Haiku. Declarado en el informe, no escondido.
