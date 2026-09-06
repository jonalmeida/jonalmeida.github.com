"""Speed to colour.

Dark navy for the slow parts, near-white blue for the fast parts. The full ramp
fails at one end on each theme, so each theme samples a different sub-range of
the same ramp; that is what LIGHT_SPAN and DARK_SPAN are for.
"""

from __future__ import annotations


# Blue speed ramp, from moresamwilson/running-heatmap (cmap_speed_rgb):
# dark navy for the slow parts, near-white blue for the fast parts.
SPEED_RAMP: tuple[tuple[float, tuple[float, float, float]], ...] = (
    (0.00, (0.00, 0.10, 0.40)),
    (0.35, (0.05, 0.30, 0.80)),
    (0.65, (0.20, 0.55, 1.00)),
    (0.85, (0.55, 0.75, 1.00)),
    (1.00, (0.85, 0.92, 1.00)),
)


RAMP_BUCKETS = 16


# The full ramp fails at one end on each theme: near-white blue disappears on the
# light #fff background, and navy disappears on the dark #01242e one. So sample
# the same ramp over a different sub-range per theme.
LIGHT_SPAN = (0.00, 0.72)


DARK_SPAN = (0.42, 1.00)


def ramp_rgb(t: float) -> tuple[int, int, int]:
    """Interpolate SPEED_RAMP at t in 0..1."""
    t = min(1.0, max(0.0, t))
    for (p0, c0), (p1, c1) in zip(SPEED_RAMP, SPEED_RAMP[1:]):
        if t <= p1:
            span = p1 - p0
            f = (t - p0) / span if span else 0.0
            return tuple(round((a + (b - a) * f) * 255) for a, b in zip(c0, c1))
    return tuple(round(c * 255) for c in SPEED_RAMP[-1][1])


def ramp_hex(t: float) -> str:
    r, g, b = ramp_rgb(t)
    return f"#{r:02X}{g:02X}{b:02X}"


def ramp_at_speed(t: float, span: tuple[float, float]) -> str:
    """Colour for a normalised speed t, where 0 is slowest and 1 is fastest.

    The ramp is walked backwards on purpose: darker means faster.
    """
    lo, hi = span
    return ramp_hex(hi - (hi - lo) * t)


def _bucket_table(span: tuple[float, float]) -> list[str]:
    """Bucket colours, slowest first."""
    return [
        ramp_at_speed((i + 0.5) / RAMP_BUCKETS, span)
        for i in range(RAMP_BUCKETS)
    ]


def bucket_of(value: float, lo: float, hi: float) -> int:
    """Quantise a speed into 0 … RAMP_BUCKETS-1."""
    t = (value - lo) / (hi - lo)
    return min(RAMP_BUCKETS - 1, max(0, int(t * RAMP_BUCKETS)))


RAMP_LIGHT_HEX: list[str] = _bucket_table(LIGHT_SPAN)


RAMP_DARK_HEX: list[str] = _bucket_table(DARK_SPAN)
