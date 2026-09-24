"""OpenAI embeddings, shared by ingestion (chunks) and retrieval (queries).

One code path for both sides so the model and dimensions can't drift apart —
a query vector is only comparable to chunk vectors from the same model.
"""

from openai import AsyncOpenAI

from app.config import settings

# The embeddings endpoint accepts many inputs per call; batch generously to
# cut request count while staying well under payload/token limits.
BATCH_SIZE = 100


async def embed_texts(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        response = await client.embeddings.create(
            input=batch,
            model=settings.openai_embedding_model,
            dimensions=settings.openai_embedding_dimensions,
        )
        embeddings.extend(item.embedding for item in response.data)
    return embeddings


async def embed_query(client: AsyncOpenAI, text: str) -> list[float]:
    [embedding] = await embed_texts(client, [text])
    return embedding
