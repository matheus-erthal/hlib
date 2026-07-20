from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import aiohttp
import pandas as pd
from ...types import Dataset

class DataAdapter(ABC):
    """
    Interface abstrata para adaptadores de fontes de dados (e.g. CKAN, Socrata).
    """

    def __init__(self, base_url: str, **config):
        self.base_url = base_url.rstrip('/')
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        headers = {
            "User-Agent": "Hipolita/1.0"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @abstractmethod
    async def connect(self) -> bool:
        """Verifica se a fonte de dados está acessível."""
        pass

    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        """Método genérico GET."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        # Merge headers
        req_headers = {}
        if headers:
            req_headers.update(headers)
            
        async with self.session.get(url, params=params, headers=req_headers) as response:
            if response.status == 200:
                # Tenta retornar JSON, se falhar retorna texto ou raw?
                # Por padrao JSON é o esperado para APIs
                try:
                    return await response.json()
                except:
                    return await response.text()
            return None

    async def post(self, url: str, json: Any = None, headers: Optional[Dict[str, str]] = None) -> Any:
        """Método genérico POST."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        req_headers = {}
        if headers:
            req_headers.update(headers)

        async with self.session.post(url, json=json, headers=req_headers) as response:
            if response.status == 200:
                try:
                    return await response.json()
                except:
                    return await response.text()
            return None

    @abstractmethod
    async def fetch_resource(self, resource_url: str) -> pd.DataFrame:
        """
        Baixa e carrega o recurso em um DataFrame.
        """
        pass