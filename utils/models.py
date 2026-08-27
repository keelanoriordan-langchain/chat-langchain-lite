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
model = init_chat_model(
    model=MODEL_CONFIG["model"],
    model_provider=MODEL_CONFIG["provider"],
    base_url=MODEL_CONFIG["base_url"],
    api_key=os.environ["LANGSMITH_API_KEY_GATEWAY"],
    max_tokens=4096,
    temperature=0,
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
