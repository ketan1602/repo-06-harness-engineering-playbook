"""Subprocess worker: replay stored raw decisions through whichever harness_core is first on
PYTHONPATH. Stdlib + harness_core only. Usage: replay_worker.py <items.json> <out.json> <version>.

The tag's own `live_model` runs unchanged; only the network client under it is replaced by a fake
that returns the stored raw decision, so exactly one thing varies: the harness version.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import types


def fake_openai(current: dict) -> types.SimpleNamespace:
    async def create(**_):
        d = current["decision"]
        message = types.SimpleNamespace(content=json.dumps(
            {"tool": d["tool"], "arguments": d["arguments"]}))
        usage = types.SimpleNamespace(total_tokens=d.get("tokens", 0))
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)], usage=usage)

    class Client:
        def __init__(self, **_):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=create))
    return Client


def summarise(out: dict) -> dict:
    return {"status": out["status"], "effects": out["effects"], "violated": out["violated"],
            "interventions": out["interventions"], "attempts": out["attempts"],
            "normalizations": out.get("normalizations"), "passed": out["verdict"]["passed"]}


async def replay(items: list[dict]) -> list[dict]:
    import openai
    from harness_core.scenarios.support.cases import load_cases, run_harnessed

    cases, current, results = {c["id"]: c for c in load_cases()}, {}, []
    openai.AsyncOpenAI = fake_openai(current)
    for item in items:
        key = {k: item[k] for k in ("dataset", "model", "framework", "case", "repeat")}
        if item["case"] not in cases:
            results.append({**key, "error": "case id not in this harness version"})
            continue
        current["decision"] = item["decision"]
        try:
            out = await run_harnessed(cases[item["case"]], model_name=item["model"])
            results.append({**key, **summarise(out)})
        except Exception as exc:  # noqa: BLE001 - recorded per item, never hidden
            results.append({**key, "error": f"{type(exc).__name__}: {exc}"})
    return results


def main(items_path: str, out_path: str, expected_version: str) -> int:
    import harness_core
    if harness_core.__version__ != expected_version:
        print(f"version mismatch: {harness_core.__version__} != {expected_version}", file=sys.stderr)
        return 2
    os.environ["LLM_API_KEY"] = "replay-not-a-key"
    os.environ["LLM_BASE_URL"] = "http://replay.invalid"
    with open(items_path) as fh:
        items = json.load(fh)
    results = asyncio.run(replay(items))
    with open(out_path, "w") as fh:
        json.dump({"harness_version": harness_core.__version__, "results": results}, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
