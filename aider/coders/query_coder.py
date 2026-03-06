from .query_prompts import QueryPrompts
from .base_coder import Coder


class QueryCoder(Coder):
    """Query code without making any changes."""

    edit_format = "query"
    gpt_prompts = QueryPrompts()
