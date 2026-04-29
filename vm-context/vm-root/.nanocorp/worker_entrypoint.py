"""Worker entrypoint - runs inside the Modal sandbox.

This script is synced into the sandbox and executed for each task.
It uses the Claude Agent SDK to process the task with full tool access.
Tools are accessed via the nanocorp CLI binary (installed at /usr/local/bin/nanocorp).

Environment variables:
- AGENT_SECRET: Required for authenticating with backend
- BACKEND_URL: Backend API URL
- NANOCORP_BACKEND_URL: Backend URL for the nanocorp CLI
- RUN_ID / TASK_ID: Passed via CLI args
- ANTHROPIC_API_KEY: API key (or LiteLLM virtual key)
- ANTHROPIC_BASE_URL: Anthropic API base URL (or LiteLLM proxy)
- AGENT_MODEL: Claude model to use (default: claude-opus-4-6)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from loguru import logger
from prompts import build_worker_system_prompt
from worker_utils import (
    close_http_client,
    get_http_client,
    post_message_to_backend,
)

try:
    from claude_agent_sdk._errors import ProcessError
except ImportError:
    ProcessError = None

# Force line-buffered stdout so logs stream in real-time to the orchestrator
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# Configure loguru for sandbox — DEBUG level for full trace
logger.remove()
logger.add(sys.stdout, level="DEBUG")
# Also log ERROR+ to stderr so the orchestrator captures errors in stderr
logger.add(sys.stderr, level="ERROR")

WORKDIR = "/home/worker/workspace"
REPO_DIR = "/home/worker/repo"
# No max_turns limit — the soft timeout (see D7 in SPEC_CREDIT_USAGE_BILLING.md)
# handles execution time, not turn count. Setting max_turns causes a hard abort
# that the agent can't anticipate or wrap up from.

EXIT_CODE_AUTH_FAILURE = 2

_AUTH_PATTERNS = ("authentication", "401", "unauthorized", "invalid_api_key")


def _build_langfuse_span_attrs(run_id: str, task_id: str, model: str) -> dict[str, str]:
    """Build the dict of Langfuse-recognized attrs to set on every emitted span.

    Langfuse only treats `langfuse.user.id` and `langfuse.trace.metadata.*`
    as filterable top-level fields when they appear as span attributes on
    every span. We attach them via a custom SpanProcessor that sets the same
    set of attrs on every span the TracerProvider creates — this avoids the
    Baggage cross-thread propagation pitfall in LangSmith's queued exporter,
    where child spans started in the background thread don't see baggage
    set in the main thread.

    Empty values are excluded so they don't pollute Langfuse with empty
    strings — a missing env var means "skip the key entirely".
    """
    candidates = {
        "langfuse.user.id": os.environ.get("COMPANY_ID", ""),
        "langfuse.trace.metadata.run_id": run_id,
        "langfuse.trace.metadata.task_id": task_id,
        "langfuse.trace.metadata.company_id": os.environ.get("COMPANY_ID", ""),
        "langfuse.trace.metadata.conglomerate_id": os.environ.get("CONGLOMERATE_ID", ""),
        "langfuse.trace.metadata.agent_id": os.environ.get("AGENT_ID", ""),
        "langfuse.trace.metadata.model": model,
    }
    return {k: v for k, v in candidates.items() if v}


_RESULT_MESSAGE_TAG = "__NANOCORP_RESULT_MESSAGE__:"


def _serialize_result_message(message: ResultMessage) -> str | None:
    """Serialize a ResultMessage to a tagged JSON line for stdout.

    The orchestrator parses this tag to extract the agent's result
    and populate task.result_summary.

    Returns the full tagged line, or None on failure.
    """
    try:
        data = {
            "claude_code": {
                "result": str(message.result) if message.result else None,
                "is_error": bool(message.is_error) if message.is_error is not None else False,
                "duration_ms": message.duration_ms,
                "duration_api_ms": getattr(message, "duration_api_ms", None),
                "num_turns": message.num_turns,
                "total_cost_usd": message.total_cost_usd,
                "usage": getattr(message, "usage", None),
                "session_id": getattr(message, "session_id", None),
                "stop_reason": getattr(message, "stop_reason", None),
            }
        }
        return f"{_RESULT_MESSAGE_TAG}{json.dumps(data, default=str)}"
    except Exception:
        logger.exception("Failed to serialize result message")
        return None


def _is_auth_error(text: str) -> bool:
    """Check if error text indicates an API authentication failure."""
    lower = text.lower()
    return any(p in lower for p in _AUTH_PATTERNS)


async def _update_run_stats(
    run_id: str,
    token_count_input: int = 0,
    token_count_output: int = 0,
    cost_usd: float = 0.0,
    cache_read_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
) -> None:
    """Update run record with token/cost stats via internal API."""
    backend_url = os.environ.get("BACKEND_URL", "")
    agent_secret = os.environ.get("AGENT_SECRET", "")
    if not backend_url or not agent_secret:
        return

    url = f"{backend_url}/internal/runs/{run_id}/stats"
    headers = {"Authorization": f"Bearer {agent_secret}"}
    payload = {
        "token_count_input": token_count_input,
        "token_count_output": token_count_output,
        "cost_usd": cost_usd,
        "cache_read_input_tokens": cache_read_input_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
    }
    try:
        client = get_http_client()
        await client.put(url, json=payload, headers=headers)
    except Exception:
        logger.exception("Failed to update run stats")


async def fetch_task(task_id: str, max_retries: int = 3) -> dict[str, object] | None:
    """Fetch task details from the backend with retry."""
    backend_url = os.environ.get("BACKEND_URL", "")
    agent_secret = os.environ.get("AGENT_SECRET", "")

    url = f"{backend_url}/internal/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {agent_secret}"}
    logger.debug(f"Fetching task from {url}")

    last_error = ""
    for attempt in range(max_retries):
        try:
            client = get_http_client()
            response = await client.get(url, headers=headers)
            logger.debug(f"Task fetch response: status={response.status_code}")
            if response.status_code == 200:
                data: dict[str, object] = response.json()
                logger.debug(f"Task fetch body: {json.dumps(data, default=str)}")
                return data
            last_error = f"status={response.status_code} body={response.text[:500]}"
            logger.warning(f"Failed to fetch task (attempt {attempt + 1}/{max_retries}): {last_error}")
        except Exception as e:
            last_error = f"{type(e).__name__}: {e!r}"
            logger.warning(f"Failed to fetch task (attempt {attempt + 1}/{max_retries}): {last_error}")

        if attempt < max_retries - 1:
            await asyncio.sleep(1.0 * (attempt + 1))

    logger.error(f"Failed to fetch task after {max_retries} attempts: {last_error}")
    return None


def _setup_git_repo() -> bool:
    """Clone or pull the company's GitHub repo via SSH deploy key.

    Expects:
    - GITHUB_SSH_URL env var (e.g. git@github.com:nanocorp-hq/company.git)
    - ~/.ssh/id_ed25519 to exist on disk (injected by sandbox orchestrator)

    Returns True if repo is available at REPO_DIR.
    """
    import subprocess

    ssh_url = os.environ.get("GITHUB_SSH_URL", "")
    os.environ.get("COMPANY_HANDLE", "agent")
    home = os.environ.get("HOME", "/home/worker")

    if not ssh_url:
        logger.debug("No GITHUB_SSH_URL set, skipping git setup")
        return False

    # Verify SSH key exists
    ssh_key_path = os.path.join(home, ".ssh", "id_ed25519")
    if not os.path.exists(ssh_key_path):
        logger.warning("GITHUB_SSH_URL set but no SSH key found at ~/.ssh/id_ed25519")
        return False

    # Configure git identity
    # Email must match a real GitHub account for Vercel deployment checks
    git_email = os.environ.get("GIT_AUTHOR_EMAIL", "78322686+plbiojout@users.noreply.github.com")
    subprocess.run(
        ["git", "config", "--global", "user.name", "NanoCorp Agent"],
        check=False,
    )
    subprocess.run(
        ["git", "config", "--global", "user.email", git_email],
        check=False,
    )

    # Clone or pull
    if not os.path.exists(os.path.join(REPO_DIR, ".git")):
        logger.info(f"Cloning repo {ssh_url} to {REPO_DIR}")
        result = subprocess.run(
            ["git", "clone", ssh_url, REPO_DIR],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(f"Git clone failed: stderr={result.stderr}")
            return False
        logger.info(f"Cloned repo to {REPO_DIR}: stdout={result.stdout.strip()}")
    else:
        # Update remote URL to SSH
        subprocess.run(
            ["git", "-C", REPO_DIR, "remote", "set-url", "origin", ssh_url],
            check=False,
        )
        logger.info("Pulling latest changes with --rebase")
        result = subprocess.run(
            ["git", "-C", REPO_DIR, "pull", "--rebase"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(f"Git pull failed: stderr={result.stderr}")
        else:
            logger.info(f"Pulled latest: stdout={result.stdout.strip()}")

    return True


async def _upload_session_trace(run_id: str, session_id: str, agent_cwd: str) -> None:
    """Upload the Claude Code session JSONL to the backend.

    Constructs the session file path from session_id + cwd, reads it,
    and PUTs it to /internal/runs/{run_id}/trace. Retries up to 3 times.
    Does not fail the run on error.
    """
    # Claude Code encodes the cwd by replacing "/" with "-", keeping the leading dash
    # e.g. /home/worker/repo -> -home-worker-repo
    encoded_cwd = agent_cwd.replace("/", "-")
    session_file = Path.home() / ".claude" / "projects" / encoded_cwd / f"{session_id}.jsonl"

    if not session_file.exists():
        logger.warning(f"Session file not found at {session_file}, skipping trace upload")
        return

    file_size = session_file.stat().st_size
    logger.info(f"Uploading session trace: {session_file} ({file_size} bytes)")

    backend_url = os.environ.get("BACKEND_URL", "")
    agent_secret = os.environ.get("AGENT_SECRET", "")
    if not backend_url or not agent_secret:
        logger.warning("BACKEND_URL or AGENT_SECRET not set, skipping trace upload")
        return

    data = session_file.read_bytes()
    url = f"{backend_url}/internal/runs/{run_id}/trace?filename={session_id}.jsonl"
    headers = {
        "Authorization": f"Bearer {agent_secret}",
        "Content-Type": "application/octet-stream",
    }

    last_error = ""
    for attempt in range(3):
        try:
            client = get_http_client()
            response = await client.put(url, content=data, headers=headers, timeout=60.0)
            if response.status_code == 200:
                resp_data = response.json()
                logger.info(f"Trace uploaded: path={resp_data.get('path')} size={resp_data.get('size_bytes')}")
                return
            last_error = f"status={response.status_code} body={response.text[:200]}"
            logger.warning(f"Trace upload failed (attempt {attempt + 1}/3): {last_error}")
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(f"Trace upload failed (attempt {attempt + 1}/3): {last_error}")

        if attempt < 2:
            await asyncio.sleep(1.0 * (attempt + 1))

    logger.error(f"Trace upload failed after 3 attempts for run {run_id}: {last_error}")
    try:
        import sentry_sdk

        sentry_sdk.capture_message(
            f"Trace upload failed for run {run_id}: {last_error}",
            level="warning",
        )
    except ImportError:
        pass


async def run_agent(run_id: str, task_id: str) -> int:
    """Run the Claude Agent SDK to process the task.

    Returns exit code: 0 for success, 1 for error.
    """
    import time as _time

    _worker_start = _time.monotonic()
    logger.info(f"=== WORKER START === run_id={run_id} task_id={task_id}")

    # Log environment (no secrets)
    model = os.environ.get("AGENT_MODEL", "claude-opus-4-6")
    backend_url = os.environ.get("BACKEND_URL", "")
    company_name = os.environ.get("COMPANY_NAME", "NanoCorp Company")
    logger.info(
        f"Environment: model={model} backend_url={backend_url} "
        f"company={company_name} "
        f"has_github={bool(os.environ.get('GITHUB_SSH_URL'))} "
        f"has_vercel={bool(os.environ.get('VERCEL_PROJECT_URL'))} "
        f"has_db={bool(os.environ.get('DATABASE_URL'))}"
    )

    # Initialize Sentry for sandbox error tracking
    # Wrapped in try/except because sandboxes restored from old snapshots
    # may not have sentry-sdk installed yet
    if os.environ.get("SENTRY_DSN"):
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=os.environ.get("SENTRY_DSN"),
                environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
                traces_sample_rate=0.05,
                profiles_sample_rate=0.05,
            )
            sentry_sdk.set_tag("service", "nanocorp-sandbox-worker")
            sentry_sdk.set_tag("run_id", run_id)
            sentry_sdk.set_tag("task_id", task_id)
            logger.debug("Sentry initialized for worker sandbox")
        except ImportError:
            logger.warning("sentry-sdk not installed in sandbox, skipping Sentry init")

    # OTel + Langfuse tracing — initialized before any agent SDK construction.
    # Wrapped in try/except ImportError so worker images restored from older
    # snapshots (without langsmith/opentelemetry installed) keep working.
    # Tracing is best-effort: a failure here does not break the run.
    _otel_provider: Any = None
    try:
        from langsmith.integrations.claude_agent_sdk import configure_claude_agent_sdk
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        class _LangfuseAttrsSpanProcessor(SpanProcessor):
            """Sets a fixed set of Langfuse attrs on every emitted span.

            Replaces the BaggageSpanProcessor approach: LangSmith's OTEL
            exporter starts child spans (LLM, tool) in a background thread
            from a parent context that does NOT carry baggage seeded in the
            main thread, so baggage-propagated attrs only land on root
            spans. A static-attrs processor sidesteps cross-thread context
            propagation entirely — every span gets the attrs regardless of
            which thread or context started it.
            """

            def __init__(self, attrs: dict[str, str]) -> None:
                self._attrs = dict(attrs)

            def on_start(self, span: Any, parent_context: Any = None) -> None:
                for _ak, _av in self._attrs.items():
                    span.set_attribute(_ak, _av)

            def on_end(self, span: Any) -> None:
                return None

            def shutdown(self) -> None:
                return None

            def force_flush(self, timeout_millis: int = 30_000) -> bool:
                return True

        # Resource attrs land in Langfuse's catch-all metadata.resourceAttributes
        # (non-filterable), so we keep only OTel-standard fields here. Trace-
        # level attribution and user-id are set per-span by
        # _LangfuseAttrsSpanProcessor below — Langfuse mapping treats those as
        # queryable top-level fields when present on every span.
        _resource = Resource.create(
            {
                "service.name": "nanocorp-worker",
                "service.namespace": os.environ.get("SENTRY_ENVIRONMENT", "development"),
            }
        )
        _otel_provider = TracerProvider(resource=_resource)
        _span_attrs = _build_langfuse_span_attrs(run_id=run_id, task_id=task_id, model=model)
        _otel_provider.add_span_processor(_LangfuseAttrsSpanProcessor(_span_attrs))
        # Configure the OTLP exporter programmatically (not via env vars) so
        # the relay endpoint + agent_secret bearer don't leak to child
        # processes via OTEL_EXPORTER_OTLP_HEADERS / _ENDPOINT inheritance.
        _backend_url = os.environ.get("NANOCORP_BACKEND_URL", "").rstrip("/")
        _agent_secret = os.environ.get("AGENT_SECRET", "")
        _exporter = OTLPSpanExporter(
            endpoint=f"{_backend_url}/internal/otel/v1/traces" if _backend_url else None,
            headers={"Authorization": f"Bearer {_agent_secret}"} if _agent_secret else None,
        )
        _otel_provider.add_span_processor(BatchSpanProcessor(_exporter))
        trace.set_tracer_provider(_otel_provider)

        configure_claude_agent_sdk()
        logger.info("OTel/Langfuse tracing initialized")
    except ImportError as _ie:
        logger.warning(f"langsmith/opentelemetry not installed in sandbox, skipping tracing: {_ie}")
    except Exception as _ote:
        logger.warning(f"OTel/Langfuse init failed: {type(_ote).__name__}: {_ote}")
        _otel_provider = None

    # Set up git repo if configured
    has_repo = _setup_git_repo()
    agent_cwd = REPO_DIR if has_repo else WORKDIR
    logger.info(f"Git setup: has_repo={has_repo} cwd={agent_cwd}")

    # Symlink baked-in skills into agent cwd so the SDK discovers them
    skills_src = "/opt/nanocorp/skills"
    skills_dst = os.path.join(agent_cwd, ".claude", "skills")
    if os.path.isdir(skills_src) and not os.path.exists(skills_dst):
        os.makedirs(os.path.join(agent_cwd, ".claude"), exist_ok=True)
        os.symlink(skills_src, skills_dst)
        skill_dirs = [d for d in os.listdir(skills_src) if os.path.isdir(os.path.join(skills_src, d))]
        logger.info(f"Linked {len(skill_dirs)} skills into {skills_dst}: {skill_dirs}")

    # Fetch task details
    task_data = await fetch_task(task_id)
    if task_data is None:
        await post_message_to_backend(run_id, "error", "Failed to fetch task details")
        return 1

    task_title = str(task_data.get("title", "Unknown task"))
    task_description = str(task_data["description"]) if task_data.get("description") else None
    logger.info(f"Task: title={task_title}")
    logger.debug(f"Task description: {task_description}")

    # Build system prompt
    agent_instructions = os.environ.get("AGENT_INSTRUCTIONS", "")

    github_repo_full_name = os.environ.get("GITHUB_REPO_FULL_NAME")
    vercel_project_url = os.environ.get("VERCEL_PROJECT_URL")
    database_url = os.environ.get("DATABASE_URL")
    company_handle = os.environ.get("COMPANY_HANDLE")

    has_cli = bool(os.environ.get("HAS_CLI"))

    outbound_paused = bool(os.environ.get("OUTBOUND_PAUSED"))

    # User-provided secrets metadata (keys + descriptions only — values are in
    # their own NANO_USER_<KEY> env vars already). Missing / empty / malformed
    # all collapse to "no secrets section".
    user_secrets: list[tuple[str, str | None]] = []
    _meta_raw = os.environ.get("NANO_USER_SECRETS_META")
    if _meta_raw:
        try:
            _meta = json.loads(_meta_raw)
            if isinstance(_meta, list):
                for item in _meta:
                    if isinstance(item, dict) and isinstance(item.get("key"), str):
                        user_secrets.append((item["key"], item.get("description")))
        except Exception as _e:
            logger.warning(f"Failed to parse NANO_USER_SECRETS_META: {_e}")

    system_prompt = build_worker_system_prompt(
        task_title=task_title,
        task_description=task_description,
        company_name=company_name,
        company_handle=company_handle or None,
        agent_instructions=agent_instructions or None,
        github_repo_full_name=github_repo_full_name if has_repo else None,
        vercel_project_url=vercel_project_url or None,
        database_url=database_url or None,
        backend_url=backend_url or None,
        has_cli=has_cli,
        outbound_paused=outbound_paused,
        user_secrets=user_secrets or None,
    )
    logger.debug(f"SYSTEM_PROMPT:\n{system_prompt}")

    await post_message_to_backend(run_id, "system", f"Starting execution of task: {task_title}")

    # Build agent options (tools are accessed via nanocorp CLI binary)
    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": system_prompt,
        },
        permission_mode="bypassPermissions",
        max_turns=None,  # unlimited — soft timeout handles execution time
        model=model,
        cwd=agent_cwd,
        setting_sources=["project"],
        allowed_tools=["Skill"],
        max_buffer_size=10_000_000,  # 10MB - default 1MB is too small for large tool results
    )
    logger.info(f"Agent config: model={model} max_turns=unlimited cwd={agent_cwd}")

    # Build the prompt instructing the agent to execute the task
    prompt = f"Execute the following task.\n\nTask: {task_title}"
    if task_description:
        prompt += f"\n\nDescription: {task_description}"
    prompt += (
        "\n\nREMINDER: If the description has a 'Long term overall goal' section, that is context only — "
        "do NOT try to achieve it. ONLY work on the 'Task (what you should do now)' section. "
        "Future tasks will be created towards achieving the goal. "
        "Your result MUST list what was completed and what remains as follow-up tasks."
    )

    logger.debug(f"AGENT_PROMPT:\n{prompt}")

    # Three-phase soft timeout (SPEC_CREDIT_USAGE_BILLING.md D7):
    # Phase 1: Primary work (0 - SOFT_TIMEOUT seconds)
    # Phase 2: interrupt() + "5 min to wrap up" query
    # Phase 3: interrupt() + "wrap up NOW" query
    # Hard kill after Phase 3 timeout
    SOFT_TIMEOUT_SEC = float(os.environ.get("SOFT_TIMEOUT_MIN", "30")) * 60
    WRAPUP_TIMEOUT_SEC = float(os.environ.get("WRAPUP_TIMEOUT_MIN", "5")) * 60
    FINAL_TIMEOUT_SEC = float(os.environ.get("FINAL_TIMEOUT_MIN", "1")) * 60

    try:
        _background_tasks: set[asyncio.Task[None]] = set()
        _turn_count = 0
        _total_cost_usd = 0.0
        _last_result_message: ResultMessage | None = None
        _last_session_id: str | None = None
        _assistant_texts: list[str] = []  # All assistant text blocks across phases
        _tool_names: list[str] = []  # Tools used (for synthetic summary)

        async def _consume_response(
            client: ClaudeSDKClient,
        ) -> ResultMessage | None:
            """Consume one response from the client until its ResultMessage.

            Iterates client.receive_response() which auto-terminates after a
            ResultMessage. Captures assistant text, tool calls, and token/cost
            stats into the surrounding closure state.
            """
            nonlocal _turn_count, _total_cost_usd, _last_session_id
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    if hasattr(message, "error") and message.error == "authentication_failed":
                        logger.error("API authentication failed (detected in AssistantMessage.error)")
                        await post_message_to_backend(run_id, "error", "API authentication failed")
                        raise SystemExit(EXIT_CODE_AUTH_FAILURE)

                    _turn_count += 1
                    logger.info(f"--- Turn {_turn_count} ---")

                    for block in message.content:
                        if isinstance(block, TextBlock):
                            logger.info(f"RAW_ASSISTANT: {block.text}")
                            _assistant_texts.append(block.text)
                            bg = asyncio.create_task(post_message_to_backend(run_id, "assistant", block.text))
                            _background_tasks.add(bg)
                            bg.add_done_callback(_background_tasks.discard)

                        elif isinstance(block, ToolUseBlock):
                            _tool_names.append(block.name)
                            logger.info(
                                f"RAW_TOOL_INPUT: name={block.name} "
                                f"id={block.id} "
                                f"input={json.dumps(block.input, default=str)}"
                            )
                            bg = asyncio.create_task(
                                post_message_to_backend(
                                    run_id,
                                    "tool_use",
                                    f"Using tool: {block.name}",
                                    {"tool_name": block.name, "tool_id": block.id},
                                )
                            )
                            _background_tasks.add(bg)
                            bg.add_done_callback(_background_tasks.discard)

                        elif isinstance(block, ToolResultBlock):
                            content_str = (
                                block.content
                                if isinstance(block.content, str)
                                else json.dumps(block.content, default=str)
                            )
                            logger.info(
                                f"RAW_TOOL_OUTPUT: tool_id={block.tool_use_id} "
                                f"is_error={block.is_error} "
                                f"content={content_str}"
                            )
                            bg = asyncio.create_task(
                                post_message_to_backend(
                                    run_id,
                                    "tool_result",
                                    content_str[:1000],
                                    {"is_error": block.is_error},
                                )
                            )
                            _background_tasks.add(bg)
                            bg.add_done_callback(_background_tasks.discard)

                elif isinstance(message, ResultMessage):
                    logger.info(
                        f"=== RESULT === duration={message.duration_ms}ms "
                        f"turns={message.num_turns} "
                        f"is_error={message.is_error} "
                        f"cost=${message.total_cost_usd or 0:.4f}"
                    )
                    if message.result:
                        logger.info(f"RAW_RESULT: {message.result}")
                    _total_cost_usd += message.total_cost_usd or 0.0
                    _last_session_id = getattr(message, "session_id", None)
                    return message
            return None

        async with ClaudeSDKClient(options=options) as client:
            # Three-phase pattern:
            #   Each phase spawns a consume task and waits for its ResultMessage,
            #   shielded so a timeout doesn't cancel the consumer mid-stream.
            #   On timeout, interrupt() tells the CLI to finish — the consumer
            #   naturally drains the interrupted ResultMessage, then the next
            #   phase starts a fresh query + consume task.
            result_msg: ResultMessage | None = None

            # --- Phase 1: Primary work ---
            await client.query(prompt)
            phase1_task = asyncio.create_task(_consume_response(client))
            timed_out = False
            try:
                result_msg = await asyncio.wait_for(
                    asyncio.shield(phase1_task),
                    timeout=SOFT_TIMEOUT_SEC,
                )
            except TimeoutError:
                timed_out = True
                logger.info(f"=== SOFT TIMEOUT === after {SOFT_TIMEOUT_SEC}s, interrupting agent")
                await post_message_to_backend(run_id, "system", "Soft timeout: entering wrap-up phase")
                try:
                    await client.interrupt()
                except Exception as e:
                    logger.warning(f"Failed to interrupt client (phase 1->2): {e}")

                # Drain phase 1's interrupted ResultMessage. Capture any
                # ResultMessage the SDK produced on interrupt so it feeds
                # the finalization path below. We also need the stream
                # cleared before the phase-2 query.
                try:
                    phase1_drained = await asyncio.wait_for(asyncio.shield(phase1_task), timeout=30.0)
                    if phase1_drained is not None:
                        result_msg = phase1_drained
                        logger.info(
                            f"Phase 1 drained ResultMessage: is_error={phase1_drained.is_error} "
                            f"has_result={bool(phase1_drained.result)}"
                        )
                    else:
                        logger.info("Phase 1 drain returned None (no ResultMessage)")
                except TimeoutError:
                    logger.warning("Phase 1 consumer did not drain in 30s after interrupt")
                    if not phase1_task.done():
                        phase1_task.cancel()
                except Exception as e:
                    logger.warning(f"Phase 1 consumer errored during drain: {e}")

            if timed_out:
                # --- Phase 2: Wrap-up ---
                wrapup_prompt = (
                    "You have 5 minutes to wrap up. "
                    "Commit and push any code you've written. "
                    "Write a summary of what was completed and what remains. "
                    "Do NOT start any new work."
                )
                logger.info("=== PHASE 2: WRAP-UP ===")
                try:
                    await client.query(wrapup_prompt)
                except Exception as e:
                    logger.warning(f"Phase 2 client.query() failed: {e}")
                else:
                    phase2_task = asyncio.create_task(_consume_response(client))
                    try:
                        _phase2_result = await asyncio.wait_for(
                            asyncio.shield(phase2_task),
                            timeout=WRAPUP_TIMEOUT_SEC,
                        )
                        if _phase2_result is not None:
                            result_msg = _phase2_result
                        logger.info(f"Phase 2 consume returned: has_result={_phase2_result is not None}")
                    except TimeoutError:
                        logger.info(f"=== WRAPUP TIMEOUT === after {WRAPUP_TIMEOUT_SEC}s")
                        try:
                            await client.interrupt()
                        except Exception as e:
                            logger.warning(f"Failed to interrupt client (phase 2->3): {e}")
                        try:
                            _phase2_drain = await asyncio.wait_for(asyncio.shield(phase2_task), timeout=30.0)
                            if _phase2_drain is not None:
                                result_msg = _phase2_drain
                        except TimeoutError:
                            logger.warning("Phase 2 consumer did not drain in 30s after interrupt")
                            if not phase2_task.done():
                                phase2_task.cancel()
                        except Exception as e:
                            logger.warning(f"Phase 2 consumer errored during drain: {e}")

                        # --- Phase 3: Final warning ---
                        # Only fires if wrap-up didn't produce a usable result.
                        if result_msg is None or not result_msg.result:
                            final_prompt = (
                                "You MUST stop NOW. Output your result summary immediately. "
                                "List what was completed and what remains."
                            )
                            logger.info("=== PHASE 3: FINAL WARNING ===")
                            try:
                                await client.query(final_prompt)
                            except Exception as e:
                                logger.warning(f"Phase 3 client.query() failed: {e}")
                            else:
                                phase3_task = asyncio.create_task(_consume_response(client))
                                try:
                                    _phase3_result = await asyncio.wait_for(
                                        asyncio.shield(phase3_task),
                                        timeout=FINAL_TIMEOUT_SEC,
                                    )
                                    if _phase3_result is not None:
                                        result_msg = _phase3_result
                                except TimeoutError:
                                    logger.warning("=== HARD TIMEOUT === Agent did not respond in final phase")
                                    try:
                                        await client.interrupt()
                                    except Exception as e:
                                        logger.warning(f"Failed to interrupt client (phase 3 drain): {e}")
                                    try:
                                        _phase3_drain = await asyncio.wait_for(
                                            asyncio.shield(phase3_task), timeout=10.0
                                        )
                                        if _phase3_drain is not None:
                                            result_msg = _phase3_drain
                                    except Exception:
                                        if not phase3_task.done():
                                            phase3_task.cancel()

            _last_result_message = result_msg

        # Process the final result
        _elapsed_ms = int((_time.monotonic() - _worker_start) * 1000)

        if _last_result_message:
            # Patch the result message with accumulated cost across all phases.
            # The SDK's total_cost_usd only reflects the last query's cost,
            # but we need the total across all phases for accurate billing.
            if _total_cost_usd > (_last_result_message.total_cost_usd or 0.0):
                _last_result_message.total_cost_usd = _total_cost_usd

            # After an interrupt, the SDK's ResultMessage.result is often empty
            # because the SDK flushes the interrupted phase's result before the
            # wrap-up response (which never arrives). Build a synthetic summary
            # from the assistant text and tool calls we captured.
            if not _last_result_message.result and _assistant_texts:
                logger.info("ResultMessage.result is empty, building summary from captured activity")
                summary_parts = []
                # Use the last assistant text (most recent context)
                summary_parts.append(_assistant_texts[-1])
                if _tool_names:
                    unique_tools = list(dict.fromkeys(_tool_names))  # dedupe preserving order
                    summary_parts.append(f"\n\nTools used: {', '.join(unique_tools)}")
                summary_parts.append("\n\n*Agent was interrupted by soft timeout before completing the task.*")
                _last_result_message.result = "".join(summary_parts)

            result_text = str(_last_result_message.result) if _last_result_message.result else "Agent completed"
            await post_message_to_backend(
                run_id,
                "system",
                f"Execution completed: {result_text[:500]}",
                {
                    "duration_ms": _last_result_message.duration_ms,
                    "num_turns": _last_result_message.num_turns,
                    "cost_usd": _total_cost_usd,
                },
            )

            await _update_run_stats(
                run_id,
                token_count_input=0,
                token_count_output=0,
                cost_usd=_total_cost_usd,
            )

            _tag_line = _serialize_result_message(_last_result_message)
            if _tag_line:
                print(_tag_line)

            if _last_session_id:
                await _upload_session_trace(run_id, _last_session_id, agent_cwd)
            else:
                logger.warning("No session_id in ResultMessage, skipping trace upload")

            if _last_result_message.is_error:
                result_text = str(_last_result_message.result) if _last_result_message.result else ""
                if _is_auth_error(result_text):
                    logger.error("API authentication failed (detected in ResultMessage)")
                    return EXIT_CODE_AUTH_FAILURE
                return 1
        else:
            # No ResultMessage at all — emit a synthetic one for the orchestrator.
            # If we captured any assistant text during phase 1 (common after a
            # balance breach that interrupted an in-flight session), synthesize
            # a best-effort summary from it so the user sees what the agent was
            # doing, not a bare timeout notice.
            logger.warning("No ResultMessage received — emitting synthetic result")
            if _assistant_texts:
                summary_parts = [_assistant_texts[-1]]
                if _tool_names:
                    unique_tools = list(dict.fromkeys(_tool_names))
                    summary_parts.append(f"\n\nTools used: {', '.join(unique_tools)}")
                summary_parts.append("\n\n*Agent was interrupted before completing the task.*")
                synthetic_result_text = "".join(summary_parts)
            else:
                synthetic_result_text = "Agent timed out without producing a result summary."
            synthetic = ResultMessage(
                subtype="result",
                duration_ms=_elapsed_ms,
                duration_api_ms=0,
                is_error=True,
                num_turns=_turn_count,
                session_id=_last_session_id or "unknown",
                total_cost_usd=_total_cost_usd,
                result=synthetic_result_text,
            )
            await _update_run_stats(run_id, cost_usd=_total_cost_usd)
            _tag_line = _serialize_result_message(synthetic)
            if _tag_line:
                print(_tag_line)
            await post_message_to_backend(
                run_id,
                "system",
                f"Execution completed: {synthetic_result_text[:500]}",
                {"duration_ms": _elapsed_ms, "num_turns": _turn_count, "cost_usd": _total_cost_usd},
            )

        # Wait for background message posts before exiting
        if _background_tasks:
            logger.info(f"Waiting for {len(_background_tasks)} pending message posts...")
            _done, pending = await asyncio.wait(_background_tasks, timeout=10.0)
            if pending:
                logger.warning(f"{len(pending)} message posts timed out")
                for t in pending:
                    t.cancel()

        await close_http_client()

        _total_elapsed = _time.monotonic() - _worker_start
        logger.info(
            f"=== WORKER END === run_id={run_id} duration={_total_elapsed:.1f}s turns={_turn_count} exit_code=0"
        )
        return 0

    except SystemExit as e:
        await close_http_client()
        return e.code if isinstance(e.code, int) else 1

    except Exception as e:
        if ProcessError is not None and isinstance(e, ProcessError) and _is_auth_error(str(e)):
            logger.error(f"API auth failure via ProcessError: {e}")
            await close_http_client()
            return EXIT_CODE_AUTH_FAILURE

        import traceback

        _total_elapsed = _time.monotonic() - _worker_start
        error_msg = f"Agent execution failed: {type(e).__name__}: {e}"

        if _is_auth_error(str(e)):
            logger.error(f"API auth failure via exception: {e}")
            await close_http_client()
            return EXIT_CODE_AUTH_FAILURE

        tb = traceback.format_exc()
        logger.error(error_msg)
        logger.error(f"Traceback:\n{tb}")
        logger.info(
            f"=== WORKER END === run_id={run_id} duration={_total_elapsed:.1f}s turns={_turn_count} exit_code=1"
        )
        await post_message_to_backend(run_id, "error", error_msg)
        await close_http_client()
        return 1

    finally:
        # Drain trace buffers before the sandbox terminates. Order matters:
        # the LangSmith integration enqueues runs on its own background queue
        # (even with LANGSMITH_OTEL_ONLY=true) and the queue drains by calling
        # tracer.start_span on the OTel provider. If we only flushed the OTel
        # BatchSpanProcessor, items still sitting in the LangSmith queue would
        # be lost. Flush LangSmith first so its queue feeds OTel, then flush
        # OTel so the BatchSpanProcessor pushes to the relay.
        if _otel_provider is not None:
            try:
                from langsmith.run_trees import get_cached_client

                get_cached_client().flush(timeout=10.0)
            except Exception as _ls_e:
                logger.warning(f"LangSmith client flush failed: {type(_ls_e).__name__}: {_ls_e}")
            try:
                _otel_provider.force_flush(timeout_millis=10_000)
                _otel_provider.shutdown()
            except Exception as _flush_e:
                logger.warning(f"OTel provider shutdown failed: {type(_flush_e).__name__}: {_flush_e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NanoCorp Worker Entrypoint")
    parser.add_argument("--run-id", required=True, help="Run ID")
    parser.add_argument("--task-id", required=True, help="Task ID")
    args = parser.parse_args()

    if not args.run_id or not args.task_id:
        logger.error("Both --run-id and --task-id are required")
        sys.exit(1)

    # Ensure working directories exist
    os.makedirs(WORKDIR, exist_ok=True)
    os.makedirs(REPO_DIR, exist_ok=True)

    exit_code = asyncio.run(run_agent(args.run_id, args.task_id))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
