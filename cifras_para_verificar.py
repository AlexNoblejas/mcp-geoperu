"""Calcula cada cifra desde la capa y da la URL del geoservidor para comprobarla a mano.

    uv run cifras_para_verificar.py

La URL que imprime es del servicio ArcGIS del MINAM, es decir la fuente primaria: ábranla en el
navegador y confirmen el número antes de escribirlo en la columna «verdad» de preguntas.csv.
"""
from server import CAPA, registros

COMILLA = "%27"


def url_count(where):
    return f"{CAPA}/query?where={where}&returnCountOnly=true&f=json"


filas = registros()
por_depa, por_tipo = {}, {}
for f in filas:
    por_depa[f["departamento"]] = por_depa.get(f["departamento"], 0) + 1
    por_tipo[f["tipo"]] = por_tipo.get(f["tipo"], 0) + 1

print(f"TOTAL NACIONAL: {len(filas)}")
print(f"  verificar en: {url_count('1%3D1')}\n")

print("POR DEPARTAMENTO (top 10)")
for d, n in sorted(por_depa.items(), key=lambda x: -x[1])[:10]:
    patron = "UPPER(DEPARTAMEN)%20LIKE%20" + COMILLA + "%25" + d.replace(" ", "%20") + "%25" + COMILLA
    print(f"  {d:<20} {n:>5}   {url_count(patron)}")

print("\nPOR TIPO")
for t, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
    print(f"  {t[:40]:<42} {n:>5}")

print(f"\nDEPARTAMENTOS DISTINTOS: {len(por_depa)}")
print(f"TIPOS DISTINTOS: {len(por_tipo)}")
print("\nCopien estos numeros a la columna «verdad» de preguntas.csv tras abrir cada URL.")
