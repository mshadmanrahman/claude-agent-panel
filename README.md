# claude-agent-panel

Two small mods for Claude Code. Both draw a band just above the prompt box, in the terminal and in the Claude desktop app's Code tab.

## agent-panel

Shows what your agents are doing while they work.

- **Weekly usage bar.** How much of your weekly limit you have used, next to how much of the week has passed, with a verdict: under pace, on pace, ahead of pace or over pace. A green bar means you can relax; red means slow down.
- **One row per agent.** The main chat gets its own row, and every subagent it starts gets one too, each with a small pixel avatar. The avatar's hat follows the agent's job: architect, developer, reviewer, shipper, scout or explorer.
- **Per-row numbers.** Model, effort, how full its context is, running time and an estimated cost.
- **Finished agents fold away** into a single "done" row you can open. The Hide button collapses the whole band.

The weekly bar needs a Claude subscription (Pro or Max). On an API key there is no weekly limit, so the bar stays hidden. Costs are estimates from list prices, not your bill.

## context-band

When your conversation fills 60% of the model's context window, a band appears with a **Compact now** button. Compacting summarizes the conversation so far, which frees room and makes each turn cheaper. **Later** hides the band until the context grows by another 50K tokens.

## Install

Open Claude Code in a terminal and type each line at the prompt:

```
/plugin install agent-panel --marketplace mshadmanrahman/claude-agent-panel
```

```
/plugin install context-band --marketplace mshadmanrahman/claude-agent-panel
```

The first time, Claude Code asks whether to add the marketplace: answer `y`, then pick where to install it (user scope puts it in every project). Start a new session and the band shows up after your first message.

To remove one, run `/plugin uninstall agent-panel` (or `context-band`).

## Change it yourself

Each mod is one file, `hooks/register.tsx`. Some easy changes to try:

| What | Where |
| --- | --- |
| When the context band appears | `WARN` in `context-band/hooks/register.tsx` |
| Prices used for cost estimates | `PRICES` in `agent-panel/hooks/register.tsx` |
| Which agent names map to which avatar | `roleOf()` in `agent-panel/hooks/register.tsx` |
| Avatar colors and hats | `PERSONAS` in `agent-panel/hooks/register.tsx` |

To try your edits before installing, start Claude Code with the folder loaded directly:

```
claude --plugin-dir ./agent-panel
```

Built by Shadman Rahman.
