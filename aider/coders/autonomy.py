"""Autonomy strategies — orchestration patterns applied to any coder.

The autonomy level is orthogonal to the edit mode (query / edit / selection).
Each strategy implements ``reply_completed`` which is called by the base
coder after the LLM responds.

Levels
------
- **direct** (L1): Single turn — the coder runs once, edits are applied, done.
- **compose** (L2): Two-phase — the LLM plans (query-like), then an editor
  coder implements the plan.
- **agent** (L3): Multi-step — the LLM produces a YAML plan that is executed
  via slash commands.
"""

# Valid autonomy level names.
AUTONOMY_LEVELS = ("direct", "compose", "agent")


class AutonomyStrategy:
    """Base strategy — direct, single-turn autonomy (no-op)."""

    name = "direct"

    def reply_completed(self, coder):
        """Called after the LLM responds.  Return truthy to skip further processing."""
        pass


class ComposeStrategy(AutonomyStrategy):
    """Two-phase: the LLM plans, then a separate editor coder implements."""

    name = "compose"

    def reply_completed(self, coder):
        from .base_coder import Coder

        content = coder.partial_response_content
        if not content or not content.strip():
            return True  # nothing to do, but skip apply_updates

        # Signal that planning is done (for UI phase transitions)
        if hasattr(coder.io, "compose_phase"):
            coder.io.compose_phase("planning_done")

        if not coder.auto_accept_architect:
            confirm_plan = getattr(coder.io, "confirm_plan", None)
            if confirm_plan:
                result = confirm_plan("Implement this plan?")
                action = result.get("action", "proceed")
                if action == "stop":
                    coder.io.tool_output("Plan cancelled.")
                    return True
                if action == "refine":
                    refinement = result.get("text", "").strip()
                    coder.reflected_message = (
                        f"The user wants you to revise the plan:\n\n{refinement}"
                        if refinement
                        else "The user wants you to revise the plan. Please try again."
                    )
                    return True
            elif not coder.io.confirm_ask("Edit the files?"):
                return True  # user declined, skip apply_updates

        # Signal that editing is starting
        if hasattr(coder.io, "compose_phase"):
            coder.io.compose_phase("editing_start")

        # Determine the edit format for the editor phase.  The phase-2
        # coder should match the base edit mode:
        #   query     → QueryCoder answers using the plan as guidance
        #   selection → SelectionCoder applies the planned replacement
        #   edit      → model's preferred editor format (editor-diff, etc.)
        base_format = coder.edit_format
        if base_format in ("query", "selection"):
            editor_edit_format = base_format
        else:
            editor_edit_format = coder.main_model.editor_edit_format

        # Phase 2 model: let Coder.create() resolve from .composez based
        # on the editor edit format.  Don't pass main_model so the
        # role-based resolution kicks in (query_model, edit_model, or
        # selection_model depending on editor_edit_format).  Fall back to
        # the legacy editor_model / main_model if .composez has nothing.
        phase2_model = Coder._resolve_composez_model(
            editor_edit_format, "direct", coder, getattr(coder, "root", None)
        )
        if phase2_model is None:
            phase2_model = coder.main_model.editor_model or coder.main_model

        kwargs = dict()
        kwargs["main_model"] = phase2_model
        kwargs["edit_format"] = editor_edit_format
        kwargs["autonomy"] = "direct"  # editor phase is always single-turn
        kwargs["suggest_shell_commands"] = False
        kwargs["map_tokens"] = 0
        kwargs["total_cost"] = coder.total_cost
        kwargs["cache_prompts"] = False
        kwargs["num_cache_warming_pings"] = 0
        kwargs["summarize_from_coder"] = False

        new_kwargs = dict(io=coder.io, from_coder=coder)
        new_kwargs.update(kwargs)

        editor_coder = Coder.create(**new_kwargs)

        # Disable auto-context on the editor coder — context was already
        # gathered during the planning phase and carries over via from_coder.
        editor_coder._auto_context_enabled = False

        editor_coder.cur_messages = []
        editor_coder.done_messages = []

        if coder.verbose:
            editor_coder.show_announcements()

        editor_coder.run(with_message=content, preproc=False)

        if base_format != "query":
            coder.move_back_cur_messages("I made those changes to the files.")
        coder.total_cost = editor_coder.total_cost
        coder.aider_commit_hashes = editor_coder.aider_commit_hashes
        # Propagate edit metadata so the caller (e.g. _handle_chat) can
        # report edited files and commits back to the browser.
        if editor_coder.aider_edited_files:
            coder.aider_edited_files.update(editor_coder.aider_edited_files)
        if editor_coder.last_aider_commit_hash:
            coder.last_aider_commit_hash = editor_coder.last_aider_commit_hash
            coder.last_aider_commit_message = editor_coder.last_aider_commit_message
        return True  # phase 2 handled everything, skip apply_updates


class AgentStrategy(AutonomyStrategy):
    """Multi-step: the LLM produces a YAML plan executed via slash commands."""

    name = "agent"

    def reply_completed(self, coder):
        content = coder.partial_response_content
        if not content or not content.strip():
            return True  # nothing to do, but skip apply_updates

        try:
            from composez_core.agent_runner import AgentRunner
        except ImportError:
            coder.io.tool_error("Agent runner not available.")
            return True  # can't proceed, skip apply_updates

        runner = AgentRunner(coder)
        coder._agent_runner = runner  # expose for pause/resume
        plan = runner.parse_plan(content)
        if plan is None:
            # Ask the model to retry — reflected_message triggers a new
            # LLM round, so we must still skip apply_updates to prevent
            # the planning coder's get_edits() from running on the
            # malformed response.
            coder.reflected_message = (
                "Please respond with a concrete YAML plan as described in your instructions. "
                "Include `/add` steps to load the files you need and `/query` steps to gather "
                "information before making changes. Do not try to search or analyze files "
                "yourself — just output the YAML plan directly."
            )
            return True

        runner.show_plan(plan)

        confirm_plan = getattr(coder.io, "confirm_plan", None)
        if confirm_plan:
            result = confirm_plan("Execute this plan?")
            action = result.get("action", "proceed")
            if action == "stop":
                coder.io.tool_output("Plan cancelled.")
                return True
            if action == "refine":
                refinement = result.get("text", "").strip()
                coder.reflected_message = (
                    f"The user wants you to revise the plan:\n\n{refinement}"
                    if refinement
                    else "The user wants you to revise the plan. Please try again."
                )
                return True
        elif not coder.io.confirm_ask("Execute this plan?"):
            coder.io.tool_output("Plan cancelled.")
            return True

        runner.execute(plan)
        return True


def get_strategy(name):
    """Return an autonomy strategy instance for the given level name."""
    strategies = {
        "direct": AutonomyStrategy,
        "compose": ComposeStrategy,
        "agent": AgentStrategy,
    }
    cls = strategies.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown autonomy level {name!r}. "
            f"Valid levels are: {', '.join(AUTONOMY_LEVELS)}"
        )
    return cls()
