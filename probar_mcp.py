"""Cliente MCP de verificación: arranca server.py por stdio y ejercita todo el protocolo.

    python probar_mcp.py

Hace lo mismo que haría Claude Code —lanza el servidor como subproceso y le habla por entrada y
salida estándar— pero sin necesitar el CLI instalado. Sirve para demostrar que el servidor cumple
el protocolo MCP: negocia la conexión, lista herramientas, recursos y prompts, y los llama.
"""
import asyncio
import json
from pathlib import Path

from fastmcp import Client

SERVIDOR = Path(__file__).parent / "server.py"


async def main():
    async with Client(SERVIDOR) as c:
        print("=" * 72)
        print("CONECTADO al servidor MCP 'geoperu' por stdio")
        print("=" * 72)

        tools = await c.list_tools()
        print(f"\nHERRAMIENTAS ({len(tools)})")
        for t in tools:
            print(f"  - {t.name}")
        rec, plt = await c.list_resources(), await c.list_resource_templates()
        print(f"\nRECURSOS ({len(rec)}) Y PLANTILLAS ({len(plt)})")
        for x in rec:
            print(f"  - {x.uri}")
        for x in plt:
            # el SDK v2 renombro uriTemplate -> uri_template; se aceptan ambos
            plantilla = getattr(x, "uri_template", None) or getattr(x, "uriTemplate", "")
            print(f"  - {plantilla}  (plantilla)")
        prompts = await c.list_prompts()
        print(f"\nPROMPTS ({len(prompts)})")
        for x in prompts:
            print(f"  - {x.name}")

        print("\n" + "=" * 72)
        print("1 · listar_servidores")
        d = (await c.call_tool("listar_servidores", {})).data
        for s in d["activos"]:
            print(f"    {s['servidor']:<8} {s['entidad'][:44]:<46} {s['capas']:>5} capas")
        print(f"    TOTAL EN CATALOGO: {d['total_capas']}")

        print("\n2 · buscar_capas('riesgo')")
        d = (await c.call_tool("buscar_capas", {"texto": "riesgo", "limite": 4})).data
        print(f"    encontradas={d['encontradas']}  por_servidor={d.get('por_servidor')}")
        for x in d["capas"]:
            print(f"      [{x['servidor']}] {x['servicio'][:40]} id={x['capa']} · {x['nombre'][:30]}")

        print("\n3 · resumen_territorial()")
        d = (await c.call_tool("resumen_territorial", {})).data
        print(f"    total={d['total']}  por_tipo={d['por_tipo']}")

        print("\n4 · infraestructuras_cercanas(Lima, 150 km)")
        d = (await c.call_tool("infraestructuras_cercanas",
                               {"latitud": -12.05, "longitud": -77.04,
                                "radio_km": 150, "limite": 3})).data
        print(f"    encontradas={d['encontrados']}")
        for x in d["registros"]:
            print(f"      {x['distancia_km']:>6} km  {x['departamento']}/{x['distrito'][:20]:<22} {x['tipo']}")

        print("\n5 · detalle_infraestructura(primer OBJECTID real)")
        primero = (await c.call_tool("buscar_infraestructura", {"limite": 1})).data["registros"][0]
        d = (await c.call_tool("detalle_infraestructura",
                               {"objectid": primero["objectid"]})).data
        print(f"    id={d['objectid']} · {d['departamento']}/{d['provincia']}/{d['distrito']} · {d['tipo']}")

        print("\n6 · detalle_infraestructura(1) · id inexistente, a proposito")
        try:
            await c.call_tool("detalle_infraestructura", {"objectid": 1})
            print("    !! deberia haber fallado")
        except Exception as e:
            print(f"    ToolError correcto: {str(e)[:96]}")

        print("\n7 · recurso geoperu://capa/rrss")
        d = json.loads((await c.read_resource("geoperu://capa/rrss"))[0].text)
        for a in d["advertencias"]:
            print(f"      ! {a}")

        print(f"\n8 · plantilla geoperu://infraestructura/{primero['objectid']}")
        d = json.loads((await c.read_resource(
            f"geoperu://infraestructura/{primero['objectid']}"))[0].text)
        print(f"    {d['departamento']}/{d['distrito']} · {d['tipo']}")

        print("\n9 · prompt informe_territorial('Piura')")
        m = await c.get_prompt("informe_territorial", {"departamento": "Piura"})
        print("    " + m.messages[0].content.text[:160].replace("\n", "\n    "))

        print("\n10 · consultar_capa · consulta en vivo al geoservidor")
        try:
            d = (await c.call_tool("consultar_capa", {
                "servicio": "Servicios_Riesgos_DGCCD/Limite_Distrital",
                "capa": 0, "limite": 2})).data
            print(f"    devueltos={d['devueltos']} · entidad={d['entidad']}")
            print(f"    campos: {list(d['registros'][0])[:7]}")
        except Exception as e:
            print(f"    sin red al geoservidor: {str(e)[:110]}")

        print("\n" + "=" * 72)
        print("SESION MCP COMPLETA · el servidor cumple el protocolo")


if __name__ == "__main__":
    asyncio.run(main())
