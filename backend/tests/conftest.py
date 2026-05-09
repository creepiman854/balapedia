"""Configuración compartida de pytest para todos los tests del backend.

Las fixtures definidas aquí (decoradas con ``@pytest.fixture``) están
disponibles automáticamente en cualquier test del directorio sin necesidad
de importarlas. Esto sigue el patrón estándar de pytest.
"""
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "wiki"


@pytest.fixture
def load_wiki_fixture():
    """Devuelve una función para cargar wikitext de fixtures por nombre.

    Uso en un test::

        def test_algo(load_wiki_fixture):
            wikitext = load_wiki_fixture("joker")
            ...

    Los archivos viven en ``tests/fixtures/wiki/<name>.txt`` con codificación
    UTF-8 (necesaria para caracteres especiales del wikitext).
    """

    def _load(name: str) -> str:
        path = FIXTURES_DIR / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"Fixture not found: {path}. "
                f"¿Olvidaste ejecutar _create_wiki_fixtures.py?"
            )
        return path.read_text(encoding="utf-8")

    return _load