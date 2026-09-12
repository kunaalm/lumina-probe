"""Luminance (perceived brightness) computation from image frames."""
from __future__ import annotations

import io
import logging
from typing import Dict, Optional

import requests
from PIL import Image

log = logging.getLogger(__name__)


def fetch_frame(url: str, timeout: float = 10.0) -> Optional[Image.Image]:
    """GET a frame from url and return it as an RGB PIL Image, or None on error."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        return img.convert("RGB")
    except Exception as e:  # network, HTTP status, or decode
        log.warning("fetch %s failed: %s", url, e)
        return None


def luminance_rgb(img: Image.Image) -> float:
    """Perceived luminance (0-255) of an RGB image using Rec.601 weights."""
    r, g, b = img.split()
    lr, lg, lb = _mean_channel(r), _mean_channel(g), _mean_channel(b)
    return 0.299 * lr + 0.587 * lg + 0.114 * lb


def _mean_channel(channel: Image.Image) -> float:
    hist = channel.histogram()
    total = sum(hist)
    if total == 0:
        return 0.0
    weighted = sum(i * c for i, c in enumerate(hist))
    return weighted / total


def compute_sources(sources, timeout: float = 10.0) -> Dict[str, float]:
    """Fetch + compute luminance (0-255) for each source. Skips failures."""
    out: Dict[str, float] = {}
    for s in sources:
        img = fetch_frame(s.url, timeout=timeout)
        if img is not None:
            out[s.name] = luminance_rgb(img)
            log.debug("%s luminance=%.1f", s.name, out[s.name])
    return out


def aggregate(values: Dict[str, float], mode: str) -> Optional[float]:
    """Combine per-source luminance into one value per the aggregate mode."""
    if not values:
        return None
    nums = list(values.values())
    if mode == "min":
        return min(nums)
    if mode == "median":
        ordered = sorted(nums)
        n = len(ordered)
        mid = n // 2
        if n % 2 == 1:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2.0
    if mode == "per_source":
        # caller handles per-source publishing; return mean as the default view
        return sum(nums) / len(nums)
    # mean
    return sum(nums) / len(nums)
