from typing import List, Optional

from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.ckan_adapter import CkanAdapter


class PortalAvoindataFI(Portal):
    def __init__(self, **config):
        super().__init__(**config)
        self.adapter = CkanAdapter("https://www.avoindata.fi/data")

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            if not await ad.connect():
                print("Could not connect to avoindata.fi")
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

        # Standard CKAN tags
        tags = [t.get("name") for t in pkg.get("tags", []) if t.get("name")]
        # Finnish CKAN may use multilingual keyword dicts instead of standard tags
        if not tags:
            keywords = pkg.get("keywords", {})
            if isinstance(keywords, dict):
                tags = keywords.get("en") or next(iter(keywords.values()), [])

        return Dataset(
            id=pkg.get("id"),
            title=pkg.get("title"),
            description=pkg.get("notes"),
            resources=resources,
            tags=tags,
            organization=pkg.get("organization", {}).get("title"),
            license=pkg.get("license_title"),
            source_portal="avoindata.fi"
        )
