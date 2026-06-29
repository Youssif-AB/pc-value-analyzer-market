from backend.app.services.extraction import extract_listing


def test_extracts_messy_listing_for_review() -> None:
    text = """
    Gaming PC - like new. Ryzen 7 7800X3D, GeForce RTX4070 12GB,
    32GB DDR5, 2TB M.2 NVMe. Asking $1,650. Built about 1 year old.
    """
    result = extract_listing(text)
    assert result.cpu == "AMD Ryzen 7 7800X3D"
    assert result.gpu == "NVIDIA GeForce RTX 4070"
    assert result.ram_gb == 32
    assert result.storage_gb == 2048
    assert result.storage_type == "NVMe SSD"
    assert result.condition == "like_new"
    assert result.asking_price == 1650


def test_missing_hardware_is_exposed_not_hidden() -> None:
    result = extract_listing("Custom desktop for sale with 16GB DDR4 and 1TB SSD. Price $650, good condition.")
    assert result.cpu is None
    assert result.gpu is None
    assert len(result.extraction_warnings) >= 2
