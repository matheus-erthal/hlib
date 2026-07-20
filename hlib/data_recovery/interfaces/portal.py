from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from ...types import Dataset, DataFrameWithMeta
import pandas as pd

PARSEABLE_FORMATS = {"csv", "tsv", "xls", "xlsx", "json"}


class Portal(ABC):
    """
    Classe base para portais de dados específicos (e.g. Dados.gov.br, Data.gov).
    Gerencia a tradução entre o modelo de dados do Hipólita e a implementação específica do adaptador.
    """

    def __init__(self, **config):
        self.config = config

    @abstractmethod
    async def search(self, query: str) -> List[Dataset]:
        """
        Busca datasets no portal padronizando a saída para o modelo Dataset do Hipólita.
        """
        pass

    @abstractmethod
    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """
        Obtém dataset detalhado pelo ID.
        """
        pass

    async def fetch_dataset_data(self, dataset_id: str) -> DataFrameWithMeta:
        """
        Busca um dataset e tenta baixar o primeiro recurso parseável como DataFrame.
        Se não houver recurso parseável, retorna DataFrame vazio com metadados e links.
        """
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            return DataFrameWithMeta(df=pd.DataFrame(), meta={"error": "Dataset not found"})

        meta = {
            "id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
            "tags": dataset.tags,
            "organization": dataset.organization,
            "license": dataset.license,
            "source_portal": dataset.source_portal,
            "resources": [
                {"id": r.id, "name": r.name, "format": r.format, "url": r.url}
                for r in dataset.resources
            ],
        }

        parseable_resource = self._find_parseable_resource(dataset)
        if not parseable_resource or not parseable_resource.url:
            meta["parsed"] = False
            return DataFrameWithMeta(df=pd.DataFrame(), meta=meta)

        meta["parsed"] = True
        meta["parsed_resource"] = {
            "id": parseable_resource.id,
            "name": parseable_resource.name,
            "format": parseable_resource.format,
            "url": parseable_resource.url,
        }

        async with self.adapter as ad:
            df = await ad.fetch_resource(parseable_resource.url)

        return DataFrameWithMeta(df=df, meta=meta)

    @staticmethod
    def _find_parseable_resource(dataset: Dataset):
        """Encontra o primeiro recurso com formato parseável por pandas."""
        for resource in dataset.resources:
            fmt = (resource.format or "").lower().strip().lstrip(".")
            if fmt in PARSEABLE_FORMATS:
                return resource
            if resource.url:
                ext = resource.url.rsplit(".", 1)[-1].lower().split("?")[0]
                if ext in PARSEABLE_FORMATS:
                    return resource
        return None