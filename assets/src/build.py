"""Builds the README images: one HTML page per image, screenshotted by headless Chrome.

Run from anywhere:  python3 assets/src/build.py
"""
import pathlib
import subprocess

SRC = pathlib.Path(__file__).resolve().parent
OUT = SRC.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

FONTS = (
    '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900'
    '&family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
)

BASE_CSS = """
:root{
  --paper:#FAF9F5; --card:#FFFFFF; --ink:#1F1E1C; --mute:#8A877F; --line:#E7E4DC;
  --coral:#D97757; --green:#3BA55C; --amber:#D99A3B; --red:#C0392B; --grey:#9AA0A6;
  --blue:#2B35FF; --yellow:#FFE14D; --pink:#FF5C7A; --night:#1C2632;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.mono{font-family:'JetBrains Mono',monospace}
.dim{color:var(--mute)}
img.av{width:50px;height:41px;image-rendering:pixelated;flex-shrink:0}

/* The band as the app draws it */
.band{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px;display:flex;flex-direction:column;gap:12px;font-size:14px}
.row{display:flex;align-items:center;gap:10px;white-space:nowrap}
.row .desc{font-weight:600;overflow:hidden;text-overflow:ellipsis}
.grow{flex:1}
.bar{font-family:'JetBrains Mono',monospace;letter-spacing:-1px}
.btn{border:1px solid var(--line);border-radius:7px;padding:3px 10px;font-size:13px;font-weight:500;background:#fff}
.btn.primary{background:var(--ink);color:#fff;border-color:var(--ink)}
.prompt{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;color:var(--mute);font-size:15px;display:flex;justify-content:space-between;align-items:center}
.send{width:30px;height:30px;border-radius:9px;background:var(--coral);display:grid;place-items:center;color:#fff;font-weight:700}

/* Numbered callouts */
.pin{width:30px;height:30px;border-radius:50%;background:var(--blue);color:#fff;font:800 15px Archivo,sans-serif;display:grid;place-items:center;box-shadow:0 0 0 4px var(--paper)}
.legend{display:grid;grid-template-columns:repeat(3,1fr);gap:14px 28px;margin-top:26px}
.legend div{display:flex;gap:12px;align-items:flex-start;font-size:15px;line-height:1.4}
.legend b{display:block;font-size:16px}
.legend .pin{flex-shrink:0}

/* Terminal */
.term{background:#1E1E1E;border-radius:12px;overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.18);font-family:'JetBrains Mono',monospace;font-size:15px;color:#E6E6E6}
.term .top{background:#323232;height:34px;display:flex;align-items:center;gap:8px;padding:0 14px}
.term .top i{width:12px;height:12px;border-radius:50%;display:block}
.term .top span{flex:1;text-align:center;color:#A0A0A0;font-size:13px;font-family:Inter,sans-serif;margin-right:56px}
.term .body{padding:20px 22px;line-height:1.75;white-space:pre-wrap}
.ok{color:#4EC97A}.cy{color:#6CB6FF}.yl{color:#FFD866}.gr{color:#7A7A7A}
.cursor{display:inline-block;width:9px;height:18px;background:#E6E6E6;vertical-align:-3px}

h1,h2,.display{font-family:Archivo,sans-serif}
.step{font:800 15px Archivo,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--blue)}
.cap{font-size:22px;font-weight:700;font-family:Archivo,sans-serif;margin:6px 0 18px}
"""


def page(body: str, css: str = "") -> str:
    return (
        f'<!doctype html><html><head><meta charset="utf-8">{FONTS}'
        f"<style>{BASE_CSS}{css}</style></head><body>{body}</body></html>"
    )


def av(role: str, mood: str = "running") -> str:
    return f'<img class="av" src="../crew/{role}-{mood}.svg" alt="">'


def bar(pct: int, color: str, width: int = 10, full: str = "█", empty: str = "░") -> str:
    n = round(pct / 100 * width)
    return f'<span class="bar"><span style="color:{color}">{full * n}</span><span style="color:#D5D2CA">{empty * (width - n)}</span></span>'


def agent_row(role, mood, mark, desc, effort, ecolor, model, ctx_pct, ctx, time, cost):
    lead = '<img src="../crew/dots.svg" style="width:20px;height:10px" alt="">' if mark == "dots" else f'<b style="color:{ {"✓": "#3BA55C", "✗": "#C0392B", "◦": "#9AA0A6"}[mark] }">{mark}</b>'
    return (
        f'<div class="row">{av(role, mood)}{lead}<span class="desc">{desc}</span>'
        f'<span style="color:{ecolor}">{effort}</span><span class="dim">{model}</span><span class="grow"></span>'
        f'{bar(ctx_pct, ecolor, 6, "━", "━")}<span class="dim">{ctx}</span><span class="dim">{time}</span><span class="dim">≈${cost}</span></div>'
    )


BAND_ROWS = (
    agent_row("main", "running", "dots", "Main agent", "medium", "#4A9FD9", "Opus 5.5", 31, "312k", "4:12", "1.06")
    + agent_row("architect", "running", "dots", "Plan the recipe-search page", "careful", "#D99A3B", "Opus 5.5", 18, "184k", "2:40", "0.41")
    + agent_row("developer", "running", "dots", "Build the search filters", "medium", "#4A9FD9", "Sonnet 5.5", 12, "121k", "1:55", "0.18")
    + agent_row("scout", "running", "dots", "Run the tests and report", "light", "#3BB8A0", "Haiku 5.5", 5, "48k", "0:37", "0.02")
)


def totals(used=58, elapsed=64, verdict="On Pace", color="#9AA0A6"):
    return (
        '<div class="row"><b>Agents</b><span class="dim">≈$1.67 · 665k · 4:12</span><span class="grow"></span>'
        f'<span class="dim">Usage</span>{bar(used, color)}<span class="dim">{used}% / {elapsed}% Week, {verdict}</span>'
        '<span class="btn">Hide</span></div>'
    )


def done_row():
    return '<div class="row"><span class="dim">3 done · ≈$0.52</span><span class="btn">Show</span></div>'


IMAGES = {}

# 1. Hero: the crew on a blue poster, the band underneath.
crew = "".join(
    f'<figure>{av(r)}<figcaption>{n}</figcaption></figure>'
    for r, n in [("main", "Captain"), ("architect", "Architect"), ("developer", "Developer"), ("reviewer", "Reviewer"),
                 ("shipper", "Shipper"), ("scout", "Scout"), ("explore", "Explorer")]
)
IMAGES["hero"] = (1280, 590, page(f"""
<div class="hero">
  <div class="mono tag">a mod for Claude Code</div>
  <h1>See your agents <em>work.</em></h1>
  <p>A tiny pixel crew above your prompt box, plus a bar that tells you if your weekly limit will last.</p>
  <div class="crew">{crew}</div>
  <div class="band" style="margin-top:34px">{totals()}{BAND_ROWS}</div>
</div>""", """
body{background:var(--blue)}
.hero{padding:52px 64px;color:#fff;position:relative}
.tag{display:inline-block;background:var(--yellow);color:var(--ink);font-weight:700;font-size:14px;padding:5px 12px;border-radius:6px}
h1{font-size:88px;font-weight:900;font-stretch:75%;line-height:.95;margin:18px 0 12px;letter-spacing:-.01em}
h1 em{font-style:normal;color:var(--yellow)}
.hero>p{font-size:22px;max-width:760px;opacity:.92;line-height:1.35}
.crew{position:absolute;right:58px;top:60px;display:grid;grid-template-columns:repeat(4,auto);gap:10px 18px;background:rgba(255,255,255,.1);padding:18px 20px;border-radius:16px}
.crew figure{display:flex;flex-direction:column;align-items:center;gap:4px}
.crew img.av{width:68px;height:56px}
.crew figcaption{font:600 12px 'JetBrains Mono',monospace;color:var(--yellow)}
.band{color:var(--ink);box-shadow:0 20px 50px rgba(0,0,0,.25)}
"""))

# 2. Anatomy of the band, numbered.
IMAGES["band-anatomy"] = (1280, 690, page(f"""
<div style="padding:40px 48px 40px 68px">
  <div class="step">What you are looking at</div>
  <div class="cap">The agent band sits right above the box where you type.</div>
  <div style="position:relative">
    <div class="band">{totals()}{BAND_ROWS}{done_row()}</div>
    <div class="pin" style="position:absolute;left:-42px;top:12px">1</div>
    <div class="pin" style="position:absolute;right:470px;top:-14px">2</div>
    <div class="pin" style="position:absolute;left:-42px;top:62px">3</div>
    <div class="pin" style="position:absolute;left:330px;top:52px">4</div>
    <div class="pin" style="position:absolute;right:150px;top:52px">5</div>
    <div class="pin" style="position:absolute;left:-42px;bottom:12px">6</div>
  </div>
  <div class="prompt" style="margin-top:12px"><span>Reply to Claude…</span><span class="send">↑</span></div>
  <div class="legend">
    <div><span class="pin">1</span><span><b>Running total</b>Rough cost, tokens read and time for this chat and all its helpers.</span></div>
    <div><span class="pin">2</span><span><b>Weekly limit</b>How much of your week you have used, against how much of the week has passed.</span></div>
    <div><span class="pin">3</span><span><b>The crew</b>The main chat wears the captain's hat. Each helper agent gets its own character.</span></div>
    <div><span class="pin">4</span><span><b>Effort and model</b>How hard it thinks (light, medium, careful, heavy) and which Claude it is.</span></div>
    <div><span class="pin">5</span><span><b>Memory, time, cost</b>How full its memory is, how long it has run, about what it cost.</span></div>
    <div><span class="pin">6</span><span><b>Finished helpers</b>Done agents fold into one line. Press Show to see them again.</span></div>
  </div>
</div>"""))

# 3. The four pace colors.
pace = [
    (30, 60, "Under Pace", "#3BA55C", "Green", "You are using less than the week so far. Relax, keep going."),
    (52, 55, "On Pace", "#9AA0A6", "Grey", "Right on track to last the whole week."),
    (61, 55, "Ahead Of Pace", "#D99A3B", "Orange", "A bit fast. Use lighter models or shorter chats for a while."),
    (80, 55, "Over Pace", "#C0392B", "Red", "At this speed you run out before the week resets. Slow down."),
]
cards = "".join(
    f'<div class="pc"><div class="row" style="gap:8px">{bar(u, c)}<span class="dim mono" style="font-size:13px">{u}% / {e}% Week</span></div>'
    f'<div class="vd" style="color:{c}">{v}</div><p>{t}</p></div>'
    for u, e, v, c, _, t in pace
)
IMAGES["pace"] = (1280, 320, page(f"""
<div style="padding:40px 48px">
  <div class="step">The weekly bar</div>
  <div class="cap">First number: how much you used. Second: how much of the week is gone.</div>
  <div class="grid">{cards}</div>
  <p class="dim" style="margin-top:22px;font-size:15px">Example: <b style="color:var(--ink)">58% / 64%</b> means you used 58% of your weekly limit, and 64% of the week has passed. You are fine.</p>
</div>""", """
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.pc{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px}
.vd{font:800 22px Archivo,sans-serif;margin:14px 0 6px}
.pc p{font-size:15px;line-height:1.4;color:#4A4843}
"""))

# 4. Moods.
moods = [("running", "Working", "Walking, blinking, busy with its job."), ("done", "Done", "Happy eyes. The job finished fine."),
         ("failed", "Failed", "Turns red with crossed eyes. Something went wrong."), ("scheduled", "Waiting", "Faded and sleepy. Not started yet.")]
IMAGES["moods"] = (1280, 270, page(f"""
<div style="padding:40px 48px">
  <div class="step">Read the faces</div>
  <div class="cap">Every character shows how its job is going.</div>
  <div class="grid">{"".join(f'<div class="m">{av("developer", m)}<div><b>{t}</b><p>{d}</p></div></div>' for m, t, d in moods)}</div>
</div>""", """
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.m{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px;display:flex;gap:14px;align-items:center}
.m img.av{width:84px;height:69px}
.m b{font:800 19px Archivo,sans-serif}.m p{font-size:14px;color:#4A4843;line-height:1.35;margin-top:3px}
"""))

# 5. Context band.
IMAGES["context-band"] = (1280, 290, page(f"""
<div style="padding:40px 48px">
  <div class="step">The context band</div>
  <div class="cap">When Claude's memory is 60% full, this pops up. One click tidies it.</div>
  <div class="band"><div class="row"><b>Context 64%</b><span>(128K tokens)</span><span class="btn primary">Compact now</span><span class="btn">Later</span></div></div>
  <div class="prompt" style="margin-top:12px"><span>Reply to Claude…</span><span class="send">↑</span></div>
  <p class="dim" style="margin-top:18px;font-size:15px"><b style="color:var(--ink)">Compact now</b> makes Claude write a short summary of the chat and continue from it, so answers stay sharp and cost less. <b style="color:var(--ink)">Later</b> hides it for a while.</p>
</div>"""))

# 6. Install steps.
def term(title: str, body: str, h: int) -> str:
    return (f'<div class="term"><div class="top"><i style="background:#FF5F57"></i><i style="background:#FEBC2E"></i>'
            f'<i style="background:#28C840"></i><span>{title}</span></div><div class="body" style="min-height:{h}px">{body}</div></div>')

IMAGES["step-1-terminal"] = (1280, 260, page("""
<div style="padding:40px 48px">
  <div class="step">Step 1 · Open Terminal</div>
  <div class="cap">Press ⌘ Command + Space, type <u>Terminal</u>, press Enter.</div>
  <div class="spot"><span class="glass">⌕</span><span>Terminal</span><span class="cursor" style="background:#2B35FF;height:26px;width:2px"></span></div>
  <div class="hit"><span class="ticon">&gt;_</span><b>Terminal</b><span class="dim" style="margin-left:auto">Application</span></div>
</div>""", """
.spot{background:#fff;border:1px solid var(--line);border-radius:14px 14px 0 0;padding:16px 20px;font-size:26px;display:flex;gap:14px;align-items:center;box-shadow:0 20px 50px rgba(0,0,0,.08);max-width:720px}
.glass{color:var(--mute);font-size:28px}
.hit{background:#2B35FF;color:#fff;border-radius:0 0 14px 14px;padding:12px 20px;display:flex;gap:14px;align-items:center;font-size:18px;max-width:720px}
.hit .dim{color:#C9CCFF}
.ticon{background:#1E1E1E;color:#fff;font:700 13px 'JetBrains Mono';border-radius:7px;padding:6px 7px}
"""))

CMD = ("claude plugin marketplace add mshadmanrahman/claude-agent-panel &amp;&amp; "
       "claude plugin install agent-panel@claude-agent-panel &amp;&amp; "
       "claude plugin install context-band@claude-agent-panel")

IMAGES["step-2-paste"] = (1280, 290, page(f"""
<div style="padding:40px 48px">
  <div class="step">Step 2 · Paste the magic line</div>
  <div class="cap">Paste it with ⌘ Command + V, then press Enter.</div>
  {term("Terminal", f'<span class="ok">you@mac</span> <span class="cy">~</span> % {CMD}<span class="cursor"></span>', 120)}
</div>"""))

IMAGES["step-3-success"] = (1280, 370, page(f"""
<div style="padding:40px 48px">
  <div class="step">Step 3 · Look for three green ticks</div>
  <div class="cap">Three ✔ lines means it worked. That's the whole install.</div>
  {term("Terminal", f'''<span class="ok">you@mac</span> <span class="cy">~</span> % <span class="gr">claude plugin marketplace add … &amp;&amp; claude plugin install …</span>
<span class="gr">Clone complete, validating marketplace…</span>
<span class="ok">✔ Successfully added marketplace: claude-agent-panel</span>
<span class="ok">✔ Successfully installed plugin: agent-panel@claude-agent-panel (scope: user)</span>
<span class="ok">✔ Successfully installed plugin: context-band@claude-agent-panel (scope: user)</span>
<span class="ok">you@mac</span> <span class="cy">~</span> % <span class="cursor"></span>''', 200)}
</div>"""))

IMAGES["step-0-ask-claude"] = (1280, 320, page("""
<div style="padding:40px 48px">
  <div class="step">The lazy way · Let Claude do it</div>
  <div class="cap">Open the Claude app, go to the Code tab, paste this, press Enter.</div>
  <div class="chat">
    <div class="tabs"><span>Chat</span><span class="on">Code</span></div>
    <div class="prompt" style="color:var(--ink);align-items:flex-start;min-height:120px;font-size:17px;line-height:1.5">
      <span>Install the Claude Code mods from github.com/mshadmanrahman/claude-agent-panel for me. Run: claude plugin marketplace add mshadmanrahman/claude-agent-panel, then claude plugin install agent-panel@claude-agent-panel and claude plugin install context-band@claude-agent-panel. Tell me when all three say Successfully.</span>
      <span class="send" style="flex-shrink:0;margin-left:16px">↑</span>
    </div>
  </div>
</div>""", """
.chat{max-width:980px}
.tabs{display:inline-flex;background:#EFECE4;border-radius:10px;padding:4px;margin-bottom:12px;gap:4px}
.tabs span{padding:6px 16px;border-radius:7px;font-weight:600;font-size:14px;color:var(--mute)}
.tabs .on{background:#fff;color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
"""))


def main() -> None:
    for name, (w, h, html) in IMAGES.items():
        src = SRC / f"{name}.html"
        src.write_text(html)
        out = OUT / f"{name}.png"
        subprocess.run(
            [CHROME, "--headless=new", "--hide-scrollbars", f"--window-size={w},{h}", "--force-device-scale-factor=2",
             "--virtual-time-budget=4000", f"--screenshot={out}", src.as_uri()],
            check=True, capture_output=True,
        )
        print(out.name)


if __name__ == "__main__":
    main()
