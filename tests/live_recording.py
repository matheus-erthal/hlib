"""
Suporte para testes "live" (tests/test_integration.py): grava as respostas reais
dos portais em tests/cassettes/*.json e atualiza a tabela de status no README.md.

As cassettes gravadas aqui são consumidas por tests/test_cassettes.py, que
reproduz essas respostas via aioresponses sem tocar a rede.
"""

import json
import re
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from yarl import URL

from hlib.data_recovery.interfaces.adapter import DataAdapter

CASSETTE_DIR = Path(__file__).parent / "cassettes"
README_PATH = Path(__file__).parent.parent / "README.md"

LIVE_STATUS_START = "<!-- live-status:start -->"
LIVE_STATUS_END = "<!-- live-status:end -->"


@contextmanager
def recording():
    """
    Intercepta DataAdapter.get (único ponto de busca de JSON usado por todos
    os adapters) e acumula cada chamada (url, params, response) em uma lista,
    sem alterar o comportamento real da chamada.
    """
    calls = []
    original_get = DataAdapter.get

    async def recording_get(self, url, params=None, headers=None):
        result = await original_get(self, url, params=params, headers=headers)
        calls.append({"url": url, "params": params, "response": result})
        return result

    with patch.object(DataAdapter, "get", recording_get):
        yield calls


def save_cassette(name: str, calls: list) -> str:
    """Grava a cassette em disco e retorna a data de captura (ISO)."""
    CASSETTE_DIR.mkdir(exist_ok=True)
    captured_at = date.today().isoformat()
    payload = {"captured_at": captured_at, "calls": calls}
    path = CASSETTE_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return captured_at


def load_cassette(name: str) -> dict:
    """Lê a cassette; pula o teste (skip) se ela ainda não tiver sido gravada."""
    path = CASSETTE_DIR / f"{name}.json"
    if not path.exists():
        pytest.skip(
            f"Nenhuma cassette gravada para '{name}' ainda — "
            f"rode `pytest -m live` para gerar tests/cassettes/{name}.json"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def register_cassette(mock, cassette: dict):
    """Registra no aioresponses cada chamada gravada na cassette."""
    for call in cassette["calls"]:
        url = str(URL(call["url"]).with_query(call["params"])) if call["params"] else call["url"]
        mock.get(url, payload=call["response"])


def update_readme_status(cassette_name: str, captured_at: str):
    """Atualiza a data de validação da linha `cassette_name` na tabela do README."""
    text = README_PATH.read_text(encoding="utf-8")
    start = text.index(LIVE_STATUS_START)
    end = text.index(LIVE_STATUS_END)
    block = text[start:end]

    pattern = re.compile(
        r"^(\|\s*" + re.escape(cassette_name) + r"\s*\|.*\|)[^|\n]*\|[ \t]*$",
        re.MULTILINE,
    )
    new_block, count = pattern.subn(lambda m: f"{m.group(1)} {captured_at} |", block)
    if count == 0:
        raise ValueError(
            f"Linha da cassette '{cassette_name}' não encontrada na tabela de "
            f"status do README.md — adicione uma linha para ela primeiro."
        )

    README_PATH.write_text(text[:start] + new_block + text[end:], encoding="utf-8")
