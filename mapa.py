"""Mapa interactivo (HTML + Leaflet, sin dependencias) de una capa del geoservidor.

    python mapa.py                                   # los 76 puntos de residuos solidos (del cache)
    python mapa.py --servicio "ZEE_VISOR/20_CARACTERIZACIÓN_DEL_TERRITORIO_CUSCO" --capa 1
    python mapa.py --servicio ... --capa 1 --where "1=1" --salida conflictos_cusco.html

Escribe un .html que se abre en el navegador. La geometria se pide al geoservidor con
returnGeometry=true y se convierte de esriJSON a GeoJSON aqui.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import quote

import httpx

from server import CAMPOS, registros, vivos

AQUI = Path(__file__).parent

PLANTILLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITULO__</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
 html,body{margin:0;height:100%;font-family:system-ui,sans-serif}
 #mapa{height:100%}
 .ficha{position:absolute;top:12px;right:12px;z-index:1000;background:#fff;
  padding:12px 14px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.2);max-width:300px;font-size:13px}
 .ficha h1{margin:0 0 6px;font-size:15px}
 .ficha p{margin:4px 0;color:#444}
 .ficha a{color:#2a6f97;font-size:11px;word-break:break-all}
</style></head><body>
<div id="mapa"></div>
<div class="ficha"><h1>__TITULO__</h1><p>__SUBTITULO__</p><p>__CONTEO__</p>
<a href="__FUENTE__" target="_blank">fuente: geoservidor del MINAM</a></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const datos = __GEOJSON__;
const mapa = L.map('mapa');
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {attribution:'&copy; OpenStreetMap', maxZoom:18}).addTo(mapa);
function popup(p){
  return Object.entries(p).filter(([k,v])=>v!==null&&v!==''&&!k.startsWith('Shape'))
    .slice(0,12).map(([k,v])=>`<b>${k}</b>: ${v}`).join('<br>');
}
const capa = L.geoJSON(datos, {
  style: {color:'#2a6f97', weight:1.5, fillColor:'#2a6f97', fillOpacity:.35},
  pointToLayer: (f,ll)=>L.circleMarker(ll,{radius:6,color:'#a44a3f',fillColor:'#a44a3f',
     fillOpacity:.85,weight:1}),
  onEachFeature: (f,l)=>l.bindPopup(popup(f.properties||{}))
}).addTo(mapa);
try { mapa.fitBounds(capa.getBounds(), {padding:[30,30]}); }
catch(e) { mapa.setView([-9.2,-75.0], 5); }
</script></body></html>
"""


def esri_a_geojson(cuerpo):
    """Convierte la respuesta esriJSON de ArcGIS a GeoJSON."""
    rasgos = []
    for f in cuerpo.get("features", []):
        g, props = f.get("geometry") or {}, f.get("attributes", {})
        geom = None
        if "x" in g and "y" in g:
            geom = {"type": "Point", "coordinates": [g["x"], g["y"]]}
        elif "rings" in g:
            geom = {"type": "Polygon" if len(g["rings"]) == 1 else "MultiPolygon",
                    "coordinates": g["rings"] if len(g["rings"]) == 1 else [[r] for r in g["rings"]]}
        elif "paths" in g:
            geom = {"type": "LineString" if len(g["paths"]) == 1 else "MultiLineString",
                    "coordinates": g["paths"][0] if len(g["paths"]) == 1 else g["paths"]}
        if geom:
            rasgos.append({"type": "Feature", "geometry": geom, "properties": props})
    return {"type": "FeatureCollection", "features": rasgos}


def de_la_capa(servicio, capa, where, tipo, servidor, limite):
    raiz = vivos()[servidor]["raiz"]
    url = f"{raiz}/{quote(servicio)}/{tipo}/{capa}/query"
    r = httpx.get(url, params={"where": where, "outFields": "*", "returnGeometry": "true",
                               "outSR": "4326", "f": "json",
                               "resultRecordCount": limite}, timeout=120, follow_redirects=True)
    r.raise_for_status()
    cuerpo = r.json()
    if "error" in cuerpo:
        raise SystemExit(f"ArcGIS rechazo la consulta: {cuerpo['error']}")
    return esri_a_geojson(cuerpo), f"{url}?where={quote(where)}&f=json"


def de_residuos():
    """Los 76 puntos de residuos solidos, desde el cache: no necesita red."""
    rasgos = [{"type": "Feature",
               "geometry": {"type": "Point", "coordinates": [f["lon"], f["lat"]]},
               "properties": {k: f[k] for k in ("objectid", "departamento", "provincia",
                                                "distrito", "tipo")}}
              for f in registros() if f["lat"] is not None]
    fuente = f"{vivos()['minam']['raiz']}/Servicios_GeoPERU/ServicioRRSS_MINAM/MapServer/0/query?where=1%3D1&outFields={CAMPOS}&f=json"
    return {"type": "FeatureCollection", "features": rasgos}, fuente


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--servicio", default=None)
    p.add_argument("--capa", type=int, default=0)
    p.add_argument("--where", default="1=1")
    p.add_argument("--tipo", default="MapServer")
    p.add_argument("--servidor", default="minam")
    p.add_argument("--limite", type=int, default=1000)
    p.add_argument("--salida", default=None)
    p.add_argument("--titulo", default=None)
    a = p.parse_args()

    if a.servicio:
        gj, fuente = de_la_capa(a.servicio, a.capa, a.where, a.tipo, a.servidor, a.limite)
        titulo = a.titulo or f"{a.servicio.split('/')[-1]} · capa {a.capa}"
        sub = f"{a.servicio} · {a.tipo}/{a.capa}"
        salida = a.salida or f"mapa_capa_{a.capa}.html"
    else:
        gj, fuente = de_residuos()
        titulo = a.titulo or "Infraestructura de residuos sólidos del Perú"
        sub = "ServicioRRSS_MINAM · MINAM vía GEOPERÚ"
        salida = a.salida or "mapa_residuos.html"

    n = len(gj["features"])
    if not n:
        raise SystemExit("La consulta no devolvio geometria.")
    html = (PLANTILLA.replace("__GEOJSON__", json.dumps(gj, ensure_ascii=False))
            .replace("__TITULO__", titulo).replace("__SUBTITULO__", sub)
            .replace("__CONTEO__", f"{n} elementos dibujados").replace("__FUENTE__", fuente))
    destino = AQUI / salida
    destino.write_text(html, encoding="utf-8")
    print(f"{salida} escrito · {n} elementos · {destino.stat().st_size//1024} KB")
