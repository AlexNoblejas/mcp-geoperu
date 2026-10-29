"""Recorre el catálogo de un ArcGIS Server del Estado y lista TODO lo consultable.

    python descubrir.py                        # el geoservidor del MINAM
    python descubrir.py https://otro/arcgis/rest/services

Esto responde la pregunta «¿a qué puedo acceder?»: un ArcGIS Server publica su propio catálogo,
así que no hay que adivinar. Cada capa que aparezca con Query se puede consultar con
consultar_capa() del server.py, sin escribir código nuevo.
"""
import json
import sys
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else
        "https://geoservidorperu.minam.gob.pe/arcgis/rest/services").rstrip("/")


def get(url):
    u = urllib.parse.quote(url, safe=":/?&=")
    with urllib.request.urlopen(u + ("&" if "?" in u else "?") + "f=json", timeout=60) as r:
        return json.load(r)


def servicios(folder=""):
    d = get(f"{BASE}/{folder}" if folder else BASE)
    for s in d.get("services", []):
        yield s["name"], s["type"]
    for sub in d.get("folders", []):
        yield from servicios(sub)


total_capas = 0
print(f"CATALOGO: {BASE}\n")
try:
    raiz = get(BASE)
except Exception as e:
    sys.exit(f"No se pudo leer el catalogo: {e}")

print(f"Carpetas: {raiz.get('folders', [])}\n")

for nombre, tipo in servicios():
    if tipo not in ("MapServer", "FeatureServer"):
        continue
    try:
        d = get(f"{BASE}/{nombre}/{tipo}")
    except Exception as e:
        print(f"  !! {nombre} ({tipo}): {e}")
        continue
    capas = d.get("layers", [])
    if not capas:
        continue
    print(f"{nombre} [{tipo}]  -  {len(capas)} capa(s)")
    for c in capas:
        print(f"    id={c['id']:<3} {c['name']}")
        total_capas += 1

print(f"\nTOTAL DE CAPAS CONSULTABLES: {total_capas}")
print("Para usar una: consultar_capa(servicio='Servicios_GeoPERU/ServicioRRSS_MINAM',")
print("                             tipo='MapServer', capa=0, where='1=1')")
