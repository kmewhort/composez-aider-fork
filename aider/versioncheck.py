import os
import sys
import time
from pathlib import Path

import packaging.version

import aider
from aider import utils
from aider.dump import dump  # noqa: F401

VERSION_CHECK_FNAME = Path.home() / ".aider" / "caches" / "versioncheck"


def install_from_main_branch(io):
    """Disabled — composez does not auto-update from upstream."""
    return False


def install_upgrade(io, latest_version=None):
    """Disabled — composez does not auto-update from PyPI."""
    return False


def check_version(io, just_check=False, verbose=False):
    """Disabled — composez does not check for upstream aider versions."""
    return False
