import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VECTOR_STORE_PATH = os.path.join(PROJECT_ROOT, "vector_store.pkl")
