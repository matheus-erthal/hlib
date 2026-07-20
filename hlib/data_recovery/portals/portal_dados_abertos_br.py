from typing import List, Optional
from ...types import Dataset, Resource
from ..interfaces.portal import Portal
from ..adapters.api_adapter import ApiAdapter

class DadosAbertosBR(Portal):
    """
    Implementação para dados.gov.br (API Nova)
    Usa um ApiAdapter genérico e define a lógica de endpoints aqui.
    """
    
    BASE_API_PATH = "/dados/api/publico/conjuntos-dados"

    def __init__(self, **config):
        super().__init__(**config)
        # Inicializa o adaptador genérico apontando para a base
        self.adapter = ApiAdapter("https://dados.gov.br")
        self.api_key = config.get("api_key")

    async def search(self, query: str) -> List[Dataset]:
        if not self.api_key:
            raise ValueError("The Dados Abertos BR portal requires an 'api_key' for searching.")
            
        results = []
        async with self.adapter as ad:
            # Check de conexão genérico ou específico?
            # O ApiAdapter.connect faz check na raiz. 
            # Se quisermos check específico, podemos fazer um request manual aqui.
            if not await ad.connect():
                 # Tentar conectar direto no endpoint da API se a raiz for bloqueada ou redirect
                 # Mas vamos assumir connect ok ou proceder
                 pass

            # Montar request específico do Portal
            url = f"{self.adapter.base_url}{self.BASE_API_PATH}"
            params = {
                "nomeConjuntoDados": query,
                "pagina": 1,
                "registrosPorPagina": 10,
                "isPrivado": "false"
            }
            headers = {}
            if self.api_key:
                headers["chave-api-dados-abertos"] = self.api_key
            
            # Executa request usando adaptador genérico
            data = await ad.get(url, params=params, headers=headers)
            
            if data:
                # Trata response
                items = data.get("conjuntosDados", []) if isinstance(data, dict) else data
                if isinstance(items, list):
                    for pkg in items:
                        dataset = self._map_package_to_dataset(pkg)
                        results.append(dataset)
        
        return results

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        if not self.api_key:
            raise ValueError("The Dados Abertos BR portal requires an 'api_key' for fetching a dataset.")

        async with self.adapter as ad:
            if not await ad.connect():
                pass

            url = f"{self.adapter.base_url}{self.BASE_API_PATH}/{dataset_id}"
            headers = {"chave-api-dados-abertos": self.api_key}

            data = await ad.get(url, headers=headers)

            if data and isinstance(data, dict):
                return self._map_package_to_dataset(data)
        return None

    def _map_package_to_dataset(self, pkg: dict) -> Dataset:
        resources = []
        for res in pkg.get("recursos", []):
            resources.append(Resource(
                id=str(res.get("id")),
                name=res.get("titulo"),
                description=res.get("descricao"),
                format=res.get("formato"),
                url=res.get("url"),
                mimetype=res.get("mimeType")
            ))

        tags = [t.get("termo") for t in pkg.get("palavrasChave", [])]
        
        return Dataset(
            id=str(pkg.get("id")),
            title=pkg.get("title"), 
            description=pkg.get("descricao"), 
            resources=resources,
            tags=tags,
            organization=pkg.get("nomeOrganizacao"), 
            source_portal="dados.gov.br"
        )
