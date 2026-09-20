from fastapi import APIRouter, Form
from fastapi.responses import FileResponse, JSONResponse

from versioning.breaking_change_detector import detect

router = APIRouter()

_V1_EXAMPLE = """\
__all__ = [
    "AgentHarness", "HarnessResult", "HarnessConfig",
    "LifecycleManager", "AgentLifecycleState",
    "RetryPolicy", "with_retry",
    "ContractValidator", "ContractViolationError",
    "AuditEmitter", "CostTracker",
    "get_logger", "load_config",
]

class AgentHarness:
    def __init__(self, graph, agent_name, agent_version, input_schema, output_schema, config=None):
        pass
    def run(self, input_data):
        pass
    def run_count(self):
        pass
    def failure_rate(self):
        pass
"""

_V2_EXAMPLE = """\
__all__ = [
    "AgentHarness", "HarnessResult",
    "LifecycleManager", "AgentLifecycleState",
    "RetryPolicy", "with_retry",
    "ContractValidator", "ContractViolationError",
    "AuditEmitter", "CostTracker",
    "get_logger", "load_config",
]

class AgentHarness:
    def __init__(self, graph, agent_name, agent_version, input_schema, output_schema):
        pass
    def run(self, input_data, timeout=None):
        pass
    def run_count(self):
        pass
"""


@router.get("/demo")
async def demo_page():
    return FileResponse("dashboard/static/demo.html")


@router.get("/api/demo/examples")
async def demo_examples():
    return JSONResponse({"v1": _V1_EXAMPLE.strip(), "v2": _V2_EXAMPLE.strip()})


@router.post("/demo")
async def demo_post(v1_source: str = Form(...), v2_source: str = Form(...)):
    changes = detect(v1_source, v2_source)
    return JSONResponse({
        "breaking_change_count": len(changes),
        "is_breaking": len(changes) > 0,
        "summary": f"Found {len(changes)} breaking change(s)" if changes else "No breaking changes detected",
        "changes": [{"kind": c.kind, "name": c.name, "detail": c.detail} for c in changes],
    })
