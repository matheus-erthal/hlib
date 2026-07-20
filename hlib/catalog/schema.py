from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AuthSpec:
    required: bool = False
    type: str = "none"  # "none" | "header" | "query_param"
    header_name: Optional[str] = None
    query_param_name: Optional[str] = None
    env_var_hint: Optional[str] = None


@dataclass(frozen=True)
class PortalRecord:
    id: str
    name: str
    country: str
    level: str  # "national" | "state" | "municipal"
    base_url: str
    platform: str
    source_portal_label: str
    auth: AuthSpec
    status: str = "unverified"
    region: Optional[str] = None
    municipality: Optional[str] = None
    strategy_class: Optional[str] = None
    platform_config: dict = field(default_factory=dict)
    aliases: list = field(default_factory=list)
    notes: Optional[str] = None
    last_verified_at: Optional[str] = None
    maintainer: Optional[str] = None


def validate_records(records) -> list:
    """Retorna lista de mensagens de erro (vazia se o catálogo for válido)."""
    errors = []
    seen_ids = set()
    for r in records:
        if r.id in seen_ids:
            errors.append(f"id duplicado: '{r.id}'")
        seen_ids.add(r.id)
        for alias in r.aliases:
            if alias in seen_ids:
                errors.append(f"'{r.id}': alias '{alias}' colide com outro id/alias já usado")
            seen_ids.add(alias)
        if r.platform == "custom" and not r.strategy_class:
            errors.append(f"'{r.id}': platform=custom exige strategy_class")
        if r.level != "national" and not r.region:
            errors.append(f"'{r.id}': level='{r.level}' exige 'region'")
        if r.level == "municipal" and not r.municipality:
            errors.append(f"'{r.id}': level='municipal' exige 'municipality'")
    return errors
