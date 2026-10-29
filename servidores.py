"""Registro de servidores ArcGIS REST del Estado peruano.

`confirmado` lo pone `probar_servidores.py`, no la intuición: un servidor entra al registro como
candidato y solo se marca vivo cuando respondió su catálogo. Los que fallan se quedan con
confirmado=False y el MCP los ignora, sin romperse.

    python probar_servidores.py        # prueba todos y reescribe servidores_vivos.json
"""

SERVIDORES = {
    "minam": {
        "entidad": "Ministerio del Ambiente",
        "raiz": "https://geoservidorperu.minam.gob.pe/arcgis/rest/services",
        "confirmado": True,   # verificado: 4,659 capas en 209 servicios
    },
    "sernanp": {
        "entidad": "Servicio Nacional de Áreas Naturales Protegidas",
        "raiz": "https://geo.sernanp.gob.pe/arcgis/rest/services",
        "confirmado": False,
    },
    "ana": {
        "entidad": "Autoridad Nacional del Agua",
        "raiz": "https://snirh.ana.gob.pe/arcgis/rest/services",
        "confirmado": False,
    },
    "midagri": {
        "entidad": "Ministerio de Desarrollo Agrario y Riego",
        "raiz": "https://geomidagri.midagri.gob.pe/arcgis/rest/services",
        "confirmado": False,
    },
    "ign": {
        "entidad": "Instituto Geográfico Nacional",
        "raiz": "https://www.idep.gob.pe/arcgis/rest/services",
        "confirmado": False,
    },
    "senamhi": {
        "entidad": "Servicio Nacional de Meteorología e Hidrología",
        "raiz": "https://geoservicios.senamhi.gob.pe/arcgis/rest/services",
        "confirmado": False,
    },
    "sigrid": {
        "entidad": "CENEPRED · Sistema de Información para la Gestión del Riesgo",
        "raiz": "https://sigrid.cenepred.gob.pe/arcgis/rest/services",
        "confirmado": False,
    },
    "mtc": {
        "entidad": "Ministerio de Transportes y Comunicaciones",
        "raiz": "https://gis.mtc.gob.pe/arcgis/rest/services",
        "confirmado": False,
    },
}


def vivos():
    """Los servidores que se pueden consultar. Lee servidores_vivos.json si existe."""
    import json
    from pathlib import Path
    archivo = Path(__file__).parent / "servidores_vivos.json"
    if archivo.exists():
        estado = json.loads(archivo.read_text(encoding="utf-8"))
        salida = {}
        for k, s in SERVIDORES.items():
            e = estado.get(k, {})
            if e.get("vivo", s["confirmado"]):
                # el probador puede haber hallado la ruta correcta: esa manda
                salida[k] = {**s, "confirmado": True, "raiz": e.get("raiz", s["raiz"])}
        return salida
    return {k: v for k, v in SERVIDORES.items() if v["confirmado"]}
