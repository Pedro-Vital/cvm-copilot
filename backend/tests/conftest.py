from collections.abc import Callable
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.logging_setup import configure_logging
from app.retrieval.types import RetrievedPassage

# Same renderer as the app: the default rich tracebacks take minutes to
# render through PydanticAI's agent graph when a test hits log.exception.
configure_logging()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _passage_row(**overrides) -> dict:
    return {
        "chunk_id": uuid4(),
        "document_id": UUID(int=100),
        "chunk_index": 7,
        "content": "Receita líquida por segmento.",
        "page": 91,
        "section": "Notas Explicativas — Informações por segmento",
        "ticker": "VALE3",
        "company_name": "VALE S.A.",
        "form": "DFP",
        "fiscal_year": 2023,
        "reference_period": date(2023, 12, 31),
        "source_url": "https://example.com/vale-2023",
    } | overrides


@pytest.fixture
def make_row() -> Callable[..., dict]:
    """A hydrated chunk row, shaped like app.database.documents results."""
    return _passage_row


@pytest.fixture
def make_passage() -> Callable[..., RetrievedPassage]:
    def factory(**overrides) -> RetrievedPassage:
        return RetrievedPassage(**({"fusion_score": 0.03} | _passage_row() | overrides))

    return factory
