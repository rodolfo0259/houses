import requests

from etl import START_URL, get_house, get_html, get_links



def test_get_links():
    """
    <a href="/imovel/terreno-leme-132-m/TE0483-ELQL?from=sale" rel="follow" data-testid="btn_details" class="btn btn-details">Detalhes</a>
    <a rel="noopener" aria-label="Enviar mensagem no WhatsApp" href="https://api.whatsapp.com/send?phone=5519991696517&amp;text=Gostaria de receber mais informações sobre Terreno de 132 m² Vila São Jorge - Leme, à venda por R$ 60.000 https://www.bethpivaimoveis.com.br/imovel/terreno-leme-132-m/TE0483-ELQL" target="_blank" class="btn btn-md btn-primary">Contato</a>
    """

    # Should get the first link, and not the second


def main() -> None:
    try:
        links = get_links(get_html(START_URL))
    except requests.HTTPError as e:
        print(f"request failed: {e}")
        return

    print(f"links: {len(links)}")

    if not links:
        return

    print(f"first link: {links[0]}")
    print(get_house(links[0]))


if __name__ == "__main__":
    main()
