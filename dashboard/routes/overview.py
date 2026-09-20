from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()


@router.get("/")
async def overview_page():
    return FileResponse("dashboard/static/index.html")


@router.get("/api/overview")
async def overview_data():
    return JSONResponse({
        "article_number": "06",
        "article_title": "Harness Engineering as a Discipline",
        "central_claim": "Breaking changes discovered in production cost 10x more to fix than those caught in CI.",
        "key_finding": "Breaking changes caught in CI in under 5 minutes. Before: discovered in production.",
        "use_case": "AST-based breaking-change detection, compatibility suite, version governance playbook",
        "repo_name": "repo-06-harness-engineering-playbook",
        "series_position": "Article 06 — defines the Harness Engineer role and version governance discipline",
        "next_repo": "repo-07-agent-factory-scaffold",
    })
