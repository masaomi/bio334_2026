"""Thin LLM call shim with backend toggle (api | bedrock | claude-code).

Per ARCHITECTURE.md §3.1, this is extracted from bio334-teaching's
chat.py to avoid pulling in the full TeachingChat with its 4 transitive
deps (knowledge, progress, prompt, timetable).

Three backends, selected by env ``BIO334_LLM_BACKEND``:

- ``api``: Anthropic SDK direct call. Default model ``claude-sonnet-4-6``,
  override via ``BIO334_LLM_MODEL`` (e.g., ``claude-opus-4-7``). Reads
  ``ANTHROPIC_API_KEY`` from env.
- ``bedrock``: Anthropic SDK via AWS Bedrock (``AnthropicBedrock``).
  Auth via the AWS credential chain — on EC2 with an attached IAM role
  no env vars are needed; off-EC2 set ``AWS_ACCESS_KEY_ID`` /
  ``AWS_SECRET_ACCESS_KEY`` (or the new Bedrock API key) plus
  ``AWS_REGION``. Model id is a Bedrock model identifier; default
  ``BIO334_BEDROCK_MODEL`` falls back to a sensible Claude Sonnet 4
  cross-region inference profile.
- ``claude-code``: subprocess ``claude -p '<prompt>' --output-format json``.
  Offline / dev only; serialized per invocation.

All three backends conform to ``llm_call(...) -> LLMResponse``.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Optional


DEFAULT_MODEL_API = "claude-sonnet-4-6"
DEFAULT_MODEL_OPUS = "claude-opus-4-7"
DEFAULT_MODEL_BEDROCK = "us.anthropic.claude-sonnet-4-20250514-v1:0"
DEFAULT_BEDROCK_REGION = "us-east-1"
CLAUDE_CODE_TIMEOUT_S = 120
API_TIMEOUT_S = 60


class LLMError(Exception):
    """Backend-agnostic LLM error. Raised on transient or permanent failure.

    The grader treats this as 'API outage' and routes the submission to the
    degraded-mode pending-status path (ARCHITECTURE.md §6.3).
    """

    def __init__(self, msg: str, *, transient: bool = True) -> None:
        super().__init__(msg)
        self.transient = transient


@dataclass
class LLMResponse:
    """Conformance contract for both backends.

    - ``text``: the model's text reply (concatenation of text blocks).
    - ``raw_json``: the full provider response serialized as JSON string.
                    Stored on submissions for I-GRADE-2 audit.
    - ``model_id``: the actual model that produced the response.
    - ``backend``: 'api' or 'claude-code'.
    """

    text: str
    raw_json: str
    model_id: str
    backend: str


def _backend() -> str:
    return os.getenv("BIO334_LLM_BACKEND", "api").strip().lower()


def _model() -> str:
    return os.getenv("BIO334_LLM_MODEL", DEFAULT_MODEL_API).strip()


def llm_call(
    prompt: str,
    *,
    system: Optional[str] = None,
    max_tokens: int = 2048,
    cache_system: bool = True,
) -> LLMResponse:
    """Single-shot LLM call. Returns LLMResponse or raises LLMError.

    Parameters
    ----------
    prompt:
        The user prompt. The grader wraps untrusted student code in
        ``<<<UNTRUSTED_STUDENT_CODE>>>`` fences before passing here
        (see ARCHITECTURE.md §6.5).
    system:
        Optional system prompt. The grader sets this to the rubric prefix.
    max_tokens:
        Output budget.
    cache_system:
        If True (default) and using the Anthropic API backend, mark the
        system prompt as a cache breakpoint via ``cache_control``. The
        grader system prompt is intentionally engineered to exceed
        Anthropic's ~1024-token cache minimum.
    """
    backend = _backend()
    if backend == "api":
        return _call_api(prompt, system=system, max_tokens=max_tokens, cache_system=cache_system)
    if backend == "bedrock":
        return _call_bedrock(prompt, system=system, max_tokens=max_tokens, cache_system=cache_system)
    if backend == "claude-code":
        return _call_claude_code(prompt, system=system, max_tokens=max_tokens)
    raise LLMError(f"Unknown BIO334_LLM_BACKEND: {backend!r}", transient=False)


def _call_api(
    prompt: str,
    *,
    system: Optional[str],
    max_tokens: int,
    cache_system: bool,
) -> LLMResponse:
    try:
        import anthropic
    except ImportError as e:
        raise LLMError(f"anthropic SDK not installed: {e}", transient=False) from e

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY not set", transient=False)

    model = _model()
    client = anthropic.Anthropic(api_key=api_key, timeout=API_TIMEOUT_S)

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system is not None:
        if cache_system:
            kwargs["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        else:
            kwargs["system"] = system

    try:
        response = client.messages.create(**kwargs)
    except anthropic.APIStatusError as e:
        # 4xx is permanent (bad input), 5xx is transient
        transient = (e.status_code or 500) >= 500
        raise LLMError(f"Anthropic API status {e.status_code}: {e}", transient=transient) from e
    except anthropic.APIConnectionError as e:
        raise LLMError(f"Anthropic API connection: {e}", transient=True) from e
    except anthropic.APITimeoutError as e:
        raise LLMError(f"Anthropic API timeout: {e}", transient=True) from e
    except Exception as e:
        raise LLMError(f"Anthropic API unknown error: {e}", transient=True) from e

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    raw_json = response.model_dump_json()

    return LLMResponse(text=text, raw_json=raw_json, model_id=model, backend="api")


def _bedrock_model() -> str:
    return os.getenv("BIO334_BEDROCK_MODEL", DEFAULT_MODEL_BEDROCK).strip()


def _call_bedrock(
    prompt: str,
    *,
    system: Optional[str],
    max_tokens: int,
    cache_system: bool,
) -> LLMResponse:
    """Anthropic on AWS Bedrock via boto3 directly (no Anthropic Python SDK).

    Why boto3 direct instead of ``anthropic.AnthropicBedrock``:
    the Anthropic SDK silently falls back to SigV4 signing with whatever
    ~/.aws/credentials profile is active, ignoring
    ``AWS_BEARER_TOKEN_BEDROCK``. That makes Bedrock API key auth
    impossible whenever the host happens to have a regular AWS profile.
    boto3 detects ``AWS_BEARER_TOKEN_BEDROCK`` for Bedrock service
    calls specifically and prefers it over SigV4, so the long-term
    Bedrock API key path actually works.

    Matches the auth pattern used by the sibling GenomicsChain project
    (Ruby ``Aws::BedrockRuntime::Client``).

    Auth resolution (boto3 default chain, in order):
      1. ``AWS_BEARER_TOKEN_BEDROCK`` env var → bearer-token auth (preferred)
      2. ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` → SigV4
      3. ``~/.aws/credentials`` default profile → SigV4
      4. IAM role attached to the EC2 instance → SigV4
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, BotoCoreError
    except ImportError as e:
        raise LLMError(f"boto3 not installed: {e}", transient=False) from e

    region = (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or DEFAULT_BEDROCK_REGION
    )
    model = _bedrock_model()

    client_kwargs: dict = {"region_name": region}
    # Pass explicit static creds only when the caller did NOT supply a
    # bearer token. Otherwise boto3's own credential chain picks up
    # ``AWS_BEARER_TOKEN_BEDROCK`` and prefers it (the whole point of
    # switching off the Anthropic SDK).
    if (
        os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
        and not os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    ):
        client_kwargs["aws_access_key_id"] = os.environ["AWS_ACCESS_KEY_ID"]
        client_kwargs["aws_secret_access_key"] = os.environ["AWS_SECRET_ACCESS_KEY"]
        if os.getenv("AWS_SESSION_TOKEN"):
            client_kwargs["aws_session_token"] = os.environ["AWS_SESSION_TOKEN"]

    try:
        client = boto3.client("bedrock-runtime", **client_kwargs)
    except Exception as e:
        raise LLMError(f"boto3 bedrock-runtime init failed: {e}", transient=False) from e

    payload: dict = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system is not None:
        if cache_system:
            payload["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        else:
            payload["system"] = system

    try:
        response = client.invoke_model(
            modelId=model,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        status = int(e.response.get("ResponseMetadata", {}).get("HTTPStatusCode") or 500)
        transient = status >= 500 or code in (
            "ThrottlingException",
            "ServiceUnavailableException",
        )
        raise LLMError(
            f"Bedrock {code} (HTTP {status}): {e}", transient=transient
        ) from e
    except BotoCoreError as e:
        raise LLMError(f"Bedrock connection: {e}", transient=True) from e
    except Exception as e:
        raise LLMError(f"Bedrock unknown error: {e}", transient=True) from e

    body = json.loads(response["body"].read())
    text = "".join(
        block.get("text", "")
        for block in body.get("content", [])
        if block.get("type") == "text"
    )
    raw_json = json.dumps(body)
    return LLMResponse(text=text, raw_json=raw_json, model_id=model, backend="bedrock")


def _call_claude_code(
    prompt: str,
    *,
    system: Optional[str],
    max_tokens: int,
) -> LLMResponse:
    """Subprocess `claude -p '<prompt>' --output-format json` backend.

    Serialized per invocation. Use for offline dev only; not for class.
    """
    full_prompt = prompt if system is None else f"{system}\n\n{prompt}"

    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=CLAUDE_CODE_TIMEOUT_S,
        )
    except FileNotFoundError as e:
        raise LLMError("claude CLI not found in PATH", transient=False) from e
    except subprocess.TimeoutExpired as e:
        raise LLMError(f"claude -p timed out after {CLAUDE_CODE_TIMEOUT_S}s", transient=True) from e

    if result.returncode != 0:
        raise LLMError(
            f"claude -p exited {result.returncode}: {result.stderr[:500]}",
            transient=True,
        )

    raw = result.stdout
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMError(f"claude -p returned non-JSON: {e}", transient=True) from e

    text = parsed.get("result") or parsed.get("text") or ""
    if not isinstance(text, str):
        text = json.dumps(text)

    return LLMResponse(text=text, raw_json=raw, model_id="claude-code", backend="claude-code")
