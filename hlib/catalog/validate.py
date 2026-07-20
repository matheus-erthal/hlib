"""Entrypoint de CI: `python -m hlib.catalog.validate`."""
import sys

from .loader import load_catalog_records


def main() -> int:
    try:
        records = load_catalog_records()
    except ValueError as e:
        print(e)
        return 1
    print(f"Catálogo válido: {len(records)} portal(is).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
