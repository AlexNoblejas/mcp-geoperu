"""Mapa estatico de la infraestructura de residuos solidos. python mapa_png.py"""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).parent
f = json.load(open(AQUI / "datos" / "geoperu_rrss.json", encoding="utf-8"))

LIM = AQUI / "datos" / "limites_departamentales.json"
limites = json.load(open(LIM, encoding="utf-8"))["poligonos"] if LIM.exists() else []

COLOR = {"RSA": "#2a6f97", "RSM": "#a44a3f", "RSE": "#5a8f4a", "CELDA TRANSITORIA": "#c9962c"}
ETIQ = {"RSA": "RSA · ámbito municipal", "RSM": "RSM · municipal (otro)",
        "RSE": "RSE · ámbito no municipal", "CELDA TRANSITORIA": "Celda transitoria"}

fig, (ax, bx) = plt.subplots(1, 2, figsize=(14, 8.5), gridspec_kw={"width_ratios": [1.45, 1]})

# contorno departamental, de la capa Limite Departamental del geoservidor
for p in limites:
    xs = [v[0] for v in p["anillo"]]
    ys = [v[1] for v in p["anillo"]]
    ax.fill(xs, ys, facecolor="#eef2f5", edgecolor="#9fb3c0", linewidth=.6, zorder=1)

for tipo, color in COLOR.items():
    pts = [(x["lon"], x["lat"]) for x in f if x["tipo"] == tipo]
    if pts:
        ax.scatter(*zip(*pts), s=95, c=color, edgecolor="white", linewidth=1.1,
                   label=f"{ETIQ[tipo]}  ({len(pts)})", zorder=3, alpha=.92)

ax.set_xlim(-81.6, -68.4); ax.set_ylim(-18.6, 0.2)
ax.set_aspect("equal")
ax.set_xticks([]); ax.set_yticks([])
for lado in ("top", "right", "bottom", "left"):
    ax.spines[lado].set_visible(False)
sub = "contorno: capa Límite Departamental del geoservidor" if limites else "sin contorno"
ax.set_title(f"Infraestructura de residuos sólidos del Perú\n{len(f)} registros · MINAM vía GEOPERÚ",
             fontsize=12.5, pad=10)
ax.text(.5, -.03, sub, transform=ax.transAxes, ha="center", fontsize=7.5, color="#778")
ax.legend(loc="lower left", fontsize=8.5, framealpha=.95)

# anotar el vacio amazonico
ax.annotate("Pucallpa: 1 registro a 20 km,\nel siguiente a 182 km",
            xy=(-74.717, -8.456), xytext=(-72.6, -4.6), fontsize=8, color="#5a3a3a",
            ha="left", arrowprops=dict(arrowstyle="->", color="#8a6a6a", lw=1.1),
            bbox=dict(boxstyle="round,pad=.35", fc="white", ec="#c8b0b0", lw=.7, alpha=.92))

depa = {}
for x in f:
    d = x["departamento"].replace("Á", "A").replace("Í", "I").replace("Ú", "U")
    depa[d] = depa.get(d, 0) + 1
top = sorted(depa.items(), key=lambda x: x[1])
bx.barh([k.title() for k, _ in top], [v for _, v in top], color="#2a6f97", height=.72)
for i, (_, v) in enumerate(top):
    bx.text(v + .12, i, str(v), va="center", fontsize=8)
bx.set_title(f"Por departamento\n{len(depa)} con al menos un registro", fontsize=11, pad=12)
bx.set_xlabel("registros"); bx.grid(axis="x", alpha=.18, linestyle=":")
for s in ("top", "right"): bx.spines[s].set_visible(False)
bx.tick_params(labelsize=8)

plt.tight_layout()
plt.savefig(AQUI / "mapa_residuos.png", dpi=160, bbox_inches="tight", facecolor="white")
print(f"mapa_residuos.png · {len(f)} puntos · {len(depa)} departamentos")
