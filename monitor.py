
import requests
from bs4 import BeautifulSoup
import json
import os

URL = "https://mayoristathenewclassic.mitiendanube.com/calzados/"

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(URL, headers=HEADERS)
soup = BeautifulSoup(r.text, "html.parser")

productos = {}

cards = soup.select(".js-item-product")

for card in cards:
    nombre = card.select_one(".item-name")
    if not nombre:
        continue

    nombre = nombre.get_text(strip=True)

    texto = card.get_text(" ", strip=True).lower()

    sin_stock = "sin stock" in texto

    productos[nombre] = not sin_stock

try:
    with open("stock.json") as f:
        anterior = json.load(f)
except:
    anterior = {}

avisos = []

for nombre, stock in productos.items():
    if nombre in anterior:
        if anterior[nombre] is False and stock is True:
            avisos.append(f"🟢 Volvió el stock: {nombre}")
    else:
        if stock:
            avisos.append(f"✨ Nuevo producto con stock: {nombre}")

with open("stock.json", "w") as f:
    json.dump(productos, f)

for mensaje in avisos:
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": mensaje}
    )

print("Productos revisados:", len(productos))
print("Avisos:", len(avisos))
