import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://mayoristathenewclassic.mitiendanube.com/calzados/"
TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ==========================================================
# TELEGRAM
# ==========================================================

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        r = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": mensaje
            },
            timeout=20
        )

        if not r.ok:
            print("Error Telegram:", r.text)

    except Exception as e:
        print(f"Error Telegram: {e}")

# ==========================================================
# 1. OBTENER TODOS LOS PRODUCTOS
# ==========================================================

links = set()
page = 1

while True:

    url = f"{BASE_URL}?page={page}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"Error página {page}: {e}")
        break

    soup = BeautifulSoup(r.text, "html.parser")

    nuevos = 0

    for a in soup.select("a[href]"):
        href = a.get("href")

        if not href:
            continue

        link = urljoin(BASE_URL, href)

        if "/productos/" in link and link not in links:
            links.add(link)
            nuevos += 1

    print(f"Página {page}: {nuevos} productos nuevos")

    if nuevos == 0:
        break

    page += 1

print(f"Productos encontrados: {len(links)}")

# ==========================================================
# 2. REVISAR PRODUCTOS Y TALLES
# ==========================================================

stock_actual = {}

for link in sorted(links):

    try:

        r = requests.get(link, headers=HEADERS, timeout=20)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        titulo = soup.select_one("h1")
        nombre = titulo.get_text(" ", strip=True) if titulo else "Producto"

        variantes = soup.select("a.js-insta-variations.btn-variant")

        if not variantes:
            print(f"Sin variantes: {nombre}")
            continue

        for variante in variantes:

            talle = (
                variante.get("data-option")
                or variante.get_text(" ", strip=True)
            ).strip()

            if not talle:
                continue

            clases = variante.get("class", [])
            aria_disabled = variante.get("aria-disabled")
            disabled_attr = variante.get("disabled")
            data_stock = variante.get("data-stock")

            disponible = not (
                "btn-variant-no-stock" in clases
                or aria_disabled == "true"
                or disabled_attr is not None
                or data_stock == "0"
            )

            clave = f"{nombre}|||{talle}"

            stock_actual[clave] = {
                "nombre": nombre,
                "talle": talle,
                "disponible": disponible,
                "url": link
            }

            print(
                f"{nombre} | {talle} | "
                f"{'Disponible' if disponible else 'Agotado'}"
            )

    except Exception as e:
        print(f"Error revisando {link}: {e}")

print(f"Talles revisados: {len(stock_actual)}")

# ==========================================================
# 3. CARGAR STOCK ANTERIOR
# ==========================================================

try:
    with open("stock.json", "r", encoding="utf-8") as f:
        anterior = json.load(f)
except FileNotFoundError:
    anterior = {}

# ==========================================================
# 4. COMPARAR CAMBIOS
# ==========================================================

avisos = []

productos_anteriores = {
    k.split("|||")[0]
    for k in anterior
}

productos_avisados = set()

for clave, actual in stock_actual.items():

    nombre = actual["nombre"]

    # Producto nuevo
    if (
        nombre not in productos_anteriores
        and nombre not in productos_avisados
    ):
        avisos.append(
            f"🆕 PRODUCTO NUEVO\n\n"
            f"{nombre}\n\n"
            f"{actual['url']}"
        )
        productos_avisados.add(nombre)

    # Si el talle no existía antes,
    # no lo comparamos todavía.
    if clave not in anterior:
        continue

    antes = anterior[clave]["disponible"]
    ahora = actual["disponible"]

    # Se agotó
    if antes and not ahora:
        avisos.append(
            f"🔴 SE AGOTÓ\n\n"
            f"{nombre}\n"
            f"Talle: {actual['talle']}\n\n"
            f"{actual['url']}"
        )

    # Reingresó
    elif (not antes) and ahora:
        avisos.append(
            f"🟢 REINGRESÓ\n\n"
            f"{nombre}\n"
            f"Talle: {actual['talle']}\n\n"
            f"{actual['url']}"
        )

# ==========================================================
# 5. GUARDAR ESTADO NUEVO
# ==========================================================

with open("stock.json", "w", encoding="utf-8") as f:
    json.dump(
        stock_actual,
        f,
        ensure_ascii=False,
        indent=2
    )

# ==========================================================
# 6. ENVIAR AVISOS
# ==========================================================

print(f"Avisos: {len(avisos)}")

for mensaje in avisos:
    enviar_telegram(mensaje)
    print("Enviado:")
    print(mensaje)
