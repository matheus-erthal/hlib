"""
Testes de estrutura por portal (search/get_dataset) usando respostas reais
previamente capturadas (tests/cassettes/*.json), sem tocar a rede.

As cassettes são geradas por `pytest -m live` (tests/test_integration.py).
Se uma cassette ainda não existir, o teste correspondente é pulado (skip)
com instrução de como gerá-la — ver a tabela "Status de Validação ao Vivo"
no README.md para saber quais portais já têm cassette e quando foi capturada.
"""

import pytest
from aioresponses import aioresponses

from hlib.data_recovery.portals.usa.portal_data_gov_us import PortalDataGovUS
from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
from hlib.data_recovery.portals.france.portal_data_gouv_fr import PortalDataGouvFR
from hlib.data_recovery.portals.spain.portal_datos_gob_es import PortalDatosGobES
from hlib.data_recovery.portals.singapore.portal_data_gov_sg import PortalDataGovSG
from hlib.data_recovery.portals.india.portal_data_gov_in import PortalDataGovIN

from live_recording import load_cassette, register_cassette


# ==========================================
# CKAN portals — search() (connect() é chamado)
# ==========================================

@pytest.mark.asyncio
async def test_portal_us_structure():
    # data.gov usa a API v4 (DCAT-US), não CKAN — sem endpoint de connect() separado.
    cassette = load_cassette("data_gov_us_search")
    portal = PortalDataGovUS()
    with aioresponses() as m:
        register_cassette(m, cassette)
        datasets = await portal.search("health")
        assert len(datasets) > 0
        assert datasets[0].title is not None


@pytest.mark.asyncio
async def test_portal_uk_structure():
    cassette = load_cassette("data_gov_uk_search")
    portal = CkanPortal(base_url="https://ckan.publishing.service.gov.uk", source_portal="data.gov.uk")
    with aioresponses() as m:
        m.get("https://ckan.publishing.service.gov.uk/api/3/action/package_search?rows=0", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("transport")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "data.gov.uk"


@pytest.mark.asyncio
async def test_portal_swiss_structure():
    cassette = load_cassette("opendata_swiss_search")
    portal = CkanPortal(base_url="https://opendata.swiss", source_portal="opendata.swiss", localized_fields=True)
    with aioresponses() as m:
        m.get("https://opendata.swiss/api/3/action/package_search?rows=0", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("transport")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "opendata.swiss"


@pytest.mark.asyncio
async def test_portal_finland_structure():
    cassette = load_cassette("avoindata_fi_search")
    portal = CkanPortal(base_url="https://www.avoindata.fi/data", source_portal="avoindata.fi", keyword_fallback_field="keywords")
    with aioresponses() as m:
        m.get("https://www.avoindata.fi/data/api/3/action/package_search?rows=0", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("population")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "avoindata.fi"


@pytest.mark.asyncio
async def test_portal_australia_structure():
    cassette = load_cassette("data_gov_au_search")
    portal = CkanPortal(base_url="https://data.gov.au/data", source_portal="data.gov.au")
    with aioresponses() as m:
        m.get("https://data.gov.au/data/api/3/action/package_search?rows=0", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("environment")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "data.gov.au"


# ==========================================
# API portals — search() (connect() é chamado contra a raiz)
# ==========================================

@pytest.mark.asyncio
async def test_portal_france_structure():
    cassette = load_cassette("data_gouv_fr_search")
    portal = PortalDataGouvFR()
    with aioresponses() as m:
        m.get("https://www.data.gouv.fr/", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("transport")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "data.gouv.fr"


@pytest.mark.asyncio
async def test_portal_spain_structure():
    cassette = load_cassette("datos_gob_es_search")
    portal = PortalDatosGobES()
    with aioresponses() as m:
        m.get("https://datos.gob.es/", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("datos")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "datos.gob.es"


@pytest.mark.asyncio
async def test_portal_singapore_structure():
    cassette = load_cassette("data_gov_sg_search")
    portal = PortalDataGovSG()
    with aioresponses() as m:
        m.get("https://api-production.data.gov.sg/", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("population")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "data.gov.sg"


@pytest.mark.asyncio
async def test_portal_india_structure():
    cassette = load_cassette("data_gov_in_search")
    portal = PortalDataGovIN()
    with aioresponses() as m:
        m.get("https://www.data.gov.in/", status=200)
        register_cassette(m, cassette)
        datasets = await portal.search("population")
        assert len(datasets) > 0
        assert datasets[0].source_portal == "data.gov.in"


# ==========================================
# CKAN portals — get_dataset() (não chama connect())
# ==========================================

@pytest.mark.asyncio
async def test_get_dataset_us():
    # get_dataset() resolve via cache local dos itens vistos em search() na
    # mesma instância — por isso a cassette é o search() que alimentou o
    # cache, e get_dataset() depois não faz nenhuma chamada HTTP extra.
    cassette = load_cassette("data_gov_us_get_dataset")
    portal = PortalDataGovUS()

    with aioresponses() as m:
        register_cassette(m, cassette)
        results = await portal.search("health")
        assert len(results) > 0

        ds = await portal.get_dataset(results[0].id)
        assert ds is not None
        assert ds.id == results[0].id


@pytest.mark.asyncio
async def test_get_dataset_uk():
    cassette = load_cassette("data_gov_uk_get_dataset")
    portal = CkanPortal(base_url="https://ckan.publishing.service.gov.uk", source_portal="data.gov.uk")
    dataset_id = cassette["calls"][0]["params"]["id"]
    with aioresponses() as m:
        register_cassette(m, cassette)
        ds = await portal.get_dataset(dataset_id)
        assert ds is not None
        assert ds.id == dataset_id


@pytest.mark.asyncio
async def test_get_dataset_swiss():
    cassette = load_cassette("opendata_swiss_get_dataset")
    portal = CkanPortal(base_url="https://opendata.swiss", source_portal="opendata.swiss", localized_fields=True)
    dataset_id = cassette["calls"][0]["params"]["id"]
    with aioresponses() as m:
        register_cassette(m, cassette)
        ds = await portal.get_dataset(dataset_id)
        assert ds is not None
        assert ds.id == dataset_id


@pytest.mark.asyncio
async def test_get_dataset_finland():
    cassette = load_cassette("avoindata_fi_get_dataset")
    portal = CkanPortal(base_url="https://www.avoindata.fi/data", source_portal="avoindata.fi", keyword_fallback_field="keywords")
    dataset_id = cassette["calls"][0]["params"]["id"]
    with aioresponses() as m:
        register_cassette(m, cassette)
        ds = await portal.get_dataset(dataset_id)
        assert ds is not None
        assert ds.id == dataset_id


@pytest.mark.asyncio
async def test_get_dataset_australia():
    cassette = load_cassette("data_gov_au_get_dataset")
    portal = CkanPortal(base_url="https://data.gov.au/data", source_portal="data.gov.au")
    dataset_id = cassette["calls"][0]["params"]["id"]
    with aioresponses() as m:
        register_cassette(m, cassette)
        ds = await portal.get_dataset(dataset_id)
        assert ds is not None
        assert ds.id == dataset_id


# ==========================================
# API portals — get_dataset() (connect() é chamado contra a raiz)
# ==========================================

@pytest.mark.asyncio
async def test_get_dataset_france():
    cassette = load_cassette("data_gouv_fr_get_dataset")
    portal = PortalDataGouvFR()
    dataset_id = cassette["calls"][0]["response"]["id"]
    with aioresponses() as m:
        m.get("https://www.data.gouv.fr/", status=200)
        register_cassette(m, cassette)
        ds = await portal.get_dataset(str(dataset_id))
        assert ds is not None
        assert str(ds.id) == str(dataset_id)


@pytest.mark.asyncio
async def test_get_dataset_spain():
    cassette = load_cassette("datos_gob_es_get_dataset")
    portal = PortalDatosGobES()
    with aioresponses() as m:
        m.get("https://datos.gob.es/", status=200)
        register_cassette(m, cassette)
        dataset_id = cassette["calls"][0]["url"].rsplit("/", 1)[-1]
        ds = await portal.get_dataset(dataset_id)
        assert ds is not None


@pytest.mark.asyncio
async def test_get_dataset_singapore():
    cassette = load_cassette("data_gov_sg_get_dataset")
    portal = PortalDataGovSG()
    with aioresponses() as m:
        m.get("https://api-production.data.gov.sg/", status=200)
        register_cassette(m, cassette)
        dataset_id = cassette["calls"][0]["response"]["data"]["datasetId"]
        ds = await portal.get_dataset(dataset_id)
        assert ds is not None
        assert ds.source_portal == "data.gov.sg"


@pytest.mark.asyncio
async def test_get_dataset_india():
    cassette = load_cassette("data_gov_in_get_dataset")
    portal = PortalDataGovIN()
    with aioresponses() as m:
        m.get("https://www.data.gov.in/", status=200)
        register_cassette(m, cassette)
        dataset_id = cassette["calls"][0]["params"]["filters[catalog_uuid]"]
        ds = await portal.get_dataset(dataset_id)
        assert ds is not None
        assert ds.source_portal == "data.gov.in"
