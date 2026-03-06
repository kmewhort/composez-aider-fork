from .agent_prompts import AgentPrompts
from .query_coder import QueryCoder


class AgentCoder(QueryCoder):
    """Orchestrate multi-step plans using slash commands."""

    edit_format = "agent"
    gpt_prompts = AgentPrompts()

    def reply_completed(self):
        content = self.partial_response_content
        if not content or not content.strip():
            return

        try:
            from composez_core.agent_runner import AgentRunner
        except ImportError:
            self.io.tool_error("Agent runner not available.")
            return

        runner = AgentRunner(self)
        plan = runner.parse_plan(content)
        if plan is None:
            # Ask the model to retry with a proper YAML plan
            self.reflected_message = (
                "Please respond with a concrete YAML plan as described in your instructions."
            )
            return

        runner.show_plan(plan)

        if not self.io.confirm_ask("Execute this plan?"):
            self.io.tool_output("Plan cancelled.")
            return

        runner.execute(plan)
        return True
