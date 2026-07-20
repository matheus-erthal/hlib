from typing import List, Optional
from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.ckan_adapter import CkanAdapter


class PortalOpendataSwiss(Portal):
    def __init__(self, **config):
        super().__init__(**config)
        self.adapter = CkanAdapter("https://opendata.swiss")

    def _get_localized(self, value) -> Optional[str]:
        if isinstance(value, dict):
            return value.get("en") or value.get("de") or next(iter(value.values()), None)
        return value

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            if not await ad.connect():
                print("Could not connect to opendata.swiss")
                return []
            raw_packages = await ad.search_packages(query)
            for pkg in raw_packages:
                dataset = self._map_package_to_dataset(pkg)
                results.append(dataset)
        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        async with self.adapter as ad:
            raw_pkg = await ad.get_package(dataset_id)
            if raw_pkg:
                return self._map_package_to_dataset(raw_pkg)
        return None

    def _map_package_to_dataset(self, pkg: dict) -> Dataset:
        resources = []
        for res in pkg.get("resources", []):
            resources.append(Resource(
                id=res.get("id"),
                name=res.get("name"),
                description=res.get("description"),
                format=res.get("format"),
                url=res.get("url"),
                mimetype=res.get("mimetype"),
                created=res.get("created"),
                last_modified=res.get("last_modified"),
                size_bytes=res.get("size")
            ))
        tags = [t.get("name") for t in pkg.get("tags", [])]
        return Dataset(
            id=pkg.get("id"),
            title=self._get_localized(pkg.get("title")),
            description=self._get_localized(pkg.get("notes")),
            resources=resources,
            tags=tags,
            organization=pkg.get("organization", {}).get("title"),
            license=pkg.get("license_title"),
            source_portal="opendata.swiss"
        )
