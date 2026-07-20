from typing import List, Optional
from ....types import Dataset, Resource
from ...interfaces.portal import Portal
from ...adapters.api_adapter import ApiAdapter

class PortalDataGovUS(Portal):
    """
    Implementação para catalog.data.gov (US).

    A API clássica do CKAN (`/api/3/action/...`) foi descontinuada pelo GSA.
    O substituto oficial é a "Catalog API" v4 (api.gsa.gov/technology/datagov/v4),
    que fala DCAT-US em vez de CKAN e exige uma `X-Api-Key` (a pública `DEMO_KEY`
    funciona para uso leve). Por isso usa o ApiAdapter genérico, no mesmo padrão
    de DadosAbertosBR, em vez do CkanAdapter usado pelos demais portais CKAN.
    """

    SEARCH_PATH = "/search"

    def __init__(self, **config):
        super().__init__(**config)
        self.adapter = ApiAdapter("https://api.gsa.gov/technology/datagov/v4")
        self.api_key = config.get("api_key", "DEMO_KEY")
        # A API v4 não tem endpoint de busca por ID — get_dataset() precisa
        # paginar o /search procurando o `identifier` correspondente. Isso tem
        # custo (várias requisições) e não garante achar o dataset, então é
        # opt-out (não opt-in) via este flag.
        self.id_lookup_fallback = config.get("id_lookup_fallback", True)
        self.max_scan_pages = config.get("max_scan_pages", 20)
        # Cache local de itens já vistos em search() nesta instância, indexado
        # por identifier. Cobre de graça o padrão mais comum de uso — buscar e
        # depois pedir o dataset de um dos resultados — sem precisar do scan
        # paginado (que só roda para um ID "frio", que não veio de um search()
        # anterior nesta mesma instância).
        self._seen_items: dict[str, dict] = {}

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            url = f"{self.adapter.base_url}{self.SEARCH_PATH}"
            params = {"q": query, "per_page": 10}
            headers = {"X-Api-Key": self.api_key}

            data = await ad.get(url, params=params, headers=headers)

            if data and isinstance(data, dict):
                for item in data.get("results", []):
                    identifier = item.get("identifier")
                    if identifier:
                        self._seen_items[str(identifier)] = item
                    results.append(self._map_package_to_dataset(item))

        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        cached = self._seen_items.get(str(dataset_id))
        if cached is not None:
            return self._map_package_to_dataset(cached)

        if not self.id_lookup_fallback:
            return None

        async with self.adapter as ad:
            url = f"{self.adapter.base_url}{self.SEARCH_PATH}"
            headers = {"X-Api-Key": self.api_key}
            after = None

            for _ in range(self.max_scan_pages):
                params = {"per_page": 100}
                if after:
                    params["after"] = after

                data = await ad.get(url, params=params, headers=headers)
                if not data or not isinstance(data, dict):
                    break

                for item in data.get("results", []):
                    if str(item.get("identifier")) == str(dataset_id):
                        return self._map_package_to_dataset(item)

                after = data.get("after")
                if not after:
                    break

        return None

    def _map_package_to_dataset(self, item: dict) -> Dataset:
        """
        Mapeia um resultado DCAT-US da API v4 -> Hipólita Dataset.
        """
        dcat = item.get("dcat", {}) or {}
        org = item.get("organization") or {}

        resources = []
        for i, dist in enumerate(dcat.get("distribution", []) or []):
            resources.append(Resource(
                id=dist.get("downloadURL") or dist.get("describedBy") or str(i),
                name=dist.get("title"),
                description=dist.get("description"),
                format=dist.get("format"),
                url=dist.get("downloadURL"),
                mimetype=dist.get("mediaType"),
            ))

        return Dataset(
            id=str(item.get("identifier") or ""),
            title=item.get("title"),
            description=item.get("description"),
            resources=resources,
            tags=item.get("keyword", []) or [],
            organization=org.get("name") or item.get("publisher"),
            license=dcat.get("license"),
            source_portal="data.gov"
        )
