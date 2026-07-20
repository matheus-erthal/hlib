import pytest
import aiohttp
from aioresponses import aioresponses
from hlib.data_recovery.adapters.ckan_adapter import CkanAdapter
from hlib.data_recovery.adapters.api_adapter import ApiAdapter
from hlib.data_recovery.portals.portal_data_gov_us import PortalDataGovUS
from hlib.data_recovery.portals.portal_dados_abertos_br import DadosAbertosBR
from hlib.data_recovery.portals.portal_data_gov_uk import PortalDataGovUK
from hlib.data_recovery.portals.portal_data_gov_au import PortalDataGovAU
from hlib.data_recovery.portals.portal_data_gouv_fr import PortalDataGouvFR

# Fixtures for Adapters
@pytest.fixture
def ckan_adapter():
    return CkanAdapter("https://mock-ckan.org")

@pytest.fixture
def api_adapter():
    return ApiAdapter("https://mock-br.gov.br")

# Tests for CkanAdapter
@pytest.mark.asyncio
async def test_ckan_connect_success(ckan_adapter):
    with aioresponses() as m:
        # Mock package_search for connect check
        m.get("https://mock-ckan.org/api/3/action/package_search?rows=0", status=200)

        async with ckan_adapter as ad:
            assert await ad.connect() == True

@pytest.mark.asyncio
async def test_ckan_connect_fail(ckan_adapter):
    with aioresponses() as m:
        m.get("https://mock-ckan.org/api/3/action/package_search?rows=0", status=500)
        async with ckan_adapter as ad:
            assert await ad.connect() == False

@pytest.mark.asyncio
async def test_ckan_search_packages(ckan_adapter):
    mock_response = {
        "success": True,
        "result": {
            "results": [
                {"id": "pkg1", "title": "Test Package 1", "organization": {"title": "Org 1"}},
                {"id": "pkg2", "title": "Test Package 2"}
            ]
        }
    }

    with aioresponses() as m:
        m.get("https://mock-ckan.org/api/3/action/package_search?q=health&rows=10", payload=mock_response)

        async with ckan_adapter as ad:
            results = await ad.search_packages("health")
            assert len(results) == 2
            assert results[0]["id"] == "pkg1"

# Tests for ApiAdapter
@pytest.mark.asyncio
async def test_api_adapter_get(api_adapter):
    mock_response = {"success": True}
    with aioresponses() as m:
        m.get("https://mock-br.gov.br/test", payload=mock_response)
        async with api_adapter as ad:
            resp = await ad.get("https://mock-br.gov.br/test")
            assert resp["success"] == True

# Tests for Portal BR (ApiAdapter) — não tem teste "live"/cassette pois exige api_key própria
@pytest.mark.asyncio
async def test_portal_br_structure():
    portal = DadosAbertosBR(api_key="TEST")

    mock_br_resp = {
        "conjuntosDados": [
            {
                "id": "br_ds_1",
                "title": "Dataset Brasileiro",
                "descricao": "Descricao teste",
                "nomeOrganizacao": "Gov BR",
                "recursos": [{"id": "r1", "formato": "CSV", "url": "http://br.gov/data.csv"}]
            }
        ]
    }

    with aioresponses() as m:
         # connect check (using ApiAdapter base connect which hits base_url)
         m.get("https://dados.gov.br/", status=200)

         # search - specific logic now in Portal
         m.get("https://dados.gov.br/dados/api/publico/conjuntos-dados?isPrivado=false&nomeConjuntoDados=teste&pagina=1&registrosPorPagina=10", payload=mock_br_resp)

         datasets = await portal.search("teste")
         assert len(datasets) == 1
         ds = datasets[0]
         assert ds.title == "Dataset Brasileiro"


# ==========================================
# Tests for get_dataset() (individual fetch)
# ==========================================
# Nota: os testes de estrutura de search()/get_dataset() dos demais portais
# (US, UK, Suíça, Finlândia, Austrália, França, Espanha, Singapura, Índia)
# vivem em tests/test_cassettes.py, usando respostas reais capturadas por
# `pytest -m live` em vez de mocks sintéticos.

@pytest.mark.asyncio
async def test_get_dataset_br():
    portal = DadosAbertosBR(api_key="TEST")
    mock_resp = {
        "id": "br1",
        "title": "BR Single Dataset",
        "descricao": "Descricao",
        "nomeOrganizacao": "Gov BR",
        "recursos": [{"id": "r1", "formato": "CSV", "url": "http://br.gov/data.csv"}],
        "palavrasChave": [],
    }
    with aioresponses() as m:
        m.get("https://dados.gov.br/", status=200)
        m.get("https://dados.gov.br/dados/api/publico/conjuntos-dados/br1", payload=mock_resp)
        ds = await portal.get_dataset("br1")
        assert ds is not None
        assert ds.title == "BR Single Dataset"
        assert ds.source_portal == "dados.gov.br"


@pytest.mark.asyncio
async def test_get_dataset_br_no_key():
    portal = DadosAbertosBR()
    with pytest.raises(ValueError, match="requires an 'api_key'"):
        await portal.get_dataset("br1")


# ==========================================
# Tests for fetch_dataset_data()
# ==========================================
# Estes testam a lógica de parsing (CSV/JSON/PDF/fallback de extensão), não a
# fidelidade a uma resposta específica de portal — por isso continuam sintéticos.

@pytest.mark.asyncio
async def test_fetch_dataset_data_with_csv():
    """Testa fetch_dataset_data com recurso CSV disponível (API v4 do data.gov)."""
    portal = PortalDataGovUS()

    mock_search_resp = {
        "results": [
            {
                "identifier": "us1",
                "title": "US CSV Dataset",
                "description": "desc",
                "organization": {"name": "US Org"},
                "keyword": [],
                "dcat": {
                    "license": "cc-by",
                    "distribution": [
                        {"title": "data.csv", "format": "CSV", "downloadURL": "http://example.com/data.csv"}
                    ],
                },
            }
        ]
    }
    csv_content = b"col1,col2\n1,2\n3,4"

    with aioresponses() as m:
        m.get("https://api.gsa.gov/technology/datagov/v4/search?per_page=100", payload=mock_search_resp)
        m.get("http://example.com/data.csv", body=csv_content, content_type="text/csv")

        result = await portal.fetch_dataset_data("us1")
        assert not result.df.empty
        assert len(result.df) == 2
        assert list(result.df.columns) == ["col1", "col2"]
        assert result.meta["parsed"] is True
        assert result.meta["title"] == "US CSV Dataset"
        assert result.meta["parsed_resource"]["format"] == "CSV"


@pytest.mark.asyncio
async def test_fetch_dataset_data_no_parseable_resource():
    """Testa fetch_dataset_data sem recurso parseável — retorna DataFrame vazio com meta."""
    portal = PortalDataGovUK()

    mock_pkg_resp = {
        "success": True,
        "result": {
            "id": "uk1",
            "title": "UK PDF Dataset",
            "organization": {"title": "UK Org"},
            "resources": [
                {"id": "r1", "name": "report.pdf", "format": "PDF", "url": "http://example.com/report.pdf"}
            ],
            "tags": [{"name": "reports"}],
        }
    }

    with aioresponses() as m:
        m.get("https://ckan.publishing.service.gov.uk/api/3/action/package_show?id=uk1", payload=mock_pkg_resp)

        result = await portal.fetch_dataset_data("uk1")
        assert result.df.empty
        assert result.meta["parsed"] is False
        assert result.meta["title"] == "UK PDF Dataset"
        assert len(result.meta["resources"]) == 1
        assert result.meta["resources"][0]["url"] == "http://example.com/report.pdf"


@pytest.mark.asyncio
async def test_fetch_dataset_data_json_resource():
    """Testa fetch_dataset_data com recurso JSON."""
    portal = PortalDataGouvFR()

    mock_pkg_resp = {
        "id": "fr1",
        "title": "French JSON Dataset",
        "description": "Data in JSON",
        "organization": {"name": "French Org"},
        "tags": [],
        "resources": [
            {"id": "r1", "title": "data.json", "format": "json", "url": "http://example.fr/data.json"}
        ],
    }
    json_content = b'[{"a": 1, "b": 2}, {"a": 3, "b": 4}]'

    with aioresponses() as m:
        m.get("https://www.data.gouv.fr/", status=200)
        m.get("https://www.data.gouv.fr/api/1/datasets/fr1/", payload=mock_pkg_resp)
        m.get("http://example.fr/data.json", body=json_content, content_type="application/json")

        result = await portal.fetch_dataset_data("fr1")
        assert not result.df.empty
        assert len(result.df) == 2
        assert result.meta["parsed"] is True


@pytest.mark.asyncio
async def test_fetch_dataset_data_not_found():
    """Testa fetch_dataset_data quando dataset não existe (API v4 do data.gov)."""
    portal = PortalDataGovUS()

    mock_resp = {"results": []}

    with aioresponses() as m:
        m.get("https://api.gsa.gov/technology/datagov/v4/search?per_page=100", payload=mock_resp)

        result = await portal.fetch_dataset_data("nonexistent")
        assert result.df.empty
        assert result.meta.get("error") == "Dataset not found"


@pytest.mark.asyncio
async def test_fetch_dataset_data_url_extension_fallback():
    """Testa que fetch_dataset_data detecta formato pela extensão da URL quando format está vazio."""
    portal = PortalDataGovAU()

    mock_pkg_resp = {
        "success": True,
        "result": {
            "id": "au1",
            "title": "AU Extensible",
            "organization": {"title": "AU Org"},
            "resources": [
                {"id": "r1", "name": "data", "format": "", "url": "http://example.au/data.csv"}
            ],
            "tags": [],
        }
    }
    csv_content = b"x,y\n10,20"

    with aioresponses() as m:
        m.get("https://data.gov.au/data/api/3/action/package_show?id=au1", payload=mock_pkg_resp)
        m.get("http://example.au/data.csv", body=csv_content, content_type="text/csv")

        result = await portal.fetch_dataset_data("au1")
        assert not result.df.empty
        assert result.meta["parsed"] is True
