from backend.app.schemas import NormalizedSpecs
from backend.app.services.features import FEATURE_COLUMNS, specs_to_frame


def test_feature_contract_excludes_asking_price() -> None:
    specs = NormalizedSpecs(cpu="AMD Ryzen 7 7800X3D", gpu="NVIDIA GeForce RTX 4070", ram_gb=32, ram_type="DDR5", storage_gb=2048, storage_type="NVMe SSD", condition="good")
    frame = specs_to_frame(specs)
    assert list(frame.columns) == FEATURE_COLUMNS
    assert "asking_price" not in frame.columns
    assert frame.loc[0, "cpu_score"] > 0
    assert frame.loc[0, "gpu_score"] > 0


def test_unknown_hardware_has_conservative_fallback_score() -> None:
    specs = NormalizedSpecs(cpu="Rare CPU", gpu="Rare GPU", condition="good")
    frame = specs_to_frame(specs)
    assert frame.loc[0, "cpu_score"] == 35
    assert frame.loc[0, "gpu_score"] == 30
