"""Centralized model initialization"""

import os
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env", override=True)

from langchain.chat_models import init_chat_model

# --- Default: OpenAI, direct ---
# model = init_chat_model("openai:gpt-4.1-mini")

# --- OpenAI via the LangSmith LLM Gateway ---
# Routes every model call through the LangSmith Gateway so that workspace
# policies (PII / secrets / allow-lists / cost caps) are enforced.
# MODEL_CONFIG is the single source the frontend's Gateway pane reads.
# MODEL_CONFIG is also the single source of truth for the model id and
# generation cap traced as root-run metadata (agent/agent.py), so the label on a
# trace can never drift from the model that actually ran.
MODEL_CONFIG = {
    "model": os.getenv("CHAT_LANGCHAIN_LITE_MODEL") or "claude-sonnet-4-6",
    "provider": "anthropic",
    "base_url": "https://gateway.smith.langchain.com/anthropic",
    "max_tokens": 300,
}
model = init_chat_model(
    model=MODEL_CONFIG["model"],
    model_provider=MODEL_CONFIG["provider"],
    base_url=MODEL_CONFIG["base_url"],
    api_key=os.environ["LANGSMITH_API_KEY_GATEWAY"],
    max_tokens=MODEL_CONFIG["max_tokens"],
    temperature=0,
)

# --- Anthropic ---
# model = init_chat_model("anthropic:claude-sonnet-4-5")

# --- Azure OpenAI ---
# from langchain_openai import AzureChatOpenAI
# model = AzureChatOpenAI(azure_deployment="gpt-4.1-mini", streaming=True)

# --- AWS Bedrock ---
# from langchain_aws import ChatBedrockConverse
# model = ChatBedrockConverse(
#     provider="anthropic",
#     model_id="anthropic.claude-sonnet-4-20250514-v1:0",
# )