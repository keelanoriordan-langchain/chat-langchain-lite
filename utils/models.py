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

# --- Default: OpenAI, direct ---
# model = init_chat_model("openai:gpt-4.1-mini")

# --- LangSmith LLM Gateway, OpenAI-compatible route ---
# Routes every model call through the LangSmith Gateway so that workspace
# policies (PII / secrets / allow-lists / cost caps) are enforced. No direct
# provider key is involved: the gateway resolves the upstream credential.
#
# `GATEWAY` is the unified `/v1` endpoint — langchain-openai appends
# `/chat/completions` itself. Model ids must use the `provider/model` form (a
# bare id returns 400); the gateway translates to whichever upstream format the
# prefix selects, so `bedrock/...` tags (setup.py baselines) work here too.
GATEWAY = "https://gateway.smith.langchain.com/v1"
DEFAULT_MODEL = "custom/gpt-5.6-luna-langsmith-gateway"
MAX_TOOL_CALLS_PER_RUN = 20

# Gateway auth is a LangSmith key, not a provider one. Prefer a dedicated
# gateway key (either name — CI exports LANGSMITH_API_KEY_GATEWAY),
# then the plain workspace key, so CI and schema-only imports don't hard-fail
# on a missing var. `or` rather than nested .get() defaults so an empty value
# falls through instead of being sent as the key.
GATEWAY_API_KEY = (
    os.environ.get("LANGSMITH_GATEWAY_API_KEY")
    or os.environ.get("LANGSMITH_API_KEY_GATEWAY")
    or os.environ.get("LANGSMITH_API_KEY")
    or "missing-langsmith-api-key"
)

# MODEL_CONFIG is the single source the frontend's Gateway pane reads, so it
# carries non-secret metadata only — the API key never belongs in here.
MODEL_CONFIG = {
    "model": DEFAULT_MODEL,
    "provider": "openai",
    "base_url": GATEWAY,
}


def build_model(model_name: str | None = None):
    """Gateway-routed chat model, defaulting to DEFAULT_MODEL.

    `model_name` must be a gateway `provider/model` tag (e.g.
    "bedrock/anthropic.claude-haiku-4-5") — a bare model id returns 400. Keeping
    this a factory lets callers pick a model per run (baseline experiments,
    CHAT_LANGCHAIN_LITE_MODEL) without duplicating the gateway routing or the
    credential resolution above.
    """
    return init_chat_model(
        model_name or DEFAULT_MODEL,
        model_provider=MODEL_CONFIG["provider"],
        base_url=GATEWAY,
        api_key=GATEWAY_API_KEY,
        # temperature is omitted: GPT-5-class models reject non-default values.
        max_tokens=300,
        # max_tokens is sent as max_completion_tokens, which also covers
        # reasoning tokens. At the default effort, long answers spent the whole
        # 300-token budget reasoning and came back with no text at all, so the
        # chat UI rendered an empty bubble. "none" puts the budget into visible
        # text. (This model rejects "minimal"; "low" still burned ~230 tokens.)
        reasoning_effort="none",
    )


model = build_model()

# --- Anthropic, direct ---
# model = init_chat_model("anthropic:claude-sonnet-4-5")

# --- Azure OpenAI ---
# from langchain_openai import AzureChatOpenAI
# model = AzureChatOpenAI(azure_deployment="gpt-4.1-mini", streaming=True)

# --- AWS Bedrock, direct ---
# from langchain_aws import ChatBedrockConverse
# model = ChatBedrockConverse(
#     provider="anthropic",
#     model_id="anthropic.claude-sonnet-4-20250514-v1:0",
# )
