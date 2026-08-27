import os

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_core.runnables import RunnableConfig

from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.backends.context_hub import ContextHubBackend

from agent.tools import TOOLS
from context import CONTEXT_HUB_REPO, get_prompt
from utils.streaming import iter_text
from utils.models import MODEL_CONFIG, build_model

# AGENTS.md is the agent's system prompt — pulled fresh from LangSmith
# Context Hub at module import.
# Seed source: utils/context_hub.py (`_SEED_AGENTS_MD`), pushed to Context Hub by
# `scripts/setup.py` (`push_agents_md()`). A prompt fix can be applied BOTH as a
# PR to that seed AND to the live Context Hub.
SYSTEM_PROMPT = get_prompt()

# Override with CHAT_LANGCHAIN_LITE_MODEL env var — used by setup.py to seed
# baseline experiments against a more expensive model (Sonnet) for the
# demo's cost/latency comparison.
# Gateway `provider/model` tag. Defaults to the same model the Gateway pane
# advertises, so an unset CHAT_LANGCHAIN_LITE_MODEL behaves exactly as before.
_DEFAULT_MODEL = MODEL_CONFIG["model"]


def _model_id() -> str:
    return os.getenv("CHAT_LANGCHAIN_LITE_MODEL") or _DEFAULT_MODEL


# The Context Hub-backed filesystem holds the agent's OWN context (AGENTS.md,
# playbooks) — it is a read-only reference, NOT a user-delivery channel.
_READONLY_FS_TOOLS = {"ls", "read_file", "glob", "grep"}


def _readonly_context_hub_fs() -> FilesystemMiddleware:
    fs = FilesystemMiddleware(backend=ContextHubBackend(CONTEXT_HUB_REPO))
    fs.tools = [t for t in fs.tools if t.name in _READONLY_FS_TOOLS]
    return fs


def build_agent():
    return create_agent(
        # Built per call from _model_id() so CHAT_LANGCHAIN_LITE_MODEL actually
        # switches the model (setup.py's baseline experiments rely on this), not
        # just the trace metadata. temperature is omitted — the gateway's Bedrock
        # route rejects it as deprecated; the intentional demo bugs (tone, scope,
        # truncation) come from the prompt and max_tokens, not sampling.
        model=build_model(_model_id()),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[_readonly_context_hub_fs()],
    )


def _config(thread_id: str | None = None) -> RunnableConfig:
    metadata = {"demo": "true", "demo_type": "chat-lc-lite", "model": _model_id()}
    if thread_id:
        metadata["thread_id"] = thread_id
    return RunnableConfig(
        run_name="chat-lc-lite-demo",
        metadata=metadata,
        tags=["engine-demo", CONTEXT_HUB_REPO],
    )


def _user_msg(question: str) -> dict:
    return {"messages": [{"role": "user", "content": question}]}


def _message_text(message) -> str:
    """Return a message's user-visible text, flattening Anthropic block lists."""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text") or ""
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def invoke_agent(question: str, thread_id: str | None = None) -> dict:
    """Run the agent once. Returns {output, tools_called, messages}."""
    result = build_agent().invoke(_user_msg(question), _config(thread_id))
    output = next(
        (text for m in reversed(result["messages"]) if (text := _message_text(m))),
        "",
    )
    if not output:
        raise ValueError(
            "Agent produced no text content — the final AI message carried only "
            "thinking/tool blocks. Check that max_tokens leaves room for a text "
            "block after any reasoning budget."
        )
    tools_called = [m.name for m in result["messages"] if isinstance(m, ToolMessage)]
    return {"output": output, "tools_called": tools_called, "messages": result["messages"]}


def stream_agent(question: str, thread_id: str | None = None):
    """Stream the agent's response text as it's generated."""
    for chunk, _meta in build_agent().stream(
        _user_msg(question), _config(thread_id), stream_mode="messages"
    ):
        if isinstance(chunk, AIMessageChunk):
            yield from iter_text(chunk)
