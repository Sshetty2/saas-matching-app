import os
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
VECTOR_STORE_PATH = os.path.join(PROJECT_ROOT, "vector_store.pkl")


def get_vector_store_path(prefix: Optional[str] = None):
    if prefix:
        return os.path.join(PROJECT_ROOT, f"{prefix}_vector_store.pkl")
    return VECTOR_STORE_PATH
