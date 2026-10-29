"""Prueba cada servidor del registro y escribe servidores_vivos.json con el resultado.

    python probar_servidores.py

Un servidor cuenta como vivo si su catálogo raíz responde JSON de ArcGIS con carpetas o servicios.
"""
import json
from pathlib import Path

import httpx

from servidores import SERVIDORES

AQUI = Path(__file__).parent
estado = {}

# Un ArcGIS Server puede estar montado en varias rutas: se prueban todas antes de descartarlo.
VARIANTES = ["", "/arcgis/rest/services", "/server/rest/services", "/rest/services",
             "/arcgis/rest/services/", "/gisserver/rest/services"]


def probar(raiz):
    """Devuelve (url_que_funciono, datos) o (None, ultimo_error)."""
    base = raiz.split("/arcgis")[0].split("/server/rest")[0].split("/rest/services")[0].rstrip("/")
    candidatas = [raiz] + [base + v for v in VARIANTES if v]
    visto, ultimo = set(), "sin intentos"
    for url in candidatas:
        url = url.rstrip("/")
        if url in visto:
            continue
        visto.add(url)
        try:
            r = httpx.get(url, params={"f": "json"}, timeout=20, follow_redirects=True)
            r.raise_for_status()
            d = r.json()
            if d.get("services") or d.get("folders"):
                return url, d
            ultimo = "respondio sin servicios ni carpetas"
        except Exception as e:
            ultimo = f"{type(e).__name__}"
    return None, ultimo


for clave, s in SERVIDORES.items():
    url, d = probar(s["raiz"])
    if url:
        n_serv, n_carp = len(d.get("services", [])), len(d.get("folders", []))
        estado[clave] = {"vivo": True, "raiz": url, "servicios_raiz": n_serv,
                         "carpetas": n_carp, "version": d.get("currentVersion")}
        extra = "" if url == s["raiz"] else f"  (ruta corregida: {url})"
        print(f"VIVO  {clave:<10} {s['entidad'][:40]:<42} carpetas={n_carp:<3} servicios={n_serv}{extra}")
    else:
        estado[clave] = {"vivo": False, "error": str(d)[:120]}
        print(f"NO    {clave:<10} {s['entidad'][:40]:<42} {d}")

(AQUI / "servidores_vivos.json").write_text(json.dumps(estado, indent=1, ensure_ascii=False),
                                            encoding="utf-8")
n = sum(1 for v in estado.values() if v["vivo"])
print(f"\n{n} de {len(SERVIDORES)} servidores vivos. Escrito en servidores_vivos.json.")
print("Los no vivos quedan en el registro pero el MCP los ignora.")
