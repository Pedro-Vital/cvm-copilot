"""OpenAI embedding generation for document chunks."""

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
