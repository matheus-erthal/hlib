import json
import difflib
import importlib.resources
from functools import lru_cache

import pandas as pd

from .schema import PortalRecord, AuthSpec, validate_records


def _record_from_raw(raw: dict) -> PortalRecord:
    raw = dict(raw)
    raw["auth"] = AuthSpec(**raw["auth"])
    return PortalRecord(**raw)


@lru_cache(maxsize=1)
def load_catalog_records() -> tuple:
    raw = json.loads(
        importlib.resources.files("hlib.catalog").joinpath("portals.json").read_text(encoding="utf-8")
    )
    records = tuple(_record_from_raw(r) for r in raw)
    errors = validate_records(records)
    if errors:
        raise ValueError("hlib: catálogo de portais inválido:\n" + "\n".join(errors))
    return records


@lru_cache(maxsize=1)
def load_catalog_df() -> pd.DataFrame:
    """DataFrame com uma linha por portal — usado por list_portals()/search_portals()."""
    return pd.DataFrame([r.__dict__ for r in load_catalog_records()])


@lru_cache(maxsize=1)
def _index() -> dict:
    idx = {}
    for r in load_catalog_records():
        idx[r.id] = r
        for alias in r.aliases:
            idx[alias] = r
    return idx


def get_portal_record(key: str):
    return _index().get(key.lower())


def suggest_similar(key: str, n: int = 3) -> list:
    return difflib.get_close_matches(key.lower(), _index().keys(), n=n, cutoff=0.5)


def list_portals(country: str = None, platform: str = None, level: str = None, status: str = None) -> pd.DataFrame:
    df = load_catalog_df()
    if country:
        df = df[df["country"] == country]
    if platform:
        df = df[df["platform"] == platform]
    if level:
        df = df[df["level"] == level]
    if status:
        df = df[df["status"] == status]
    return df.reset_index(drop=True)


def search_portals(text: str) -> pd.DataFrame:
    df = load_catalog_df()
    mask = df["name"].str.contains(text, case=False, na=False) | df["id"].str.contains(text, case=False, na=False)
    return df[mask].reset_index(drop=True)
