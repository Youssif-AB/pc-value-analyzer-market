from fastapi import APIRouter

from backend.app.services.features import CPU_SCORE, GPU_SCORE

router = APIRouter(prefix="/hardware", tags=["hardware"])


@router.get("/catalog")
def hardware_catalog() -> dict[str, list[str]]:
    return {
        "cpus": sorted(CPU_SCORE.keys()),
        "gpus": sorted(GPU_SCORE.keys()),
    }