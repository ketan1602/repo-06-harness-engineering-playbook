from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from eval.runner import run_eval

router = APIRouter()


@router.get("/eval")
async def eval_page():
    return FileResponse("dashboard/static/eval.html")


@router.post("/eval")
async def eval_post():
    results = run_eval()
    return JSONResponse(results)
