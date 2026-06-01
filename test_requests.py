import asyncio
import importlib

import pytest
from bs4 import BeautifulSoup


@pytest.fixture
def etl():
    try:
        return importlib.import_module("etl")
    except ImportError as e:
        pytest.fail(f"Could not import etl.py: {e}")


def test_clean(etl):
    assert etl.clean("  Casa   com\n3 quartos  ") == "Casa com 3 quartos"


def test_get_id(etl):
    url = "https://www.bethpivaimoveis.com.br/imovel/casa-leme/CA1234-ELQL?from=sale"

    assert etl.get_id(url) == "CA1234-ELQL"


def test_get_links(etl):
    html = """
    <a class="btn btn-details" href="/imovel/terreno-leme-132-m/TE0483-ELQL?from=sale">Detalhes</a>
    <a class="btn btn-details" href="/imovel/terreno-leme-132-m/TE0483-ELQL?from=sale">Detalhes</a>
    <a href="https://api.whatsapp.com/send?phone=5519991696517">Contato</a>
    <a class="btn btn-details" href="/imovel/casa-leme/CA1234-ELQL?from=sale">Detalhes</a>
    """

    assert etl.get_links(html) == [
        "https://www.bethpivaimoveis.com.br/imovel/terreno-leme-132-m/TE0483-ELQL?from=sale",
        "https://www.bethpivaimoveis.com.br/imovel/casa-leme/CA1234-ELQL?from=sale",
    ]


def test_get_text(etl):
    soup = BeautifulSoup('<h1 class="first-line"> Casa   em Leme </h1>', "html.parser")

    assert etl.get_text(soup, ".first-line") == "Casa em Leme"
    assert etl.get_text(soup, ".missing") == ""


def test_get_breadcrumb(etl):
    html = """
    <div class="breadcrumb">
        <ol>
            <li>Home</li>
            <li>Imóveis</li>
            <li>À venda</li>
            <li>Casa</li>
            <li>Leme</li>
            <li>Jardim Ana Lúcia</li>
        </ol>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    assert etl.get_breadcrumb(soup) == ("Jardim Ana Lúcia", "Leme")


def test_get_house(etl, monkeypatch):
    html = """
    <h1 class="first-line">Casa com 3 dormitórios</h1>
    <span class="usable_floor_area">118 m² Área construída</span>
    <span class="gross_floor_area">151 m² Área do terreno</span>
    <span class="sale-price">R$ 250.000,00</span>
    <span class="meter-price">R$ 2.118/m²</span>
    <span class="bedrooms">3 Quartos</span>
    <span class="bathrooms">2 Banheiros</span>
    <div class="breadcrumb">
        <ol>
            <li>Home</li>
            <li>Imóveis</li>
            <li>À venda</li>
            <li>Casa</li>
            <li>Leme</li>
            <li>Jardim Ana Lúcia</li>
        </ol>
    </div>
    """

    async def fake_get_html_async(url, session):
        return html

    monkeypatch.setattr(etl, "get_html_async", fake_get_html_async)

    house = asyncio.run(
        etl.get_house(
            "https://www.bethpivaimoveis.com.br/imovel/casa-leme/CA1234-ELQL?from=sale",
            None,
        )
    )

    assert house == {
        "id": "CA1234-ELQL",
        "title": "Casa com 3 dormitórios",
        "built_area": "118 m² Área construída",
        "total_area": "151 m² Área do terreno",
        "total_price": "R$ 250.000,00",
        "meter_price": "R$ 2.118/m²",
        "general_info": "3 Quartos - 2 Banheiros",
        "address": "Jardim Ana Lúcia",
        "city": "Leme",
        "url": "https://www.bethpivaimoveis.com.br/imovel/casa-leme/CA1234-ELQL?from=sale",
    }
