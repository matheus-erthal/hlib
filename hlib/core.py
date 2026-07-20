def package_name():
    return "Hipólita"


from typing import Optional, Union
import asyncio
from .types import PortalType, Dataset, DataFrameWithMeta
from .data_recovery.portals.portal_dados_abertos_br import DadosAbertosBR
from .data_recovery.portals.portal_data_gov_us import PortalDataGovUS
from .data_recovery.portals.portal_data_gov_uk import PortalDataGovUK
from .data_recovery.portals.portal_opendata_swiss import PortalOpendataSwiss
from .data_recovery.portals.portal_avoindata_fi import PortalAvoindataFI
from .data_recovery.portals.portal_data_gov_au import PortalDataGovAU
from .data_recovery.portals.portal_data_gouv_fr import PortalDataGouvFR
from .data_recovery.portals.portal_datos_gob_es import PortalDatosGobES
from .data_recovery.portals.portal_data_gov_sg import PortalDataGovSG
from .data_recovery.portals.portal_data_gov_in import PortalDataGovIN

PORTAL_MAP = {
    PortalType.DADOS_GOV_BR: DadosAbertosBR,
    PortalType.DATA_GOV_US: PortalDataGovUS,
    PortalType.DATA_GOV_UK: PortalDataGovUK,
    PortalType.OPENDATA_SWISS: PortalOpendataSwiss,
    PortalType.AVOINDATA_FI: PortalAvoindataFI,
    PortalType.DATA_GOV_AU: PortalDataGovAU,
    PortalType.DATA_GOUV_FR: PortalDataGouvFR,
    PortalType.DATOS_GOB_ES: PortalDatosGobES,
    PortalType.DATA_GOV_SG: PortalDataGovSG,
    PortalType.DATA_GOV_IN: PortalDataGovIN,
}

PortalSpec = Union[PortalType, str, dict]


def _split_portal_spec(spec: PortalSpec):
    """
    Normaliza um item de portal em (chave_do_portal, config_do_portal).
    `spec` pode ser um PortalType/string isolado (sem config extra) ou um
    dict `{"portal": ..., **config_especifica_desse_portal}`.
    """
    if isinstance(spec, dict):
        if "portal" not in spec:
            raise ValueError(
                "Cada item de uma lista de portais precisa da chave 'portal' "
                "(ex: {'portal': 'data_gov_us', 'api_key': '...'})."
            )
        spec = dict(spec)
        return spec.pop("portal"), spec
    return spec, {}


def _resolve_portal_class(portal_key, fails_silently: bool):
    """
    Normaliza `portal_key` (PortalType ou string) para a classe do portal.
    Retorna (PortalType, classe) em caso de sucesso, ou (None, None) se
    inválido e fails_silently=True (já loga a mensagem nesse caso).
    """
    if isinstance(portal_key, str):
        try:
            portal_key = PortalType(portal_key.lower())
        except ValueError:
            valid_options = [p.value for p in PortalType]
            msg = f"Invalid portal: '{portal_key}'. Valid options: {valid_options}"
            if fails_silently:
                print(msg)
                return None, None
            raise ValueError(msg) from None

    portal_cls = PORTAL_MAP.get(portal_key)
    if not portal_cls:
        msg = f"Unsupported portal: {portal_key}"
        if fails_silently:
            print(msg)
            return None, None
        raise ValueError(msg)

    return portal_key, portal_cls


async def search_data_async(
    query: str,
    portal: Union[PortalType, str, list],
    fails_silently: bool = False,
    **auth_config
) -> list[Dataset]:
    """
    Busca dados em portais governamentais de forma assíncrona.

    Args:
        query: Termo de busca.
        portal: um PortalType/string único (ex: 'data_gov_us'), OU uma lista
            de portais para buscar em paralelo. Cada item da lista pode ser
            um PortalType/string simples (sem config extra) ou um dict
            `{"portal": ..., **config_desse_portal}` para passar parâmetros
            específicos daquele portal (ex: api_key) sem afetar os demais.
        fails_silently: Se True, erros por portal são apenas logados; a busca
            continua nos demais e retorna os resultados parciais.
        **auth_config: Credenciais para um portal único (não use junto com
            uma lista — nesse caso, passe a config dentro de cada item).

    Exemplos:
        await search_data_async("clima", "data_gov_us")

        await search_data_async("saúde", [
            {"portal": "dados_gov_br", "api_key": "CHAVE_BR"},
            {"portal": "data_gov_us", "api_key": "CHAVE_US"},
            "data_gov_uk",
        ])
    """
    is_multi = isinstance(portal, (list, tuple))

    if is_multi and auth_config:
        raise ValueError(
            "Quando 'portal' é uma lista, a config de cada portal vai dentro "
            "do próprio item (ex: {'portal': 'data_gov_us', 'api_key': '...'}), "
            "não como argumento solto de search_data()."
        )

    specs = portal if is_multi else [portal]

    portals_to_search = []
    for spec in specs:
        portal_key, config = _split_portal_spec(spec)
        portal_key, portal_cls = _resolve_portal_class(portal_key, fails_silently)
        if portal_cls is None:
            continue
        portals_to_search.append(portal_cls(**{**auth_config, **config}))

    results = []
    tasks = [p.search(query) for p in portals_to_search]
    search_results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in search_results:
        if isinstance(res, list):
            results.extend(res)
        elif isinstance(res, Exception):
            # Com um portal único, qualquer erro é repassado (a menos de
            # fails_silently). Com uma lista, só erros de validação
            # (ValueError) interrompem — erros de um portal específico só são
            # logados, e a busca segue com os resultados parciais dos demais.
            if not fails_silently and (not is_multi or isinstance(res, ValueError)):
                raise res

            print(f"Search error: {res}")

    return results


def search_data(
    query: str,
    portal: Union[PortalType, str, list],
    fails_silently: bool = False,
    **auth_config
) -> list[Dataset]:
    """
    Busca dados em portais governamentais de forma síncrona.
    """
    return asyncio.run(search_data_async(query, portal, fails_silently, **auth_config))


async def get_dataset_async(
    dataset_id: str,
    portal: PortalType | str,
    fails_silently: bool = False,
    **auth_config
) -> Optional[Dataset]:
    """
    Busca um dataset individual por ID em um portal específico (assíncrono).

    Args:
        dataset_id: ID do dataset no portal.
        portal: PortalType ou string de um único portal (não aceita lista —
            uma busca por ID é sempre contra um portal específico).
        fails_silently: Se True, erros são logados e retorna None.
        **auth_config: Credenciais extras (ex: api_key para Portal BR).
    """
    if isinstance(portal, (list, tuple)):
        msg = "get_dataset requires a single specific portal; lists are only supported by search_data()."
        if fails_silently:
            print(msg)
            return None
        raise ValueError(msg)

    portal_key, portal_cls = _resolve_portal_class(portal, fails_silently)
    if portal_cls is None:
        return None

    try:
        portal_instance = portal_cls(**auth_config)
        return await portal_instance.get_dataset(dataset_id)
    except Exception as e:
        if not fails_silently:
            raise
        print(f"get_dataset error: {e}")
        return None


def get_dataset(
    dataset_id: str,
    portal: PortalType | str,
    fails_silently: bool = False,
    **auth_config
) -> Optional[Dataset]:
    """
    Busca um dataset individual por ID em um portal específico (síncrono).
    """
    return asyncio.run(get_dataset_async(dataset_id, portal, fails_silently, **auth_config))


async def fetch_dataset_data_async(
    dataset_id: str,
    portal: PortalType | str,
    fails_silently: bool = False,
    **auth_config
) -> DataFrameWithMeta:
    """
    Busca um dataset e tenta baixar o primeiro recurso parseável como DataFrame (assíncrono).

    Se o dataset possuir um recurso em formato parseável (CSV, TSV, XLS, XLSX, JSON),
    retorna DataFrameWithMeta com o DataFrame preenchido.
    Caso contrário, retorna DataFrameWithMeta com DataFrame vazio e metadados com links de acesso.

    Args:
        dataset_id: ID do dataset no portal.
        portal: PortalType ou string de um único portal (não aceita lista).
        fails_silently: Se True, erros são logados e retorna DataFrameWithMeta vazio.
        **auth_config: Credenciais extras (ex: api_key para Portal BR).
    """
    import pandas as pd

    if isinstance(portal, (list, tuple)):
        msg = "fetch_dataset_data requires a single specific portal; lists are only supported by search_data()."
        if fails_silently:
            print(msg)
            return DataFrameWithMeta(df=pd.DataFrame(), meta={"error": msg})
        raise ValueError(msg)

    portal_key, portal_cls = _resolve_portal_class(portal, fails_silently)
    if portal_cls is None:
        return DataFrameWithMeta(df=pd.DataFrame(), meta={"error": f"Unsupported or invalid portal: {portal}"})

    try:
        portal_instance = portal_cls(**auth_config)
        return await portal_instance.fetch_dataset_data(dataset_id)
    except Exception as e:
        if not fails_silently:
            raise
        print(f"fetch_dataset_data error: {e}")
        return DataFrameWithMeta(df=pd.DataFrame(), meta={"error": str(e)})


def fetch_dataset_data(
    dataset_id: str,
    portal: PortalType | str,
    fails_silently: bool = False,
    **auth_config
) -> DataFrameWithMeta:
    """
    Busca um dataset e tenta baixar o primeiro recurso parseável como DataFrame (síncrono).
    """
    return asyncio.run(fetch_dataset_data_async(dataset_id, portal, fails_silently, **auth_config))


class Hipolita:
    """Núcleo da biblioteca Hipolita."""

    def __init__(self):
        pass

    @staticmethod
    async def search_data_async(
        query: str,
        portal: Union[PortalType, str, list],
        fails_silently: bool = False,
        **auth_config
    ) -> list[Dataset]:
        """Busca dados em portais governamentais (Método estático assíncrono)."""
        return await search_data_async(query, portal, fails_silently, **auth_config)

    @staticmethod
    def search_data(
        query: str,
        portal: Union[PortalType, str, list],
        fails_silently: bool = False,
        **auth_config
    ) -> list[Dataset]:
        """Busca dados em portais governamentais (Método estático síncrono)."""
        return search_data(query, portal, fails_silently, **auth_config)

    @staticmethod
    async def get_dataset_async(
        dataset_id: str,
        portal: PortalType | str,
        fails_silently: bool = False,
        **auth_config
    ) -> Optional[Dataset]:
        """Busca um dataset individual por ID (assíncrono)."""
        return await get_dataset_async(dataset_id, portal, fails_silently, **auth_config)

    @staticmethod
    def get_dataset(
        dataset_id: str,
        portal: PortalType | str,
        fails_silently: bool = False,
        **auth_config
    ) -> Optional[Dataset]:
        """Busca um dataset individual por ID (síncrono)."""
        return get_dataset(dataset_id, portal, fails_silently, **auth_config)

    @staticmethod
    async def fetch_dataset_data_async(
        dataset_id: str,
        portal: PortalType | str,
        fails_silently: bool = False,
        **auth_config
    ) -> DataFrameWithMeta:
        """Busca dataset e baixa primeiro recurso parseável como DataFrame (assíncrono)."""
        return await fetch_dataset_data_async(dataset_id, portal, fails_silently, **auth_config)

    @staticmethod
    def fetch_dataset_data(
        dataset_id: str,
        portal: PortalType | str,
        fails_silently: bool = False,
        **auth_config
    ) -> DataFrameWithMeta:
        """Busca dataset e baixa primeiro recurso parseável como DataFrame (síncrono)."""
        return fetch_dataset_data(dataset_id, portal, fails_silently, **auth_config)
