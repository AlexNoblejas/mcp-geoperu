"""Evaluación sin el CLI de Claude Code: modo memoria respondido por un modelo en sesión.

El `claude -p` del proyecto original no se pudo usar porque esta máquina no tiene el CLI de
Claude Code instalado. En su lugar se hizo la misma comparación con n=1 por pregunta:

  · modo «memoria»: Claude Opus 5, sin ninguna herramienta, con la MISMA instrucción del curso
    («si no puedes saberlo con certeza, pon valor null: no estimes»). Las respuestas están
    transcritas literalmente en RESPUESTAS_MEMORIA.
  · modo «mcp»: el valor que devuelve este servidor, que es el que verifican las pruebas.

Limitación declarada: n=1 por celda y modelo distinto (Opus 5 en vez de Haiku), así que esto no
reemplaza la corrida de 20 llamadas del proyecto original. Se documenta como tal en informe.md.

    python evaluar_manual.py
"""
import csv
import json
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent

# Respuestas del modo memoria, dadas sin herramientas y sin ver la capa.
# valor=None significa que el modelo declaró no poder saberlo.
RESPUESTAS_MEMORIA = {
    "total_nacional": (None, "No tengo memorizado el conteo de esa capa del MINAM."),
    "depa_piura":     (None, "No conozco el detalle por departamento de esa capa."),
    "depa_ayacucho":  (None, "No conozco el detalle por departamento de esa capa."),
    "depa_lima":      (None, "No conozco el detalle por departamento de esa capa."),
    "depa_amazonas":  (None, "No conozco el detalle por departamento de esa capa."),
    "depa_ica":       (None, "No conozco el detalle por departamento de esa capa."),
    "depa_pasco":     (None, "No conozco el detalle por departamento de esa capa."),
    "tipo_rsa":       (None, "No conozco la distribucion por tipo de esa capa."),
    "tipo_celda":     (None, "No conozco la distribucion por tipo de esa capa."),
    "cerca_lima":     (None, "Requiere calcular distancias sobre la capa; no la tengo."),
}


def valor_mcp(pid):
    """El valor que devuelve el servidor, por la misma ruta que usaria Claude con el MCP."""
    from server import (_fn, buscar_infraestructura, infraestructuras_cercanas,
                        resumen_territorial)
    resumen = _fn(resumen_territorial); buscar = _fn(buscar_infraestructura)
    cercanas = _fn(infraestructuras_cercanas)
    if pid == "total_nacional":
        return resumen()["total"], "resumen_territorial"
    if pid.startswith("depa_"):
        d = pid.removeprefix("depa_")
        return buscar(departamento=d, limite=1)["encontrados"], "buscar_infraestructura"
    if pid == "tipo_rsa":
        return resumen()["por_tipo"].get("RSA", 0), "resumen_territorial"
    if pid == "tipo_celda":
        return resumen()["por_tipo"].get("CELDA TRANSITORIA", 0), "resumen_territorial"
    if pid == "cerca_lima":
        return cercanas(-12.05, -77.04, 150, 1)["encontrados"], "infraestructuras_cercanas"
    raise KeyError(pid)


def calificar(valor, verdad, tolerancia):
    if valor is None:
        return "no sabe"
    return "acierta" if abs(valor - verdad) <= tolerancia else "se equivoca"


if __name__ == "__main__":
    preguntas = list(csv.DictReader(open(AQUI / "preguntas.csv", encoding="utf-8")))
    filas = []
    for q in preguntas:
        verdad, tol = float(q["verdad"]), float(q["tolerancia"])
        v, f = RESPUESTAS_MEMORIA[q["id"]]
        filas.append({"id": q["id"], "modo": "memoria", "verdad": verdad, "valor": v,
                      "fuente": f, "resultado": calificar(v, verdad, tol)})
        v, f = valor_mcp(q["id"])
        filas.append({"id": q["id"], "modo": "mcp", "verdad": verdad, "valor": v,
                      "fuente": f, "resultado": calificar(v, verdad, tol)})

    res = pd.DataFrame(filas)
    res.to_csv(AQUI / "resultados.csv", index=False)
    print(res.pivot(index="id", columns="modo", values="valor").to_string())
    print()
    print(res.groupby("modo").resultado.value_counts().unstack(fill_value=0).to_string())
