# chat-lc-lite

A LangChain ecosystem chatbot ("Chat LangChain Lite") with intentional bugs, built to demonstrate LangSmith Engine's ability to identify issues in agent traces and propose fixes via PR. The agent answers questions about LangChain, LangGraph, LangSmith, and Deep Agents using three tools: `lookup_concept`, `get_setup_guide`, and `get_security_advice`.

## What this demos

1. **Engine identifies bugs** — the agent has bugs in the prompt and code that cause bad responses
2. **Engine proposes a PR fix** — targets the root cause code and opens a PR on your fork
3. **Engine proposes offline examples and online evals to add** — expand dataset coverage and monitoring with one click
4. **Offline evals in CI/CD** — the PR can't merge until eval scores pass a threshold
5. **Before/after scores in LangSmith** — CI's PR-branch ("after") experiment lands next to the `baseline-*` ("before") experiments seeded by setup

## The bugs

Bugs are spread across three files so Engine has to reason about code, not just prompts:

| # | Bug | File / Location | Effect | Caught by |
|---|-----|------|--------|-----------|
| 1 | "Never use tools, never decline" instruction | LangSmith Context Hub (`chat-lc-lite-agent-<your-name>` / AGENTS.md) — fix in the Context Hub UI, not the repo | Answers any topic; answers from memory instead of calling tools | `tool_usage`, `scope_adherence` |
| 2 | Casual / emoji voice | LangSmith Context Hub (`chat-lc-lite-agent-<your-name>` / AGENTS.md) — fix in the Context Hub UI, not the repo | Every response starts with "Hey there! 👋", uses emojis throughout, ends with "Happy building! 🚀" | `professional_tone` |
| 3 | Wrong docs URL in SAFE_PATTERNS | `agent/tools.py` | Agent recommends stale `python.langchain.com` / `js.langchain.com` links instead of `docs.langchain.com` | `security_advice` |
| 4 | Wrong LangGraph min Python version | `agent/tools.py` | Returns "3.7+" instead of the correct "3.10+" | `factual_accuracy` |
| 5 | `max_tokens=300` | `utils/models.py` (`build_model`) | Truncates responses on complex technical questions | `response_completeness` |

## Setup

**1. Fork and clone this repo**

**2. Create a virtual environment**
```bash
uv sync
source .venv/bin/activate
```

Or with pip:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e . "langgraph-cli[inmem]"
```

> `uv sync` installs `langgraph-cli` (a project dependency) for you; the pip
> path installs it explicitly. The CLI runs the graph server that serves both
> the API and the chat UI (`langgraph dev`).

**3. Configure environment**
```bash
cp .env.example .env
```

Edit `.env`:
```
LANGSMITH_API_KEY=your-demo-workspace-api-key
LANGSMITH_GATEWAY_API_KEY=your-gateway-key
LANGSMITH_PROJECT=chat-lc-lite
LANGSMITH_WORKSPACE_ID=your-demo-workspace-id
LANGSMITH_TRACING=true
DEMO_PRESENTER=your-name
```

> The agent's model calls go through the LangSmith LLM Gateway (see [Model](#model)), so the agent needs no provider key. `LANGSMITH_GATEWAY_API_KEY` must belong to a role with `gateway:invoke`; `LANGSMITH_API_KEY_GATEWAY` is accepted too, and if neither is set the code falls back to `LANGSMITH_API_KEY`. The offline eval judge is the exception: it calls Claude with the `anthropic` SDK, so `scripts.run_evals` also needs the `ANTHROPIC_*` variables from `.env.example`.
>
> `DEMO_PRESENTER` scopes your dataset (`chat-lc-lite-scope-<your-name>`), Context Hub repo (`chat-lc-lite-agent-<your-name>`), and cleanup's `baseline-<your-name>` git tag.

> If multiple presenters share a LangSmith workspace, use a unique `LANGSMITH_PROJECT` per person (e.g. `chat-lc-lite-morgan`) to avoid mixing traces and online evaluators. The project is created automatically on first use.

**4. Run one-shot setup**
```bash
python -m scripts.setup
```

This does five things in one command:
1. **Seeds Context Hub** — pushes the buggy `AGENTS.md` and demo skills to `chat-lc-lite-agent-<your-name>`
2. **Creates the LangSmith project** by sending one trace (required before online evaluators can be registered)
3. **Creates the dataset** `chat-lc-lite-scope-<your-name>` with 3 curated test cases, then tags that version as `baseline` in LangSmith
4. **Creates 6 online evaluators** in the LangSmith Evaluators UI at 100% sampling rate — every future trace is automatically scored for `security_advice`, `scope_adherence`, `tool_usage`, `response_completeness`, `professional_tone`, and `factual_accuracy`. Their run rule IDs are saved to `.demo_state.json` so cleanup can tell them apart from evaluators Engine adds.
5. **Seeds `baseline-*` experiments** — one run of the dataset per model (Haiku and Sonnet) as the "before" reference for CI's PR experiment. Skip with `--skip-baseline-experiments`.

Only needs to be run once. Between demos, run `python -m scripts.cleanup` instead.

**5. Generate traces**
```bash
python -m scripts.generate_traces
```

Runs 11 single-turn queries and 1 multi-turn threaded conversation through the buggy agent to populate LangSmith with trace and thread variety beyond the dataset examples.

**6. Add GitHub secrets** (for CI/CD)

In your fork: Settings → Secrets and variables → Actions → add secrets `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, and `LANGSMITH_WORKSPACE_ID`, plus a repository **variable** `DEMO_PRESENTER`.

> **Important:** When pasting secrets, make sure there are no trailing newlines or spaces.

**7. Enable GitHub Actions**

In your fork: Actions → (if prompted) enable workflows. GitHub disables Actions on forks by default — this step is required for offline evals to run on PRs.

**8. Connect Engine**

In LangSmith Engine, connect your LangSmith project (`LANGSMITH_PROJECT`) and your GitHub fork so Engine can read traces and open PRs against your repo.

## Demo flow

### Before the demo

```bash
# One-shot setup: creates dataset, sets up online evaluators
python -m scripts.setup

# Generate more traces including threads
python -m scripts.generate_traces

# Start the chat UI (graph API + FastHTML frontend, served from one origin)
uv run langgraph dev
```

`uv run langgraph dev` boots the LangGraph server; the chat UI is mounted on it and
served at the server root (**http://localhost:2024/**). The graph API on the same
port powers streaming, thread history, and feedback.

### During the demo

1. Show Chat LangChain Lite UI — ask questions (concept lookups, setup guides, security advice, etc.); rate responses 👍/👎 to send feedback to LangSmith
2. Show traces in LangSmith with online eval scores (`security_advice`, `scope_adherence`, etc.)
3. Engine analyzes traces and identifies root causes across prompt and code
4. Add Engine-suggested offline examples — show ability to edit in annotation queue
5. Engine opens a PR on your fork
6. Add the `run-evals` label to the PR — GitHub Actions runs evals on the PR branch (the "after" experiment) and passes the 0.7 threshold ✅
7. Merge the PR
8. Add Engine-suggested online eval
9. Show the experiments in LangSmith — the CI experiment against the `baseline-*` "before" experiments

### After the demo

```bash
python -m scripts.cleanup
```

## The chat UI

The frontend (`web/app.py`) is a [FastHTML](https://fastht.ml) app mounted onto
the LangGraph server, so a single `langgraph dev` (or one deployment) serves both
the UI and the graph API from the same origin. It talks to the graph over the
LangGraph SDK on loopback — it never imports the graph directly.

- **Streaming chat** — responses stream token-by-token over SSE, rendered as
  markdown client-side (sanitized with DOMPurify).
- **Feedback** — rate any response 👍/👎 and leave an optional comment; feedback
  is written to LangSmith (as `user_score` / `user_comment`) keyed to the run, so
  it shows up on the trace and feeds online evals.
- **Trace deep-link** — every response has a ↗ Trace link that opens its LangSmith
  trace.
- **Thread history** — a sidebar lists prior conversations; reopening a thread
  rebuilds it from the graph's persisted state, with each response's stored vote
  restored.

## Model

The app's model calls go through the [LangSmith LLM Gateway](https://docs.langchain.com/langsmith/llm-gateway), so workspace gateway policies (guardrails, spend caps, rate limits) apply and no provider key lives in the app. The config is in `utils/models.py`:

| Setting | Value | Notes |
|---------|-------|-------|
| `GATEWAY` | `https://gateway.smith.langchain.com/v1` | The gateway's OpenAI-compatible route, called via `langchain-openai` |
| `DEFAULT_MODEL` | `custom/gpt-5.6-luna-langsmith-gateway` | The model the agent runs. Gateway model IDs use the `provider/model` form |
| `MAX_TOOL_CALLS_PER_RUN` | `20` | Enforced by `ToolCallLimitMiddleware` in `agent/agent.py`. Past the cap, tool calls are blocked and the model answers |

The chat UI's Gateway pane reads `MODEL_CONFIG` from the same file to show the route, and lists the workspace's live gateway policies.

The evaluators don't use this config. The offline judge (`evals/evaluators.py`) calls Claude Haiku with the `anthropic` SDK, which reads `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` from the environment. The online evaluators from `scripts/setup.py` run inside LangSmith on the workspace's own model credentials.

## Scripts

| Script | What it does |
|--------|-------------|
| `python -m scripts.setup` | One-shot setup: creates dataset and creates 6 online evaluators |
| `python -m scripts.generate_traces` | Runs 11 single-turn queries + 1 multi-turn thread through the buggy agent |
| `python -m scripts.run_evals` | Runs offline evals against the dataset and prints scores |
| `python -m scripts.run_evals --skip-dataset` | Re-runs evals against existing dataset (used in CI) |
| `python -m scripts.run_evals --threshold 0.7` | Exits with code 1 if scores < 0.7 (used in CI) |
| `python -m scripts.cleanup` | Resets demo to clean state — see Cleanup section |
| `python -m scripts.cleanup --full` | Same, plus deletes the LangSmith project (so Engine sees a fresh project on the next demo). Re-run `scripts.setup` after. |
| `uv run langgraph dev` | Start the graph server with the Chat LangChain Lite UI mounted on it (http://localhost:2024/) |

## Evaluators

CI runs one offline LLM-as-judge evaluator, `assertion_evaluator` (`evals/evaluators.py`). Each dataset example carries a list of assertions. Claude Haiku judges each assertion yes/no, and the example scores `assertions_pass_rate`: the fraction of its assertions that passed. The feedback comment has a ✓/✗ breakdown per assertion. Examples Engine proposes use the same assertion format, so they're scored the same way.

## Online Evaluators

Online evaluators run automatically on every trace as it arrives in LangSmith. This gives Engine a continuous signal on live traffic, not just offline evals on a fixed dataset.

Six online evaluators are registered by `python -m scripts.setup`: `security_advice`, `scope_adherence`, `tool_usage`, `response_completeness`, `professional_tone`, and `factual_accuracy`.

## CI/CD

`.github/workflows/evals.yml` runs on PRs to `main` that carry the `run-evals` label. The gate is manual on purpose: Engine opens both quick-fix PRs (no gating wanted) and regression-prevention PRs (gating wanted), and you label the latter by hand. Labels applied by `GITHUB_TOKEN` don't trigger workflows.

Add these to your repo (Settings → Secrets and variables → Actions):
- Secrets: `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_WORKSPACE_ID`
- Variable: `DEMO_PRESENTER`

`LANGSMITH_PROJECT` should match what you used locally — that's the project the agent traces against.

```
PR labeled run-evals → GitHub Actions → run_evals --skip-dataset --threshold 0.7
                                                    ↓
                                         scores < 0.7 → ❌ blocks merge
                                         scores ≥ 0.7 → ✅ mergeable
```

CI runs a single experiment on the PR branch (the "after"). The "before" reference is the `baseline-*` experiments seeded by `scripts/setup.py`. A before/after pair on the PR alone would score identically for Context Hub fixes, because those PRs have an empty diff. Because `--skip-dataset` fetches the existing dataset from LangSmith by name, any examples Engine adds to the dataset are included in the eval run automatically.

## Repo structure

```
context/
└── __init__.py       # get_prompt() — pulls the agent's system prompt from
                      # LangSmith Context Hub at runtime. The prompt content
                      # lives in the hub, not this repo (Bugs 1 & 2 are fixed
                      # in the Context Hub UI, not via code PR).

agent/
├── tools.py          # concept lookup, setup guides, security advice (Bugs 3 & 4)
└── agent.py          # create_agent + read-only Context Hub filesystem + tool-call limit

utils/
├── models.py         # LangSmith Gateway model config (Bug 5 — max_tokens)
├── streaming.py      # provider-agnostic text extraction for streamed chunks
└── context_hub.py    # setup-time push helper. Holds the *initial seed* for
                      # Context Hub only; not the runtime source of truth.

evals/
├── dataset.py        # creates per-user LangSmith dataset (3 curated examples)
└── evaluators.py     # assertion-based LLM-as-judge evaluator (used in CI)

scripts/
├── setup.py          # one-shot setup: dataset + online evaluators + Context Hub
├── generate_traces.py    # populate LangSmith with extra traces and threads
├── run_evals.py          # offline evals + CI threshold check
└── cleanup.py            # resets demo to clean state after presentation

.github/workflows/
└── evals.yml                 # CI/CD: offline evals on PRs to main, gated on the
                              # manually-applied 'run-evals' label

web/
└── app.py           # Chat LangChain Lite UI (FastHTML). Mounted onto the graph
                     # server via langgraph.json's `http.app`, so the UI and the
                     # graph API are served from the same origin.

langgraph.json       # LangGraph deployment manifest: exposes the `chat_langchain_lite` graph
                     # and mounts the FastHTML UI (`http.app`).
```

## Cleanup

Run after the demo to reset everything for the next presenter:

```bash
python -m scripts.cleanup
```

This does five things:
1. **Resets dataset to original 3 examples** — deletes all examples and re-uploads the canonical 3, removing anything Engine added
2. **Deletes CI/Engine experiments** — keeps the `baseline-*` seed experiments from `setup.py` (the Haiku-vs-Sonnet "before" reference); CI/CD regenerates before/after experiments on every PR
3. **Removes Engine-added online evaluators** — uses saved run rule IDs from `.demo_state.json` to delete only evaluators Engine added, leaving the 6 from `setup.py` in place
4. **Re-seeds Context Hub to the buggy baseline** — re-pushes the seed `AGENTS.md` and demo skills, restoring the buggy prompt if it was fixed in the Context Hub UI during the demo (a code/dataset reset can't touch Context Hub)
5. **Resets main to the `baseline-<your-name>` tag** — force-resets to remove Engine's merged PR, restoring the buggy agent state. The tag name is derived from `DEMO_PRESENTER`, so create it once on your fork with `git tag -a baseline-<your-name> -m "..." && git push origin baseline-<your-name>` before the first cleanup

After cleanup, the demo is ready to run again — no need to re-run `setup.py`.

For a **full** reset that also removes the LangSmith project (clearing all traces and Engine's per-project issue state):

```bash
python -m scripts.cleanup --full
python -m scripts.setup         # recreates project, dataset, evaluators
python -m scripts.generate_traces
```

Use this when you want Engine to see a completely fresh project for the next demo — for example when a new presenter takes over and you don't want them to inherit any pre-flagged issues.
