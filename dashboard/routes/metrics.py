import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from dashboard.charts import progress_bar, stat_card

router = APIRouter()

_KEY_FINDING = (
    "Breaking changes caught in CI in under 5 minutes. Before: discovered in production."
)


@router.get("/metrics")
async def metrics_page():
    return FileResponse("dashboard/static/metrics.html")


@router.get("/api/metrics")
async def metrics_data():
    path = Path("measurements/discipline_metrics.json")
    if not path.exists():
        return JSONResponse({"no_data": True, "seed_command": "measurements/discipline_metrics.json"})

    with open(path) as f:  # noqa: ASYNC230
        data = json.load(f)

    detection_stat = stat_card(
        value=f"{data.get('detection_time_seconds', 0)}s",
        label="CI detection time",
        sublabel="from push to failure",
        color="#22c55e",
    )
    upgrade_bar = progress_bar(
        value=data.get("upgrade_success_rate_pct", 0) / 100,
        label=f"Upgrade success rate: {data.get('upgrade_success_rate_pct', 0):.0f}%",
        color="#22c55e",
    )
    drift_stat = stat_card(
        value=f"{data.get('contract_drift_pct', 0):.0f}%",
        label="Agents on current version",
        sublabel="contract drift",
        color="#6366f1",
    )

    return JSONResponse({
        "no_data": False,
        "data": data,
        "charts": {
            "detection_stat": detection_stat,
            "upgrade_bar": upgrade_bar,
            "drift_stat": drift_stat,
        },
        "key_finding": _KEY_FINDING,
    })
