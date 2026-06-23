import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationResult:
    value: str | None
    matched: bool
    raw: str | None = None


GPU_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:geforce\s*)?rtx\s*4090", re.I), "NVIDIA GeForce RTX 4090"),
    (re.compile(r"(?:geforce\s*)?rtx\s*4080(?:\s*super)?", re.I), "NVIDIA GeForce RTX 4080"),
    (re.compile(r"(?:geforce\s*)?rtx\s*4070\s*ti\s*super", re.I), "NVIDIA GeForce RTX 4070 Ti SUPER"),
    (re.compile(r"(?:geforce\s*)?rtx\s*4070\s*ti", re.I), "NVIDIA GeForce RTX 4070 Ti"),
    (re.compile(r"(?:geforce\s*)?rtx\s*4070(?:\s*super)?", re.I), "NVIDIA GeForce RTX 4070"),
    (re.compile(r"(?:geforce\s*)?rtx\s*4060\s*ti", re.I), "NVIDIA GeForce RTX 4060 Ti"),
    (re.compile(r"(?:geforce\s*)?rtx\s*4060", re.I), "NVIDIA GeForce RTX 4060"),
    (re.compile(r"(?:geforce\s*)?rtx\s*3090(?:\s*ti)?", re.I), "NVIDIA GeForce RTX 3090"),
    (re.compile(r"(?:geforce\s*)?rtx\s*3080(?:\s*ti)?", re.I), "NVIDIA GeForce RTX 3080"),
    (re.compile(r"(?:geforce\s*)?rtx\s*3070(?:\s*ti)?", re.I), "NVIDIA GeForce RTX 3070"),
    (re.compile(r"(?:geforce\s*)?rtx\s*3060(?:\s*ti)?", re.I), "NVIDIA GeForce RTX 3060"),
    (re.compile(r"(?:geforce\s*)?rtx\s*2080(?:\s*ti|\s*super)?", re.I), "NVIDIA GeForce RTX 2080"),
    (re.compile(r"(?:radeon\s*)?rx\s*7900\s*xtx", re.I), "AMD Radeon RX 7900 XTX"),
    (re.compile(r"(?:radeon\s*)?rx\s*7900\s*xt", re.I), "AMD Radeon RX 7900 XT"),
    (re.compile(r"(?:radeon\s*)?rx\s*7800\s*xt", re.I), "AMD Radeon RX 7800 XT"),
    (re.compile(r"(?:radeon\s*)?rx\s*7700\s*xt", re.I), "AMD Radeon RX 7700 XT"),
    (re.compile(r"(?:radeon\s*)?rx\s*7600", re.I), "AMD Radeon RX 7600"),
    (re.compile(r"(?:radeon\s*)?rx\s*6800\s*xt", re.I), "AMD Radeon RX 6800 XT"),
    (re.compile(r"(?:radeon\s*)?rx\s*6700\s*xt", re.I), "AMD Radeon RX 6700 XT"),
    (re.compile(r"intel\s*arc\s*a770", re.I), "Intel Arc A770"),
    (re.compile(r"intel\s*arc\s*a750", re.I), "Intel Arc A750"),
]

CPU_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ryzen\s*9\s*7950x3d", re.I), "AMD Ryzen 9 7950X3D"),
    (re.compile(r"ryzen\s*9\s*7950x", re.I), "AMD Ryzen 9 7950X"),
    (re.compile(r"ryzen\s*9\s*7900x", re.I), "AMD Ryzen 9 7900X"),
    (re.compile(r"ryzen\s*7\s*7800x3d", re.I), "AMD Ryzen 7 7800X3D"),
    (re.compile(r"ryzen\s*7\s*7700x", re.I), "AMD Ryzen 7 7700X"),
    (re.compile(r"ryzen\s*7\s*5800x3d", re.I), "AMD Ryzen 7 5800X3D"),
    (re.compile(r"ryzen\s*7\s*5800x", re.I), "AMD Ryzen 7 5800X"),
    (re.compile(r"ryzen\s*5\s*7600x", re.I), "AMD Ryzen 5 7600X"),
    (re.compile(r"ryzen\s*5\s*5600x", re.I), "AMD Ryzen 5 5600X"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i9[-\s]?14900k[f]?", re.I), "Intel Core i9-14900K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i9[-\s]?13900k[f]?", re.I), "Intel Core i9-13900K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i7[-\s]?14700k[f]?", re.I), "Intel Core i7-14700K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i7[-\s]?13700k[f]?", re.I), "Intel Core i7-13700K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i7[-\s]?12700k[f]?", re.I), "Intel Core i7-12700K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i5[-\s]?14600k[f]?", re.I), "Intel Core i5-14600K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i5[-\s]?13600k[f]?", re.I), "Intel Core i5-13600K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i5[-\s]?12600k[f]?", re.I), "Intel Core i5-12600K"),
    (re.compile(r"(?:intel\s*)?(?:core\s*)?i5[-\s]?12400f?", re.I), "Intel Core i5-12400"),
]


def _normalize(value: str | None, patterns: list[tuple[re.Pattern[str], str]]) -> NormalizationResult:
    if not value:
        return NormalizationResult(None, False, value)
    compact = re.sub(r"[_]+", " ", value).strip()
    for pattern, canonical in patterns:
        if pattern.search(compact):
            return NormalizationResult(canonical, True, value)
    return NormalizationResult(compact, False, value)


def normalize_gpu(value: str | None) -> NormalizationResult:
    return _normalize(value, GPU_PATTERNS)


def normalize_cpu(value: str | None) -> NormalizationResult:
    return _normalize(value, CPU_PATTERNS)


def normalize_ram_type(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"ddr\s*([345])", value, re.I)
    return f"DDR{match.group(1)}" if match else value.upper().strip()


def normalize_storage_type(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.lower()
    if "nvme" in lowered or "m.2" in lowered:
        return "NVMe SSD"
    if "ssd" in lowered:
        return "SATA SSD"
    if "hdd" in lowered or "hard drive" in lowered:
        return "HDD"
    return value.strip()


def normalize_condition(value: str | None) -> str:
    if not value:
        return "good"
    lowered = value.lower().replace("-", " ").replace("_", " ")
    if "brand new" in lowered or lowered.strip() == "new":
        return "new"
    if "like new" in lowered or "mint" in lowered:
        return "like_new"
    if "excellent" in lowered:
        return "excellent"
    if "parts" in lowered or "not working" in lowered:
        return "parts"
    if "fair" in lowered:
        return "fair"
    return "good"
