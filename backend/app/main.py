from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.config import settings
from app.database.session import create_engine, create_session_factory
from app.retrieval.retriever import DocumentRetriever


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine()
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    app.state.retriever = DocumentRetriever(create_session_factory(engine), openai_client)
    yield
    await openai_client.close()
    await engine.dispose()


app = FastAPI(title="CVM Copilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
