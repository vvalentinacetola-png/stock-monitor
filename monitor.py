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

# --------------------------------------------------
# Función para enviar mensaje a Telegram
# --------------------------------------------------

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensaje
        },
        timeout=20
    )


# --------------------------------------------------
# 1. Obtener todos los productos
# --------------------------------------------------

r = requests.get(BASE_URL, headers=HEADERS, timeout=20)
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

links = set()

for a in soup.select("a[href]"):
    href = a.get("href")

    if not href:
        continue

    url = urljoin(BASE_URL, href)

    # Solo productos de la tienda
    if "/productos/" in url:
        links.add(url)


print(f"Productos encontrados: {len(links)}")


# --------------------------------------------------
# 2. Revisar todos los productos y todos los talles
# --------------------------------------------------

stock_actual = {}

for link in links:

    try:
        prod_resp = requests.get(
            link,
            headers=HEADERS,
            timeout=20
        )

        prod_resp.raise_for_status()

        prod_soup = BeautifulSoup(
            prod_resp.text,
            "html.parser"
        )

        # Nombre
        titulo = prod_soup.select_one("h1")

        if titulo:
            nombre = titulo.get_text(
                " ",
                strip=True
            )
        else:
            nombre = "Producto"

        # --------------------------------------------------
        # Buscar variantes
        # --------------------------------------------------

        variantes = prod_soup.select(
            ".js-product-variant-option"
        )

        if not variantes:
            print(f"Sin variantes: {nombre}")
            continue

        for variante in variantes:

            talle = variante.get_text(
                " ",
                strip=True
            )

            if not talle:
                continue

            clases = variante.get("class", [])

            # --------------------------------------------------
            # Detectar si está disponible
            # --------------------------------------------------

            disponible = True

            if "js-disabled" in clases:
                disponible = False

            if "out-of-stock" in clases:
                disponible = False

            if "disabled" in clases:
                disponible = False

            # --------------------------------------------------
            # Guardar cada talle individualmente
            # --------------------------------------------------

            clave = f"{nombre}|||{talle}"

            stock_actual[clave] = {
                "nombre": nombre,
                "talle": talle,
                "disponible": disponible,
                "url": link
            }

    except Exception as e:
        print(f"Error revisando {link}: {e}")


print(f"Variantes revisadas: {len(stock_actual)}")


# --------------------------------------------------
# 3. Cargar stock anterior
# --------------------------------------------------

try:
    with open("stock.json", "r", encoding="utf-8") as f:
        anterior = json.load(f)

except FileNotFoundError:
    anterior = {}


# --------------------------------------------------
# 4. Detectar cambios
# --------------------------------------------------

avisos = []

for clave, actual in stock_actual.items():

    disponible_actual = actual["disponible"]

    if clave in anterior:

        disponible_anterior = anterior[clave]["disponible"]

        # AGOTADO
        if disponible_anterior is True and disponible_actual is False:

            avisos.append(
                f"🔴 SE AGOTÓ\n"
                f"{actual['nombre']}\n"
                f"Talle: {actual['talle']}"
            )

        # REINGRESÓ
        elif disponible_anterior is False and disponible_actual is True:

            avisos.append(
                f"🟢 REINGRESÓ\n"
                f"{actual['nombre']}\n"
                f"Talle: {actual['talle']}"
            )

    else:
        # Primera vez que aparece:
        # NO mandamos aviso para evitar cientos de mensajes
        pass


# --------------------------------------------------
# 5. Guardar estado actual
# --------------------------------------------------

with open("stock.json", "w", encoding="utf-8") as f:
    json.dump(
        stock_actual,
        f,
        ensure_ascii=False,
        indent=2
    )


# --------------------------------------------------
# 6. Enviar avisos
# --------------------------------------------------

print(f"Avisos: {len(avisos)}")

for mensaje in avisos:

    enviar_telegram(mensaje)

    print(mensaje)
