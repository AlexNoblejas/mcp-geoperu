# MCP de GEOPERÚ · Infraestructura de residuos sólidos del MINAM

Servidor MCP construido con FastMCP sobre el servicio ArcGIS REST que el **Ministerio del Ambiente**
publica en **GEOPERÚ**. Es la alternativa institucional al MCP del BCRP de la sesión 04, autorizada
por el docente.

**Autor:** Alexander Noblejas · Diplomatura en Ciencia de Datos (QLAB) · sesión 04

## Por qué otra institución

El proyecto del curso usa las 17,167 series del BCRP: datos **macroeconómicos y de serie de tiempo**.
Esta capa es lo contrario: un registro **territorial y georreferenciado**, sin dimensión temporal. Eso
cambia qué preguntas puede responder un MCP y qué puede hacer mal:

| | MCP del BCRP | MCP de GEOPERÚ |
|---|---|---|
| Unidad | serie de tiempo nacional | punto georreferenciado |
| Pregunta típica | ¿cuánto fue la inflación en setiembre? | ¿cuántos rellenos hay en Piura y dónde? |
| Riesgo del modelo sin MCP | inventa un decimal | inventa una ubicación |
| Cuenta que hace Python | variación, promedio, extremos | conteos, desgloses, distancias |

La fuente es el servicio `ServicioRRSS_MINAM` del geoservidor del MINAM, consultado por la API REST
de ArcGIS. No necesita clave.

## Alcance: el catálogo completo, no una capa

Los servidores registrados publican **4,708 capas georreferenciadas** (4,659 del MINAM en 209
servicios y 15 carpetas, 49 de CENEPRED/SIGRID)
temáticas (riesgo de desastres, zonificación ecológica económica, biodiversidad, agua, suelos,
deforestación, áreas naturales protegidas, residuos). El catálogo se descubre solo recorriendo
`?f=json`, igual que el del BCRP se baja de una URL.

| El proyecto del BCRP | Este |
|---|---|
| `catalogo()` · 17,167 series, cacheado en `datos/` | `catalogo()` · 4,708 capas de 2 entidades, cacheado en `datos/` |
| `buscar_series("ipc 12 meses")` | `buscar_capas("riesgo distrital")` |
| `serie(codigo, desde, hasta)` | `consultar_capa(servicio, capa, where)` |

`descubrir.py` imprime el catálogo entero si quieren verlo sin pasar por el MCP.

### Multi-entidad

El servidor no está atado a una institución. `servidores.py` es un registro de ArcGIS REST del
Estado peruano, y `probar_servidores.py` decide cuáles entran **por evidencia**: prueba varias rutas
de montaje por host y marca vivo solo el que devolvió su catálogo. Los que no responden se quedan
registrados y el MCP los ignora sin romperse.

```bash
python probar_servidores.py     # reescribe servidores_vivos.json
```

Confirmados: **MINAM** (geoservidor de GEOPERÚ, 4,659 capas) y **CENEPRED/SIGRID** (gestión del
riesgo de desastres, 49 capas). En el registro, sin responder al momento de la entrega: SERNANP, ANA, MIDAGRI, IGN,
SENAMHI, MTC. Agregar una entidad es una entrada en el diccionario, no código nuevo.

`listar_servidores` le dice al modelo qué entidades hay y cuántas capas aporta cada una.

**Lo que GEOPERÚ es y no es:** un visor que agrega capas publicadas por varias entidades, cada una
en su propio ArcGIS. No hay una API única de GEOPERÚ. Lo que generaliza es el protocolo ArcGIS REST,
y por eso el registro puede crecer.

## Arquitectura

| Archivo | Qué es |
|---|---|
| `server.py` | El servidor: 7 herramientas, 2 recursos, 1 prompt |
| `test_server.py` | El contrato: 8 pruebas equivalentes a las 8 del BCRP, con datos reales |
| `.mcp.json` | `geoperu` y `fetch`, sin claves |
| `preguntas.csv` | Las 10 preguntas de la evaluación |
| `servidores.py` | El registro de ArcGIS REST del Estado |
| `probar_servidores.py` | Prueba cada servidor y escribe `servidores_vivos.json` |
| `descubrir.py` | Recorre el catálogo del servidor y lista todas las capas |
| `cifras_para_verificar.py` | Calcula cada cifra y da la URL del MINAM para comprobarla a mano |
| `evaluar.py` | Igual que el del curso; solo cambia `mcp__bcrp` por `mcp__geoperu` |
| `datos/` | La capa descargada. No se versiona: se vuelve a bajar sola |

### Las cuatro herramientas

| Herramienta | Qué hace | Por qué existe |
|---|---|---|
| `listar_servidores` | qué entidades están registradas y respondiendo | el modelo no adivina de dónde viene un dato |
| `buscar_capas` | busca entre las capas de todos los servidores vivos | el equivalente de `buscar_series`: descubrir antes de consultar |
| `consultar_capa` | consulta cualquier capa con un `where` de ArcGIS | el equivalente de `serie`: una función para todas las capas |
| `buscar_infraestructura` | filtra por departamento, provincia o tipo | el equivalente de `buscar_series` |
| `resumen_territorial` | totales y desgloses por tipo, departamento y provincia | el equivalente de `resumen`: Python cuenta, no el modelo |
| `detalle_infraestructura` | ficha de un OBJECTID con coordenadas | el equivalente de `serie` |
| `infraestructuras_cercanas` | radio en km desde una coordenada, con haversine | **la herramienta propia**: proximidad, algo que el proyecto del BCRP no puede hacer |

Cada respuesta incluye el campo `fuente` con la URL de consulta al geoservidor, así cualquiera
reproduce la cifra sin pasar por este servidor.

### Recursos y prompt

- `geoperu://capa/rrss` — ficha de la capa, **con sus advertencias metodológicas**
- `geoperu://infraestructura/{objectid}` — plantilla: una ficha por cada punto
- `/mcp__geoperu__informe_territorial` — informe que obliga a citar la URL de cada cifra

El recurso de la capa declara explícitamente lo que **no** se puede concluir: no hay serie de tiempo,
y la ausencia de un punto no prueba la ausencia de infraestructura, solo que no está registrada. El
prompt le exige al modelo respetar esas advertencias.

## Cómo correrlo

```bash
cd "C:\Users\alexa\Videos\Python Intermedio\Tareas\tarea_MPC"

uv run pytest -q                  # 1. las 8 pruebas (la primera baja la capa a datos/)
uv run cifras_para_verificar.py   # 2. las cifras + la URL del MINAM de cada una
                                  # 3. abrir las URLs, confirmar, y llenar «verdad» en preguntas.csv
uv run evaluar.py                 # 4. memoria contra MCP
```

Para conectarlo a Claude Code:

```bash
claude mcp add --scope project geoperu -- uv run server.py
claude mcp add --scope project fetch -- uvx mcp-server-fetch
claude
```

Dentro de la sesión: `/mcp` para ver los dos conectados, una pregunta territorial para la
herramienta, `@geoperu:geoperu://capa/rrss` para el recurso y
`/mcp__geoperu__informe_territorial Piura` para el prompt.

## Cómo responde a la rúbrica

| Criterio | Puntos | Dónde está |
|---|---|---|
| Pruebas | 6 | `test_server.py`: 8 pruebas, una por cada una de las del docente, con datos reales del MINAM |
| Herramienta propia | 3 | `infraestructuras_cercanas`: haversine en Python, docstring con ejemplo, `fuente` en la respuesta |
| Recurso y prompt | 2 | `geoperu://capa/rrss` y `informe_territorial`, probados con `@` y `/` |
| `.mcp.json` | 2 | en el repo, con `geoperu` y `fetch`, sin claves |
| Evaluación | 4 | `preguntas.csv` con 10 preguntas verificadas contra la URL del geoservidor |
| Informe | 3 | `informe.md` + `grafico.png` |

## Equivalencia de las ocho pruebas

| N.º | Prueba del BCRP | Prueba aquí |
|---:|---|---|
| 1 | `buscar_encuentra_el_ipc` | `buscar_encuentra_lima` |
| 2 | `cuatro_herramientas_como_minimo` | igual |
| 3 | `serie_mensual` | `consulta_trae_datos_y_fuente` |
| 4 | `serie_diaria` | `filtro_por_tipo_es_subconjunto` |
| 5 | `resumen_sin_cuentas_a_mano` | igual, verificando que los desgloses sumen el total |
| 6 | `codigo_inexistente_da_un_error_claro` | `objectid_inexistente_da_un_error_claro` |
| 7 | `un_recurso` | igual |
| 8 | `un_prompt` | igual |

Más una novena, extra, para la herramienta propia de proximidad.

Las pruebas 3, 4 y 5 verifican **invariantes** (que los desgloses sumen el total, que un filtro
devuelva un subconjunto) en vez de números fijos, porque la capa del MINAM se actualiza y un número
clavado volvería la prueba frágil. Las cifras fijas se verifican a mano en el informe, contra la URL
del geoservidor.
