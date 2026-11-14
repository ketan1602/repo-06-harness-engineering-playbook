"""Curated harness edits (data only). Labels were fixed before any guard was run.

`intended_behaviour_change` is the author's own label: does the author mean this edit to change
what the harness does or exposes. Signature-visible edits are labelled True (a deliberate interface
change). `edit_type` is the author's prediction of where the edit lives, not a measured fact.
"""
from __future__ import annotations

P = "src/harness_core/"
SUP = P + "scenarios/support/support.py"
CTL = P + "capabilities/reference/control.py"
PIPE = P + "capabilities/pipeline.py"
ON, OFF, SIG, BEN = "logic_on_replay_path", "logic_off_replay_path", "signature_visible", "benign"


def _e(id_, type_, file, find, replace, why, intended):
    return {"id": id_, "edit_type": type_, "file": file, "find": find, "replace": replace,
            "rationale": why, "intended_behaviour_change": intended}


_BUDGET_FIRST = (
    '        budget = run.manifest.budget\n'
    '        spend = await self._caps.governance.check_budget(\n'
    '            {"tokens": decision.tokens, "cost_usd": decision.cost_usd},\n'
    '            {"tokens": budget.max_tokens, "cost_usd": budget.max_cost_usd})\n'
    '        if not spend["allowed"]:\n'
    '            return "terminated", spend["reason"]\n'
    '        call = await self._caps.tools.check(\n'
    '            decision.tool, decision.arguments, run.manifest.agent_id)\n'
    '        if not call["allowed"]:\n'
    '            return "blocked", call["reason"]\n')
_CHECK_FIRST = (
    '        call = await self._caps.tools.check(\n'
    '            decision.tool, decision.arguments, run.manifest.agent_id)\n'
    '        if not call["allowed"]:\n'
    '            return "blocked", call["reason"]\n'
    '        budget = run.manifest.budget\n'
    '        spend = await self._caps.governance.check_budget(\n'
    '            {"tokens": decision.tokens, "cost_usd": decision.cost_usd},\n'
    '            {"tokens": budget.max_tokens, "cost_usd": budget.max_cost_usd})\n'
    '        if not spend["allowed"]:\n'
    '            return "terminated", spend["reason"]\n')
_LIN = ('def _linear_delay(base: float, max_delay: float, attempt: int) -> float:\n'
        '    return min(base * (attempt + 1), max_delay)\n\n\n')
_EXP = ('def _exponential_delay(base: float, max_delay: float, attempt: int) -> float:\n'
        '    return min(base * (2 ** attempt), max_delay)\n\n\n')
_STRIP = ('    for prefix in PROVIDER_PREFIXES:\n        if name.startswith(prefix):\n'
          '            return name[len(prefix):]\n    return name\n')
_ALLOW = ('        if self._allowed is not None and name not in self._allowed:\n'
          '            return {"allowed": False, "reason": f"tool_not_allowed:{name}"}\n')
_TRANS = 'AgentLifecycleState.FAILED:       [AgentLifecycleState.READY, AgentLifecycleState.SHUTDOWN],'

EDITS = [
    _e("refund_limit_raised", ON, SUP, "REFUND_LIMIT = 100.0", "REFUND_LIMIT = 200.0",
       "Raise the refund amount that needs supervisor approval from 100 to 200.", True),
    _e("nonnumeric_amount_fails_open", ON, SUP,
       "isinstance(amount, int | float):\n        return True",
       "isinstance(amount, int | float):\n        return False",
       "Treat a non-numeric refund amount as needing no approval instead of failing closed.", True),
    _e("preflight_budget_before_tool_check", ON, PIPE, _CHECK_FIRST, _BUDGET_FIRST,
       "Run the budget check before the tool-authorisation check in pre-flight.", True),
    _e("namespace_strip_any_prefix", ON, P + "adapters/normalize.py", _STRIP,
       '    return name.rpartition(".")[2]\n',
       "Strip everything up to the last dot from a tool name, not only the provider prefix.", True),
    _e("budget_check_inclusive", ON, CTL, 'if v > limits.get(k, float("inf"))',
       'if v >= limits.get(k, float("inf"))',
       "Treat spend exactly at the limit as over budget.", True),
    _e("any_named_approver_accepted", ON, CTL, "if approver not in self._approvers:",
       "if not approver:", "Accept any non-empty approver id instead of the allow-list.", True),
    _e("suspended_agents_allowed", ON, CTL, 'frozenset({"suspended", "retired"})',
       'frozenset({"retired"})', "Stop treating a suspended agent as blocked.", True),
    _e("tool_grant_check_removed", ON, P + "capabilities/reference/runtime.py",
       "        if tool not in self._grants.get(identity, set()):\n"
       '            return {"allowed": False, "reason": f"tool_not_allowed:{tool}"}\n', "",
       "Drop the per-identity tool grant check in the reference tool registry.", True),
    _e("backoff_base_three", OFF, P + "retry.py", "base * (2 ** attempt)", "base * (3 ** attempt)",
       "Make exponential backoff triple instead of double.", True),
    _e("failed_state_no_recovery", OFF, P + "lifecycle.py", _TRANS,
       "AgentLifecycleState.FAILED:       [AgentLifecycleState.SHUTDOWN],",
       "A FAILED agent can no longer return to READY.", True),
    _e("audit_drops_span_id", OFF, P + "audit.py", '            "span_id": self._span_id,\n', "",
       "Stop including span_id in audit events.", True),
    _e("registry_ignores_allowed_tools", OFF, P + "tools.py", _ALLOW, "",
       "ToolRegistry.check no longer enforces allowed_tools.", True),
    _e("harness_requires_tenant_id", SIG, P + "harness.py",
       "        output_schema: type[BaseModel],\n        config:",
       "        output_schema: type[BaseModel],\n        tenant_id: str,\n        config:",
       "Add a required tenant_id parameter to AgentHarness.__init__.", True),
    _e("lifecycle_history_removed", SIG, P + "lifecycle.py",
       "    def state_history(self) -> list[dict]:\n        return self._history.copy()\n\n", "",
       "Remove the public LifecycleManager.state_history method.", True),
    _e("docstring_reworded", BEN, SUP, "Whether a request needs a human.",
       "Say whether a request must be routed to a human.",
       "Reword the needs_approval docstring.", False),
    _e("local_variable_renamed", BEN, PIPE, _CHECK_FIRST,
       _CHECK_FIRST.replace("budget = ", "limits = ").replace("budget.max", "limits.max"),
       "Rename the local variable `budget` to `limits` in pre-flight.", False),
    _e("helper_definitions_reordered", BEN, P + "retry.py", _LIN + _EXP, _EXP + _LIN,
       "Swap the definition order of the linear and exponential delay helpers.", False),
]
