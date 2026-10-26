---
name: agent-browser-session-login
description: Use when agent-browser needs login or saved auth state.
category: browser-automation
---

# agent-browser: login, saved state, isolated sessions

Log in once per isolated session, verify the URL left the sign-in page, save the state, and reuse it. Never fill a field from a ref you matched loosely.

- One account or lane = one `--session <name>` (or `AGENT_BROWSER_SESSION=<name>`). Cookies and refs are per session.
- Set the viewport per session right after `open`: `agent-browser set viewport 1440 900`.
- Launch flags (`--args` / `AGENT_BROWSER_ARGS`, comma-separated) apply only when a session first launches. To change them, open a new `--session` name; reusing an existing one keeps the old browser. Close only that session with `agent-browser --session <name> close`, never `close --all`, which kills other sessions running in parallel.
- After `open`, run `wait --load networkidle`, then a short `wait 1500` before the first snapshot. SPA sign-in forms render late; fill against an early snapshot fails with "Element not found".
- Pick refs by the exact role and name line, e.g. `grep 'textbox "Email Address"'`, then take the `eN` from it. Never match a bare label substring: a container line such as `generic "...Email AddressPassword..."` gets picked up and the submit goes to the wrong element.
- Confirm with `agent-browser get url` that the page left the sign-in route before saving state. If it did not, the login failed; do not save.
- Save with `agent-browser state save ./auth-<name>.json`. Reuse with `agent-browser --session <name> --state ./auth-<name>.json open <url>`.
- Re-snapshot after every navigation or form submit; refs are stale after any page change.
- `find ... fill ... || true` swallows failures. Do not use it as the login step.
- Keep state files outside the repo, and never paste credentials into chat or into a subagent prompt; pass a file path instead.
