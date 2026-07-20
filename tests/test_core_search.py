import pytest
from aioresponses import aioresponses
from hlib import search_data, search_data_async, get_dataset, get_dataset_async, fetch_dataset_data, fetch_dataset_data_async, PortalType

@pytest.mark.asyncio
async def test_search_all_aggregates_results_async():
    """Testa busca em uma lista de portais (cada um com sua própria config), agregando resultados."""

    # Mock BR response
    mock_br_resp = {
        "conjuntosDados": [{"id": "br1", "title": "BR Dataset", "nomeOrganizacao": "Org BR"}]
    }
    # Mock US response (API v4, DCAT-US)
    mock_us_resp = {
        "results": [{"identifier": "us1", "title": "US Dataset", "organization": {"name": "Org US"}}]
    }

    with aioresponses() as m:
        # Connect checks
        m.get("https://dados.gov.br/", status=200) # BR Connect

        # Searches
        m.get("https://dados.gov.br/dados/api/publico/conjuntos-dados?isPrivado=false&nomeConjuntoDados=test&pagina=1&registrosPorPagina=10", payload=mock_br_resp)
        m.get("https://api.gsa.gov/technology/datagov/v4/search?q=test&per_page=10", payload=mock_us_resp)

        # A config de cada portal fica isolada dentro do próprio item da lista
        # — a api_key do BR não vaza para o portal dos EUA (nem vice-versa).
        results = await search_data_async("test", [
            {"portal": "dados_gov_br", "api_key": "TEST_KEY"},
            {"portal": "data_gov_us"},
        ])

        assert len(results) == 2
        titles = [d.title for d in results]
        assert "BR Dataset" in titles
        assert "US Dataset" in titles


@pytest.mark.asyncio
async def test_search_list_forbids_top_level_auth_config():
    """Testa que passar **auth_config junto com uma lista de portais levanta ValueError."""
    with pytest.raises(ValueError, match="Quando 'portal' é uma lista"):
        await search_data_async("test", ["data_gov_us", "dados_gov_br"], api_key="TEST_KEY")

def test_search_sync_wrapper():
    """Testa o wrapper síncrono search_data."""
    
    mock_us_resp = {
        "results": [{"identifier": "us1", "title": "US Dataset", "organization": {"name": "Org US"}}]
    }

    with aioresponses() as m:
         m.get("https://api.gsa.gov/technology/datagov/v4/search?q=sync_test&per_page=10", payload=mock_us_resp)

         # search_data (sync) utiliza asyncio.run internamente
         results = search_data("sync_test", PortalType.DATA_GOV_US)
         assert len(results) == 1
         assert results[0].title == "US Dataset"

@pytest.mark.asyncio
async def test_pass_auth_config_async():
    """Testa passagem de credenciais na função async."""
    mock_br_resp = {"conjuntosDados": []}
    
    with aioresponses() as m:
        m.get("https://dados.gov.br/", status=200)
        m.get("https://dados.gov.br/dados/api/publico/conjuntos-dados?isPrivado=false&nomeConjuntoDados=authtest&pagina=1&registrosPorPagina=10", payload=mock_br_resp)
        
        await search_data_async("authtest", PortalType.DADOS_GOV_BR, api_key="MY_KEY")

def test_search_invalid_portal():
    """Testa se busca com portal inválido levanta ValueError."""
    with pytest.raises(ValueError) as excinfo:
        search_data("query", portal="portal_inexistente")
    assert "Invalid portal" in str(excinfo.value)

def test_search_by_string_key():
    """Testa se busca funciona passando portal como string."""
    mock_us_resp = {
        "results": [{"identifier": "us1", "title": "US Dataset"}]
    }
    with aioresponses() as m:
        m.get("https://api.gsa.gov/technology/datagov/v4/search?q=test&per_page=10", payload=mock_us_resp)

        # Passando portal como string 'data_gov_us'
        results = search_data("test", portal="data_gov_us")
        assert len(results) == 1
        assert results[0].title == "US Dataset"

def test_search_br_without_key_raises_error():
    """Testa se busca no portal BR sem carregar api_key levanta ValueError."""
    with pytest.raises(ValueError) as excinfo:
        search_data("educação", portal="dados_gov_br")
    assert "requires an 'api_key'" in str(excinfo.value)

def test_search_fails_silently_on():
    """Testa se com fails_silently=True não levanta erro mesmo sem chave BR."""
    # Não deve levantar erro
    results = search_data("educação", portal="dados_gov_br", fails_silently=True)
    assert results == []

def test_search_fails_silently_off():
    """Testa se mantém comportamento de raise quando fails_silently=False (default)."""
    with pytest.raises(ValueError):
        search_data("educação", portal="dados_gov_br", fails_silently=False)


def test_search_by_string_key_uk():
    """Testa busca no portal UK por string key."""
    mock_uk_resp = {
        "success": True,
        "result": {"results": [{"id": "uk1", "title": "UK Dataset", "organization": {"title": "UK Org"}}]}
    }
    with aioresponses() as m:
        m.get("https://ckan.publishing.service.gov.uk/api/3/action/package_search?rows=0", status=200)
        m.get("https://ckan.publishing.service.gov.uk/api/3/action/package_search?q=test&rows=10", payload=mock_uk_resp)

        results = search_data("test", portal="data_gov_uk")
        assert len(results) == 1
        assert results[0].title == "UK Dataset"
        assert results[0].source_portal == "data.gov.uk"


def test_search_by_string_key_france():
    """Testa busca no portal França por string key."""
    mock_fr_resp = {
        "data": [{"id": "fr1", "title": "French Dataset", "resources": [], "tags": []}]
    }
    with aioresponses() as m:
        m.get("https://www.data.gouv.fr/", status=200)
        m.get("https://www.data.gouv.fr/api/1/datasets/?page_size=10&q=test", payload=mock_fr_resp)

        results = search_data("test", portal="data_gouv_fr")
        assert len(results) == 1
        assert results[0].title == "French Dataset"
        assert results[0].source_portal == "data.gouv.fr"


def test_search_by_string_key_singapore():
    """Testa busca no portal Singapura por string key."""
    mock_sg_resp = {
        "code": 0,
        "data": {"datasets": [{"datasetId": "sg1", "name": "SG Dataset", "managedByAgencyName": "SG Agency"}]}
    }
    with aioresponses() as m:
        m.get("https://api-production.data.gov.sg/", status=200)
        m.get("https://api-production.data.gov.sg/v2/public/api/datasets?page=1&query=test", payload=mock_sg_resp)

        results = search_data("test", portal="data_gov_sg")
        assert len(results) == 1
        assert results[0].title == "SG Dataset"
        assert results[0].source_portal == "data.gov.sg"


# ==========================================
# Tests for get_dataset() via core API
# ==========================================

def test_get_dataset_core_us():
    """Testa get_dataset via core para portal US (API v4, paginação por identifier)."""
    mock_resp = {
        "results": [
            {
                "identifier": "us1",
                "title": "US Dataset Detail",
                "organization": {"name": "US Org"},
            }
        ]
    }
    with aioresponses() as m:
        m.get("https://api.gsa.gov/technology/datagov/v4/search?per_page=100", payload=mock_resp)
        ds = get_dataset("us1", portal="data_gov_us")
        assert ds is not None
        assert ds.title == "US Dataset Detail"


def test_get_dataset_core_france():
    """Testa get_dataset via core para portal França."""
    mock_resp = {
        "id": "fr1",
        "title": "French Detail",
        "description": "FR desc",
        "organization": {"name": "French Org"},
        "tags": [],
        "resources": [],
    }
    with aioresponses() as m:
        m.get("https://www.data.gouv.fr/", status=200)
        m.get("https://www.data.gouv.fr/api/1/datasets/fr1/", payload=mock_resp)
        ds = get_dataset("fr1", portal="data_gouv_fr")
        assert ds is not None
        assert ds.title == "French Detail"
        assert ds.source_portal == "data.gouv.fr"


@pytest.mark.asyncio
async def test_get_dataset_async_singapore():
    """Testa get_dataset_async via core para portal Singapura."""
    mock_resp = {
        "code": 0,
        "data": {
            "datasetId": "d_sg1",
            "name": "SG Detail",
            "format": "CSV",
            "managedBy": "SG Agency",
        }
    }
    with aioresponses() as m:
        m.get("https://api-production.data.gov.sg/", status=200)
        m.get("https://api-production.data.gov.sg/v2/public/api/datasets/d_sg1/metadata", payload=mock_resp)
        ds = await get_dataset_async("d_sg1", portal="data_gov_sg")
        assert ds is not None
        assert ds.title == "SG Detail"


def test_get_dataset_list_raises():
    """Testa que get_dataset com uma lista de portais levanta ValueError."""
    with pytest.raises(ValueError, match="requires a single specific portal"):
        get_dataset("id", portal=["data_gov_us", "dados_gov_br"])


def test_get_dataset_invalid_portal():
    """Testa que get_dataset com portal inválido levanta ValueError."""
    with pytest.raises(ValueError, match="Invalid portal"):
        get_dataset("id", portal="portal_inexistente")


def test_get_dataset_fails_silently():
    """Testa que get_dataset com fails_silently=True retorna None para portal inválido."""
    result = get_dataset("id", portal="portal_inexistente", fails_silently=True)
    assert result is None


# ==========================================
# Tests for fetch_dataset_data() via core API
# ==========================================

def test_fetch_dataset_data_core_csv():
    """Testa fetch_dataset_data via core com recurso CSV (API v4 do data.gov)."""
    mock_resp = {
        "results": [
            {
                "identifier": "us1",
                "title": "US Core CSV",
                "organization": {"name": "Org"},
                "dcat": {
                    "distribution": [
                        {"title": "data.csv", "format": "CSV", "downloadURL": "http://example.com/data.csv"}
                    ]
                },
            }
        ]
    }
    csv_content = b"a,b\n1,2"

    with aioresponses() as m:
        m.get("https://api.gsa.gov/technology/datagov/v4/search?per_page=100", payload=mock_resp)
        m.get("http://example.com/data.csv", body=csv_content, content_type="text/csv")

        result = fetch_dataset_data("us1", portal="data_gov_us")
        assert not result.df.empty
        assert result.meta["parsed"] is True
        assert result.meta["title"] == "US Core CSV"


def test_fetch_dataset_data_list_raises():
    """Testa que fetch_dataset_data com uma lista de portais levanta ValueError."""
    with pytest.raises(ValueError, match="requires a single specific portal"):
        fetch_dataset_data("id", portal=["data_gov_us", "dados_gov_br"])


def test_fetch_dataset_data_fails_silently():
    """Testa que fetch_dataset_data com fails_silently retorna DataFrameWithMeta vazio."""
    result = fetch_dataset_data("id", portal="portal_inexistente", fails_silently=True)
    assert result.df.empty
    assert "error" in result.meta
