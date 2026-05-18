"""Server-side SVG chart rendering (no JS / CDN dependency).

Two primitives:
- ``bar_chart_svg(items, ...)``  for Likert distributions.
- ``pie_chart_svg(items, ...)``  for single-choice questions.

Items are ``[(label, count), ...]``. Empty / all-zero data renders a
gray "no data yet" plate. Output is plain SVG markup safe to inline
via ``| safe`` from a Jinja2 template.
"""

from __future__ import annotations

import math
from html import escape
from typing import Iterable


_PALETTE = [
    "#5b8def", "#69c47a", "#f5b948", "#e07b7b",
    "#9a7bdb", "#3ec1c1", "#d99a4a", "#8aa4d4",
    "#c47ed9", "#7ac98a",
]


def _color(i: int) -> str:
    return _PALETTE[i % len(_PALETTE)]


def bar_chart_svg(
    items: Iterable[tuple[str, int]],
    *,
    width: int = 480,
    bar_height: int = 22,
    bar_gap: int = 8,
    left_label_w: int = 200,
    right_value_w: int = 60,
) -> str:
    items = list(items)
    n = len(items)
    if n == 0:
        return _empty(width, bar_height + 30)
    total = sum(c for _, c in items)
    if total == 0:
        return _empty(width, n * (bar_height + bar_gap))

    plot_x = left_label_w
    plot_w = width - left_label_w - right_value_w
    height = bar_gap + n * (bar_height + bar_gap)

    bars: list[str] = []
    for i, (label, count) in enumerate(items):
        y = bar_gap + i * (bar_height + bar_gap)
        frac = count / total if total else 0
        bar_w = max(2, plot_w * frac) if count else 0
        label_e = escape(label)
        bars.append(
            f'<text x="{left_label_w - 8}" y="{y + bar_height * 0.7}" '
            f'text-anchor="end" font-size="12" fill="#333">{label_e}</text>'
        )
        if bar_w:
            bars.append(
                f'<rect x="{plot_x}" y="{y}" width="{bar_w:.1f}" '
                f'height="{bar_height}" fill="{_color(i)}" rx="2"/>'
            )
        bars.append(
            f'<text x="{plot_x + bar_w + 6}" y="{y + bar_height * 0.7}" '
            f'font-size="12" fill="#333">{count}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="bar chart">'
        + "".join(bars)
        + "</svg>"
    )


def pie_chart_svg(
    items: Iterable[tuple[str, int]],
    *,
    size: int = 240,
    legend_w: int = 240,
) -> str:
    items = list(items)
    total = sum(c for _, c in items)
    if total == 0:
        return _empty(size + legend_w, size)

    cx = cy = size / 2
    r = size / 2 - 4
    angle = -math.pi / 2  # start at 12 o'clock
    paths: list[str] = []
    legend: list[str] = []
    legend_x = size + 16
    legend_line = 22

    for i, (label, count) in enumerate(items):
        if count == 0:
            continue
        frac = count / total
        sweep = frac * 2 * math.pi
        end = angle + sweep
        large = 1 if sweep > math.pi else 0
        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(end)
        y2 = cy + r * math.sin(end)
        if frac >= 0.999:
            # Full circle: render as a circle to avoid degenerate arc.
            paths.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{_color(i)}"/>'
            )
        else:
            paths.append(
                f'<path d="M{cx:.2f},{cy:.2f} L{x1:.2f},{y1:.2f} '
                f'A{r:.2f},{r:.2f} 0 {large},1 {x2:.2f},{y2:.2f} Z" '
                f'fill="{_color(i)}"/>'
            )
        angle = end

        y = 10 + i * legend_line
        pct = 100 * frac
        legend.append(
            f'<rect x="{legend_x}" y="{y}" width="14" height="14" '
            f'fill="{_color(i)}" rx="2"/>'
            f'<text x="{legend_x + 22}" y="{y + 11}" font-size="12" '
            f'fill="#333">{escape(label)} — {count} ({pct:.0f}%)</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size + legend_w}" height="{size}" '
        f'viewBox="0 0 {size + legend_w} {size}" role="img" '
        f'aria-label="pie chart">'
        + "".join(paths) + "".join(legend) + "</svg>"
    )


def _empty(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="no data">'
        f'<rect width="100%" height="100%" fill="#f4f4f4" rx="3"/>'
        f'<text x="50%" y="50%" text-anchor="middle" '
        f'dominant-baseline="middle" font-size="13" fill="#888">'
        f'no responses yet</text></svg>'
    )
