import pytest

from backend.app.services.normalization import normalize_cpu, normalize_gpu, normalize_storage_type


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("RTX4070", "NVIDIA GeForce RTX 4070"),
        ("GeForce RTX 4070 12GB", "NVIDIA GeForce RTX 4070"),
        ("NVIDIA 4070", "NVIDIA GeForce RTX 4070"),
        ("Radeon RX 7900 XTX 24GB", "AMD Radeon RX 7900 XTX"),
    ],
)
def test_gpu_aliases(raw: str, expected: str) -> None:
    assert normalize_gpu(raw).value == expected


def test_cpu_alias() -> None:
    assert normalize_cpu("Intel i7 13700KF").value == "Intel Core i7-13700K"


def test_nvme_normalization() -> None:
    assert normalize_storage_type("2TB M.2 NVMe") == "NVMe SSD"
