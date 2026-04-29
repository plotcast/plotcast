"""Utilities for worker agent execution in sandbox.

Provides:
- post_message_to_backend: posts run messages to the internal API
- get_http_client / close_http_client: shared async HTTP client management
"""

from __future__ import annotations

import asyncio
import os

import httpx
from loguru import logger


def _strip_null_bytes(text: str) -> str:
    """Remove null bytes that PostgreSQL rejects in text columns."""
    return text.replace("\x00", "") if text else text


# Shared httpx client — reuses TCP connections across all requests.
# Avoids creating a new connection + TLS handshake per call.
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create the shared async HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _http_client


async def close_http_client() -> None:
    """Close the shared HTTP client. Call before process exit."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


async def post_message_to_backend(
    run_id: str,
    message_type: str,
    content: str,
    metadata: dict[str, object] | None = None,
    max_retries: int = 3,
) -> None:
    """Post a run message to the backend API with retry."""
    backend_url = os.environ.get("BACKEND_URL", "")
    agent_secret = os.environ.get("AGENT_SECRET", "")

    if not backend_url or not agent_secret:
        logger.warning("BACKEND_URL or AGENT_SECRET not set, skipping message post")
        return

    url = f"{backend_url}/internal/runs/{run_id}/messages"
    headers = {"Authorization": f"Bearer {agent_secret}"}
    payload = {
        "message_type": message_type,
        "content": _strip_null_bytes(content),
        "metadata": metadata or {},
    }

    last_error = ""
    for attempt in range(max_retries):
        try:
            logger.debug(f"Posting message (attempt {attempt + 1}): type={message_type} content_len={len(content)}")
            client = get_http_client()
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (200, 201):
                logger.debug(f"Message posted: type={message_type}")
                return
            last_error = f"status={response.status_code} body={response.text[:200]}"
            logger.warning(f"Failed to post message (attempt {attempt + 1}): {last_error}")
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(f"Failed to post message (attempt {attempt + 1}): {last_error}")

        if attempt < max_retries - 1:
            await asyncio.sleep(0.5 * (attempt + 1))

    logger.error(
        f"Failed to post message after {max_retries} attempts: "
        f"run_id={run_id} type={message_type} last_error={last_error}"
    )
