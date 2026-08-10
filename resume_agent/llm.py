from pathlib import Path

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(Path(__file__).parent / ".env")

MODEL = "claude-sonnet-4-6"
REQUEST_TIMEOUT = 60.0

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
