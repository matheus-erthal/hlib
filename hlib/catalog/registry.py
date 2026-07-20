import importlib

from ..data_recovery.portals.generic_ckan_portal import CkanPortal


def _build_ckan(record, **runtime_config):
    cfg = {**record.platform_config, **runtime_config}
    return CkanPortal(base_url=record.base_url, source_portal=record.source_portal_label, **cfg)


def _build_custom(record, **runtime_config):
    if not record.strategy_class:
        raise ValueError(f"Portal '{record.id}' está com platform=custom mas sem strategy_class no catálogo.")
    module_path, _, class_name = record.strategy_class.rpartition(".")
    cls = getattr(importlib.import_module(module_path), class_name)
    return cls(**runtime_config)


PLATFORM_BUILDERS = {
    "ckan": _build_ckan,
    "custom": _build_custom,
}
