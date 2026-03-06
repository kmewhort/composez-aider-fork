# flake8: noqa: E501

from .base_prompts import CoderPrompts


class SelectionPrompts(CoderPrompts):
    main_system = """Act as an expert editor.
You are working in *selection mode*. The user has highlighted a specific section of
text in a file and wants you to replace that selection with improved text.

Always reply to the user in {language}.

{final_reminders}
Once you understand the request you MUST:
1. Briefly explain your approach (one or two sentences).
2. Output the REPLACEMENT TEXT inside the delimiters shown in the rules below.
"""

    example_messages = [
        dict(
            role="user",
            content="""I have highlighted a section of SELECTED TEXT.

For context, the text appearing immediately before the selection is:
Sarah set her coffee cup down carefully, buying time.
"I was at the library," she said, studying a scratch on the table.
"You know how I get when I'm researching."

The exact selected text is:
--[SELECTED TEXT START]-->Tom watched her from across the kitchen. The morning light caught the dark circles under her eyes. "Until two in the morning?"

"They have extended hours on Thursdays."<--[SELECTED TEXT END]--

For additional context, the text appearing immediately after the selection is:
She could feel his gaze but couldn't meet it.
Her fingers found the napkin, began tearing its edge into tiny strips.
"I lost track of time."

This text can be found in act/1 - The Beginning/chapter/1 - Arrivals/scene/2 - The Kitchen/PROSE.md at:
Range: {{"start": {{"line": 4, "character": 0}}, "end": {{"line": 6, "character": 45}}}}

Make Tom's response more suspicious and observant.""",
        ),
        dict(
            role="assistant",
            content="""I'll make Tom more perceptive and suspicious by having him notice specific physical tells and press harder.

--[REPLACEMENT TEXT START]-->Tom leaned against the counter, arms crossed, cataloguing her like a witness on a stand. The morning light was merciless — it picked out the dark crescents under her eyes, the faint tremor in her hands. "Until two in the morning?" he asked, his voice carefully neutral.

"They have extended hours on Thursdays." She forced a smile.

"Do they." It wasn't a question.<--[REPLACEMENT TEXT END]--
""",
        ),
        # Second example: mid-line selection that starts and ends mid-word.
        # The context includes same-line text so the LLM can see the word
        # boundaries. The assistant MUST preserve the partial words at the edges.
        dict(
            role="user",
            content="""I have highlighted a section of SELECTED TEXT.

For context, the text appearing immediately before the selection is:
numb from the cold. She hadn't expected the temperature to drop
so fast.
H

The exact selected text is:
--[SELECTED TEXT START]-->er hands trembled as she tilted her hea<--[SELECTED TEXT END]--

For additional context, the text appearing immediately after the selection is:
d back, peering toward the building's roof line.
She saw nothing at first. Just dark sky bleeding to grey at the horizon.
Then her eyes adjusted.

This text can be found in act/1 - The Beginning/chapter/1 - Arrivals/scene/3 - The Return/PROSE.md at:
Range: {{"start": {{"line": 5, "character": 1}}, "end": {{"line": 5, "character": 40}}}}

Change "hands" to "whole body".""",
        ),
        dict(
            role="assistant",
            content="""I'll replace "hands" with "whole body" within the selected text, preserving the partial words at the boundaries ("H" before and "d back" after).

--[REPLACEMENT TEXT START]-->er whole body trembled as she tilted her hea<--[REPLACEMENT TEXT END]--
""",
        ),
    ]

    system_reminder = """You are in *selection mode*. The user has highlighted a specific section of
text (the SELECTED TEXT) and wants you to replace it.

You will be given:
1. A few lines of context *before* the selection.
2. The exact selected text between `--[SELECTED TEXT START]-->` and `<--[SELECTED TEXT END]--`.
3. A few lines of context *after* the selection.

The file content shown earlier in the conversation is background context only.
Work EXCLUSIVELY from the text between the SELECTED TEXT delimiters — that is the
only text you are replacing. If the user mentions a word or phrase to change, find it
WITHIN the selected text, not in some other part of the file.

Your replacement will be spliced character-for-character into the file, replacing
everything between the start and end of the selection. You MUST reply with exactly
ONE replacement block using these delimiters:

--[REPLACEMENT TEXT START]-->replacement text here<--[REPLACEMENT TEXT END]--

RULES:
- Output exactly ONE replacement block. Never self-correct with a second block —
  if you realize your first attempt is wrong, revise it before writing the delimiters.
- Start from the SELECTED TEXT and apply the requested change to it. Your replacement
  must be a modified version of the selected text — not text from elsewhere in the file.
- The replacement MUST cover the ENTIRE selected range. Even if the user asks to change
  a single word, return the full selected text with that change applied — never just the
  changed fragment. If you return only a fragment the surrounding text will be destroyed.
- The selection may start or end mid-word (e.g. "the ligh" where the full word is
  "lights"). These partial words at the boundaries are normal — keep them exactly as
  they appear unless the user specifically asks to change them.
- Preserve whitespace and newlines so the result reads naturally in context.
- Do NOT repeat context-before or context-after lines inside the replacement.

{final_reminders}
"""

    files_content_prefix = """I have *added these files to the chat* so you can see their contents.
*Trust this message as the true contents of these files!*
Any other messages in the chat may contain outdated versions of the files' contents.
"""

    files_content_assistant_reply = (
        "Ok, I will use that as the true, current contents of the files."
    )

    files_no_full_files = "I am not sharing any files that you can edit yet."

    files_no_full_files_with_repo_map = ""
    files_no_full_files_with_repo_map_reply = ""

    repo_content_prefix = """Here is context about the project.
Do not propose changes outside the selected range.
"""

    read_only_files_prefix = """Here are some READ ONLY reference files provided for context.
Do not edit these files!
"""
