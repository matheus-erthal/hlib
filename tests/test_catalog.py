import importlib

import pytest
from aioresponses import aioresponses

from hlib.catalog.loader import load_catalog_records, get_portal_record, list_portals, search_portals
from hlib.catalog.registry import PLATFORM_BUILDERS
from hlib.catalog.schema import validate_records
from hlib import search_data_async, PortalType


def test_catalog_has_no_validation_errors():
    records = load_catalog_records()
    assert validate_records(records) == []


def test_catalog_ids_are_unique():
    records = load_catalog_records()
    ids = [r.id for r in records]
    assert len(ids) == len(set(ids))


def test_catalog_platforms_are_registered():
    records = load_catalog_records()
    for record in records:
        assert record.platform in PLATFORM_BUILDERS, f"platform '{record.platform}' de '{record.id}' sem builder"


def test_custom_portals_resolve_strategy_class():
    records = load_catalog_records()
    for record in records:
        if record.platform != "custom":
            continue
        module_path, _, class_name = record.strategy_class.rpartition(".")
        cls = getattr(importlib.import_module(module_path), class_name)
        assert cls is not None


def test_dynamic_portal_type_matches_catalog_ids():
    records = load_catalog_records()
    for record in records:
        assert PortalType(record.id).value == record.id


def test_get_portal_record_unknown_returns_none():
    assert get_portal_record("portal_que_nao_existe") is None


def test_list_portals_filters_by_country():
    df = list_portals(country="BR")
    assert len(df) >= 1
    assert (df["country"] == "BR").all()


def test_search_portals_matches_by_name_or_id():
    df = search_portals("dados.gov.br")
    assert (df["id"] == "dados_gov_br").any()


@pytest.mark.asyncio
async def test_ckan_platform_works_from_catalog_data_alone(monkeypatch):
    """
    Prova a promessa central do catálogo: um portal CKAN novo, cadastrado só
    como dado (sem nenhuma classe Python nova), funciona via search_data().
    """
    from hlib.catalog import loader as loader_module
    from hlib.catalog.schema import PortalRecord, AuthSpec

    fake_record = PortalRecord(
        id="fake_ckan_portal",
        name="Portal CKAN Fictício",
        country="BR",
        level="state",
        region="SP",
        base_url="https://fake-ckan.example.org",
        platform="ckan",
        source_portal_label="fake-ckan.example.org",
        auth=AuthSpec(),
        status="unverified",
    )

    monkeypatch.setattr(loader_module, "_index", lambda: {"fake_ckan_portal": fake_record})

    mock_response = {
        "success": True,
        "result": {"results": [{"id": "pkg1", "title": "Dataset Fictício"}]},
    }

    with aioresponses() as m:
        m.get("https://fake-ckan.example.org/api/3/action/package_search?rows=0", status=200)
        m.get("https://fake-ckan.example.org/api/3/action/package_search?q=teste&rows=10", payload=mock_response)

        results = await search_data_async("teste", portal="fake_ckan_portal")
        assert len(results) == 1
        assert results[0].title == "Dataset Fictício"
        assert results[0].source_portal == "fake-ckan.example.org"
