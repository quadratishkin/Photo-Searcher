from __future__ import annotations

import sys
from pathlib import Path


SHIPPING_DIR_NAME = "NovaAI-Shipping"


def _ensure_shipping_module_path() -> None:
    shipping_dir = Path(__file__).resolve().parent.parent / SHIPPING_DIR_NAME
    shipping_dir_str = str(shipping_dir)
    if shipping_dir_str not in sys.path:
        sys.path.insert(0, shipping_dir_str)


_ensure_shipping_module_path()

from nova_ai_shipping.faces import (  # noqa: E402
    extract_faces,
    get_face_runtime_config,
    get_face_runtime_status,
)

__all__ = [
    "extract_faces",
    "get_face_runtime_config",
    "get_face_runtime_status",
]
