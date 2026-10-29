"""Figura del informe: distribucion territorial de la capa y el efecto del MCP si ya hay resultados."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).parent
c = json.load(open(AQUI / "datos" / "cifras.json", encoding="utf-8"))
hay_res = (AQUI / "resultados.csv").exists()

fig, ejes = plt.subplots(1, 3 if hay_res else 2, figsize=(16 if hay_res else 11, 4.6))

# 1 · por departamento (normalizado)
top = sorted(c["norm"].items(), key=lambda x: x[1])[-12:]
ejes[0].barh([d.title() for d, _ in top], [n for _, n in top], color="#2a6f97")
ejes[0].set_title(f"Infraestructura de residuos por departamento\n(12 primeros de {len(c['norm'])})", fontsize=10)
ejes[0].set_xlabel("registros")
for i, (_, n) in enumerate(top):
    ejes[0].text(n + 0.1, i, str(n), va="center", fontsize=8)

# 2 · por tipo
t = sorted(c["tipo"].items(), key=lambda x: -x[1])
ejes[1].bar([k[:14] for k, _ in t], [v for _, v in t], color="#a44a3f")
ejes[1].set_title(f"Por tipo de infraestructura\n(total nacional: {c['total']})", fontsize=10)
ejes[1].set_ylabel("registros")
ejes[1].tick_params(axis="x", rotation=20, labelsize=8)
for i, (_, v) in enumerate(t):
    ejes[1].text(i, v + 0.6, str(v), ha="center", fontsize=8)

# 3 · aciertos por modo, si evaluar.py ya corrio
if hay_res:
    import pandas as pd
    res = pd.read_csv(AQUI / "resultados.csv")
    tabla = res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    for col, color in (("acierta", "#2d6a4f"), ("se equivoca", "#9d0208"), ("no sabe", "#adb5bd")):
        if col not in tabla:
            tabla[col] = 0
    tabla[["acierta", "se equivoca", "no sabe"]].plot(
        kind="bar", stacked=True, ax=ejes[2], color=["#2d6a4f", "#9d0208", "#adb5bd"])
    ejes[2].set_title(f"Aciertos sobre {len(res.id.unique())} preguntas\npor modo de respuesta", fontsize=10)
    ejes[2].set_xlabel(""); ejes[2].set_ylabel("preguntas")
    ejes[2].tick_params(axis="x", rotation=0)
    ejes[2].legend(fontsize=8)

plt.suptitle("MCP de GEOPERU · infraestructura de residuos solidos del MINAM", fontsize=12, y=1.02)
plt.tight_layout()
plt.savefig(AQUI / "grafico.png", dpi=150, bbox_inches="tight")
print("grafico.png escrito ·", "3 paneles (con resultados)" if hay_res else "2 paneles (sin resultados.csv aun)")
