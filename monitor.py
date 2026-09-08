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


# ==========================================================
# 1. OBTENER TODOS LOS PRODUCTOS
# ==========================================================

response = requests.get(
    BASE_URL,
    headers=HEADERS,
    timeout=20
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

links = set()

for a in soup.select("a[href]"):
    href = a.get("href")

    if not href:
        continue

    url = urljoin(BASE_URL, href)

    if "/productos/" in url:
        links.add(url)


print(f"Productos encontrados: {len(links)}")


# ==========================================================
# 2. REVISAR CADA PRODUCTO Y CADA TALLE
# ==========================================================

stock_actual = {}

for link in sorted(links):

    try:

        response = requests.get(
            link,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        product_soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # --------------------------------------------------
        # Nombre del producto
        # --------------------------------------------------

        titulo = product_soup.select_one("h1")

        if titulo:
            nombre = titulo.get_text(
                " ",
                strip=True
            )
        else:
            nombre = "Producto"

        # --------------------------------------------------
        # BUSCAR TODOS LOS TALLES
        # --------------------------------------------------

        variantes = product_soup.select(
            "a.js-insta-variations.btn-variant"
        )

        if not variantes:
            print(f"Sin variantes: {nombre}")
            continue

        # --------------------------------------------------
        # Revisar cada talle individualmente
        # --------------------------------------------------

        for variante in variantes:

            talle = variante.get("data-option")

            if not talle:
                # Por si algún producto no tiene data-option
                talle = variante.get_text(
                    " ",
                    strip=True
                )

            talle = talle.strip()

            if not talle:
                continue

            clases = variante.get("class", [])

            # --------------------------------------------------
            # STOCK
            # --------------------------------------------------

            disponible = "btn-variant-no-stock" not in clases

            # --------------------------------------------------
            # CLAVE ÚNICA:
            # producto + talle
            # --------------------------------------------------

            clave = f"{nombre}|||{talle}"

            stock_actual[clave] = {
                "nombre": nombre,
                "talle": talle,
                "disponible": disponible,
                "url": link
            }

        print(
            f"{nombre}: "
            f"{len(variantes)} talles revisados"
        )

    except Exception as e:

        print(
            f"ERROR revisando {link}: {e}"
        )


print(
    f"Variantes revisadas: {len(stock_actual)}"
)


# ==========================================================
# 3. CARGAR STOCK ANTERIOR
# ==========================================================

try:

    with open(
        "stock.json",
        "r",
        encoding="utf-8"
    ) as f:

        anterior = json.load(f)

except FileNotFoundError:

    anterior = {}


# ==========================================================
# 4. COMPARAR CADA TALLE
# ==========================================================

avisos = []

for clave, actual in stock_actual.items():

    disponible_actual = actual["disponible"]

    if clave not in anterior:
        # Primera vez que vemos ese talle.
        # No mandamos aviso.
        continue

    disponible_anterior = anterior[clave]["disponible"]

    # ------------------------------------------------------
    # SE AGOTÓ
    # ------------------------------------------------------

    if (
        disponible_anterior is True
        and disponible_actual is False
    ):

        avisos.append(
            f"🔴 SE AGOTÓ\n"
            f"{actual['nombre']}\n"
            f"Talle: {actual['talle']}"
        )

    # ------------------------------------------------------
    # REINGRESÓ
    # ------------------------------------------------------

    elif (
        disponible_anterior is False
        and disponible_actual is True
    ):

        avisos.append(
            f"🟢 REINGRESÓ\n"
            f"{actual['nombre']}\n"
            f"Talle: {actual['talle']}"
        )


# ==========================================================
# 5. GUARDAR ESTADO ACTUAL
# ==========================================================

with open(
    "stock.json",
    "w",
    encoding="utf-8"
) as f:

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

    print(
        "Aviso enviado:"
    )

    print(mensaje)
