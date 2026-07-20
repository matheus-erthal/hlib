# HLib

[![Build](https://github.com/matheus-erthal/hlib/actions/workflows/python-package.yml/badge.svg)](https://github.com/matheus-erthal/hlib/actions/workflows/python-package.yml)
[![PyPI](https://img.shields.io/pypi/v/hlib-hipolita?color=blue)](https://pypi.org/project/hlib-hipolita/)
[![License](https://img.shields.io/pypi/l/hlib-hipolita)](https://opensource.org/licenses/MIT)

## Descrição

Implementação do framework **Hipólita**, proposto originalmente em [_Hippolyta: a framework to enhance open data interpretability and empower citizens_](https://dl.acm.org/doi/10.1145/3598469.3598559).

Hlib facilita o acesso e a interpretação de dados governamentais abertos, fornecendo uma interface unificada para buscar, recuperar e consumir datasets de múltiplos portais nacionais — cada um com APIs, padrões de metadados e formatos de resposta diferentes.

---

## Portais Suportados

| Portal | País | URL | Chave (`PortalType`) | Plataforma / API | Autenticação |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Portal de Dados Abertos** | Brasil 🇧🇷 | [dados.gov.br](https://dados.gov.br) | `DADOS_GOV_BR` | REST API própria | Requer `api_key` |
| **Data.gov** | EUA 🇺🇸 | [data.gov](https://catalog.data.gov) | `DATA_GOV_US` | Catalog API v4 (DCAT-US) | `X-Api-Key` (`DEMO_KEY` público funciona) |
| **CKAN Publishing** | Reino Unido 🇬🇧 | [ckan.publishing.service.gov.uk](https://ckan.publishing.service.gov.uk) | `DATA_GOV_UK` | CKAN v3 | Acesso público |
| **opendata.swiss** | Suíça 🇨🇭 | [opendata.swiss](https://opendata.swiss) | `OPENDATA_SWISS` | CKAN v3 (multilíngue) | Acesso público |
| **Avoindata.fi** | Finlândia 🇫🇮 | [avoindata.fi](https://www.avoindata.fi) | `AVOINDATA_FI` | CKAN v3 | Acesso público |
| **data.gov.au** | Austrália 🇦🇺 | [data.gov.au](https://data.gov.au) | `DATA_GOV_AU` | CKAN v3 | Acesso público |
| **data.gouv.fr** | França 🇫🇷 | [data.gouv.fr](https://www.data.gouv.fr) | `DATA_GOUV_FR` | udata REST API | Acesso público |
| **datos.gob.es** | Espanha 🇪🇸 | [datos.gob.es](https://datos.gob.es) | `DATOS_GOB_ES` | Linked Data API | Acesso público |
| **data.gov.sg** | Singapura 🇸🇬 | [data.gov.sg](https://data.gov.sg) | `DATA_GOV_SG` | REST API v2 | Acesso público |
| **data.gov.in** | Índia 🇮🇳 | [data.gov.in](https://data.gov.in) | `DATA_GOV_IN` | OGDP REST API | Acesso público |

> **Autenticação:** dois portais precisam de chave de API, cada um passada via `api_key=` na instância/chamada daquele portal (não é compartilhada entre portais — ver exemplo de busca em lista acima):
> - **BR** (`dados.gov.br`) — obrigatória, sem ela `search()`/`get_dataset()` levantam `ValueError`. Solicite em [dados.gov.br](https://dados.gov.br).
> - **EUA** (`data.gov`) — opcional para uso leve: sem `api_key`, usa a `DEMO_KEY` pública (limite baixo de requisições/hora). Para uso mais intenso, registre uma chave própria em [api.data.gov/signup](https://api.data.gov/signup/).

### Portais Investigados (Sem Integração Programática)

| Portal | País | Motivo |
| :--- | :--- | :--- |
| data.gov.cy | Chipre 🇨🇾 | Portal Drupal sem API REST pública |
| data.gov.ru | Rússia 🇷🇺 | SPA Vue.js sem endpoint de API acessível |
| data.gv.at | Áustria 🇦🇹 | Migrou para SPA; CKAN API desativada |
| data.gov.tw | Taiwan 🇹🇼 | API v1 desativada; v2 requer chave de autenticação |

---

## Instalação

```bash
pip install hlib-hipolita
```

Requer **Python 3.10+**. Dependências: `pandas`, `numpy`, `aiohttp`.

---

## Como Usar

### Busca de Datasets (`search_data`)

Busca datasets por texto em um ou mais portais simultaneamente.

```python
from hlib import search_data, PortalType

# Busca em um portal específico
datasets = search_data("climate", portal=PortalType.DATA_GOV_US)

# Também aceita string no lugar do enum
datasets = search_data("education", portal="data_gov_uk")

# Busca em vários portais em paralelo — cada item da lista pode ser um
# PortalType/string simples, ou um dict com a config específica daquele
# portal (ex: api_key). A config de um portal nunca vaza para os outros.
datasets = search_data("saúde", portal=[
    {"portal": PortalType.DADOS_GOV_BR, "api_key": "SUA_CHAVE_BR"},
    {"portal": "data_gov_us", "api_key": "SUA_CHAVE_US"},  # opcional, usa DEMO_KEY se omitido
    "data_gov_uk",
])
```

> Não existe mais um valor `PortalType.ALL` — como cada portal pode precisar de uma config diferente (ver seção de autenticação abaixo), buscar em vários portais exige listá-los explicitamente, como no exemplo acima.

#### Controle de erros (`fails_silently`)

```python
# Se o portal estiver offline ou a chave for inválida, retorna [] ao invés de lançar exceção
datasets = search_data("health", portal=PortalType.DADOS_GOV_BR, fails_silently=True)
```

### Busca de Dataset Individual (`get_dataset`)

Recupera os metadados completos de um dataset específico pelo seu ID.

```python
from hlib import get_dataset, PortalType

# Buscar um dataset por ID
dataset = get_dataset("dataset-id-123", portal=PortalType.DATA_GOV_US)

if dataset:
    print(dataset.title)
    print(dataset.description)
    for resource in dataset.resources:
        print(f"  {resource.name} ({resource.format}): {resource.url}")
```

### Download e Parse de Dados (`fetch_dataset_data`)

Busca um dataset e, se houver um recurso em formato parseável (CSV, TSV, XLS, XLSX, JSON), retorna os dados como `pandas.DataFrame`.

```python
from hlib import fetch_dataset_data, PortalType

result = fetch_dataset_data("dataset-id-123", portal=PortalType.DATA_GOV_AU)

if not result.df.empty:
    # Dados parseados com sucesso
    print(result.df.head())
    print(f"Formato: {result.meta['format']}")
    print(f"URL: {result.meta['resource_url']}")
else:
    # Sem recurso parseável — metadados disponíveis com links
    print(f"Dataset: {result.meta.get('title')}")
    for link in result.meta.get("resource_links", []):
        print(f"  {link['name']} ({link['format']}): {link['url']}")
```

### Uso Assíncrono (`asyncio`)

Todas as funções possuem versão assíncrona com sufixo `_async`:

```python
import asyncio
from hlib import search_data_async, get_dataset_async, fetch_dataset_data_async, PortalType

async def main():
    # Busca assíncrona em vários portais, cada um com sua config
    datasets = await search_data_async("education", portal=[
        {"portal": "dados_gov_br", "api_key": "SUA_CHAVE_BR"},
        "data_gov_uk",
    ])
    
    # Recuperar dataset individual
    dataset = await get_dataset_async("abc-123", portal=PortalType.DATA_GOUV_FR)
    
    # Baixar e parsear dados
    result = await fetch_dataset_data_async("abc-123", portal=PortalType.DATA_GOUV_FR)

asyncio.run(main())
```

### Classe `Hipolita`

Para quem prefere orientação a objetos, as mesmas operações estão disponíveis como métodos estáticos:

```python
from hlib.core import Hipolita
from hlib import PortalType

datasets = Hipolita.search_data("climate", portal=PortalType.DATA_GOV_UK)
dataset = Hipolita.get_dataset("id-123", portal=PortalType.DATA_GOV_UK)
result = Hipolita.fetch_dataset_data("id-123", portal=PortalType.DATA_GOV_UK)
```

---

## Modelo de Dados

### `Dataset`

Representa um conjunto de dados com metadados normalizados de qualquer portal.

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | `str` | Identificador único no portal de origem |
| `title` | `str \| None` | Título do dataset |
| `description` | `str \| None` | Descrição textual |
| `resources` | `list[Resource]` | Arquivos/endpoints disponíveis |
| `tags` | `list[str]` | Palavras-chave / categorias |
| `organization` | `str \| None` | Organização publicadora |
| `license` | `str \| None` | Licença de uso |
| `source_portal` | `str \| None` | Portal de origem |

### `Resource`

Representa um arquivo ou endpoint de dados dentro de um dataset.

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | `str` | Identificador do recurso |
| `name` | `str \| None` | Nome do arquivo/recurso |
| `format` | `str \| None` | Formato (CSV, JSON, XML, etc.) |
| `url` | `str \| None` | URL de download |

### `DataFrameWithMeta`

Retornado por `fetch_dataset_data()`. Combina dados tabulares com metadados.

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `df` | `pd.DataFrame` | Dados parseados (vazio se não parseável) |
| `meta` | `dict` | Metadados: `title`, `format`, `resource_url`, `resource_links` |

---

## Arquitetura

```
hlib/
├── __init__.py              # Exports públicos
├── core.py                  # API principal (search, get_dataset, fetch_dataset_data)
├── types.py                 # Dataset, Resource, DataFrameWithMeta, PortalType
├── catalog/                 # Catálogo de portais data-driven
│   ├── portals.json         # Metadados de cada portal (URL, plataforma, auth, região...)
│   ├── schema.py             # PortalRecord / AuthSpec + validação
│   ├── loader.py             # list_portals() / search_portals() / get_portal_record()
│   ├── registry.py           # platform -> factory que instancia o Portal
│   ├── dynamic_enum.py       # Constrói PortalType a partir do catálogo
│   └── validate.py           # `python -m hlib.catalog.validate` (CI)
└── data_recovery/
    ├── interfaces/
    │   ├── adapter.py       # DataAdapter (ABC)
    │   └── portal.py        # Portal (ABC) + fetch_dataset_data (concreto)
    ├── adapters/
    │   ├── ckan_adapter.py  # Adaptador CKAN v3
    │   └── api_adapter.py   # Adaptador REST genérico
    └── portals/
        ├── generic_ckan_portal.py   # CkanPortal genérico (qualquer CKAN via config;
        │                            # cobre hoje UK/AU/FI/CH via catálogo, sem classe própria)
        ├── brazil/
        │   └── portal_dados_abertos_br.py
        ├── usa/
        │   └── portal_data_gov_us.py
        ├── france/
        │   └── portal_data_gouv_fr.py
        ├── spain/
        │   └── portal_datos_gob_es.py
        ├── singapore/
        │   └── portal_data_gov_sg.py
        └── india/
            └── portal_data_gov_in.py
```

A arquitetura segue o padrão **Strategy**: cada portal implementa a lógica de mapeamento de endpoints e campos, delegando operações HTTP a um adaptador compartilhado (`CkanAdapter` ou `ApiAdapter`).

### Catálogo de portais

`PortalType` não é mais uma lista fixa de constantes — é construído dinamicamente a partir de `hlib/catalog/portals.json` (cada entrada define URL, plataforma, autenticação, região, etc). Isso existe para permitir escalar para muitos portais (por exemplo, estaduais/municipais brasileiros) sem precisar escrever uma classe Python nova por portal: quem roda uma instância CKAN "de prateleira" só precisa de uma nova entrada de dado no catálogo, resolvida em runtime por `CkanPortal` (`hlib/data_recovery/portals/generic_ckan_portal.py`). Só portais com APIs genuinamente heterogêneas (`platform: "custom"`) precisam de uma classe própria, apontada via `strategy_class` — essas classes ficam organizadas em `portals/<país>/`, já que o Brasil tende a concentrar a maioria das adições futuras (portais estaduais/municipais).

Para descobrir portais disponíveis (a lista tende a crescer além do que cabe confortavelmente em autocomplete de Enum):

```python
from hlib.catalog import list_portals, search_portals

list_portals(country="BR")      # DataFrame filtrando por país/plataforma/nível/status
search_portals("dados abertos")  # busca por nome/id
```

---

## Desenvolvimento e Testes

### Pré-requisitos
- Python 3.10+
- [Poetry](https://python-poetry.org/) (gerenciador de dependências)

### Setup

```bash
git clone https://github.com/matheus-erthal/hlib.git
cd hlib
poetry install
```

### Executando Testes

```bash
poetry run pytest
```

A suíte de testes inclui **51 testes** cobrindo:
- Conectividade e parsing de resposta de cada adaptador (CKAN, API genérica)
- Busca (`search()`) e recuperação individual (`get_dataset()`) em todos os 10 portais — 9 deles via cassette de resposta real (`tests/test_cassettes.py`), o BR (que exige `api_key` própria) via mock sintético
- Download e parse de dados (`fetch_dataset_data()`) com CSV, JSON, recursos não parseáveis
- Integração via `core.py` (funções síncronas e assíncronas)

A suíte por padrão **não** faz nenhuma chamada de rede: os testes que validam o formato de resposta de cada portal (`tests/test_cassettes.py`) reproduzem respostas reais previamente capturadas, sem depender da disponibilidade dos portais no momento do teste. São esses testes que gateiam o CI e a publicação no PyPI.

### Testes de Integração (APIs Reais)

Além da suíte padrão, existem testes que fazem requisições HTTP reais aos portais, para validar que os endpoints ainda estão funcionais. Eles **não** rodam com `pytest` puro — só manualmente:

```bash
poetry run pytest -m live -v
```

> ⚠️ Estes testes fazem requisições HTTP reais e podem falhar por indisponibilidade temporária dos portais.

Toda vez que um teste `live` passa, ele grava a resposta real do portal em `tests/cassettes/` e atualiza a data de validação abaixo — essas cassettes são o que `tests/test_cassettes.py` reproduz por padrão.

#### Status de Validação ao Vivo

Data da última execução bem-sucedida de `pytest -m live`, por cassette:

<!-- live-status:start -->
| Cassette | Portal | Última validação |
| :--- | :--- | :--- |
| data_gov_us_search | data.gov (EUA) 🇺🇸 | 2026-07-20 |
| data_gov_us_get_dataset | data.gov (EUA) 🇺🇸 | 2026-07-20 |
| data_gov_uk_search | data.gov.uk (Reino Unido) 🇬🇧 | 2026-07-20 |
| data_gov_uk_get_dataset | data.gov.uk (Reino Unido) 🇬🇧 | 2026-07-20 |
| opendata_swiss_search | opendata.swiss (Suíça) 🇨🇭 | 2026-07-20 |
| opendata_swiss_get_dataset | opendata.swiss (Suíça) 🇨🇭 | 2026-07-20 |
| avoindata_fi_search | avoindata.fi (Finlândia) 🇫🇮 | 2026-07-20 |
| avoindata_fi_get_dataset | avoindata.fi (Finlândia) 🇫🇮 | 2026-07-20 |
| data_gov_au_search | data.gov.au (Austrália) 🇦🇺 | 2026-07-20 |
| data_gov_au_get_dataset | data.gov.au (Austrália) 🇦🇺 | 2026-07-20 |
| data_gouv_fr_search | data.gouv.fr (França) 🇫🇷 | 2026-07-20 |
| data_gouv_fr_get_dataset | data.gouv.fr (França) 🇫🇷 | 2026-07-20 |
| datos_gob_es_search | datos.gob.es (Espanha) 🇪🇸 | nunca validado |
| datos_gob_es_get_dataset | datos.gob.es (Espanha) 🇪🇸 | nunca validado |
| data_gov_sg_search | data.gov.sg (Singapura) 🇸🇬 | 2026-07-20 |
| data_gov_sg_get_dataset | data.gov.sg (Singapura) 🇸🇬 | 2026-07-20 |
| data_gov_in_search | data.gov.in (Índia) 🇮🇳 | 2026-07-20 |
| data_gov_in_get_dataset | data.gov.in (Índia) 🇮🇳 | 2026-07-20 |
<!-- live-status:end -->

> `dados.gov.br` fica fora dessa tabela: exige `api_key` própria, então não há como validar automaticamente contra a API real neste repositório.
>
> `data.gov` (EUA) migrou da API clássica do CKAN para a **Catalog API v4** (DCAT-US), que não tem endpoint de busca por ID. O caso comum — pedir `get_dataset()` de um dataset que já apareceu em um `search()` anterior na mesma instância de `PortalDataGovUS` — funciona normalmente, resolvido por um cache local, sem chamada de rede extra. Só para um ID "frio" (que não veio de um `search()` prévio nesta instância) é que `get_dataset()` cai num fallback paginando `/search` até achar o `identifier`, sem garantia de encontrar. Desative esse fallback com `PortalDataGovUS(id_lookup_fallback=False)` se preferir sempre `None` nesse caso frio em vez de um scan potencialmente longo.

## Licença

Este projeto é distribuído sob a licença [MIT](LICENSE).
