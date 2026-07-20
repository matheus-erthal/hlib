from typing import List, Optional
from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.api_adapter import ApiAdapter

class PortalDataGovSG(Portal):
    """
    Implementation for data.gov.sg (Singapore Open Data Portal).
    Uses a generic ApiAdapter and defines endpoint logic here.
    """
    
    BASE_API_PATH = "/v2/public/api/datasets"

    def __init__(self, **config):
        super().__init__(**config)
        self.adapter = ApiAdapter("https://api-production.data.gov.sg")

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            if not await ad.connect():
                pass

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}"
            params = {
                "query": query,
                "page": 1,
            }

            data = await ad.get(url, params=params)

            if data and isinstance(data, dict):
                items = data.get("data", {}).get("datasets", [])
                if isinstance(items, list):
                    for pkg in items:
                        dataset = self._map_package_to_dataset(pkg)
                        results.append(dataset)

        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        async with self.adapter as ad:
            if not await ad.connect():
                pass

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}/{dataset_id}/metadata"
            data = await ad.get(url)

            if data and isinstance(data, dict) and data.get("code") == 0:
                pkg = data.get("data", {})
                if pkg:
                    if "managedBy" in pkg and "managedByAgencyName" not in pkg:
                        pkg["managedByAgencyName"] = pkg["managedBy"]
                    return self._map_package_to_dataset(pkg)
        return None

    def _map_package_to_dataset(self, pkg: dict) -> Dataset:
        dataset_id = pkg.get("datasetId", "")
        resources = [
            Resource(
                id=dataset_id,
                name=pkg.get("name"),
                format=pkg.get("format"),
                url=None,
            )
        ]

        return Dataset(
            id=dataset_id,
            title=pkg.get("name"),
            description=pkg.get("description"),
            resources=resources,
            tags=[],
            organization=pkg.get("managedByAgencyName"),
            source_portal="data.gov.sg",
        )
