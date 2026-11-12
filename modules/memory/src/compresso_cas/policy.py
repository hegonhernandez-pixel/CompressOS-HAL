"""Deterministic I/O placement planner; recommendations only, no kernel writes."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RouteDecision:
    route: str
    mode: str
    reserved_vram_mb: int
    reason: str


def choose_route(priority: str, operation: str, size_bytes: int,
                 vram_usage_percent: int, gpu_available: bool,
                 game_mode: bool = False, high_watermark: int = 85,
                 low_watermark: int = 60, fast_buffer_mb: int = 1024,
                 fallback_buffer_mb: int = 64, gpu_min_block_bytes: int = 4 * 1024 * 1024):
    if priority not in {"critical", "normal", "background"}:
        raise ValueError("priority must be critical, normal or background")
    if operation not in {"read", "write"}:
        raise ValueError("operation must be read or write")
    if size_bytes < 0 or not 0 <= vram_usage_percent <= 100:
        raise ValueError("invalid size or VRAM usage")
    if not 0 <= low_watermark < high_watermark <= 100:
        raise ValueError("watermarks must satisfy 0 <= low < high <= 100")
    if operation == "write" and priority == "background":
        return RouteDecision("nvme_background", "background", fallback_buffer_mb,
                             "background writes are deferred to persistent storage")
    if not gpu_available:
        return RouteDecision("zswap", "cpu_fallback", fallback_buffer_mb,
                             "Vulkan compute device unavailable")
    if game_mode or vram_usage_percent >= high_watermark:
        return RouteDecision("zswap", "overflow", fallback_buffer_mb,
                             "foreground graphics pressure protects VRAM")
    if (priority == "critical" and operation == "read"
            and size_bytes >= gpu_min_block_bytes
            and vram_usage_percent <= low_watermark):
        return RouteDecision("fast_vram", "fast_vram", fast_buffer_mb,
                             "critical large read and VRAM below low watermark")
    if vram_usage_percent > low_watermark:
        reason = "VRAM in hysteresis band; keep workload off GPU"
    else:
        reason = "non-critical or small request uses compressed-memory path"
    return RouteDecision("zswap", "balanced", fallback_buffer_mb, reason)


def decision_dict(**kwargs):
    return asdict(choose_route(**kwargs))
