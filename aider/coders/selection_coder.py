"""Selection-mode coder — replaces a user-selected text range in a file."""

import json
import re

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .selection_prompts import SelectionPrompts


class SelectionCoder(Coder):
    """Replace a selected range of text in a file."""

    edit_format = "selection"
    gpt_prompts = SelectionPrompts()

    # ------------------------------------------------------------------
    # Selection state — set before running the coder
    # ------------------------------------------------------------------
    #   selection_filename : str   – relative path to the file
    #   selection_range    : dict  – LSP Range, e.g.
    #       {"start": {"line": 4, "character": 0},
    #        "end":   {"line": 6, "character": 45}}
    #   selection_text     : str   – exact text of the selection
    # ------------------------------------------------------------------

    CONTEXT_LINES = 3  # lines of context before/after

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def selection_prompt(self):
        """Build the SELECTION block that precedes the user's instruction."""
        fname = getattr(self, "selection_filename", None)
        sel_range = getattr(self, "selection_range", None)
        sel_text = getattr(self, "selection_text", None)

        if not fname or sel_range is None or sel_text is None:
            return ""

        start_line = sel_range["start"]["line"]  # 0-indexed
        end_line = sel_range["end"]["line"]

        # Read the full file to extract context lines
        full_path = self.abs_root_path(fname)
        content = self.io.read_text(full_path)
        if content is None:
            return ""

        lines = content.splitlines(keepends=True)

        start_char = sel_range["start"]["character"]
        end_char = sel_range["end"]["character"]

        # Context before: full lines above + same-line text before the selection
        ctx_start = max(0, start_line - self.CONTEXT_LINES)
        before_lines = lines[ctx_start:start_line]
        before_text = "".join(before_lines).rstrip("\n")
        # Include same-line prefix so the LLM sees mid-word boundaries
        if start_line < len(lines) and start_char > 0:
            same_line_prefix = lines[start_line][:start_char]
            if before_text:
                before_text += "\n" + same_line_prefix
            else:
                before_text = same_line_prefix

        # Context after: same-line text after the selection + full lines below
        ctx_end = min(len(lines), end_line + 1 + self.CONTEXT_LINES)
        after_lines = lines[end_line + 1 : ctx_end]
        after_text = "".join(after_lines).rstrip("\n")
        # Include same-line suffix so the LLM sees mid-word boundaries
        if end_line < len(lines):
            same_line_suffix = lines[end_line][end_char:]
            if same_line_suffix.strip():
                if after_text:
                    after_text = same_line_suffix.rstrip("\n") + "\n" + after_text
                else:
                    after_text = same_line_suffix.rstrip("\n")

        range_json = json.dumps(sel_range)

        parts = [
            "I have highlighted a section of SELECTED TEXT.",
        ]
        if before_text:
            parts.append("")
            parts.append(
                "For context, the text appearing immediately before the selection is:"
            )
            parts.append(before_text)
        parts.append("")
        parts.append("The exact selected text is:")
        parts.append(f"--[SELECTED TEXT START]-->{sel_text}<--[SELECTED TEXT END]--")
        if after_text:
            parts.append("")
            parts.append(
                "For additional context, the text appearing"
                " immediately after the selection is:"
            )
            parts.append(after_text)
        parts.append("")
        parts.append(f"This text can be found in {fname} at:")
        parts.append(f"Range: {range_json}")

        return "\n".join(parts)

    def _prepend_selection_block(self, user_message):
        """Prepend the SELECTED TEXT block to the user message."""
        sel_block = self.selection_prompt()
        if sel_block and user_message:
            return sel_block + "\n\n" + user_message
        return user_message

    def run(self, with_message=None, preproc=True):
        """Override run to prepend selection context to the user message."""
        if with_message:
            with_message = self._prepend_selection_block(with_message)
        else:
            sel_block = self.selection_prompt()
            if sel_block:
                # When running interactively, the selection block is prepended
                # to whatever the user types next.
                self._pending_selection_block = sel_block

        return super().run(with_message=with_message, preproc=preproc)

    def run_stream(self, user_message):
        """Override run_stream to prepend selection context to the user message."""
        user_message = self._prepend_selection_block(user_message)
        yield from super().run_stream(user_message)

    def get_input(self):
        """Prepend pending selection block to the next user input."""
        user_msg = super().get_input()
        pending = getattr(self, "_pending_selection_block", None)
        if pending:
            self._pending_selection_block = None
            if user_msg and not self.commands.is_command(user_msg):
                user_msg = pending + "\n\n" + user_msg
        return user_msg

    # ------------------------------------------------------------------
    # Parsing — extract replacement text from the response
    # ------------------------------------------------------------------

    _REPLACEMENT_RE = re.compile(
        r"--\[REPLACEMENT TEXT START\]-->(.*?)<--\[REPLACEMENT TEXT END\]--",
        re.DOTALL,
    )

    def get_edits(self):
        """Parse the LLM response for the replacement text."""
        content = self.partial_response_content
        replacement = self._extract_replacement(content)
        if replacement is None:
            raise ValueError(
                "Could not find the replacement text delimited by "
                "--[REPLACEMENT TEXT START]--> and <--[REPLACEMENT TEXT END]-- "
                "in the response."
            )

        fname = getattr(self, "selection_filename", None)
        sel_range = getattr(self, "selection_range", None)
        if not fname or sel_range is None:
            raise ValueError("No active selection to apply edits to.")

        return [(fname, sel_range, replacement)]

    def _extract_replacement(self, content):
        """Extract text between REPLACEMENT TEXT delimiters, or fall back to fenced block."""
        m = self._REPLACEMENT_RE.search(content)
        if m:
            return m.group(1)

        # Fallback: try a fenced code block in case the LLM used backticks
        return self._extract_fenced_block(content)

    def _extract_fenced_block(self, content):
        """Return the content of the first fenced code block, or None."""
        fence_open = self.fence[0]
        fence_close = self.fence[1]

        pattern = re.compile(
            r"^" + re.escape(fence_open) + r"[^\n]*\n(.*?)\n?" + re.escape(fence_close),
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(content)
        if m:
            return m.group(1)
        return None

    # ------------------------------------------------------------------
    # Applying edits — splice replacement into the file at the range
    # ------------------------------------------------------------------

    def apply_edits_dry_run(self, edits):
        return edits

    def apply_edits(self, edits):
        for fname, sel_range, replacement in edits:
            full_path = self.abs_root_path(fname)
            content = self.io.read_text(full_path)
            if content is None:
                raise ValueError(f"Cannot read {fname}")

            new_content = _apply_selection_replacement(
                content, sel_range, replacement
            )
            self.io.write_text(full_path, new_content)

            # Update the remembered selection to cover the replaced text
            self._update_selection_after_replace(
                content, sel_range, replacement
            )

    def _update_selection_after_replace(self, old_content, sel_range, replacement):
        """Recompute selection_range and selection_text to cover the replacement."""
        start = sel_range["start"]
        new_lines = replacement.split("\n")

        if len(new_lines) == 1:
            end_line = start["line"]
            end_char = start["character"] + len(new_lines[0])
        else:
            end_line = start["line"] + len(new_lines) - 1
            end_char = len(new_lines[-1])

        self.selection_range = {
            "start": {"line": start["line"], "character": start["character"]},
            "end": {"line": end_line, "character": end_char},
        }
        self.selection_text = replacement


def _apply_selection_replacement(content, sel_range, replacement):
    """Replace the text in *content* at *sel_range* with *replacement*.

    ``sel_range`` uses LSP Range semantics (0-indexed line and character).
    """
    lines = content.splitlines(keepends=True)

    start_line = sel_range["start"]["line"]
    start_char = sel_range["start"]["character"]
    end_line = sel_range["end"]["line"]
    end_char = sel_range["end"]["character"]

    # Build prefix (everything before the selection)
    prefix_lines = lines[:start_line]
    if start_line < len(lines):
        prefix_lines.append(lines[start_line][:start_char])
    prefix = "".join(prefix_lines)

    # Build suffix (everything after the selection)
    suffix_parts = []
    if end_line < len(lines):
        suffix_parts.append(lines[end_line][end_char:])
    suffix_parts.extend(lines[end_line + 1 :])
    suffix = "".join(suffix_parts)

    return prefix + replacement + suffix
