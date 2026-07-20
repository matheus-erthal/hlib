from typing import List, Optional
from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.api_adapter import ApiAdapter

class PortalDataGovIN(Portal):
    """
    Implementation for data.gov.in (OGDP API)
    Uses a generic ApiAdapter and defines endpoint logic here.
    """

    BASE_API_PATH = "/backend/dmspublic/v1/resources"

    def __init__(self, **config):
        super().__init__(**config)
        self.adapter = ApiAdapter("https://www.data.gov.in")

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            if not await ad.connect():
                pass

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}"
            params = {
                "offset": 0,
                "limit": 10,
                "format": "json",
                "filters[title]": query,
            }

            data = await ad.get(url, params=params)

            if data and isinstance(data, dict) and data.get("statusCode") == 200:
                rows = data.get("data", {}).get("rows", [])
                for item in rows:
                    dataset = self._map_package_to_dataset(item)
                    results.append(dataset)

        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        async with self.adapter as ad:
            if not await ad.connect():
                pass

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}"
            params = {
                "filters[catalog_uuid]": dataset_id,
                "format": "json",
                "limit": 1,
            }

            data = await ad.get(url, params=params)

            if data and isinstance(data, dict) and data.get("statusCode") == 200:
                rows = data.get("data", {}).get("rows", [])
                if rows:
                    return self._map_package_to_dataset(rows[0])
        return None

    def _map_package_to_dataset(self, item: dict) -> Dataset:
        title_val = item.get("title", [None])[0]
        uuid_val = item.get("uuid", [None])[0]
        catalog_title = item.get("catalog_title", [None])[0]
        catalog_uuid = item.get("catalog_uuid", [None])[0]
        datafile = item.get("datafile", [None])[0]
        file_format = item.get("file_format", [None])[0]
        file_size = item.get("file_size", [None])[0]
        sector_resource = item.get("sector_resource", [])

        tags = [s for s in sector_resource if s is not None]

        resource = Resource(
            id=str(uuid_val) if uuid_val else "",
            name=title_val,
            format=file_format,
            url=datafile,
            size_bytes=file_size,
        )

        return Dataset(
            id=str(catalog_uuid or uuid_val or ""),
            title=catalog_title or title_val,
            description=None,
            resources=[resource],
            tags=tags,
            organization=None,
            source_portal="data.gov.in",
        )
