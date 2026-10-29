"""El contrato del servidor de GEOPERÚ: ocho pruebas, equivalentes a las ocho del BCRP.

    uv run pytest -q

Llaman al servidor en memoria, igual que lo haría Claude Code, y piden datos reales al
geoservidor del MINAM. La primera baja la capa a datos/ y las siguientes usan esa copia.
"""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from server import mcp, registros


async def _con_cliente(f):
    async with Client(mcp) as c:
        return await f(c)


def llamar(herramienta, **args):
    return asyncio.run(_con_cliente(lambda c: c.call_tool(herramienta, args))).data


# 1 · equivale a test_buscar_encuentra_el_ipc
def test_buscar_encuentra_lima():
    r = llamar("buscar_infraestructura", departamento="lima", limite=5)
    assert r["encontrados"] > 0, "no hay registros de Lima en la capa"
    assert {"objectid", "departamento", "provincia", "distrito", "tipo"} <= r["registros"][0].keys()
    assert "LIMA" in r["registros"][0]["departamento"]


# 2 · equivale a test_cuatro_herramientas_como_minimo
def test_cuatro_herramientas_como_minimo():
    nombres = {t.name for t in asyncio.run(_con_cliente(lambda c: c.list_tools()))}
    assert {"buscar_infraestructura", "resumen_territorial", "detalle_infraestructura"} <= nombres
    assert len(nombres) >= 4, "falta su herramienta propia"


# 3 · equivale a test_serie_mensual: la consulta trae datos y cita su fuente
def test_consulta_trae_datos_y_fuente():
    r = llamar("buscar_infraestructura", limite=10)
    assert len(r["registros"]) == 10
    assert r["encontrados"] == len(registros())
    assert r["fuente"].startswith("https://geoservidorperu.minam.gob.pe")


# 4 · equivale a test_serie_diaria: un filtro más fino devuelve un subconjunto coherente
def test_filtro_por_tipo_es_subconjunto():
    todo = llamar("resumen_territorial")
    tipo = max(todo["por_tipo"], key=todo["por_tipo"].get)
    r = llamar("buscar_infraestructura", tipo=tipo, limite=100)
    assert 0 < r["encontrados"] <= todo["total"]
    assert all(tipo.lower() in x["tipo"].lower() for x in r["registros"])


# 5 · equivale a test_resumen_sin_cuentas_a_mano
def test_resumen_sin_cuentas_a_mano():
    r = llamar("resumen_territorial")
    assert r["total"] == sum(r["por_tipo"].values()) == sum(r["por_departamento"].values())
    assert r["total"] == len(registros())
    assert {"por_tipo", "por_departamento", "por_provincia", "top_departamentos"} <= r.keys()
    assert r["top_departamentos"][0][1] >= r["top_departamentos"][-1][1]


# 6 · equivale a test_codigo_inexistente_da_un_error_claro
def test_objectid_inexistente_da_un_error_claro():
    with pytest.raises(ToolError, match="999999"):
        llamar("detalle_infraestructura", objectid=999999)


# 7 · equivale a test_un_recurso
def test_un_recurso():
    async def contar(c):
        return len(await c.list_resources()) + len(await c.list_resource_templates())
    assert asyncio.run(_con_cliente(contar)) >= 1


# 8 · equivale a test_un_prompt
def test_un_prompt():
    assert len(asyncio.run(_con_cliente(lambda c: c.list_prompts()))) >= 1


# extra · la herramienta propia de proximidad, que el proyecto del BCRP no tiene
def test_cercanas_desde_lima_y_fuera_del_peru():
    r = llamar("infraestructuras_cercanas", latitud=-12.05, longitud=-77.04, radio_km=150)
    assert r["encontrados"] >= 1
    assert r["registros"] == sorted(r["registros"], key=lambda x: x["distancia_km"])
    with pytest.raises(ToolError, match="fuera del Perú"):
        llamar("infraestructuras_cercanas", latitud=40.7, longitud=-74.0)


# extra · regresion: "ica" no debe arrastrar HUANCAVELICA (bug que detecto la evaluacion)
def test_nombre_exacto_no_arrastra_subcadenas():
    ica = llamar("buscar_infraestructura", departamento="ica", limite=100)
    assert all(x["departamento"] == "ICA" for x in ica["registros"])
    huanca = llamar("buscar_infraestructura", departamento="huancavelica", limite=100)
    assert all(x["departamento"] == "HUANCAVELICA" for x in huanca["registros"])
    assert ica["encontrados"] + huanca["encontrados"] <= llamar("resumen_territorial")["total"]
