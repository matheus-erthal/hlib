from enum import Enum

from .loader import load_catalog_records


def _member_name(portal_id: str) -> str:
    return portal_id.upper()


def build_portal_type() -> type:
    records = load_catalog_records()
    members = {_member_name(r.id): r.id for r in records}
    if len(members) != len(records):
        raise ValueError("hlib: dois ids do catálogo colidem no mesmo nome de Enum.")
    return Enum("PortalType", members)


PortalType = build_portal_type()
