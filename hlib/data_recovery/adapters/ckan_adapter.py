from typing import Any, Dict, List, Optional
import aiohttp
import pandas as pd
import io
from ..interfaces.adapter import DataAdapter

class CkanAdapter(DataAdapter):
    """
    Adaptador especializado para CKAN API v3.
    """

    async def connect(self) -> bool:
        """
        Testa conexão verificando a disponibilidade da API.
        """
        if not self.session:
            raise RuntimeError("Adapter needs to be used within an 'async with' context or the session must be created manually")
        
        try:
            url = f"{self.base_url}/api/3/action/package_search"
            async with self.session.get(url, params={"rows": 0}) as response:
                return response.status == 200
        except:
            return False

    async def search_packages(self, query: str, **filters) -> List[Dict[str, Any]]:
        """
        Método especializado CKAN.
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        url = f"{self.base_url}/api/3/action/package_search"
        params = {"q": query, "rows": filters.get("limit", 10)}
        
        data = await self.get(url, params=params)
        
        if data and isinstance(data, dict):
             if data.get("success"):
                return data["result"]["results"]
        return []

    async def get_package(self, package_id: str) -> Optional[Dict[str, Any]]:
        if not self.session:
            raise RuntimeError("Sessão não inicializada")

        url = f"{self.base_url}/api/3/action/package_show"
        params = {"id": package_id}
        
        data = await self.get(url, params=params)
        
        if data and isinstance(data, dict):
            if data.get("success"):
                return data["result"]
        return None

    async def fetch_resource(self, resource_url: str) -> pd.DataFrame:
        if not self.session:
             raise RuntimeError("Sessão não inicializada")

        async with self.session.get(resource_url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download resource: {response.status}")

            content = await response.read()
            content_type = response.content_type or ""
            url_lower = resource_url.lower()

            if "json" in content_type or url_lower.endswith(".json"):
                try:
                    return pd.read_json(io.BytesIO(content))
                except Exception:
                    pass

            if "tab-separated" in content_type or url_lower.endswith(".tsv"):
                try:
                    return pd.read_csv(io.BytesIO(content), sep='\t')
                except Exception:
                    pass

            try:
                return pd.read_csv(io.BytesIO(content))
            except Exception:
                pass

            try:
                return pd.read_excel(io.BytesIO(content))
            except Exception:
                return pd.DataFrame()
