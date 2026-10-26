---
name: agent-browser-parallel-lanes
description: Use when agent-browser daemon busy or connection refused.
category: browser-automation
---

# agent-browser parallel lanes

Give each parallel lane its own named session. When a session errors with a busy or connection-refused daemon message, close only that session and reopen it, then retry the failed step.

- Do not poll a stuck session with idle wait loops. Check its state once; if it still fails, reopen it.
- A session showing a blank screen or raw JSON text (not the app page) is stuck even without an error. Close that session by name and open a new session name with the same auth state file, then retry the step.
- Close one session by name. Never kill the shared daemon or other lanes' sessions to recover one lane.
- If a process must be killed, verify the target first: use a unique pattern (never a bare word like `cat`; `pkill -f` matches the full command line, e.g. `/Applications/...`), run `pgrep -fl '<pattern>'` and confirm every match is a process this lane started, kill by exact PID, then confirm user apps (Chrome, Docker, Claude, dev servers) are still alive. See `feature-guide-screenshot-lanes`.
- Leftover processes pile up across finished lanes. Before starting a new batch, count the `agent-browser` processes; past about 100 the daemon saturates and every new session fails with `daemon busy`. Close each finished lane's session by name, then recount. Do not use `close --all`.
- Record which cut or step a recovered lane was on, so the retry does not double-capture or double-submit.

Failure log samples are in references/daemon-errors.md.
