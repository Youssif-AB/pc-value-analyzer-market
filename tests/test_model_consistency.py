from backend.app.schemas import NormalizedSpecs
from backend.app.services.model_service import ModelService


def test_inference_is_deterministic_for_same_reviewed_specs() -> None:
    service = ModelService()
    specs = NormalizedSpecs(
        cpu="AMD Ryzen 7 7800X3D",
        gpu="NVIDIA GeForce RTX 4070",
        ram_gb=32,
        ram_type="DDR5",
        storage_gb=2048,
        storage_type="NVMe SSD",
        condition="good",
        brand="custom",
        system_age_years=1.0,
    )
    first = service.predict(specs, 1650)
    second = service.predict(specs, 1650)
    assert first.estimated_fair_price == second.estimated_fair_price
    assert first.model_version == second.model_version
    assert first.rating == second.rating
