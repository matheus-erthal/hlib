from aioresponses import aioresponses

from hlib.llm_tools import (
    TOOLS,
    dispatch_tool_call,
    list_government_portals,
    search_government_portals,
    search_government_datasets,
    get_government_dataset,
    fetch_government_dataset_data,
)


def test_tools_schema_is_json_safe_and_has_expected_names():
    names = {tool["name"] for tool in TOOLS}
    assert names == {
        "list_government_portals",
        "search_government_portals",
        "search_government_datasets",
        "get_government_dataset",
        "fetch_government_dataset_data",
    }
    for tool in TOOLS:
        assert "description" in tool
        assert tool["input_schema"]["type"] == "object"


def test_list_government_portals_returns_plain_dicts():
    records = list_government_portals(country="US")
    assert len(records) == 1
    assert records[0]["id"] == "data_gov_us"
    assert isinstance(records[0]["auth"], dict)  # AuthSpec já serializado


def test_search_government_portals_matches_by_text():
    records = search_government_portals("data.gov.uk")
    assert any(r["id"] == "data_gov_uk" for r in records)


def test_search_government_datasets_returns_json_safe_dict():
    mock_us_resp = {"results": [{"identifier": "us1", "title": "US Dataset"}]}
    with aioresponses() as m:
        m.get("https://api.gsa.gov/technology/datagov/v4/search?q=test&per_page=10", payload=mock_us_resp)
        result = search_government_datasets("test", "data_gov_us")

    assert "error" not in result
    assert result["datasets"][0]["title"] == "US Dataset"
    assert isinstance(result["datasets"][0], dict)


def test_search_government_datasets_invalid_portal_fails_soft():
    result = search_government_datasets("test", "portal_inexistente")
    assert result["datasets"] == []


def test_get_government_dataset_not_found_returns_none_not_exception():
    result = get_government_dataset("id", "portal_inexistente")
    assert result == {"dataset": None}


def test_fetch_government_dataset_data_returns_preview_not_dataframe():
    result = fetch_government_dataset_data("id", "portal_inexistente")
    assert result["preview_rows"] == []
    assert result["total_rows"] == 0
    assert "error" in result["meta"]


def test_dispatch_tool_call_routes_by_name():
    result = dispatch_tool_call("list_government_portals", {"country": "BR"})
    assert all(r["country"] == "BR" for r in result)


def test_dispatch_tool_call_unknown_name_is_error_not_exception():
    result = dispatch_tool_call("does_not_exist", {})
    assert "error" in result
