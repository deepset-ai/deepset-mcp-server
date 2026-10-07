---
name: evaluation
description: Use this skill before writing, reviewing or fixing an Evaluator (an Evaluation Function) for the Haystack Enterprise Platform, before suggesting which Evaluators a pipeline needs, and before picking the Sessions an Experiment should run on. Covers the @metrics declaration and its grains, the return shape the worker enforces, the judge() contract for LLM-judged criteria, the exact source shape the Judge form can open, how to find Sessions (including failed and negatively rated ones), and structural recipes over the Session helpers.
---

# Evaluators on the Haystack Enterprise Platform

## Overview

An **Evaluator** is a versioned Python function, the Evaluation Function, that reads one **Session** and reports named **Metrics**. A Session is one user's turns that share a `search_session_id`; a run without one is a single-turn Session named by its `query_id`. An **Experiment** is a named set of Evaluators run against chosen Sessions of one pipeline; each run is a grid of Sessions by Evaluators.

Two kinds of Evaluator, one mechanism:

- **Structural**: plain code over the Session's traces (tool calls, failures, tokens, replies). Deterministic, free, and the right first suggestion for agent pipelines.
- **Judged**: the function calls `judge()`, which has an Agent read the Session and report each criterion. Right for RAG and chat quality (faithfulness, helpfulness). Costs one Agent run per Session on the customer's model provider.

Everything below is enforced: hub-api reads the declaration when the Evaluator is saved and refuses a bad one with a 422, and the eval worker refuses a return that does not match it.

## The function

```python
from dc_haystack_utilities.evaluation import Label, NotApplicable, Score, metrics, replies, traces

@metrics(
    answered=Label(grain="turn", vocabulary=["answered", "unanswered"]),
    answer_rate=Score(grain="session"),
)
def evaluate(session, focus):
    turns = traces(session)
    answered = {
        f"turn/{n}": Label(label="answered" if replies(turns[n - 1]) else "unanswered")
        for n in focus
    }
    rate = sum(a.label == "answered" for a in answered.values()) / len(focus) if focus else None
    return {
        "answered": answered,
        "answer_rate": Score(score=rate) if rate is not None else NotApplicable(reason="no turns in focus"),
    }
```

Rules:

- **Exactly one public top-level function.** Helpers are underscore-prefixed or imported. The function's name does not matter; `evaluate` is the convention.
- **Signature `(session, focus)`.** `focus` is the list of turn numbers the run asks about, **numbered from 1**. `traces(session)[n - 1]` is turn `n`.
- **Imports** come from `dc_haystack_utilities.evaluation`; the standard library is available.
- Source is at most 64 000 characters.

## `@metrics`: declaring what the function reports

- Keyword arguments only, one per Metric: `key=Score(grain=...)` or `key=Label(grain=..., vocabulary=[...])`. Keys are Python identifiers.
- **Literals only.** hub-api reads the decorator with `ast.literal_eval` without running the code: no variables, no comprehensions, no constants defined elsewhere.
- **Two shapes.**
  - `Score`: a number. Declared `Score(grain=...)`; returned `Score(score=0.8, rationale="...")`.
  - `Label`: one of a set of answers. Closed with a `vocabulary`, open without one. Returned `Label(label="yes", rationale="...")`. A yes/no is a two-value Label. Labels have no order; if a mean matters, declare a Score.
  - Every returned value may carry a `rationale`. It is what a report groups failures by, so write one whenever the value is not self-explanatory.
  - A vocabulary may not contain `n/a` or similar; that is `NotApplicable`.
- **Grains** say where a Metric repeats:

| Grain | An address that fits it |
| --- | --- |
| `session` | `session` |
| `turn` | `turn/3` |
| `turn/retriever` (or `turn/*`) | `turn/3/retriever#0` |
| `turn/*/inputs.*` | `turn/3/llm#0/inputs.prompt` |
| `turn/retriever/outputs.documents[*]` | `turn/3/retriever#0/outputs.documents[2]` |

  Components are matched by their name in the pipeline YAML; `#0` is the first time that component ran in the turn.
- **A function without `@metrics` is legacy**: it reports one session Metric keyed `value`. Do not write new ones.
- **Changing a saved Evaluator**: a new version may not change what an existing key measures (its shape, its grain, a narrowed vocabulary, open versus closed). Add a new key instead.

## What the function returns

- A dict with **every declared key**.
- A `session` Metric maps to one value. A finer Metric maps each address to a value: `{"turn/1": Score(score=1.0), "turn/2": ...}`.
- A `turn` Metric needs an entry for **every focused turn**.
- `NotApplicable(reason="...")` stands in for any value. It is counted separately and kept out of means, which a `0` would not be. When nothing exists below a turn (an item Metric on a turn that retrieved nothing), put it at the turn address, `turn/4`.

## Judged criteria: `judge()`

```python
from dc_haystack_utilities.evaluation import Label, Score, judge, metrics


@metrics(
    faithful=Label(grain="turn", vocabulary=["faithful", "unfaithful"]),
    helpful=Score(grain="session"),
)
def evaluate(session, focus):
    return judge(
        session,
        focus,
        evaluator=evaluate,
        criteria={
            "faithful": "Is every claim in the reply supported by a retrieved document?",
            "helpful": "How far did the assistant get the user to their goal?",
        },
        score_range=(0, 1),
        chat_generator={...},  # a workspace Model's whole chat_generator_config
    )
```

- `evaluator=` is the function itself; `judge()` reads each criterion's shape, grain and vocabulary from its `@metrics`. Every key in `criteria` must be declared.
- **Grains a judge answers**: `session`, `turn`, and item grains that name their component and socket, such as `turn/document_joiner/outputs.documents[*]` (never `turn/*/...`).
- **A judged Label must be closed** (have a `vocabulary`).
- `score_range=(low, high)` is required as soon as one criterion is a Score, and is shared by all of them.
- `chat_generator` is a workspace Model's whole `chat_generator_config`, inlined; read it with `get_models`. Do not invent one. It carries secret names (`{"type": "env_var", ...}`), never values.
- Several criteria in one `judge()` share one Agent, one read of the Session and one bill. Criteria judged together correlate; split them into separate Evaluators when that matters.
- A judge that cannot conclude raises; it never reports a Metric of zero. The cell then shows as `ERRORED` with the error in `error_detail`.

### The shape the Judge form opens

The metric editor opens a judged Evaluator as a form, which the user can keep editing without code, only when the source has the shape of the example above. Anything else saves fine but opens as code. Precisely:

- Exactly one decorator, `@metrics(...)`, and each Metric is `Label(grain=..., vocabulary=[two or more strings])` or `Score(grain=...)`.
- Grains `"session"` or `"turn"` only.
- The function body is only `return judge(...)`, with no keyword arguments beyond `evaluator`, `criteria`, `score_range` and `chat_generator`.
- `criteria` keys equal the `@metrics` keys, and there is at least one.
- `score_range` is present when any criterion is a Score.

Prefer this shape when a user will want to tune the rubric themselves.

## Finding Sessions

- **A sample by source and time**: `list_sessions`, filtered by `origin` (`SERVICE`, `PIPELINE_RUN`, `PLAYGROUND`), Service, pipeline version, or `since`/`until`. It lists only Sessions a run can still read, and its `session_id` is what a run takes.
- **Sessions that went wrong**: `list_pipeline_traces` with an OData `query_filter`, then take each row's `search_session_id`, or its `query_id` when that is empty.
  - Failed turns: `status eq 'failed'`
  - Negative feedback: `feedbacks/score eq 'INACCURATE'`
  - Positive feedback: `feedbacks/score eq 'ACCURATE'`
  - No feedback: `feedbacks eq null`
  - Combine with a window: `status eq 'failed' and created_at ge 2026-09-28T00:00:00Z`
- **The turns of one Session**: `list_pipeline_traces` with `search_session_id eq '<id>'`, `sort_field="created_at"`, `sort_order="ASC"`. The full trace of one turn: `get_pipeline_trace` with its `query_id`.
- Sessions picked by a filter or a time window are `SAMPLED`. Sessions a user named, or that were picked because they looked wrong, are `HAND_PICKED`. Only sampled runs say anything about traffic as a whole.
- A run takes at most 100 Sessions and 500 cells (Sessions times Evaluators). A Session whose traces were deleted shows up in the run's `unresolved_sessions`, not as an error.

## Structural recipes

The helpers read one trace (`traces(session)[n - 1]`) or the Session with a turn number. They return empty values rather than raising when data is missing, for example when content tracing was off for a run.

| Helper | Returns |
| --- | --- |
| `traces(session)` | the turns' traces, in order |
| `failed(trace)` | whether the run failed |
| `replies(trace)` | every text the run's LLMs replied with |
| `token_usage(trace)` | `{"prompt_tokens", "completion_tokens", "total_tokens"}` |
| `models(trace)` | model names that generated tokens |
| `component_output(trace, name)` / `component_input(trace, name)` | one component's recorded sockets |
| `spans(trace, component=None)` | raw spans |
| `tool_calls_for_turn(session, n)` | `[{"tool", "arguments", "result"}]` for an Agent's turn `n` |
| `documents_for_turn(session, n)` | documents retrieved in turn `n` |
| `list_items(session, n, component, socket)` | a list-valued socket item by item, with each item's address |

**Failed turns**

```python
from dc_haystack_utilities.evaluation import Label, NotApplicable, Score, failed, metrics, traces


@metrics(
    turn_status=Label(grain="turn", vocabulary=["failed", "ok"]),
    failure_rate=Score(grain="session"),
)
def evaluate(session, focus):
    turns = traces(session)
    status = {f"turn/{n}": Label(label="failed" if failed(turns[n - 1]) else "ok") for n in focus}
    if not focus:
        return {"turn_status": status, "failure_rate": NotApplicable(reason="no turns in focus")}
    rate = sum(value.label == "failed" for value in status.values()) / len(focus)
    return {"turn_status": status, "failure_rate": Score(score=rate)}
```

**Tokens per turn**

```python
from dc_haystack_utilities.evaluation import Score, metrics, token_usage, traces


@metrics(total_tokens=Score(grain="turn"))
def evaluate(session, focus):
    turns = traces(session)
    return {
        "total_tokens": {
            f"turn/{n}": Score(score=token_usage(turns[n - 1])["total_tokens"]) for n in focus
        }
    }
```

**Repeated tool calls (agent pipelines)**

```python
import json

from dc_haystack_utilities.evaluation import NotApplicable, Score, metrics, tool_calls_for_turn


@metrics(tool_calls=Score(grain="turn"), repeated_tool_calls=Score(grain="turn"))
def evaluate(session, focus):
    calls, repeated = {}, {}
    for n in focus:
        made = tool_calls_for_turn(session, n)
        if not made:
            calls[f"turn/{n}"] = repeated[f"turn/{n}"] = NotApplicable(reason="no tool calls")
            continue
        seen = [(c["tool"], json.dumps(c["arguments"], sort_keys=True, default=str)) for c in made]
        duplicates = len(seen) - len(set(seen))
        calls[f"turn/{n}"] = Score(score=len(made))
        repeated[f"turn/{n}"] = Score(
            score=duplicates,
            rationale=f"{duplicates} of {len(made)} calls repeated an earlier call" if duplicates else None,
        )
    return {"tool_calls": calls, "repeated_tool_calls": repeated}
```

**Turns per Session**

```python
from dc_haystack_utilities.evaluation import Score, metrics, traces


@metrics(turns=Score(grain="session"))
def evaluate(session, focus):
    return {"turns": Score(score=len(traces(session)))}
```

Answered-or-not is the example under [The function](#the-function).

## Checking a pipeline change on real Sessions

Use this after a change to the pipeline (usually on its draft version) to see whether it holds up on Sessions it has already served. It is a check, not a measurement.

1. **Pick the Sessions.** Take the ones that motivated the change, plus a small sample of recent ones from `list_sessions`. Use at most five.
2. **Pick the Evaluators.** Choose the saved ones that measure what the change is about (`list_evaluators`), and read each one's source with `get_evaluator(evaluator_id, version_id=latest_version.evaluator_version_id)`.
3. **Say what it costs, and wait for a yes.**
   - Each replay runs the pipeline once per replayed turn on the customer's models.
   - Each try of a judged Evaluator costs about one model call per judged turn.
4. **Replay** each Session against the draft: `replay_session(session_id, pipeline_version_id=<draft version id>)`.
   - For a chat pipeline, pass `replay_mode="ALL_USER_MESSAGES"` where the server supports it. Otherwise only the first turn is replayed.
   - Keep each `replayed_session_id`.
5. **Try** each Evaluator's source on the source Session and on its replay with `try_evaluator`.
6. **Report per Session.**
   - Say what held, what changed, and both rationales.
   - Use "held" or "changed on these Sessions", never "improved": a handful of Sessions is a sanity check.
   - Say how many turns were replayed.

A replay leaves the source Session and the deployed pipeline untouched. Its new Session is tagged as a replay.

## Checklist before showing a draft

1. One public function, `(session, focus)`, imports from `dc_haystack_utilities.evaluation`.
2. `@metrics` arguments are literals; every key is returned, and every focused turn for a `turn` Metric.
3. Turn numbers start at 1; addresses are `turn/<n>`.
4. `NotApplicable(reason=...)` instead of a `0` or a missing key.
5. For a judge: closed Labels, `score_range` when a Score is judged, and a real `chat_generator_config` from `get_models`.
6. When a try tool is available, try the draft on one to three Sessions before calling it ready, and read the `error_detail` of a try that breaks.
