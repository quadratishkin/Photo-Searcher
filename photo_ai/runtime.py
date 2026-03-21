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

from nova_ai_shipping.runtime import (  # noqa: E402
    create_image_embedding,
    create_photo_index,
    create_text_embedding,
    get_ai_module_status,
    get_embedding_engine_metadata,
    load_ai_module,
    rewrite_search_query,
    translate_text_to_english,
    warm_ai_runtime,
)

__all__ = [
    "create_image_embedding",
    "create_photo_index",
    "create_text_embedding",
    "get_ai_module_status",
    "get_embedding_engine_metadata",
    "load_ai_module",
    "rewrite_search_query",
    "translate_text_to_english",
    "warm_ai_runtime",
]
