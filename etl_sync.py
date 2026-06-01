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

from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
from bs4 import BeautifulSoup


BASE_URL = "https://www.bethpivaimoveis.com.br"
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
    "Cookie": "__goc_session__=jweoqjrhrigxxbyrovilaepllexwxvxq; referer=duckduckgo.com; uniqID=ba2fb475494ebb16a7fd1f062661; _gcl_au=1.1.1360285376.1780145107; _ga_XB744BMNYQ=GS2.1.s1780307246$o4$g1$t1780307932$j29$l0$h1825314546; _ga=GA1.1.2061518206.1780145107; _ga_CH1G1GL48B=GS2.1.s1780307246$o4$g1$t1780307843$j54$l0$h0; _ga_DLYBNQTRG2=GS2.1.s1780307246$o4$g1$t1780307843$j54$l0$h1992902863; _ga_JYD45JQ9Y4=GS2.1.s1780307246$o4$g1$t1780307843$j54$l0$h0; accepted_cookie_policy=true"
}

# HEADERS = {
#     'accept-encoding': "gzip, deflate, br, zstd",
#     'user-agent': "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
#     'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#     'accept-language': "en-US,en;q=0.9",
#     'referer': "https://www.bethpivaimoveis.com.br/",
#     'dnt': "1",
#     'sec-gpc': "1",
#     'connection': "keep-alive",
#     'cookie': "__goc_session__=jweoqjrhrigxxbyrovilaepllexwxvxq; referer=duckduckgo.com; uniqID=ba2fb475494ebb16a7fd1f062661; _gcl_au=1.1.1360285376.1780145107; _ga_XB744BMNYQ=GS2.1.s1780307246$o4$g1$t1780307932$j29$l0$h1825314546; _ga=GA1.1.2061518206.1780145107; _ga_CH1G1GL48B=GS2.1.s1780307246$o4$g1$t1780307843$j54$l0$h0; _ga_DLYBNQTRG2=GS2.1.s1780307246$o4$g1$t1780307843$j54$l0$h1992902863; _ga_JYD45JQ9Y4=GS2.1.s1780307246$o4$g1$t1780307843$j54$l0$h0; accepted_cookie_policy=true",
#     'upgrade-insecure-requests': "1",
#     'sec-fetch-dest': "document",
#     'sec-fetch-mode': "navigate",
#     'sec-fetch-site': "same-origin",
#     'sec-fetch-user': "?1",
#     'priority': "u=0, i",
#     'te': "trailers"
# }

SESSION = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
SESSION.mount('https://', HTTPAdapter(max_retries=retries))
SESSION.headers.update(HEADERS)


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


def get_house(url: str) -> dict[str, str]:
    soup = BeautifulSoup(get_html(url), "html.parser")
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


def main() -> None:
    all_houses = []
    try: 
        for i in range(1, 63):
            html = get_html(f"{START_URL}?pagina={i}" if i > 1 else START_URL)
            links = get_links(html)
            houses = [get_house(link) for link in links]
            all_houses.extend(houses)
            print(f"Found {len(all_houses)} houses so far")
    except Exception as e:
        print(f"Error: {e}")

    df = pd.DataFrame(all_houses)
    df.to_csv(OUTPUT, sep=";", index=False)


if __name__ == "__main__":
    main()
