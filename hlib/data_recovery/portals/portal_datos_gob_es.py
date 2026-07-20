from typing import List, Optional
from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.api_adapter import ApiAdapter


class PortalDatosGobES(Portal):
    """
    Implementation for datos.gob.es (Spanish Open Data Portal)
    Uses the Linked Data API.
    """

    BASE_API_PATH = "/apidata/catalog/dataset"

    def __init__(self, **config):
        super().__init__(**config)
        self.adapter = ApiAdapter("https://datos.gob.es")

    async def search(self, query: str) -> List[Dataset]:
        results = []
        async with self.adapter as ad:
            await ad.connect()

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}"
            params = {
                "_pageSize": 10,
                "_page": 0,
            }

            data = await ad.get(url, params=params)

            if data and isinstance(data, dict):
                items = data.get("result", {}).get("items", [])
                for pkg in items:
                    dataset = self._map_package_to_dataset(pkg)
                    results.append(dataset)

        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        async with self.adapter as ad:
            await ad.connect()

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}/{dataset_id}"
            data = await ad.get(url)

            if data and isinstance(data, dict):
                items = data.get("result", {}).get("items", [])
                if items:
                    return self._map_package_to_dataset(items[0])
        return None

    def _get_localized_value(self, field_value, preferred_lang: str = "en", fallback_lang: str = "es") -> Optional[str]:
        """Extract a localized string from a multilingual field (list of {_value, _lang} objects)."""
        if not field_value:
            return None
        if isinstance(field_value, str):
            return field_value
        if isinstance(field_value, list):
            by_lang = {}
            for entry in field_value:
                if isinstance(entry, dict):
                    lang = entry.get("_lang", "")
                    val = entry.get("_value", "")
                    by_lang[lang] = val
            if preferred_lang in by_lang:
                return by_lang[preferred_lang]
            if fallback_lang in by_lang:
                return by_lang[fallback_lang]
            if by_lang:
                return next(iter(by_lang.values()))
        if isinstance(field_value, dict):
            return field_value.get("_value")
        return None

    def _map_package_to_dataset(self, pkg: dict) -> Dataset:
        about = pkg.get("_about", "")
        dataset_id = about.rsplit("/", 1)[-1] if about else ""

        title = self._get_localized_value(pkg.get("title"))
        description = self._get_localized_value(pkg.get("description"))

        # Tags from theme list
        tags = []
        themes = pkg.get("theme", [])
        if isinstance(themes, list):
            for t in themes:
                if isinstance(t, dict):
                    t_about = t.get("_about", "")
                    if t_about:
                        tags.append(t_about.rsplit("/", 1)[-1])

        # Organization from publisher
        organization = None
        publisher = pkg.get("publisher")
        if isinstance(publisher, dict):
            organization = publisher.get("notation") or (
                publisher.get("_about", "").rsplit("/", 1)[-1] if publisher.get("_about") else None
            )

        # Resources from distribution(s)
        resources = []
        dist = pkg.get("distribution")
        if dist is not None:
            dists = dist if isinstance(dist, list) else [dist]
            for d in dists:
                if not isinstance(d, dict):
                    continue
                fmt = None
                fmt_obj = d.get("format")
                if isinstance(fmt_obj, dict):
                    labels = fmt_obj.get("label", [])
                    if isinstance(labels, list) and labels:
                        fmt = labels[0]
                    elif isinstance(labels, str):
                        fmt = labels
                access_url = d.get("accessURL")
                res_about = d.get("_about", "")
                res_id = res_about.rsplit("/", 1)[-1] if res_about else ""
                resources.append(Resource(
                    id=res_id,
                    format=fmt,
                    url=access_url,
                ))

        return Dataset(
            id=dataset_id,
            title=title,
            description=description,
            resources=resources,
            tags=tags,
            organization=organization,
            source_portal="datos.gob.es",
        )
