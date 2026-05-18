"""Backend dispatch + Bedrock wiring tests (boto3-direct path).

We don't hit any real AWS endpoint. Instead we mock boto3.client and
check that:
- backend=bedrock is recognized (no "Unknown backend" error)
- boto3.client('bedrock-runtime', region_name=...) gets the region
  from AWS_REGION / AWS_DEFAULT_REGION
- when AWS_BEARER_TOKEN_BEDROCK is present, we do NOT pass static
  IAM creds explicitly (so boto3's own credential chain picks up the
  bearer token — the whole point of switching off AnthropicBedrock)
- when AWS_BEARER_TOKEN_BEDROCK is absent but AWS_ACCESS_KEY_ID /
  AWS_SECRET_ACCESS_KEY are set, those get forwarded explicitly
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bio334_checker.core import llm_call as llm_mod


def _fake_invoke_response(text: str = "ok"):
    """Build a fake boto3 invoke_model() response — a dict with 'body'
    that has .read() returning JSON bytes in Anthropic's Bedrock shape."""
    body_bytes = json.dumps({
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "model": "stub",
    }).encode("utf-8")
    fake_body = MagicMock()
    fake_body.read.return_value = body_bytes
    return {"body": fake_body}


def test_unknown_backend_raises_permanent(monkeypatch) -> None:
    monkeypatch.setenv("BIO334_LLM_BACKEND", "nope")
    with pytest.raises(llm_mod.LLMError) as exc:
        llm_mod.llm_call("hi")
    assert exc.value.transient is False
    assert "nope" in str(exc.value)


def test_bedrock_uses_bearer_token_path(monkeypatch) -> None:
    """When AWS_BEARER_TOKEN_BEDROCK is set, do NOT forward static
    IAM creds — let boto3's own credential chain pick up the bearer
    token for the bedrock-runtime service."""
    monkeypatch.setenv("BIO334_LLM_BACKEND", "bedrock")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "bedrock-api-key-xxx")
    # Even if these are in env (e.g. ~/.aws/credentials sourced), we
    # must NOT override boto3's bearer-token detection by passing them.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIASHOULDNOTLEAK")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "shouldnotleak")

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _fake_invoke_response("rubric verdict")
    boto3_client_factory = MagicMock(return_value=fake_client)

    with patch("boto3.client", boto3_client_factory):
        out = llm_mod.llm_call("prompt", system="sys")

    # boto3.client('bedrock-runtime', region_name='us-west-2') with
    # NO static creds in the kwargs.
    args, kwargs = boto3_client_factory.call_args
    assert args[0] == "bedrock-runtime"
    assert kwargs["region_name"] == "us-west-2"
    assert "aws_access_key_id" not in kwargs
    assert "aws_secret_access_key" not in kwargs

    assert out.backend == "bedrock"
    assert out.text == "rubric verdict"


def test_bedrock_forwards_static_creds_when_no_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("BIO334_LLM_BACKEND", "bedrock")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secrettest")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "tokentest")
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _fake_invoke_response()
    boto3_client_factory = MagicMock(return_value=fake_client)

    with patch("boto3.client", boto3_client_factory):
        llm_mod.llm_call("p")

    kwargs = boto3_client_factory.call_args.kwargs
    assert kwargs["aws_access_key_id"] == "AKIATEST"
    assert kwargs["aws_secret_access_key"] == "secrettest"
    assert kwargs["aws_session_token"] == "tokentest"
    assert kwargs["region_name"] == "eu-central-1"


def test_bedrock_iam_role_path_no_kwargs(monkeypatch) -> None:
    """EC2 IAM role case: nothing in env, boto3 walks the chain on its
    own. We should only pass region_name."""
    monkeypatch.setenv("BIO334_LLM_BACKEND", "bedrock")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _fake_invoke_response()
    boto3_client_factory = MagicMock(return_value=fake_client)

    with patch("boto3.client", boto3_client_factory):
        llm_mod.llm_call("p")

    kwargs = boto3_client_factory.call_args.kwargs
    assert kwargs == {"region_name": "us-east-1"}


def test_bedrock_default_region_when_unset(monkeypatch) -> None:
    monkeypatch.setenv("BIO334_LLM_BACKEND", "bedrock")
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _fake_invoke_response()
    boto3_client_factory = MagicMock(return_value=fake_client)

    with patch("boto3.client", boto3_client_factory):
        llm_mod.llm_call("p")

    assert boto3_client_factory.call_args.kwargs["region_name"] == \
        llm_mod.DEFAULT_BEDROCK_REGION


def test_bedrock_custom_model_via_env(monkeypatch) -> None:
    monkeypatch.setenv("BIO334_LLM_BACKEND", "bedrock")
    monkeypatch.setenv("BIO334_BEDROCK_MODEL", "eu.anthropic.claude-sonnet-4-6")

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _fake_invoke_response()
    boto3_client_factory = MagicMock(return_value=fake_client)

    with patch("boto3.client", boto3_client_factory):
        out = llm_mod.llm_call("p")

    invoke_kwargs = fake_client.invoke_model.call_args.kwargs
    assert invoke_kwargs["modelId"] == "eu.anthropic.claude-sonnet-4-6"
    assert out.model_id == "eu.anthropic.claude-sonnet-4-6"


def test_bedrock_invoke_payload_includes_system_with_cache(monkeypatch) -> None:
    """Prompt caching: when cache_system=True the system block carries
    cache_control. The boto3 invoke_model body is a JSON string, so we
    have to parse it to inspect the payload."""
    monkeypatch.setenv("BIO334_LLM_BACKEND", "bedrock")

    fake_client = MagicMock()
    fake_client.invoke_model.return_value = _fake_invoke_response()
    boto3_client_factory = MagicMock(return_value=fake_client)

    with patch("boto3.client", boto3_client_factory):
        llm_mod.llm_call("hi", system="big rubric here", cache_system=True)

    body_json = fake_client.invoke_model.call_args.kwargs["body"]
    body = json.loads(body_json)
    assert body["anthropic_version"] == "bedrock-2023-05-31"
    assert body["max_tokens"] == 2048
    assert body["system"] == [
        {"type": "text", "text": "big rubric here",
         "cache_control": {"type": "ephemeral"}}
    ]
