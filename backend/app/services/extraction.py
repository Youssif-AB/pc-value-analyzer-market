import re
from datetime import UTC, datetime

from backend.app.schemas import ExtractedSpecs
from backend.app.services.normalization import (
    CPU_PATTERNS,
    GPU_PATTERNS,
    normalize_condition,
    normalize_cpu,
    normalize_gpu,
    normalize_ram_type,
    normalize_storage_type,
)

PRICE_RE = re.compile(r"(?:\$|CAD\s*|USD\s*)\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{2,5})(?:\.[0-9]{2})?", re.I)
RAM_RE = re.compile(r"\b(8|12|16|24|32|48|64|96|128|256)\s*GB\s*(DDR\s*[345])?\b", re.I)
STORAGE_RE = re.compile(r"\b(256|500|512|1000|1024|2000|2048|4000|4096|8000)\s*(GB|TB)?\s*(NVME|M\.2|SSD|HDD|hard drive)?\b", re.I)
TB_RE = re.compile(r"\b([1-8](?:\.0)?)\s*TB\s*(NVME|M\.2|SSD|HDD|hard drive)?\b", re.I)
AGE_RE = re.compile(r"\b([0-9](?:\.[0-9])?)\s*(?:years?|yrs?)\s*old\b", re.I)
YEAR_RE = re.compile(r"\b(20(?:1[5-9]|2[0-6]))\b")

BRANDS = ["Alienware", "Dell", "HP", "Lenovo", "ASUS", "Acer", "MSI", "CyberPowerPC", "iBUYPOWER", "Skytech", "Thermaltake", "NZXT", "Corsair"]


def _first_canonical(text: str, patterns: list[tuple[re.Pattern[str], str]]) -> str | None:
    for pattern, canonical in patterns:
        if pattern.search(text):
            return canonical
    return None


def _extract_price(text: str) -> float | None:
    matches = PRICE_RE.findall(text)
    if not matches:
        return None
    values: list[float] = []
    for raw in matches:
        normalized = raw.replace(",", "")
        try:
            values.append(float(normalized))
        except ValueError:
            continue
    sensible = [v for v in values if 100 <= v <= 20000]
    return sensible[-1] if sensible else (values[-1] if values else None)


def _extract_ram(text: str) -> tuple[int | None, str | None]:
    matches = list(RAM_RE.finditer(text))
    if not matches:
        return None, None
    # Prefer a capacity explicitly paired with DDR generation; this avoids treating GPU VRAM
    # such as "RTX 4070 12GB" as system memory.
    explicit = [match for match in matches if match.group(2)]
    chosen = explicit[0] if explicit else max(matches, key=lambda match: int(match.group(1)))
    return int(chosen.group(1)), normalize_ram_type(chosen.group(2))


def _extract_storage(text: str) -> tuple[int | None, str | None]:
    tb = TB_RE.search(text)
    if tb:
        return int(float(tb.group(1)) * 1024), normalize_storage_type(tb.group(2))
    match = STORAGE_RE.search(text)
    if not match:
        return None, None
    capacity = int(match.group(1))
    unit = (match.group(2) or "GB").upper()
    if unit == "TB":
        capacity *= 1024
    return capacity, normalize_storage_type(match.group(3))


def extract_listing(text: str) -> ExtractedSpecs:
    cpu_raw = _first_canonical(text, CPU_PATTERNS)
    gpu_raw = _first_canonical(text, GPU_PATTERNS)
    cpu = normalize_cpu(cpu_raw)
    gpu = normalize_gpu(gpu_raw)
    ram_gb, ram_type = _extract_ram(text)
    storage_gb, storage_type = _extract_storage(text)
    asking_price = _extract_price(text)

    condition_text = next(
        (token for token in ["brand new", "like new", "mint", "excellent", "fair", "parts", "good"] if token in text.lower()),
        None,
    )
    brand = next((brand for brand in BRANDS if brand.lower() in text.lower()), None)
    age_match = AGE_RE.search(text)
    year_match = YEAR_RE.search(text)
    system_age = float(age_match.group(1)) if age_match else None
    if system_age is None and year_match:
        system_age = float(max(0, datetime.now(UTC).year - int(year_match.group(1))))

    warnings: list[str] = []
    failures: list[str] = []
    if not cpu.value:
        warnings.append("CPU was not confidently extracted; review before prediction.")
    if not gpu.value:
        warnings.append("GPU was not confidently extracted; review before prediction.")
    if ram_gb is None:
        warnings.append("RAM capacity was not found.")
    if storage_gb is None:
        warnings.append("Storage capacity was not found.")
    if asking_price is None:
        warnings.append("Asking price was not found; enter it manually.")
    if cpu.value and not cpu.matched:
        failures.append(f"Unrecognized CPU alias: {cpu.raw}")
    if gpu.value and not gpu.matched:
        failures.append(f"Unrecognized GPU alias: {gpu.raw}")

    return ExtractedSpecs(
        cpu=cpu.value,
        gpu=gpu.value,
        ram_gb=ram_gb,
        ram_type=ram_type,
        storage_gb=storage_gb,
        storage_type=storage_type,
        condition=normalize_condition(condition_text),
        brand=brand,
        system_age_years=system_age,
        asking_price=asking_price,
        extraction_warnings=warnings,
        normalization_failures=failures,
    )
