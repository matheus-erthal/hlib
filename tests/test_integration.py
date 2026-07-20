"""
Testes de integração real — fazem requisições HTTP aos portais.

Executar com: pytest -m live -v
Estes testes validam que os endpoints dos portais ainda estão funcionais.
Podem falhar por indisponibilidade temporária dos portais.

Toda vez que um teste passa, ele grava a resposta real do portal em
tests/cassettes/ e atualiza a tabela de status em README.md. Essas cassettes
são consumidas por tests/test_cassettes.py, que roda por padrão (sem rede).
"""

import pytest

from live_recording import recording, save_cassette, update_readme_status


def _record(cassette_name, calls):
    captured_at = save_cassette(cassette_name, calls)
    update_readme_status(cassette_name, captured_at)


# -- CKAN portals --

@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_us_search():
    """Validate US CKAN portal responds to search."""
    from hlib.data_recovery.portals.usa.portal_data_gov_us import PortalDataGovUS
    portal = PortalDataGovUS()
    with recording() as calls:
        results = await portal.search("health")
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0].title is not None
    _record("data_gov_us_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_us_get_dataset():
    """Validate US portal get_dataset(). A API v4 não tem lookup por ID: o
    portal resolve via um cache local dos itens vistos em search() na mesma
    instância — por isso search() e get_dataset() ficam juntos dentro do
    `recording()` (get_dataset() não faz nenhuma chamada HTTP extra aqui)."""
    from hlib.data_recovery.portals.usa.portal_data_gov_us import PortalDataGovUS
    portal = PortalDataGovUS()
    with recording() as calls:
        results = await portal.search("health")
        assert len(results) > 0
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("data_gov_us_get_dataset", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_uk_search():
    """Validate UK CKAN portal responds to search."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://ckan.publishing.service.gov.uk", source_portal="data.gov.uk")
    with recording() as calls:
        results = await portal.search("transport")
        assert isinstance(results, list)
        assert len(results) > 0
    _record("data_gov_uk_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_uk_get_dataset():
    """Validate UK CKAN portal responds to get_dataset."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://ckan.publishing.service.gov.uk", source_portal="data.gov.uk")
    results = await portal.search("transport")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("data_gov_uk_get_dataset", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_australia_search():
    """Validate Australia CKAN portal responds to search."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://data.gov.au/data", source_portal="data.gov.au")
    with recording() as calls:
        results = await portal.search("environment")
        assert isinstance(results, list)
        assert len(results) > 0
    _record("data_gov_au_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_australia_get_dataset():
    """Validate Australia CKAN portal responds to get_dataset."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://data.gov.au/data", source_portal="data.gov.au")
    results = await portal.search("environment")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("data_gov_au_get_dataset", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_swiss_search():
    """Validate Swiss CKAN portal responds to search."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://opendata.swiss", source_portal="opendata.swiss", localized_fields=True)
    with recording() as calls:
        results = await portal.search("transport")
        assert isinstance(results, list)
        assert len(results) > 0
    _record("opendata_swiss_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_swiss_get_dataset():
    """Validate Swiss CKAN portal responds to get_dataset."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://opendata.swiss", source_portal="opendata.swiss", localized_fields=True)
    results = await portal.search("transport")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("opendata_swiss_get_dataset", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_finland_search():
    """Validate Finland CKAN portal responds to search."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://www.avoindata.fi/data", source_portal="avoindata.fi", keyword_fallback_field="keywords")
    with recording() as calls:
        results = await portal.search("population")
        assert isinstance(results, list)
        assert len(results) > 0
    _record("avoindata_fi_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_finland_get_dataset():
    """Validate Finland CKAN portal responds to get_dataset."""
    from hlib.data_recovery.portals.generic_ckan_portal import CkanPortal
    portal = CkanPortal(base_url="https://www.avoindata.fi/data", source_portal="avoindata.fi", keyword_fallback_field="keywords")
    results = await portal.search("population")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("avoindata_fi_get_dataset", calls)


# -- Custom API portals --

@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_france_search():
    """Validate French udata portal responds to search."""
    from hlib.data_recovery.portals.france.portal_data_gouv_fr import PortalDataGouvFR
    portal = PortalDataGouvFR()
    with recording() as calls:
        results = await portal.search("transport")
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0].source_portal == "data.gouv.fr"
    _record("data_gouv_fr_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_france_get_dataset():
    """Validate French portal returns individual dataset."""
    from hlib.data_recovery.portals.france.portal_data_gouv_fr import PortalDataGouvFR
    portal = PortalDataGouvFR()
    # First search to get a valid ID
    results = await portal.search("transport")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("data_gouv_fr_get_dataset", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_spain_search():
    """Validate Spanish Linked Data portal responds."""
    from hlib.data_recovery.portals.spain.portal_datos_gob_es import PortalDatosGobES
    portal = PortalDatosGobES()
    with recording() as calls:
        results = await portal.search("datos")
        assert isinstance(results, list)
        assert len(results) > 0
    _record("datos_gob_es_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_spain_get_dataset():
    """Validate Spanish Linked Data portal responds to get_dataset."""
    from hlib.data_recovery.portals.spain.portal_datos_gob_es import PortalDatosGobES
    portal = PortalDatosGobES()
    results = await portal.search("datos")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("datos_gob_es_get_dataset", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_singapore_search():
    """Validate Singapore portal responds to search."""
    from hlib.data_recovery.portals.singapore.portal_data_gov_sg import PortalDataGovSG
    portal = PortalDataGovSG()
    with recording() as calls:
        results = await portal.search("population")
        assert isinstance(results, list)
        assert len(results) > 0
    _record("data_gov_sg_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_singapore_get_dataset():
    """Validate Singapore portal responds to get_dataset."""
    from hlib.data_recovery.portals.singapore.portal_data_gov_sg import PortalDataGovSG
    portal = PortalDataGovSG()
    results = await portal.search("population")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("data_gov_sg_get_dataset", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_india_search():
    """Validate India OGDP portal responds to search."""
    from hlib.data_recovery.portals.india.portal_data_gov_in import PortalDataGovIN
    portal = PortalDataGovIN()
    with recording() as calls:
        results = await portal.search("population")
        assert isinstance(results, list)
        assert len(results) > 0
    _record("data_gov_in_search", calls)


@pytest.mark.live
@pytest.mark.asyncio(loop_scope="function")
async def test_integration_india_get_dataset():
    """Validate India OGDP portal responds to get_dataset."""
    from hlib.data_recovery.portals.india.portal_data_gov_in import PortalDataGovIN
    portal = PortalDataGovIN()
    results = await portal.search("population")
    assert len(results) > 0
    with recording() as calls:
        dataset = await portal.get_dataset(results[0].id)
        assert dataset is not None
        assert dataset.id == results[0].id
    _record("data_gov_in_get_dataset", calls)
