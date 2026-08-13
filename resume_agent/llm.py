from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, TypeVar

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(Path(__file__).parent / ".env")

MODEL = "claude-sonnet-4-6"
REQUEST_TIMEOUT = 60.0

# These calls are I/O-bound (waiting on network round trips), so a thread pool gives
# real parallelism despite the GIL. Bounded rather than unbounded so a JD with many
# requirements doesn't fire off dozens of simultaneous requests and trip API rate limits.
MAX_CONCURRENT_CALLS = 6

T = TypeVar("T")
R = TypeVar("R")

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        # local_address="0.0.0.0" forces IPv4; some networks have a broken IPv6
        # path to api.anthropic.com where the TCP handshake succeeds but no data
        # ever flows, hanging requests indefinitely.
        http_client = httpx.Client(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.HTTPTransport(local_address="0.0.0.0"),
        )
        _client = Anthropic(timeout=REQUEST_TIMEOUT, http_client=http_client)
    return _client


def call_structured(
    system: str,
    user: str,
    schema: type[BaseModel],
    tool_name: str,
    model: str = MODEL,
    max_tokens: int = 4096,
) -> BaseModel:
    client = get_client()
    tool = {
        "name": tool_name,
        "description": f"Return data matching the {tool_name} schema.",
        "input_schema": schema.model_json_schema(),
    }
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return schema.model_validate(block.input)
    raise RuntimeError(f"Claude did not return a {tool_name} tool_use block")


def run_concurrent(fn: Callable[[T], R], items: list[T]) -> list[R]:
    """Runs fn(item) for each item in a bounded thread pool instead of a sequential
    loop — for independent LLM/embedding calls (e.g. judging N JD requirements, one
    per requirement) this turns N sequential network round trips into ceil(N /
    MAX_CONCURRENT_CALLS) parallel batches. Preserves input order in the result."""
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_CALLS, len(items))) as executor:
        futures = [executor.submit(fn, item) for item in items]
        return [f.result() for f in futures]
