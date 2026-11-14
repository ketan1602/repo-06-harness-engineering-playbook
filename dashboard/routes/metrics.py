import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from dashboard.charts import progress_bar, stat_card

router = APIRouter()

_NOT_MEASURED = "not measured"
_BEFORE_AFTER = Path("measurements/detector_before_after.json")


def _key_finding() -> str:
    if not _BEFORE_AFTER.exists():
        return "No detector measurement file found; run python -m eval.before_after."
    overall = json.loads(_BEFORE_AFTER.read_text())["overall_in_scope"]
    return (
        f"On authored cases only: baseline detector caught {overall['caught_by_baseline']} of "
        f"{overall['expected_breaking']} breaking changes, fixed detector {overall['caught_by_fixed']} of "
        f"{overall['expected_breaking']} (partly circular: same author wrote fix and cases)."
    )


def _fmt(value, template: str) -> str:
    return _NOT_MEASURED if value is None else template.format(value)


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

    detection = data.get("detection_time_seconds")
    upgrade = data.get("upgrade_success_rate_pct")
    drift = data.get("contract_drift_pct")
    detection_stat = stat_card(
        value=_fmt(detection, "{}s"),
        label="CI detection time",
        sublabel="from push to failure",
        color="#22c55e",
    )
    upgrade_bar = progress_bar(
        value=(upgrade or 0) / 100,
        label=f"Upgrade success rate: {_fmt(upgrade, '{:.0f}%')}",
        color="#22c55e",
        pct_text=_fmt(upgrade, "{:.0f}%"),
    )
    drift_stat = stat_card(
        value=_fmt(drift, "{:.0f}%"),
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
        "key_finding": _key_finding(),
    })
