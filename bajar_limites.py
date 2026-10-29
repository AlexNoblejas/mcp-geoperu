"""Baja los limites departamentales del geoservidor y los cachea en datos/.

    python bajar_limites.py

Una sola vez. Despues mapa_png.py dibuja el contorno del Peru sin volver a pedir nada.
Los poligonos se simplifican para que el archivo sea manejable.
"""
import json
from pathlib import Path
from urllib.parse import quote

import httpx

AQUI = Path(__file__).parent
RAIZ = "https://geoservidorperu.minam.gob.pe/arcgis/rest/services"
# varias capas candidatas: se usa la primera que responda con geometria
CANDIDATAS = [("ServicioCFOI", "MapServer", 15),
              ("CFOI_Dashboard_mensuales_base", "MapServer", 0),
              ("Servicio_Oportunidades_Inversion", "MapServer", 1),
              ("ServicioPMIZMC", "MapServer", 6)]


def simplificar(anillo, paso):
    """Se queda con 1 de cada `paso` vertices, conservando el primero y el ultimo."""
    if len(anillo) <= 4:
        return anillo
    recortado = anillo[::paso]
    if recortado[-1] != anillo[-1]:
        recortado.append(anillo[-1])
    return recortado


for servicio, tipo, capa in CANDIDATAS:
    url = f"{RAIZ}/{quote(servicio)}/{tipo}/{capa}/query"
    print(f"probando {servicio}/{tipo}/{capa} ...", end=" ", flush=True)
    try:
        r = httpx.get(url, params={"where": "1=1", "outFields": "*", "returnGeometry": "true",
                                   "outSR": "4326", "f": "json"}, timeout=180, follow_redirects=True)
        r.raise_for_status()
        d = r.json()
        if "error" in d or not d.get("features"):
            print("sin geometria"); continue
    except Exception as e:
        print(f"{type(e).__name__}"); continue

    poligonos = []
    for f in d["features"]:
        g = f.get("geometry") or {}
        attrs = f.get("attributes", {})
        nombre = next((str(v) for k, v in attrs.items()
                       if "DEP" in k.upper() and isinstance(v, str)), "")
        for anillo in g.get("rings", []):
            if len(anillo) >= 4:
                poligonos.append({"nombre": nombre, "anillo": simplificar(anillo, 4)})

    if not poligonos:
        print("sin anillos"); continue

    destino = AQUI / "datos" / "limites_departamentales.json"
    destino.write_text(json.dumps({"servicio": servicio, "capa": capa,
                                   "fuente": f"{url}?where=1%3D1&f=json",
                                   "poligonos": poligonos}, ensure_ascii=False), encoding="utf-8")
    v = sum(len(p["anillo"]) for p in poligonos)
    print(f"OK · {len(d['features'])} rasgos, {len(poligonos)} anillos, {v} vertices "
          f"· {destino.stat().st_size//1024} KB")
    break
else:
    raise SystemExit("Ninguna capa de limites respondio. Reintenten mas tarde.")
