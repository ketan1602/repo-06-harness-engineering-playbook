"""What the replayed stored decisions can and cannot exercise (explains misses, never hides them)."""
from __future__ import annotations

from collections import Counter


def coverage(items: list[dict]) -> dict:
    """Counts over the replayed raw decisions, from the same item list the replay used."""
    over = [i["decision"]["tokens"] for i in items if i["category"] == "over_budget"]
    refunds = [i["decision"]["arguments"].get("amount") for i in items
               if i["decision"]["tool"] == "issue_refund"]
    return {"items": len(items), "items_by_category": dict(sorted(Counter(
                i["category"] for i in items).items())),
            "suspended_agent_items": sum(i["category"] == "suspended_agent" for i in items),
            "over_budget_distinct_token_values": sorted(set(over)),
            "refund_amount_python_types": dict(Counter(type(a).__name__ for a in refunds)),
            "tool_names_containing_a_dot": sum("." in i["decision"]["tool"] for i in items),
            "distinct_tools": dict(Counter(i["decision"]["tool"] for i in items))}
