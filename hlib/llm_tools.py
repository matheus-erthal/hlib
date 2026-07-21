"""
Camada opcional de integração com function calling de LLMs (Anthropic, OpenAI, etc).

Não é importado por `hlib/__init__.py` e não altera nenhuma função existente —
quem só quer usar `search_data`/`get_dataset`/`fetch_dataset_data` diretamente
nunca precisa saber que este módulo existe. Ele expõe as mesmas operações como
schemas de tool (dicts JSON-serializáveis) e wrappers cujo retorno é sempre
JSON-safe (dataclasses -> dict, DataFrame -> preview tabular), já que um
DataFrame ou uma dataclass não podem ser devolvidos direto como resultado de
tool call.

Uso típico com a API da Anthropic:

    from hlib.llm_tools import TOOLS, dispatch_tool_call

    response = client.messages.create(
        model="claude-...",
        tools=TOOLS,
        messages=[...],
    )
    for block in response.content:
        if block.type == "tool_use":
            result = dispatch_tool_call(block.name, block.input)
"""

import dataclasses
from typing import Any

from .catalog.loader import list_portals, search_portals
from .core import search_data, get_dataset, fetch_dataset_data

DEFAULT_MAX_ROWS = 20

TOOLS = [
    {
        "name": "list_government_portals",
        "description": (
            "Lista os portais de dados governamentais abertos suportados, "
            "opcionalmente filtrando por país, plataforma ou nível "
            "(national/state/municipal). Use para descobrir a chave de "
            "portal (`portal`) a passar nas demais tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "country": {"type": "string", "description": "Código do país, ex: 'BR', 'US'."},
                "platform": {"type": "string", "description": "Plataforma do portal, ex: 'ckan', 'custom'."},
                "level": {"type": "string", "enum": ["national", "state", "municipal"]},
            },
        },
    },
    {
        "name": "search_government_portals",
        "description": "Busca portais de dados governamentais por nome ou id (texto livre).",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Termo de busca sobre nome/id do portal."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "search_government_datasets",
        "description": (
            "Busca datasets por texto em um portal de dados abertos governamentais "
            "(ou em vários simultaneamente)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca."},
                "portal": {
                    "oneOf": [
                        {"type": "string", "description": "Chave de um único portal, ex: 'data_gov_us'."},
                        {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Chaves de múltiplos portais para buscar em paralelo.",
                        },
                    ]
                },
                "api_key": {
                    "type": "string",
                    "description": (
                        "Chave de API do portal, se exigida (ex: dados.gov.br). "
                        "Só válida quando 'portal' é uma string única."
                    ),
                },
            },
            "required": ["query", "portal"],
        },
    },
    {
        "name": "get_government_dataset",
        "description": "Recupera os metadados completos de um dataset específico pelo seu ID em um portal.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string"},
                "portal": {"type": "string", "description": "Chave de um único portal, ex: 'data_gov_uk'."},
                "api_key": {"type": "string", "description": "Chave de API do portal, se exigida."},
            },
            "required": ["dataset_id", "portal"],
        },
    },
    {
        "name": "fetch_government_dataset_data",
        "description": (
            "Busca um dataset e, se houver um recurso parseável (CSV, TSV, XLS, XLSX, JSON), "
            "retorna uma prévia tabular dos dados (não o arquivo inteiro)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string"},
                "portal": {"type": "string", "description": "Chave de um único portal, ex: 'data_gov_au'."},
                "api_key": {"type": "string", "description": "Chave de API do portal, se exigida."},
                "max_rows": {
                    "type": "integer",
                    "description": f"Máximo de linhas na prévia retornada (padrão {DEFAULT_MAX_ROWS}).",
                },
            },
            "required": ["dataset_id", "portal"],
        },
    },
]


def _dataset_to_dict(dataset) -> dict | None:
    return dataclasses.asdict(dataset) if dataset is not None else None


def _portal_records_to_dicts(df) -> list[dict]:
    records = df.to_dict(orient="records")
    for record in records:
        auth = record.get("auth")
        if dataclasses.is_dataclass(auth):
            record["auth"] = dataclasses.asdict(auth)
    return records


def list_government_portals(country: str = None, platform: str = None, level: str = None) -> list[dict]:
    return _portal_records_to_dicts(list_portals(country=country, platform=platform, level=level))


def search_government_portals(text: str) -> list[dict]:
    return _portal_records_to_dicts(search_portals(text))


def search_government_datasets(query: str, portal, api_key: str = None) -> dict:
    auth_config = {"api_key": api_key} if api_key else {}
    try:
        datasets = search_data(query, portal, fails_silently=True, **auth_config)
        return {"datasets": [_dataset_to_dict(d) for d in datasets]}
    except Exception as e:
        return {"error": str(e)}


def get_government_dataset(dataset_id: str, portal: str, api_key: str = None) -> dict:
    auth_config = {"api_key": api_key} if api_key else {}
    try:
        dataset = get_dataset(dataset_id, portal, fails_silently=True, **auth_config)
        return {"dataset": _dataset_to_dict(dataset)}
    except Exception as e:
        return {"error": str(e)}


def fetch_government_dataset_data(
    dataset_id: str, portal: str, api_key: str = None, max_rows: int = DEFAULT_MAX_ROWS
) -> dict:
    auth_config = {"api_key": api_key} if api_key else {}
    try:
        result = fetch_dataset_data(dataset_id, portal, fails_silently=True, **auth_config)
    except Exception as e:
        return {"error": str(e)}

    if result.df.empty:
        return {"preview_rows": [], "total_rows": 0, "columns": [], "meta": result.meta}

    return {
        "preview_rows": result.df.head(max_rows).to_dict(orient="records"),
        "total_rows": len(result.df),
        "columns": list(result.df.columns),
        "meta": result.meta,
    }


_DISPATCH = {
    "list_government_portals": list_government_portals,
    "search_government_portals": search_government_portals,
    "search_government_datasets": search_government_datasets,
    "get_government_dataset": get_government_dataset,
    "fetch_government_dataset_data": fetch_government_dataset_data,
}


def dispatch_tool_call(name: str, arguments: dict) -> Any:
    """
    Roteia uma chamada de tool (nome + argumentos, no formato que Anthropic/OpenAI
    function calling entregam) para a função correspondente. Nunca lança exceção —
    nomes desconhecidos ou erros internos voltam como `{"error": ...}`.
    """
    handler = _DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: '{name}'. Available tools: {list(_DISPATCH)}"}
    try:
        return handler(**(arguments or {}))
    except Exception as e:
        return {"error": str(e)}
