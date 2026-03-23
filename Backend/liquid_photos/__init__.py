from __future__ import annotations

import sys
from pathlib import Path


SHIPPING_DIR_NAME = "CoreAI"


def ensure_shipping_module_path() -> None:
    shipping_dir = Path(__file__).resolve().parents[2] / SHIPPING_DIR_NAME
    shipping_dir_str = str(shipping_dir)
    if shipping_dir_str not in sys.path:
        sys.path.insert(0, shipping_dir_str)


ensure_shipping_module_path()
