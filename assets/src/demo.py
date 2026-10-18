"""Builds assets/demo.svg: the Claude Mac app's Code tab with the agent band at work.

One SMIL timeline, T seconds long, loops forever. GitHub shows SVGs through <img>,
which blocks nested image files, so the crew avatars are inlined from assets/crew.

Run: python3 assets/src/demo.py
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
T = 18.0
FADE = 0.3
MOVE = 0.35

INK = "#ecebe8"
MUTED = "#a6a39b"
LINE = "#333230"
CARD = "#201f20"
APP = "#151515"
CHROME = "#2b2a28"
ORANGE = "#D97757"
BACKDROP = "#3a3836"
CHIP = "#2a2928"
CALLOUT = "#2c2b29"
ARROW = "#d9d6cf"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', Menlo, Consolas, monospace"


def keyframes(points: list[tuple[float, str]]) -> tuple[str, str]:
    pts = sorted(points)
    if pts[0][0] > 0:
        pts.insert(0, (0.0, pts[0][1]))
    if pts[-1][0] < T:
        pts.append((T, pts[-1][1]))
    values = ";".join(v for _, v in pts)
    times = ";".join(f"{min(t / T, 1):.4f}" for t, _ in pts)
    return values, times


def anim(attr: str, points: list[tuple[float, str]]) -> str:
    v, k = keyframes(points)
    return f'<animate attributeName="{attr}" values="{v}" keyTimes="{k}" dur="{T}s" repeatCount="indefinite"/>'


def move(points: list[tuple[float, str]]) -> str:
    v, k = keyframes(points)
    return (f'<animateTransform attributeName="transform" type="translate" values="{v}" '
            f'keyTimes="{k}" dur="{T}s" repeatCount="indefinite"/>')


def shown(spans: list[tuple[float, float]]) -> str:
    """Opacity that fades in at each start and out at each end."""
    pts = [(0.0, "0")]
    for a, b in spans:
        pts += [(a, "0"), (a + FADE, "1"), (b, "1"), (min(b + FADE, T), "0")]
    return anim("opacity", pts)


def avatar(role: str, mood: str, x: float, y: float, w: float = 40) -> str:
    src = (ROOT / "crew" / f"{role}-{mood}.svg").read_text()
    m = re.match(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>\s*$', src, re.S)
    assert m, role
    vb = m.group(1)
    vw, vh = (float(n) for n in vb.split()[2:])
    h = w * vh / vw
    return (f'<svg x="{x}" y="{y}" width="{w}" height="{h:.1f}" viewBox="{vb}" '
            f'shape-rendering="crispEdges">{m.group(2)}</svg>')


def dots(x: float, y: float) -> str:
    src = (ROOT / "crew" / "dots.svg").read_text()
    m = re.match(r"<svg[^>]*>(.*)</svg>\s*$", src, re.S)
    assert m
    inner = m.group(1)
    return f'<svg x="{x}" y="{y}" width="22" height="11" viewBox="0 0 16 8">{inner}</svg>'


# ---------- the scripted session ----------

TYPE_START, TYPE_END = 0.3, 1.7
SENT = 1.9
REPLY = 2.6
STARTS = {"arch": 3.2, "dev": 3.7, "rev": 4.2}
DONE = {"arch": 8.6, "dev": 10.0, "rev": 11.4}
FOLD = 12.4
FINAL = 12.9
END = 17.3

PROMPT = "Use three agents at once: plan a birthday party, build a shopping list, and review both."

AGENTS = {
    "arch": ("architect", "Plan the birthday party", "careful", "#E0A44A", "Opus 5.5", "184k", "2:40", "≈$0.41", 0.55),
    "dev": ("developer", "Build the shopping list", "medium", "#5AA9E6", "Sonnet 5.5", "121k", "1:55", "≈$0.18", 0.4),
    "rev": ("reviewer", "Review the plan and list", "light", "#4CC38A", "Haiku 5.5", "48k", "0:37", "≈$0.02", 0.18),
}

# Window geometry.
WX, WY, WW, WH = 40, 34, 1200, 770
SIDE = 196
MX = WX + SIDE              # main area left edge
MW = WW - SIDE
BX, BW = MX + 24, MW - 48   # band box
BOTTOM = 676                # band box bottom edge
ROW = 40

# Band states: which rows stack in the box, top to bottom, from each time on.
STATES = [
    (0.0, ["hdr", "cap"]),
    (STARTS["arch"], ["hdr", "cap", "arch"]),
    (STARTS["dev"], ["hdr", "cap", "arch", "dev"]),
    (STARTS["rev"], ["hdr", "cap", "arch", "dev", "rev"]),
    (FOLD, ["hdr", "cap", "fold"]),
    (END + 0.2, ["hdr", "cap"]),
]


def box_top(rows: list[str]) -> float:
    return BOTTOM - 12 - ROW * len(rows) - 6


def row_track(name: str) -> tuple[str, str]:
    """The row's translate animation and its opacity animation across all states."""
    ys: list[tuple[float, str]] = []
    vis: list[tuple[float, str]] = []
    last_y = None
    last_v = "0"
    for t, rows in STATES:
        if name in rows:
            y = box_top(rows) + 6 + ROW * rows.index(name)
            v = "1"
        else:
            y = last_y if last_y is not None else box_top(rows)
            v = "0"
        if last_y is None:
            ys.append((t, f"0 {y}"))
            vis.append((t, v))
        else:
            ys += [(t, f"0 {last_y}"), (t + MOVE, f"0 {y}")]
            vis += [(t, last_v), (t + FADE, v)]
        last_y, last_v = y, v
    return move(ys), anim("opacity", vis)


def text(x: float, y: float, s: str, size: float = 13, fill=INK, weight=400, anchor="start", family=SANS, extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" {extra}>{s}</text>')


def agent_row(key: str) -> str:
    role, title, effort, ecolor, model, tok, tm, cost, frac = AGENTS[key]
    tr, op = row_track(key)
    run = (STARTS[key], DONE[key])
    after = (DONE[key], END)
    bar_w = 60
    return f"""
<g>{tr}{op}
  <g>{shown([run])}{avatar(role, 'running', BX + 14, 2)}{dots(BX + 62, 15)}</g>
  <g>{shown([after])}{avatar(role, 'done', BX + 14, 2)}</g>
  <text x="{BX + 92}" y="25" font-family="{SANS}" font-size="13.5" fill="{INK}">
    <tspan font-weight="650">{title}</tspan><tspan dx="9" fill="{ecolor}">{effort}</tspan><tspan dx="9" fill="{MUTED}">{model}</tspan>
  </text>
  <rect x="{BX + BW - 230}" y="19" width="{bar_w}" height="3" rx="1.5" fill="{LINE}"/>
  <rect x="{BX + BW - 230}" y="19" width="0" height="3" rx="1.5" fill="{ecolor}">{anim('width', [(run[0], '0'), (run[1], f'{bar_w * frac:.0f}')])}</rect>
  {text(BX + BW - 120, 25, tok, 12.5, MUTED, anchor='end', family=MONO)}
  {text(BX + BW - 72, 25, tm, 12.5, MUTED, anchor='end', family=MONO)}
  {text(BX + BW - 14, 25, cost, 12.5, MUTED, anchor='end', family=MONO)}
</g>"""


def band() -> str:
    box_y = []
    box_h = []
    prev = None
    for t, rows in STATES:
        y, h = box_top(rows), BOTTOM - box_top(rows)
        if prev is None:
            box_y.append((t, f"{y}"))
            box_h.append((t, f"{h}"))
        else:
            box_y += [(t, f"{prev[0]}"), (t + MOVE, f"{y}")]
            box_h += [(t, f"{prev[1]}"), (t + MOVE, f"{h}")]
        prev = (y, h)

    hdr_tr, _ = row_track("hdr")
    cap_tr, _ = row_track("cap")
    fold_tr, fold_op = row_track("fold")
    usage_x = BX + BW - 372
    return f"""
<rect x="{BX}" width="{BW}" rx="12" fill="{CARD}" stroke="{LINE}">{anim('y', box_y)}{anim('height', box_h)}</rect>
<g>{hdr_tr}
  <text x="{BX + 16}" y="25" font-family="{SANS}" font-size="13.5" fill="{INK}"><tspan font-weight="700">Agents</tspan><tspan dx="10" fill="{MUTED}" font-family="{MONO}" font-size="12.5">≈$1.67 · 665k · 4:12</tspan></text>
  {text(usage_x, 25, 'Usage', 13, MUTED)}
  <rect x="{usage_x + 46}" y="15" width="64" height="12" rx="2" fill="{CHIP}"/>
  <rect x="{usage_x + 46}" y="15" width="37" height="12" rx="2" fill="#8e8e93"/>
  {text(usage_x + 120, 25, '58% / 64% Week, On Pace', 13, INK)}
  <rect x="{BX + BW - 62}" y="9" width="48" height="24" rx="6" fill="{CARD}" stroke="{LINE}"/>
  {text(BX + BW - 38, 25, 'Hide', 12.5, INK, 500, 'middle')}
</g>
<g>{cap_tr}
  {avatar('main', 'running', BX + 14, 2)}{dots(BX + 62, 15)}
  <text x="{BX + 92}" y="25" font-family="{SANS}" font-size="13.5" fill="{INK}"><tspan font-weight="650">Main agent</tspan><tspan dx="9" fill="#5AA9E6">medium</tspan><tspan dx="9" fill="{MUTED}">Opus 5.5</tspan></text>
  <rect x="{BX + BW - 230}" y="19" width="60" height="3" rx="1.5" fill="{LINE}"/>
  <rect x="{BX + BW - 230}" y="19" width="18" height="3" rx="1.5" fill="#5AA9E6"/>
  {text(BX + BW - 120, 25, '312k', 12.5, MUTED, anchor='end', family=MONO)}
  {text(BX + BW - 72, 25, '4:12', 12.5, MUTED, anchor='end', family=MONO)}
  {text(BX + BW - 14, 25, '≈$1.06', 12.5, MUTED, anchor='end', family=MONO)}
</g>
{agent_row('arch')}{agent_row('dev')}{agent_row('rev')}
<g>{fold_tr}{fold_op}
  {text(BX + 16, 25, '3 done · ≈$0.61', 13, MUTED, family=SANS)}
  <rect x="{BX + 126}" y="9" width="50" height="24" rx="6" fill="{CARD}" stroke="{LINE}"/>
  {text(BX + 151, 25, 'Show', 12.5, INK, 500, 'middle')}
</g>"""


def spark(x: float, y: float, s: float = 18) -> str:
    rays = "".join(
        f'<line x1="12" y1="12" x2="12" y2="{2.6 if i % 2 else 1.4}" stroke="{ORANGE}" stroke-width="2.3" '
        f'stroke-linecap="round" transform="rotate({d} 12 12)"/>'
        for i, d in enumerate([0, 32, 64, 98, 130, 162, 196, 228, 262, 294, 326]))
    return f'<svg x="{x}" y="{y}" width="{s}" height="{s}" viewBox="0 0 24 24">{rays}</svg>'


def transcript() -> str:
    tx = MX + 60
    out = []
    # The sent message, as a bubble on the right.
    bw = 600
    out.append(f"""<g>{shown([(SENT, END)])}
  <rect x="{WX + WW - 60 - bw}" y="130" width="{bw}" height="40" rx="12" fill="{CHIP}"/>
  {text(WX + WW - 60 - bw + 16, 155, PROMPT, 13.5)}</g>""")
    out.append(f"""<g>{shown([(REPLY, END)])}{spark(tx, 196)}
  {text(tx + 28, 210, "On it. I'm starting three helpers so they all work at the same time.", 14.5)}</g>""")
    for i, key in enumerate(["arch", "dev", "rev"]):
        role, title = AGENTS[key][0], AGENTS[key][1]
        y = 246 + i * 28
        out.append(f"""<g>{shown([(STARTS[key], END)])}
  <path d="M{tx + 30} {y - 8} l4 4 -4 4" fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-linecap="round"/>
  {text(tx + 44, y, f'Started {role}: {title.lower()}', 13.5, MUTED)}</g>""")
    out.append(f"""<g>{shown([(FINAL, END)])}{spark(tx, 336)}
  {text(tx + 28, 350, 'All three are done. Your party plan and shopping list are ready, and the review found one thing to fix.', 14.5)}</g>""")
    return "\n".join(out)


def composer() -> str:
    cy = BOTTOM + 14
    cx, cw = BX, BW
    ph_pts = [(0, "1"), (TYPE_START - 0.1, "1"), (TYPE_START, "0"), (SENT, "0"), (SENT + FADE, "1")]
    type_pts = [(0, "0"), (TYPE_START, "0"), (TYPE_START + 0.01, "1"), (SENT - 0.05, "1"), (SENT, "0")]
    clip_w = [(0, "0"), (TYPE_START, "0"), (TYPE_END, "720")]
    return f"""
<clipPath id="typing"><rect x="{cx + 16}" y="{cy + 12}" height="26" width="0">{anim('width', clip_w)}</rect></clipPath>
<rect x="{cx}" y="{cy}" width="{cw}" height="78" rx="14" fill="{CARD}" stroke="{LINE}"/>
<g>{anim('opacity', ph_pts)}{text(cx + 18, cy + 30, 'Reply to Claude…', 14, '#77756f')}</g>
<g clip-path="url(#typing)">{anim('opacity', type_pts)}{text(cx + 18, cy + 30, PROMPT, 14)}</g>
{text(cx + cw - 132, cy + 60, 'Opus 5.5', 12.5, MUTED)}{text(cx + cw - 76, cy + 60, 'medium', 12.5, MUTED)}
<rect x="{cx + cw - 46}" y="{cy + 12}" width="30" height="30" rx="8" fill="{ORANGE}"/>
<path d="M{cx + cw - 31} {cy + 34} v-13 m-5 5 l5 -5 5 5" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>"""


def window() -> str:
    title_h = 38
    sx = WX
    return f"""
<rect x="{WX}" y="{WY + 10}" width="{WW}" height="{WH}" rx="14" fill="#000" opacity="0.28" filter="url(#blur)"/>
<rect x="{WX}" y="{WY}" width="{WW}" height="{WH}" rx="14" fill="{APP}"/>
<path d="M{WX} {WY + 14} a14 14 0 0 1 14 -14 h{WW - 28} a14 14 0 0 1 14 14 v{title_h - 14} h-{WW} z" fill="{CHROME}"/>
<circle cx="{WX + 22}" cy="{WY + 19}" r="6" fill="#ff5f57"/><circle cx="{WX + 42}" cy="{WY + 19}" r="6" fill="#febc2e"/><circle cx="{WX + 62}" cy="{WY + 19}" r="6" fill="#28c840"/>
{text(WX + WW / 2, WY + 24, 'Claude', 13, MUTED, 500, 'middle')}
<line x1="{MX}" y1="{WY + title_h}" x2="{MX}" y2="{WY + WH}" stroke="{LINE}"/>
<!-- sidebar -->
<rect x="{sx + 12}" y="{WY + 52}" width="{SIDE - 24}" height="30" rx="7" fill="{CHIP}"/>
<rect x="{sx + SIDE / 2}" y="{WY + 55}" width="{SIDE / 2 - 15}" height="24" rx="5" fill="{CARD}" stroke="{LINE}"/>
{text(sx + SIDE / 4 + 6, WY + 72, 'Chat', 12.5, MUTED, 400, 'middle')}{text(sx + SIDE * 3 / 4 - 4, WY + 72, 'Code', 12.5, INK, 650, 'middle')}
{text(sx + 22, WY + 112, '+   New session', 13, INK)}
{text(sx + 22, WY + 148, 'Recents', 11.5, MUTED)}
<rect x="{sx + 12}" y="{WY + 156}" width="{SIDE - 24}" height="28" rx="6" fill="{CHIP}"/>
{spark(sx + 20, WY + 163, 14)}{text(sx + 42, WY + 175, 'Plan a birthday party', 12.5, INK)}
<circle cx="{sx + 27}" cy="{WY + 203}" r="4" fill="none" stroke="{MUTED}"/>{text(sx + 42, WY + 207, 'Fix my CV wording', 12.5, MUTED)}
<circle cx="{sx + 27}" cy="{WY + 233}" r="4" fill="none" stroke="{MUTED}"/>{text(sx + 42, WY + 237, 'Weekend trip ideas', 12.5, MUTED)}
<!-- top bar -->
{text(MX + 24, WY + 66, 'Plan a birthday party', 14, INK, 650)}
<rect x="{MX + 190}" y="{WY + 50}" width="96" height="24" rx="6" fill="{CHIP}"/>
{text(MX + 238, WY + 66, 'party-plans', 12, MUTED, 400, 'middle')}
<line x1="{MX}" y1="{WY + 88}" x2="{WX + WW}" y2="{WY + 88}" stroke="{LINE}"/>"""


def elbow(pts: list[tuple[float, float]], r: float = 10) -> str:
    """A path through right-angle waypoints, each corner rounded to radius r."""
    d = f"M{pts[0][0]} {pts[0][1]}"
    for (ax, ay), (bx, by), (cx, cy) in zip(pts, pts[1:], pts[2:]):
        ux, uy = (bx > ax) - (bx < ax), (by > ay) - (by < ay)
        vx, vy = (cx > bx) - (cx < bx), (cy > by) - (cy < by)
        k = min(r, abs(bx - ax) + abs(by - ay), abs(cx - bx) + abs(cy - by)) / 1
        sweep = 1 if ux * vy - uy * vx > 0 else 0
        d += f" L{bx - ux * k} {by - uy * k} A{k} {k} 0 0 {sweep} {bx + vx * k} {by + vy * k}"
    return d + f" L{pts[-1][0]} {pts[-1][1]}"


def label_w(label: str) -> float:
    return 28 + len(label) * 7.9


def callout(x: float, y: float, label: str, span: tuple[float, float], route: list[tuple[float, float]]) -> str:
    """A dark label with an elbow arrow along route, which starts at the label's edge."""
    w = label_w(label)
    return f"""<g>{shown([span])}
  <path d="{elbow(route)}" fill="none" stroke="{ARROW}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#tip)"/>
  <circle cx="{route[0][0]}" cy="{route[0][1]}" r="3" fill="{ARROW}"/>
  <rect x="{x}" y="{y}" width="{w}" height="36" rx="18" fill="{CALLOUT}" stroke="{ORANGE}" stroke-width="1.5"/>
  <circle cx="{x + 18}" cy="{y + 18}" r="4" fill="{ORANGE}"/>
  {text(x + 30, y + 23, label, 14.5, INK, 600)}
</g>"""


def build() -> str:
    hdr_y_full = box_top(STATES[3][1]) + 6
    rows_y = hdr_y_full + ROW * 2
    fold_hdr = box_top(STATES[4][1]) + 6
    fold_row = fold_hdr + ROW * 2
    usage_x = BX + BW - 372
    l1, l2 = "Each helper gets a character", "Happy face means the job is done"
    l3, l4 = "Finished helpers fold away", "Weekly limit: still on pace"
    gx = BX - 4
    calls = [
        callout(gx - 12, 400, l1, (STARTS["arch"] + 0.4, DONE["arch"] - 0.2),
                [(gx, 436), (gx, rows_y + 20), (BX + 10, rows_y + 20)]),
        callout(gx - 12, 400, l2, (DONE["arch"], FOLD - 0.1),
                [(gx, 436), (gx, rows_y + 20), (BX + 10, rows_y + 20)]),
        callout(MX + 470, 440, l3, (FOLD + 0.3, FINAL + 1.6),
                [(MX + 470 + label_w(l3) / 2, 476), (MX + 470 + label_w(l3) / 2, fold_row + 21), (BX + 184, fold_row + 21)]),
        callout(usage_x + 78 - label_w(l4) / 2, 440, l4, (FINAL + 1.7, END),
                [(usage_x + 78, 476), (usage_x + 78, fold_hdr + 11)]),
    ]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="840" viewBox="0 0 1280 840" role="img" aria-labelledby="t">
<title id="t">The Claude app's Code tab: you ask for three agents, they appear in the band above the prompt box, finish one by one, and fold away.</title>
<defs>
  <filter id="blur" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="16"/></filter>
  <marker id="tip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1 L9 5 L1 9 Z" fill="{ARROW}" stroke="{ARROW}" stroke-width="1" stroke-linejoin="round"/></marker>
</defs>
<rect width="1280" height="840" fill="{BACKDROP}"/>
{window()}
{transcript()}
{band()}
{composer()}
{''.join(calls)}
</svg>
"""


if __name__ == "__main__":
    out = ROOT / "demo.svg"
    out.write_text(build())
    print(out, out.stat().st_size, "bytes")
