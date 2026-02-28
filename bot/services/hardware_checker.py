"""Hardware compatibility checker based on official HuntMe Hardware Guide.

Validates candidate CPU/GPU against minimum requirements:
- CPU: 4 cores / 8 threads minimum (Intel i3 10th gen+ or AMD Ryzen 3 3000+)
- GPU: any discrete GPU, approximately GTX 1050 level or above
- MacBook: NOT supported
- Internet: 100 Mbps minimum
"""

import re
from dataclasses import dataclass


@dataclass
class HardwareResult:
    cpu_ok: bool
    gpu_ok: bool
    cpu_reason: str
    gpu_reason: str

    @property
    def compatible(self) -> bool:
        return self.cpu_ok and self.gpu_ok


# --- Intel CPUs: 10th gen (10xxx) and above ---
# Format: {generation: minimum supported}
INTEL_MIN_GEN = 10  # 10th gen minimum

# Intel tiers (all supported from 10th gen+): i3, i5, i7, i9
INTEL_TIERS = {"i3", "i5", "i7", "i9"}

# --- AMD Ryzen CPUs: 3000 series and above ---
AMD_RYZEN_MIN_SERIES = 3000

# AMD tiers: Ryzen 3, 5, 7, 9
AMD_RYZEN_TIERS = {"3", "5", "7", "9"}

# --- Instant FAIL CPU families ---
INCOMPATIBLE_CPU_KEYWORDS = [
    "pentium", "celeron", "xeon", "atom",
    "amd fx", "amd a4", "amd a6", "amd a8", "amd a10",
    "athlon", "sempron", "phenom",
    "macbook", "apple m1", "apple m2", "apple m3", "apple m4",
    "m1 chip", "m2 chip", "m3 chip", "m4 chip",
    "mac mini", "imac", "mac pro", "mac studio",
]

# --- NVIDIA GPUs ---
# Minimum: any discrete GPU ~GTX 1050 level or above
NVIDIA_COMPATIBLE = {
    # GTX 900-series (discrete, ~GTX 1050 level)
    "950": 0, "960": 0, "970": 0, "980": 0, "980 ti": 0,
    # GTX 10-series
    "1050": 0, "1050 ti": 0,
    "1060": 0, "1070": 0, "1070 ti": 0, "1080": 0, "1080 ti": 0,
    # GTX 16-series
    "1650": 0, "1650 super": 0, "1660": 0, "1660 super": 0, "1660 ti": 0,
    # RTX 20-series
    "2060": 0, "2060 super": 0, "2070": 0, "2070 super": 0, "2080": 0, "2080 super": 0, "2080 ti": 0,
    # RTX 30-series
    "3050": 0, "3060": 0, "3060 ti": 0, "3070": 0, "3070 ti": 0, "3080": 0, "3080 ti": 0, "3090": 0, "3090 ti": 0,
    # RTX 40-series
    "4050": 0, "4060": 0, "4060 ti": 0, "4070": 0, "4070 super": 0, "4070 ti": 0, "4070 ti super": 0,
    "4080": 0, "4080 super": 0, "4090": 0,
    # RTX 50-series
    "5060": 0, "5060 ti": 0, "5070": 0, "5070 ti": 0, "5080": 0, "5090": 0,
}

# NVIDIA instant fail — entry-level display cards, not real GPUs
NVIDIA_INCOMPATIBLE = [
    "gt 710", "gt 730", "gt 1030",
]

# --- AMD GPUs ---
# Any discrete Radeon RX passes (all are ~GTX 1050+ level)
AMD_GPU_COMPATIBLE_KEYWORDS = [
    # RX 400/500-series
    "rx 460", "rx 470", "rx 480",
    "rx 550", "rx 560", "rx 570", "rx 580", "rx 590",
    # RX 5000-series
    "rx 5500", "rx 5600", "rx 5700",
    # RX 6000-series
    "rx 6400", "rx 6500", "rx 6600", "rx 6650", "rx 6700", "rx 6750", "rx 6800", "rx 6900", "rx 6950",
    # RX 7000-series
    "rx 7600", "rx 7700", "rx 7800", "rx 7900",
    # RX 9000-series
    "rx 9070",
]

AMD_GPU_INCOMPATIBLE_KEYWORDS = [
    "r7 ", "r5 ", "r9 ",  # old Radeon R-series (pre-RX, integrated-tier)
    "hd ",  # Radeon HD series
]


def _normalize(text: str) -> str:
    """Lowercase, collapse spaces, remove dashes for fuzzy matching."""
    text = text.lower().strip()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def check_cpu(model: str):
    """Check CPU compatibility. Returns (is_compatible, reason)."""
    norm = _normalize(model)

    # Check instant-fail keywords
    for kw in INCOMPATIBLE_CPU_KEYWORDS:
        if kw in norm:
            if "mac" in kw or "apple" in kw:
                return False, "MacBook/Apple Silicon is not supported. Windows PC required."
            return False, f"CPU family '{kw}' is not supported. Minimum: Intel i3 10th gen or AMD Ryzen 3 3000."

    # Check Intel Core
    intel_match = re.search(r"(?:core\s*)?i([3579])\s*[\- ]?(\d{4,5})", norm)
    if intel_match:
        tier = f"i{intel_match.group(1)}"
        model_num = int(intel_match.group(2))

        # Determine generation from model number
        if model_num >= 10000:
            gen = model_num // 1000  # 12400 -> 12th gen
        else:
            gen = model_num // 100   # legacy: 9600 -> 9th gen (but these are 4-digit)
            if gen < 10:
                # 4-digit model: e.g. 9600 = 9th gen
                pass
            else:
                gen = model_num // 1000

        if gen >= INTEL_MIN_GEN:
            return True, f"Intel Core {tier}-{model_num} ({gen}th gen) — compatible."
        else:
            return False, f"Intel Core {tier}-{model_num} ({gen}th gen) — too old. Minimum 10th gen."

    # Check AMD Ryzen
    ryzen_match = re.search(r"ryzen\s*([3579])\s*(\d{4})", norm)
    if ryzen_match:
        tier = ryzen_match.group(1)
        series_num = int(ryzen_match.group(2))
        series = (series_num // 1000) * 1000  # 5600 -> 5000

        if series >= AMD_RYZEN_MIN_SERIES:
            return True, f"AMD Ryzen {tier} {series_num} (series {series}) — compatible."
        else:
            return False, f"AMD Ryzen {tier} {series_num} — too old. Minimum Ryzen 3 3000 series."

    # Could not parse — flag for manual review
    return True, f"Could not auto-verify '{model}' — marked for manual review."


def check_gpu(model: str):
    """Check GPU compatibility. Returns (is_compatible, reason)."""
    norm = _normalize(model)

    # Check NVIDIA incompatible first
    for kw in NVIDIA_INCOMPATIBLE:
        if kw.replace(" ", "") in norm.replace(" ", ""):
            return False, f"NVIDIA {kw.upper()} is not supported. A discrete gaming GPU is required (GTX 1050+)."

    # Check NVIDIA compatible (3-digit: 950/970/980, 4-digit: 1050+)
    nvidia_match = re.search(r"(?:gtx|rtx)\s*(\d{3,4}(?:\s*(?:ti|super))*)", norm)
    if nvidia_match:
        gpu_key = nvidia_match.group(1).strip()
        base_num = re.match(r"\d{3,4}", gpu_key)
        if base_num:
            num = base_num.group()
            if num in NVIDIA_COMPATIBLE or gpu_key in NVIDIA_COMPATIBLE:
                return True, f"NVIDIA GTX/RTX {gpu_key.upper()} — compatible."
            else:
                return False, f"NVIDIA {gpu_key.upper()} — not in compatibility list. Discrete GPU required (GTX 1050+)."

    # Check AMD GPU compatible
    for kw in AMD_GPU_COMPATIBLE_KEYWORDS:
        if kw.replace(" ", "") in norm.replace(" ", ""):
            return True, f"AMD Radeon {kw.upper()} — compatible."

    # Check AMD GPU incompatible
    for kw in AMD_GPU_INCOMPATIBLE_KEYWORDS:
        if kw.strip() and kw.strip() in norm:
            return False, f"AMD Radeon series too old. A discrete RX-series GPU is required."

    # Intel integrated
    if "intel" in norm and ("uhd" in norm or "hd " in norm or "iris" in norm or "integrated" in norm):
        return False, "Integrated Intel graphics are not supported. A discrete GPU is required (GTX 1050+)."

    # AMD integrated (e.g. "AMD Radeon Graphics", "Radeon Vega")
    if ("radeon" in norm or "amd" in norm) and ("vega" in norm or norm.strip() in ("radeon graphics", "amd radeon graphics", "radeon")):
        return False, "Integrated AMD Radeon graphics are not supported. A discrete GPU is required (GTX 1050+)."

    # Could not parse
    return True, f"Could not auto-verify '{model}' — marked for manual review."


def quick_check(cpu: str, gpu: str) -> HardwareResult:
    """Run both CPU and GPU checks, return combined result."""
    cpu_ok, cpu_reason = check_cpu(cpu)
    gpu_ok, gpu_reason = check_gpu(gpu)
    return HardwareResult(cpu_ok=cpu_ok, gpu_ok=gpu_ok, cpu_reason=cpu_reason, gpu_reason=gpu_reason)
