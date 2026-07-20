from typing import List, Optional

from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.ckan_adapter import CkanAdapter


class CkanPortal(Portal):
    """
    Estratégia genérica para qualquer instância CKAN v3 padrão, parametrizada
    por catálogo (hlib.catalog). Cobre qualquer portal CKAN "de prateleira"
    sem precisar de uma classe Python nova por portal.
    """

    def __init__(self, *, base_url: str, source_portal: str,
                 localized_fields: bool = False,
                 localized_lang_order=("en", "de"),
                 keyword_fallback_field: Optional[str] = None,
                 keyword_lang_order=("en",),
                 **config):
        super().__init__(**config)
        self.adapter = CkanAdapter(base_url)
        self.source_portal = source_portal
        self.localized_fields = localized_fields
        self.localized_lang_order = localized_lang_order
        self.keyword_fallback_field = keyword_fallback_field
        self.keyword_lang_order = keyword_lang_order

    def _localized(self, value):
        if self.localized_fields and isinstance(value, dict):
            for lang in self.localized_lang_order:
                if value.get(lang):
                    return value[lang]
            return next(iter(value.values()), None)
        return value

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            if not await ad.connect():
                print(f"Could not connect to {self.source_portal}")
                return []
            raw_packages = await ad.search_packages(query)
            for pkg in raw_packages:
                results.append(self._map_package_to_dataset(pkg))
        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        async with self.adapter as ad:
            raw_pkg = await ad.get_package(dataset_id)
            if raw_pkg:
                return self._map_package_to_dataset(raw_pkg)
        return None

    def _map_package_to_dataset(self, pkg: dict) -> Dataset:
        resources = [
            Resource(
                id=res.get("id"),
                name=res.get("name"),
                description=res.get("description"),
                format=res.get("format"),
                url=res.get("url"),
                mimetype=res.get("mimetype"),
                created=res.get("created"),
                last_modified=res.get("last_modified"),
                size_bytes=res.get("size"),
            )
            for res in pkg.get("resources", [])
        ]

        tags = [t.get("name") for t in pkg.get("tags", []) if t.get("name")]
        if not tags and self.keyword_fallback_field:
            keywords = pkg.get(self.keyword_fallback_field, {})
            if isinstance(keywords, dict):
                for lang in self.keyword_lang_order:
                    if keywords.get(lang):
                        tags = keywords[lang]
                        break
                else:
                    tags = next(iter(keywords.values()), [])

        return Dataset(
            id=pkg.get("id"),
            title=self._localized(pkg.get("title")),
            description=self._localized(pkg.get("notes")),
            resources=resources,
            tags=tags,
            organization=pkg.get("organization", {}).get("title"),
            license=pkg.get("license_title"),
            source_portal=self.source_portal,
        )
