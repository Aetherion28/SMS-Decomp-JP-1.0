#!/usr/bin/env python3
"""Draw a progress treemap (like the one on decomp.dev) from the objdiff report.

Every box is one translation unit, sized by its code size.
  green      every function in the unit matches
  blue       partly matched; brighter means a higher fuzzy match
  dark grey  nothing decompiled yet (0% fuzzy)

Units are grouped by category (game, JSystem, SDK) and then by folder.
The script also refreshes the progress numbers in README.md between the
<!-- progress:start --> and <!-- progress:end --> markers.

Usage: python3 tools/progress_treemap.py [report.json] [out.svg]
Run `ninja` first so build/GMSJ01/report.json is current.
"""

import json
import os
import sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "build", "GMSJ01", "report.json")
OUT = os.path.join(ROOT, "assets", "progress.svg")
README = os.path.join(ROOT, "README.md")

W, H = 1000, 500
GREEN = (0, 200, 0)
BLUE = (0, 112, 192)
GREY = (52, 52, 52)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def colour(unit):
    m = unit["measures"]
    total = int(m.get("total_code", 0) or 0)
    matched = int(m.get("matched_code", 0) or 0)
    fuzzy = m.get("fuzzy_match_percent", 0) or 0
    if total and matched >= total:
        return GREEN
    if fuzzy <= 0:
        return GREY
    # most units sit above 80% fuzzy, so stretch that range
    return mix(GREY, BLUE, 0.35 + 0.65 * (fuzzy / 100.0) ** 3)


# --- squarified treemap (Bruls, Huizing, van Wijk) ---------------------------


def worst(row, side):
    s = sum(a for a, _ in row)
    if s <= 0 or side <= 0:
        return float("inf")
    big = max(a for a, _ in row)
    small = min(a for a, _ in row)
    return max(side * side * big / (s * s), (s * s) / (side * side * small))


def layout_row(row, x, y, w, h):
    s = sum(a for a, _ in row)
    out = []
    if w >= h:  # lay the row out as a column on the left
        cw = s / h if h else 0
        cy = y
        for a, item in row:
            ch = a / cw if cw else 0
            out.append((item, x, cy, cw, ch))
            cy += ch
        return out, (x + cw, y, w - cw, h)
    rh = s / w if w else 0
    cx = x
    for a, item in row:
        cw = a / rh if rh else 0
        out.append((item, cx, y, cw, rh))
        cx += cw
    return out, (x, y + rh, w, h - rh)


def squarify(items, x, y, w, h):
    """items: list of (weight, item). Returns [(item, x, y, w, h)]."""
    total = sum(a for a, _ in items)
    if total <= 0 or w <= 0 or h <= 0:
        return []
    scale = w * h / total
    rest = sorted(((a * scale, it) for a, it in items if a > 0), key=lambda p: -p[0])
    out = []
    row = []
    rect = (x, y, w, h)
    while rest:
        side = min(rect[2], rect[3])
        cand = rest[0]
        if not row or worst(row + [cand], side) <= worst(row, side):
            row.append(cand)
            rest.pop(0)
        else:
            placed, rect = layout_row(row, *rect)
            out += placed
            row = []
    if row:
        placed, _ = layout_row(row, *rect)
        out += placed
    return out


# --- grouping ----------------------------------------------------------------


def size(unit):
    return int(unit["measures"].get("total_code", 0) or 0)


def folder(unit):
    path = unit.get("metadata", {}).get("source_path") or unit["name"]
    return os.path.dirname(path)


def build_tree(units):
    cats = {}
    for u in units:
        if size(u) <= 0:
            continue
        cat = (u.get("metadata", {}).get("progress_categories") or ["other"])[0]
        cats.setdefault(cat, {}).setdefault(folder(u), []).append(u)
    return cats


def draw(units, measures):
    tree = build_tree(units)
    rects = []  # (unit, x, y, w, h)
    groups = []  # outlines for categories
    cat_items = [(sum(size(u) for us in f.values() for u in us), c) for c, f in tree.items()]
    for cat, cx, cy, cw, ch in squarify(cat_items, 0, 0, W, H):
        groups.append((cx, cy, cw, ch))
        folders = tree[cat]
        f_items = [(sum(size(u) for u in us), f) for f, us in folders.items()]
        for f, fx, fy, fw, fh in squarify(f_items, cx, cy, cw, ch):
            u_items = [(size(u), u) for u in folders[f]]
            rects += squarify(u_items, fx, fy, fw, fh)

    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="sans-serif">'
    )
    p.append(f'<rect width="{W}" height="{H}" rx="8" fill="#222"/>')
    p.append(f'<clipPath id="r"><rect width="{W}" height="{H}" rx="8"/></clipPath>')
    p.append('<g clip-path="url(#r)" stroke="#000" stroke-width="0.6">')
    for u, x, y, w, h in rects:
        r, g, b = colour(u)
        m = u["measures"]
        name = u["name"].replace("mario/", "", 1)
        tip = (
            f"{name}: {m.get('fuzzy_match_percent', 0):.2f}% fuzzy, "
            f"{m.get('matched_code_percent', 0):.2f}% matched, "
            f"{size(u)} bytes"
        )
        p.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="rgb({r},{g},{b})"><title>{escape(tip)}</title></rect>'
        )
    p.append("</g>")
    p.append('<g fill="none" stroke="#000" stroke-width="2">')
    for x, y, w, h in groups:
        p.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"/>')
    p.append("</g></svg>")
    return "\n".join(p)


def summary(measures, categories):
    def pct(m, k):
        return f"{float(m.get(k, 0) or 0):.2f}%"

    lines = [
        "| | Code matched | Fuzzy | Functions matched | Units complete |",
        "|---|---|---|---|---|",
    ]
    rows = [("**Total**", measures)] + [(c["name"], c["measures"]) for c in categories]
    for name, m in rows:
        lines.append(
            f"| {name} | {pct(m, 'matched_code_percent')} | {pct(m, 'fuzzy_match_percent')} "
            f"| {m.get('matched_functions', 0)} / {m.get('total_functions', 0)} "
            f"| {m.get('complete_units', 0)} / {m.get('total_units', 0)} |"
        )
    return "\n".join(lines)


def update_readme(text):
    start, end = "<!-- progress:start -->", "<!-- progress:end -->"
    try:
        readme = open(README, encoding="utf-8").read()
    except OSError:
        return False
    if start not in readme or end not in readme:
        return False
    a = readme.index(start) + len(start)
    b = readme.index(end)
    new = readme[:a] + "\n" + text + "\n" + readme[b:]
    if new != readme:
        open(README, "w", encoding="utf-8").write(new)
    return True


def main():
    report = sys.argv[1] if len(sys.argv) > 1 else REPORT
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    data = json.load(open(report))
    svg = draw(data["units"], data["measures"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(svg + "\n")
    update_readme(summary(data["measures"], data.get("categories", [])))
    m = data["measures"]
    print(
        f"wrote {os.path.relpath(out, ROOT)}: "
        f"{float(m['matched_code_percent']):.2f}% code matched, "
        f"{float(m['fuzzy_match_percent']):.2f}% fuzzy"
    )


if __name__ == "__main__":
    main()
