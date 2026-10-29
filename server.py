"""Servidor MCP de GEOPERÚ: infraestructura de residuos sólidos del MINAM.

Alternativa institucional al MCP del BCRP, autorizada por el docente (sesión 04).
Misma arquitectura del proyecto del curso: las cuentas las hace Python, no el modelo,
y cada respuesta trae la URL de consulta para que la cifra sea reproducible.

    uv run pytest -q                                             # el contrato: 8 pruebas
    uv run server.py                                             # el servidor, por stdio
    claude mcp add --scope project geoperu -- uv run server.py    # conectarlo a Claude Code

Fuente: Geoservidor del Ministerio del Ambiente, servicio ArcGIS REST publicado en GEOPERÚ.
"""
import json
import math
from urllib.parse import quote
import unicodedata
from functools import cache
from pathlib import Path

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from servidores import SERVIDORES, vivos

AQUI = Path(__file__).parent
SNAPSHOT = AQUI / "datos" / "geoperu_rrss.json"
CAPA = ("https://geoservidorperu.minam.gob.pe/arcgis/rest/services/"
        "Servicios_GeoPERU/ServicioRRSS_MINAM/MapServer/0")
CAMPOS = "OBJECTID,DEPARTAMEN,PROVINCIA,DISTRITO,Tipo_de_In"

# El catálogo de capas de TODOS los servidores vivos del registro. Es el equivalente de las
# 17,167 series del BCRP: se descubre solo en vez de escribirse a mano.
RAIZ = SERVIDORES["minam"]["raiz"]          # el servidor de la capa de residuos
CATALOGO = AQUI / "datos" / "catalogo_arcgis.json"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("geoperu", instructions=(
    "Datos georreferenciados de servidores ArcGIS del Estado peruano, entre ellos el geoservidor "
    "del Ministerio del Ambiente que publica las capas de GEOPERÚ. Tres niveles. (1) listar_servidores "
    "dice qué entidades están disponibles. (2) Para cualquier tema territorial —riesgo de desastres, "
    "ZEE, biodiversidad, agua, suelos, deforestación, áreas protegidas— busca la capa con buscar_capas "
    "y consúltala con consultar_capa. (3) Para infraestructura de residuos sólidos hay herramientas "
    "dedicadas, trabajadas a fondo: buscar_infraestructura, resumen_territorial, "
    "detalle_infraestructura e infraestructuras_cercanas. No cuentes a mano y cita siempre la URL "
    "de consulta que devuelve cada herramienta."))


def _fn(herramienta):
    """La función de Python detrás de una herramienta, en cualquier versión de FastMCP."""
    return getattr(herramienta, "fn", herramienta)


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


def _pedir(params):
    """Una consulta a la capa de residuos sólidos."""
    return _pedir_en(f"{CAPA}/query", params)


def _pedir_en(url, params):
    """Una consulta a cualquier endpoint ArcGIS, con errores que el modelo pueda entender."""
    try:
        r = httpx.get(url, params=params, timeout=90, follow_redirects=True)
        r.raise_for_status()
        cuerpo = r.json()
    except httpx.HTTPError as e:
        raise ToolError(f"El geoservidor del MINAM no respondió: {e}. Es un servidor del Estado y "
                        f"a veces está caído: reintenten en unos segundos.") from e
    except ValueError as e:
        raise ToolError("El geoservidor del MINAM devolvió HTML en vez de JSON. Reintenten.") from e
    if "error" in cuerpo:
        raise ToolError(f"ArcGIS rechazó la consulta: {cuerpo['error'].get('message', cuerpo['error'])}")
    return cuerpo


@cache
def registros():
    """Todos los puntos de la capa. Se bajan una vez y quedan en datos/, como el catálogo del BCRP."""
    if SNAPSHOT.exists():
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    filas, offset = [], 0
    while True:
        cuerpo = _pedir({"where": "1=1", "outFields": CAMPOS, "returnGeometry": "true",
                         "outSR": "4326", "f": "json", "resultOffset": offset,
                         "resultRecordCount": 1000})
        lote = cuerpo.get("features", [])
        for f in lote:
            a, g = f.get("attributes", {}), (f.get("geometry") or {})
            filas.append({"objectid": a.get("OBJECTID"),
                          "departamento": (a.get("DEPARTAMEN") or "").strip().upper(),
                          "provincia": (a.get("PROVINCIA") or "").strip().upper(),
                          "distrito": (a.get("DISTRITO") or "").strip().upper(),
                          "tipo": (a.get("Tipo_de_In") or "sin dato").strip(),
                          "lon": g.get("x"), "lat": g.get("y")})
        if not cuerpo.get("exceededTransferLimit") or not lote:
            break
        offset += len(lote)

    if not filas:
        raise ToolError("El geoservidor no devolvió ningún registro.")
    SNAPSHOT.parent.mkdir(exist_ok=True)
    SNAPSHOT.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
    return filas


def _url(where):
    return f"{CAPA}/query?where={where}&outFields={CAMPOS}&f=json"


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_infraestructura(departamento: str = "", provincia: str = "", tipo: str = "",
                           limite: int = 20) -> dict:
    """Busca infraestructura de residuos sólidos por departamento, provincia o tipo.

    Úsala para ubicar rellenos sanitarios, plantas y botaderos: dónde están, en qué distrito
    y de qué tipo son. Los filtros no distinguen tildes ni mayúsculas y aceptan parte del nombre
    ("piura", "LIMA", "relleno"). Vacíos = todo el país.

    Devuelve cada registro con su OBJECTID, ubicación y coordenadas WGS84, más la URL de consulta.
    """
    filas = registros()
    for campo, valor in (("departamento", departamento), ("provincia", provincia), ("tipo", tipo)):
        if not valor:
            continue
        aguja = _sin_tildes(valor)
        # Primero coincidencia exacta: "ica" debe dar ICA y no también HUANCAVELICA.
        exactas = [f for f in filas if _sin_tildes(f[campo]) == aguja]
        filas = exactas or [f for f in filas if aguja in _sin_tildes(f[campo])]

    where = " AND ".join(
        [f"UPPER({c}) LIKE '%{v.upper()}%'"
         for c, v in (("DEPARTAMEN", departamento), ("PROVINCIA", provincia), ("Tipo_de_In", tipo)) if v]
    ) or "1=1"

    if not filas:
        return {"filtro": where, "encontrados": 0, "registros": [],
                "sugerencia": "Pruebe con menos palabras o revise el nombre del departamento.",
                "fuente": _url(where)}

    return {"filtro": where, "encontrados": len(filas),
            "registros": filas[:max(1, limite)],
            "capa": "Infraestructura de residuos sólidos · MINAM vía GEOPERÚ",
            "fuente": _url(where)}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen_territorial(departamento: str = "") -> dict:
    """Conteos y desgloses de la infraestructura de residuos, calculados en Python.

    Úsala en vez de contar a mano cuando pregunten cuántas infraestructuras hay, cuál es el
    departamento con más, o cómo se reparten por tipo. departamento vacío = todo el país.

    Devuelve el total, el desglose por tipo, por departamento y por provincia, y el top 5.
    """
    filas = registros()
    if departamento:
        aguja = _sin_tildes(departamento)
        exactas = [f for f in filas if _sin_tildes(f["departamento"]) == aguja]
        filas = exactas or [f for f in filas if aguja in _sin_tildes(f["departamento"])]
    if not filas:
        raise ToolError(f"No hay registros para el departamento {departamento!r}.")

    def contar(campo):
        d = {}
        for f in filas:
            d[f[campo]] = d.get(f[campo], 0) + 1
        return dict(sorted(d.items(), key=lambda x: -x[1]))

    por_depa = contar("departamento")
    return {"ambito": departamento.upper() or "PERÚ", "total": len(filas),
            "por_tipo": contar("tipo"), "por_departamento": por_depa,
            "por_provincia": contar("provincia"),
            "top_departamentos": list(por_depa.items())[:5],
            "fuente": _url("1=1")}


@mcp.tool(annotations=SOLO_LECTURA)
def detalle_infraestructura(objectid: int) -> dict:
    """Ficha completa de una infraestructura por su OBJECTID, con coordenadas y enlace al mapa.

    Úsala después de buscar_infraestructura, cuando necesiten el detalle de un punto concreto.
    """
    for f in registros():
        if f["objectid"] == objectid:
            return {**f, "mapa": f"https://www.google.com/maps?q={f['lat']},{f['lon']}",
                    "fuente": _url(f"OBJECTID={objectid}")}
    raise ToolError(f"No existe OBJECTID={objectid} en la capa de GEOPERÚ. "
                    f"Búsquenlo primero con buscar_infraestructura.")


@mcp.tool(annotations=SOLO_LECTURA)
def infraestructuras_cercanas(latitud: float, longitud: float, radio_km: float = 100,
                              limite: int = 10) -> dict:
    """Infraestructura de residuos dentro de un radio desde una coordenada del Perú.

    Úsala para preguntas de proximidad: qué hay cerca de una ciudad, de una cuenca o de un
    punto del mapa. La distancia se calcula con la fórmula de haversine en Python, en kilómetros.
    Ejemplo: latitud=-12.05, longitud=-77.04 (Lima), radio_km=50.
    """
    if not (-18.5 <= latitud <= 0.5 and -81.5 <= longitud <= -68.5):
        raise ToolError(f"La coordenada ({latitud}, {longitud}) está fuera del Perú.")

    cerca = []
    for f in registros():
        if f["lat"] is None or f["lon"] is None:
            continue
        dlat = math.radians(f["lat"] - latitud)
        dlon = math.radians(f["lon"] - longitud)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(latitud)) * math.cos(math.radians(f["lat"])) * math.sin(dlon / 2) ** 2)
        km = 6371 * 2 * math.asin(math.sqrt(a))
        if km <= radio_km:
            cerca.append({**f, "distancia_km": round(km, 1)})

    cerca.sort(key=lambda x: x["distancia_km"])
    return {"centro": {"lat": latitud, "lon": longitud}, "radio_km": radio_km,
            "encontrados": len(cerca), "registros": cerca[:max(1, limite)],
            "fuente": _url("1=1")}


def _leer(url):
    r = httpx.get(url, params={"f": "json"}, timeout=90, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def _capas_de(clave, raiz):
    """Recorre un ArcGIS Server y devuelve todas sus capas. Los fallos se saltan, no abortan."""
    def recorrer(carpeta=""):
        try:
            d = _leer(f"{raiz}/{quote(carpeta)}" if carpeta else raiz)
        except (httpx.HTTPError, ValueError):
            return
        for s in d.get("services", []):
            if s.get("type") in ("MapServer", "FeatureServer"):
                yield s["name"], s["type"]
        for sub in d.get("folders", []):
            yield from recorrer(sub)

    capas = []
    for nombre, tipo in recorrer():
        try:
            d = _leer(f"{raiz}/{quote(nombre)}/{tipo}")
        except (httpx.HTTPError, ValueError):
            continue
        for c in d.get("layers", []):
            capas.append({"servidor": clave, "servicio": nombre, "tipo": tipo,
                          "capa": c["id"], "nombre": c["name"],
                          "texto": _sin_tildes(f"{clave} {nombre} {c['name']}")})
    return capas


@cache
def catalogo():
    """Las capas de todos los servidores vivos del registro. Se baja una vez y queda en datos/."""
    if CATALOGO.exists():
        guardado = json.loads(CATALOGO.read_text(encoding="utf-8"))
        # compatibilidad con el caché de la versión de un solo servidor
        for c in guardado:
            c.setdefault("servidor", "minam")
        return guardado

    capas = []
    for clave, s in vivos().items():
        capas += _capas_de(clave, s["raiz"])
    if not capas:
        raise ToolError("Ningún servidor del registro respondió. Corran probar_servidores.py.")
    CATALOGO.parent.mkdir(exist_ok=True)
    CATALOGO.write_text(json.dumps(capas, ensure_ascii=False), encoding="utf-8")
    return capas


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_capas(texto: str, servidor: str = "", limite: int = 15) -> dict:
    """Busca entre las capas georreferenciadas de los servidores del Estado peruano registrados.

    Es el primer paso para cualquier pregunta territorial: los servidores publican miles de capas
    (riesgo de desastres, zonificación ecológica económica, biodiversidad, agua, suelos,
    deforestación, áreas naturales protegidas, transporte), y esta herramienta encuentra la que
    corresponde. Todas las palabras deben aparecer en el nombre del servidor, del servicio o de la
    capa; no distingue tildes ni mayúsculas.

    servidor: limita la búsqueda a una entidad ("minam", "sernanp", "ana"...). Vacío = todas.
    Ejemplos: "riesgo distrital", "areas naturales protegidas", "deforestacion", "zee la libertad".
    Devuelve servidor, servicio, tipo, id de capa y nombre: eso es lo que pide consultar_capa.
    """
    capas = catalogo()
    if servidor:
        capas = [c for c in capas if c["servidor"] == servidor.lower().strip()]
    for palabra in _sin_tildes(texto).split():
        capas = [c for c in capas if palabra in c["texto"]]

    por_servidor = {}
    for c in capas:
        por_servidor[c["servidor"]] = por_servidor.get(c["servidor"], 0) + 1

    if not capas:
        return {"consulta": texto, "encontradas": 0, "capas": [],
                "sugerencia": "Pruebe con menos palabras o sin filtrar por servidor.",
                "servidores_disponibles": list(vivos()), "total_en_catalogo": len(catalogo())}
    return {"consulta": texto, "encontradas": len(capas), "por_servidor": por_servidor,
            "capas": [{k: c[k] for k in ("servidor", "servicio", "tipo", "capa", "nombre")}
                      for c in capas[:max(1, limite)]],
            "total_en_catalogo": len(catalogo())}


@mcp.tool(annotations=SOLO_LECTURA)
def consultar_capa(servicio: str, capa: int, where: str = "1=1", servidor: str = "minam",
                   tipo: str = "MapServer", campos: str = "*", limite: int = 20) -> dict:
    """Consulta cualquier capa de cualquier servidor registrado, con lo que devuelva buscar_capas.

    Úsala después de buscar_capas, pasando el mismo `servidor`, `servicio`, `tipo` y `capa` que
    ella devolvió. `where` es SQL de ArcGIS: "1=1" trae todo, "DEPARTAMENTO='PIURA'" filtra.
    Para saber qué campos tiene una capa antes de filtrar, consúltenla con where="1=1" y limite=1
    y miren las claves del primer registro.

    Devuelve el conteo, los registros y la URL exacta de la consulta.
    """
    registro = vivos().get(servidor.lower().strip())
    if registro is None:
        raise ToolError(f"El servidor {servidor!r} no está en el registro o no respondió. "
                        f"Disponibles: {sorted(vivos())}.")
    raiz = registro["raiz"]
    cuerpo = _pedir_en(f"{raiz}/{quote(servicio)}/{tipo}/{capa}/query",
                       {"where": where, "outFields": campos, "returnGeometry": "false",
                        "f": "json", "resultRecordCount": max(1, min(limite, 200))})
    rasgos = cuerpo.get("features", [])
    return {"servidor": servidor, "entidad": registro["entidad"], "servicio": servicio,
            "capa": capa, "where": where, "devueltos": len(rasgos),
            "registros": [f.get("attributes", {}) for f in rasgos],
            "fuente": f"{raiz}/{quote(servicio)}/{tipo}/{capa}/query?where={quote(where)}"
                      f"&outFields={campos}&f=json"}


@mcp.tool(annotations=SOLO_LECTURA)
def listar_servidores() -> dict:
    """Las entidades del Estado peruano cuyos servidores están registrados y respondiendo.

    Úsala cuando no sepas de qué entidad puede venir un dato territorial, o cuando el usuario
    pregunte qué fuentes hay disponibles. Devuelve la clave de cada servidor (para pasarla a
    buscar_capas y consultar_capa), la entidad y cuántas capas aporta al catálogo.
    """
    conteo = {}
    for c in catalogo():
        conteo[c["servidor"]] = conteo.get(c["servidor"], 0) + 1
    activos = [{"servidor": k, "entidad": v["entidad"], "capas": conteo.get(k, 0),
                "raiz": v["raiz"]} for k, v in vivos().items()]
    no_vivos = [{"servidor": k, "entidad": v["entidad"]}
                for k, v in SERVIDORES.items() if k not in vivos()]
    return {"activos": sorted(activos, key=lambda x: -x["capas"]),
            "total_capas": len(catalogo()),
            "registrados_sin_responder": no_vivos,
            "nota": "Cada servidor es un ArcGIS REST de su propia entidad; GEOPERÚ es el visor "
                    "que agrega varias de estas capas, no una API única."}


@mcp.resource("geoperu://capa/rrss")
def ficha_capa() -> dict:
    """Ficha de la capa: qué trae, qué campos, y qué NO se puede concluir con ella."""
    return {
        "capa": "Infraestructura de residuos sólidos (ServicioRRSS_MINAM)",
        "publica": "Ministerio del Ambiente (MINAM), vía GEOPERÚ",
        "url": CAPA, "visor": "https://visor.geoperu.gob.pe/",
        "geometria": "puntos, WGS84 (EPSG:4326)",
        "campos": CAMPOS.split(","),
        "advertencias": [
            "Los nombres vienen en mayúsculas y sin tildes.",
            "Es una foto del registro, no una serie de tiempo: no permite medir evolución.",
            "Ausencia de un punto no prueba ausencia de infraestructura, solo que no está registrada.",
        ],
    }


@mcp.resource("geoperu://infraestructura/{objectid}")
def ficha_punto(objectid: int) -> dict:
    """Ficha reproducible de un OBJECTID de la capa."""
    return _fn(detalle_infraestructura)(int(objectid))


@mcp.prompt
def informe_territorial(departamento: str = "", tema: str = "residuos sólidos") -> str:
    """Informe territorial con cifras verificables de GEOPERÚ."""
    donde = departamento or "el Perú"
    return (
        f"Escribe cinco viñetas sobre {tema} en {donde}, usando solo las herramientas de este "
        f"servidor.\n"
        f"1. Empieza con resumen_territorial para el total y el desglose por tipo.\n"
        f"2. Usa buscar_infraestructura para nombrar casos concretos con su distrito.\n"
        f"3. Si hay una ciudad relevante, usa infraestructuras_cercanas.\n"
        f"Reglas: cada viñeta cita la URL de consulta que devolvió la herramienta. No cuentes a "
        f"mano. Lee el recurso geoperu://capa/rrss y respeta sus advertencias: no concluyas nada "
        f"sobre evolución en el tiempo ni interpretes la ausencia de un punto como ausencia real."
    )


if __name__ == "__main__":
    mcp.run()
