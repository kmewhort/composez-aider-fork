# Aider (Composez Fork)

This is fork of https://github.com/Aider-AI/aider, modified to allow changing the command set and to add new features in support of the `composez` novel editing features.

## Modifications to aider

### Autonomy system

The fork replaces the old `architect` and `agent` edit formats with a new
**autonomy** layer (`aider/coders/autonomy.py`) that is orthogonal to the edit
mode. Three autonomy levels are available:

| Level | Description |
|-------|-------------|
| **direct** | Single-turn — one prompt, one response, edits applied. |
| **compose** | Two-phase — an LLM plans changes, then a separate editor coder implements them (replaces the old `architect` mode). |
| **agent** | Multi-step — the LLM produces a YAML plan that is executed via slash commands (requires `composez_core.agent_runner`). |

Autonomy is selected via `/chat compose`, `/chat agent`, or `/chat direct` and
is tracked on each coder instance via `coder.autonomy_strategy`.

### New coders

- **SelectionCoder** (`aider/coders/selection_coder.py`) — operates on a
  user-highlighted text range using LSP-style `Range` coordinates. The LLM
  receives context lines around the selection and responds with a replacement
  block delimited by `--[REPLACEMENT TEXT START]-->` / `<--[REPLACEMENT TEXT END]--`.
- **AgentCoder** (`aider/coders/agent_coder.py`) — produces structured YAML plans
  for multi-step orchestration (used by the `agent` autonomy strategy).
- **QueryCoder** (`aider/coders/query_coder.py`) — replaces `AskCoder`. Read-only
  queries against the project; renamed to better fit the novel-editing workflow.

### Composez integration hooks

The coder creation path (`Coder.create()`) includes soft-dependency hooks into
`composez_core`:

- **Novel mode activation** — calls `composez_core.novel_coder` to apply
  novel-specific prompts and constraints based on the coder type.
- **Role-based model resolution** — reads a `.composez` config file to map
  (edit_format, autonomy) combinations to six named model roles:
  `admin_model`, `query_model`, `edit_model`, `selection_model`,
  `compose_model`, `agent_model`.
- **Pluggable path validator** — `coder.edit_path_validator` callback to
  enforce file-editing constraints (e.g. narrative file rules).
- **Novel commands** — `Commands.novel_commands` lazily loads
  `composez_core.NovelCommands`, which can add, override, or hide slash commands.

All `composez_core` imports are guarded by `try/except ImportError` so the fork
runs standalone as a regular aider instance when `composez_core` is not installed.

### Command and branding changes

- All user-facing strings rebrand "aider" to "composez" (`args.py`, `commands.py`,
  `repo.py`, etc.).
- `/ask` renamed to `/query`; `/code` aliased as `/edit`.
- `/chat` now shows edit modes (help, query, edit, selection) and autonomy levels
  (direct, compose, agent) as separate categories.
- `/help` simplified to show the command list (removed the interactive RAG-based
  help system).
- `/report` command removed.
- New `--auto-context` CLI flags.

### Other changes

- **Auto-context** — when enabled, mentioned files are added to the chat
  automatically without prompting.
- **Auto-create files** — files in `coder.auto_create_fnames` are created
  without confirmation (e.g. `SUMMARY.md`, `PROSE.md`).
- **ConfirmGroup for multi-file edits** — `apply_edits` and `allowed_to_edit`
  now use `ConfirmGroup` so users can approve/skip all files at once.
- **Lint skipped for query/selection** — auto-lint is bypassed when the edit
  format is `query` or `selection`.

## License

Licensed under Apache Version 2.0.  See `license.txt' for details.
