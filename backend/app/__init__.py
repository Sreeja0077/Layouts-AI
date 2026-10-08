"""Layouts AI Backend Application Package."""

import sys
from pathlib import Path

# Ensure repository root and backend directory are always on sys.path
_app_dir = Path(__file__).resolve().parent
_backend_dir = _app_dir.parent
_repo_root = _backend_dir.parent

for path in (_repo_root, _backend_dir):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
