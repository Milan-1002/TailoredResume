from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

EMBEDDING_MODEL = "text-embedding-3-small"
REQUEST_TIMEOUT = 60.0

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        # Force IPv4 — see llm.py for why (broken IPv6 path hangs requests forever).
        http_client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.HTTPTransport(local_address="0.0.0.0"),
        )
        _client = OpenAI(timeout=REQUEST_TIMEOUT, http_client=http_client)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
