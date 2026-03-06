from .query_coder import QueryCoder
from .base_coder import Coder
from .context_coder import ContextCoder
from .editblock_coder import EditBlockCoder
from .editblock_fenced_coder import EditBlockFencedCoder
from .editor_diff_fenced_coder import EditorDiffFencedCoder
from .editor_editblock_coder import EditorEditBlockCoder
from .editor_whole_coder import EditorWholeFileCoder
from .help_coder import HelpCoder
from .patch_coder import PatchCoder
from .selection_coder import SelectionCoder
from .udiff_coder import UnifiedDiffCoder
from .udiff_simple import UnifiedDiffSimpleCoder
from .wholefile_coder import WholeFileCoder

# from .single_wholefile_func_coder import SingleWholeFileFunctionCoder

# ArchitectCoder and AgentCoder are no longer registered as edit formats.
# Their orchestration logic now lives in autonomy strategies
# (aider.coders.autonomy).  The modules still exist for backward
# compatibility but are not in __all__.

__all__ = [
    HelpCoder,
    QueryCoder,
    Coder,
    EditBlockCoder,
    EditBlockFencedCoder,
    WholeFileCoder,
    PatchCoder,
    UnifiedDiffCoder,
    UnifiedDiffSimpleCoder,
    #    SingleWholeFileFunctionCoder,
    EditorEditBlockCoder,
    EditorWholeFileCoder,
    EditorDiffFencedCoder,
    ContextCoder,
    SelectionCoder,
]
