"""
Extract info from
https://www.bethpivaimoveis.com.br/

Transform it into a CSV with columns:
title
built_area
total_area
total_price
meter_price
general_info
address
city
url
photos_link (future TODO)

Load this all of this into a csv file
"""

from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
from bs4 import BeautifulSoup

import aiohttp
import asyncio


BASE_URL = "https://www.bethpivaimoveis.com.br"
TOTAL_PAGES = 63
START_URL = f"{BASE_URL}/imoveis/a-venda"
OUTPUT = "houses.csv"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": BASE_URL,
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "TE": "Trailers",
    "Accept-Encoding": "gzip, deflate, br, zstd",
}

SESSION = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
SESSION.mount('https://', HTTPAdapter(max_retries=retries))
SESSION.headers.update(HEADERS)

async def get_html_async(url: str, session: aiohttp.ClientSession) -> str:
    print(f"Processing {url}")
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


def get_html(url: str):
    print(f"Processing {url}")
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    return response.text

def clean(text: str) -> str:
    return " ".join(text.split())


def get_id(url: str) -> str:
    path = urlparse(url).path
    return path.rstrip("/").split("/")[-1]


def get_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.select('a.btn-details[href*="/imovel/"]'):
        href = a.get("href")
        if not href:
            continue

        url = urljoin(BASE_URL, href)
        if url not in links:
            links.append(url)

    return links


def get_text(soup: BeautifulSoup, selector: str) -> str:
    item = soup.select_one(selector)
    if not item:
        return ""

    return clean(item.get_text(" ", strip=True))


def get_breadcrumb(soup: BeautifulSoup) -> tuple[str, str]:
    items = [clean(item.get_text(" ", strip=True)) for item in soup.select(".breadcrumb ol li")]
    items = [item for item in items if item]

    city = items[4] if len(items) > 4 else ""
    neighborhood = items[5] if len(items) > 5 else ""

    return neighborhood, city


async def get_house(url: str, session: aiohttp.ClientSession) -> dict[str, str]:
    html = await get_html_async(url, session)
    soup = BeautifulSoup(html, "html.parser")
    neighborhood, city = get_breadcrumb(soup)

    return {
        "id": get_id(url),
        "title": get_text(soup, ".first-line"),
        "built_area": get_text(soup, ".usable_floor_area"),
        "total_area": get_text(soup, ".gross_floor_area"),
        "total_price": get_text(soup, ".sale-price"),
        "meter_price": get_text(soup, ".meter-price"),
        "general_info":  get_text(soup, ".bedrooms") + ' - ' + get_text(soup, ".bathrooms"),
        "address": neighborhood,
        "city": city,
        "url": url,
        # "photos_link": "",
    }

async def run() -> list[dict[str, str]]:
    timeout = aiohttp.ClientTimeout(total=300)
    connector = aiohttp.TCPConnector(limit=100)

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout, connector=connector) as session:
        tasks = []
        for page in range(1, TOTAL_PAGES):
            tasks.append(get_html_async(f"{START_URL}?pagina={page}" if page > 1 else START_URL, session))
        
        htmls = await asyncio.gather(*tasks)
        
        links = []
        for html in htmls:
            links.extend(get_links(html))

        tasks_links = []
        for link in links:
            tasks_links.append(get_house(link, session))


        houses = await asyncio.gather(*tasks_links)
        return list(houses)



def main() -> None:
    all_houses = []
    try: 
        all_houses = asyncio.run(run())
    except Exception as e:
        print(f"Error: {e}")

    df = pd.DataFrame(all_houses)
    df.to_csv(OUTPUT, sep=";", index=False)


if __name__ == "__main__":
    main()
