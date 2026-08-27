"""Centralized model initialization"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load THIS repo's .env, anchored to this file rather than the process CWD.
# The old `dotenv_path="../.env"` resolved outside the repository and, with
# override=True, silently replaced LANGSMITH_API_KEY / LANGSMITH_WORKSPACE_ID
# with a neighbouring project's values on import — which sent traces to the
# wrong workspace and made setup.py's run-rules calls 404. override=False keeps
# real env vars (and langgraph.json's own "env": ".env" load) authoritative.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from langchain.chat_models import init_chat_model
from langsmith import traceable

# --- Anthropic-on-Bedrock via the LangSmith LLM Gateway ---
# Routes every model call through the LangSmith Gateway so that workspace
# policies (PII / secrets / allow-lists / cost caps) are enforced. No direct
# Anthropic key is involved: the gateway holds the upstream Bedrock credential.
#
# `base_url` is the gateway root with no path — langchain-anthropic appends
# `/v1/messages` itself. `model` must use the `provider/model` form the unified
# route requires (a bare id returns 400); the prefix picks which workspace
# secret the gateway resolves upstream, and this workspace holds a Bedrock one.
#
# MODEL_CONFIG is the single source the frontend's Gateway pane reads, so it
# carries non-secret metadata only — the API key never belongs in here.
MODEL_CONFIG = {
    "model": "bedrock/anthropic.claude-sonnet-5",
    "provider": "anthropic",
    "base_url": "https://gateway.smith.langchain.com",
}

# Gateway auth is a LangSmith key, not an Anthropic one. Prefer the dedicated
# gateway key, then the name used elsewhere, then the plain workspace key so CI
# (which exports only LANGSMITH_API_KEY) and schema-only imports don't hard-fail
# on a missing var the way os.environ[...] did.
GATEWAY_API_KEY = (
    os.environ.get("LANGSMITH_API_KEY_GATEWAY")
    or os.environ.get("LANGSMITH_GATEWAY_API_KEY")
    or os.environ.get("LANGSMITH_API_KEY")
    or "missing-langsmith-api-key"
)



def build_model(model_name: str | None = None):
    """Gateway-routed chat model, defaulting to MODEL_CONFIG["model"].

    `model_name` must be a gateway `provider/model` tag (e.g.
    "bedrock/anthropic.claude-haiku-4-5") — a bare model id returns 400. Keeping
    this a factory lets callers pick a model per run (baseline experiments,
    CHAT_LANGCHAIN_LITE_MODEL) without duplicating the gateway routing or the
    credential resolution above.
    """
    return init_chat_model(
        model=model_name or MODEL_CONFIG["model"],
        model_provider=MODEL_CONFIG["provider"],
        base_url=MODEL_CONFIG["base_url"],
        api_key=GATEWAY_API_KEY,
        max_tokens=300,
        # claude-sonnet-5 emits an extended-thinking block by default, which ate
        # the whole 300-token budget: responses came back as blocks=['thinking']
        # with stop_reason=max_tokens and no text at all, so the chat UI rendered
        # an empty bubble. Disabled so the budget goes to visible text.
        thinking={"type": "disabled"},
    )


@traceable(name="chat-lc-lite-probe", run_type="llm")
def probe_model(prompt: str, model_name: str | None = None):
    """One-off model call for ad-hoc probes, named so it can't land as a bare root run."""
    return build_model(model_name).invoke(prompt)
