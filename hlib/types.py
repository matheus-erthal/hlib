from dataclasses import dataclass, field
from typing import Any, Dict
import pandas as pd


@dataclass
class DataFrameWithMeta:
    df: pd.DataFrame
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Resource:
    id: str
    name: str | None = None
    description: str | None = None
    format: str | None = None
    url: str | None = None
    mimetype: str | None = None
    created: str | None = None
    last_modified: str | None = None
    size_bytes: int | None = None


@dataclass
class Dataset:
    id: str
    title: str | None = None
    description: str | None = None
    resources: list[Resource] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    organization: str | None = None
    license: str | None = None
    spatial_coverage: str | None = None
    temporal_coverage: str | None = None
    source_portal: str | None = None


from enum import Enum, auto

class PortalType(Enum):
    DADOS_GOV_BR = "dados_gov_br"
    DATA_GOV_US = "data_gov_us"
    DATA_GOV_UK = "data_gov_uk"
    OPENDATA_SWISS = "opendata_swiss"
    AVOINDATA_FI = "avoindata_fi"
    DATA_GOV_AU = "data_gov_au"
    DATA_GOUV_FR = "data_gouv_fr"
    DATOS_GOB_ES = "datos_gob_es"
    DATA_GOV_SG = "data_gov_sg"
    DATA_GOV_IN = "data_gov_in"
