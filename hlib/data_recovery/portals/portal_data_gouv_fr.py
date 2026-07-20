from typing import List, Optional

from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.api_adapter import ApiAdapter


class PortalDataGouvFR(Portal):
    BASE_API_PATH = "/api/1/datasets/"

    def __init__(self, **config):
        super().__init__(**config)
        self.adapter = ApiAdapter("https://www.data.gouv.fr")

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            if not await ad.connect():
                pass
            url = f"{self.adapter.base_url}{self.BASE_API_PATH}"
            params = {
                "q": query,
                "page_size": 10,
            }
            data = await ad.get(url, params=params)
            if data:
                items = data.get("data", []) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for pkg in items:
                        dataset = self._map_package_to_dataset(pkg)
                        results.append(dataset)
        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        async with self.adapter as ad:
            if not await ad.connect():
                pass

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}{dataset_id}/"
            data = await ad.get(url)

            if data and isinstance(data, dict):
                return self._map_package_to_dataset(data)
        return None

    def _map_package_to_dataset(self, pkg: dict) -> Dataset:
        resources = []
        for res in pkg.get("resources", []):
            resources.append(Resource(
                id=str(res.get("id")),
                name=res.get("title"),
                description=res.get("description"),
                format=res.get("format"),
                url=res.get("url"),
                mimetype=res.get("mime"),
                created=res.get("created_at"),
                last_modified=res.get("last_modified"),
                size_bytes=res.get("filesize"),
            ))
        tags = pkg.get("tags", [])
        org = pkg.get("organization") or {}
        return Dataset(
            id=str(pkg.get("id")),
            title=pkg.get("title"),
            description=pkg.get("description"),
            resources=resources,
            tags=tags,
            organization=org.get("name"),
            license=pkg.get("license"),
            source_portal="data.gouv.fr",
        )
