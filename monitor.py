import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://mayoristathenewclassic.mitiendanube.com/calzados/"

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ==========================================================
# ENVIAR MENSAJE A TELEGRAM
# ==========================================================


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        response = requests.post(
            url, data={"chat_id": CHAT_ID, "text": mensaje}, timeout=20
        )

        if not response.ok:
            print("ERROR ENVIANDO A TELEGRAM:")
            print(response.text)

    except Exception as e:
        print(f"ERROR TELEGRAM: {e}")


# ==========================================================
# 1. OBTENER TODOS LOS PRODUCTOS
# RECORRIENDO TODAS LAS PÁGINAS
# ==========================================================

links = set()
page = 1

while True:
    url_pagina = f"{BASE_URL}?page={page}"

    try:
        response = requests.get(url_pagina, headers=HEADERS, timeout=20)
        response.raise_for_status()

    except Exception as e:
        print(f"Error cargando página {page}: {e}")
        break

    soup = BeautifulSoup(response.text, "html.parser")
    links_encontrados_en_pagina = 0

    for a in soup.select("a[href]"):
        href = a.get("href")

        if not href:
            continue

        url_prod = urljoin(BASE_URL, href)

        if "/productos/" in url_prod:
            if url_prod not in links:
                links.add(url_prod)
                links_encontrados_en_pagina += 1

    print(f"Página {page}: {links_encontrados_en_pagina} productos nuevos")

    if links_encontrados_en_pagina == 0:
        break

    page += 1


print(f"Páginas revisadas: {page}")
print(f"Total de productos encontrados: {len(links)}")


# ==========================================================
# 2. REVISAR CADA PRODUCTO Y CADA TALLE
# ==========================================================

stock_actual = {}


for link in sorted(links):
    try:
        response = requests.get(link, headers=HEADERS, timeout=20)
        response.raise_for_status()

        product_soup = BeautifulSoup(response.text, "html.parser")

        # --------------------------------------------------
        # NOMBRE DEL PRODUCTO
        # --------------------------------------------------

        titulo = product_soup.select_one("h1")

        if titulo:
            nombre = titulo.get_text(" ", strip=True)
        else:
            nombre = "Producto"

        # --------------------------------------------------
        # BUSCAR TODOS LOS TALLES
        # --------------------------------------------------

        variantes = product_soup.select("a.js-insta-variations.btn-variant")

        if not variantes:
            print(f"Sin variantes: {nombre}")
            continue

        # --------------------------------------------------
        # REVISAR CADA TALLE
        # --------------------------------------------------

        for variante in variantes:
            talle = variante.get("data-option")

            if not talle:
                talle = variante.get_text(" ", strip=True)

            talle = talle.strip()

            if not talle:
                continue

            clases = variante.get("class", [])

            # --------------------------------------------------
            # STOCK
            # --------------------------------------------------

            disponible = "btn-variant-no-stock" not in clases

            # --------------------------------------------------
            # CLAVE ÚNICA: PRODUCTO + TALLE
            # --------------------------------------------------

            clave = f"{nombre}|||{talle}"

            stock_actual[clave] = {
                "nombre": nombre,
                "talle": talle,
                "disponible": disponible,
                "url": link,
            }

        print(f"{nombre}: {len(variantes)} talles revisados")

    except Exception as e:
        print(f"ERROR revisando {link}: {e}")


print(f"Variantes revisadas en total: {len(stock_actual)}")


# ==========================================================
# 3. CARGAR STOCK ANTERIOR
# ==========================================================

try:
    with open("stock.json", "r", encoding="utf-8") as f:
        anterior = json.load(f)

except FileNotFoundError:
    anterior = {}


# ==========================================================
# 4. COMPARAR CADA TALLE
# ==========================================================

avisos = []


for clave, actual in stock_actual.items():
    disponible_actual = actual["disponible"]

    # ======================================================
    # NUEVA PUBLICACIÓN O TALLE NUEVO
    # ======================================================
    if clave not in anterior:
        if disponible_actual:  # Notifica si ingresa con stock disponible
            mensaje = (
                f"✨ NUEVO PRODUCTO EN STOCK\n\n"
                f"{actual['nombre']}\n"
                f"Talle: {actual['talle']}\n\n"
                f"{actual['url']}"
            )
            avisos.append(mensaje)
        continue

    disponible_anterior = anterior[clave]["disponible"]

    # ======================================================
    # SE AGOTÓ
    # ======================================================
    if disponible_anterior is True and disponible_actual is False:
        mensaje = (
            f"🔴 SE AGOTÓ\n\n"
            f"{actual['nombre']}\n"
            f"Talle: {actual['talle']}\n\n"
            f"{actual['url']}"
        )
        avisos.append(mensaje)

    # ======================================================
    # REINGRESÓ
    # ======================================================
    elif disponible_anterior is False and disponible_actual is True:
        mensaje = (
            f"🟢 REINGRESÓ\n\n"
            f"{actual['nombre']}\n"
            f"Talle: {actual['talle']}\n\n"
            f"{actual['url']}"
        )
        avisos.append(mensaje)


# ==========================================================
# 5. GUARDAR ESTADO ACTUAL
# ==========================================================

with open("stock.json", "w", encoding="utf-8") as f:
    json.dump(stock_actual, f, ensure_ascii=False, indent=2)


# ==========================================================
# 6. ENVIAR AVISOS
# ==========================================================

print(f"Avisos: {len(avisos)}")


for mensaje in avisos:
    enviar_telegram(mensaje)
    print("Aviso enviado:")
    print(mensaje)
