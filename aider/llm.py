import importlib
import os
import warnings

from aider.dump import dump  # noqa: F401

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

COMPOSEZ_SITE_URL = "https://composez.app"
COMPOSEZ_APP_NAME = "Composez"

os.environ["OR_SITE_URL"] = COMPOSEZ_SITE_URL
os.environ["OR_APP_NAME"] = COMPOSEZ_APP_NAME
os.environ["LITELLM_MODE"] = "PRODUCTION"

# `import litellm` takes 1.5 seconds, defer it!

VERBOSE = False


class LazyLiteLLM:
    _lazy_module = None

    def __getattr__(self, name):
        if name == "_lazy_module":
            return super()
        self._load_litellm()
        return getattr(self._lazy_module, name)

    def _load_litellm(self):
        if self._lazy_module is not None:
            return

        if VERBOSE:
            print("Loading litellm...")

        self._lazy_module = importlib.import_module("litellm")

        # Always suppress litellm's own verbose logging — it produces a
        # firehose of internal noise (cost calculator retries, model_info
        # lookups, etc.) that drowns out useful information.  We install
        # our own litellm callbacks in the worker (_install_llm_logging)
        # that capture the useful info (model, tokens, latency, errors).
        self._lazy_module.suppress_debug_info = True
        self._lazy_module.set_verbose = False
        self._lazy_module.drop_params = True
        self._lazy_module._logging._disable_debugging()


litellm = LazyLiteLLM()

__all__ = [litellm]
