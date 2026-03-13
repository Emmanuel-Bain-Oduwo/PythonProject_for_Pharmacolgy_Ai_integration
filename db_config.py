"""
db_config.py — Central database path.
Change DB_PATH here and it propagates to every module.
"""
from pathlib import Path

# ✅ SQLite file lives next to your Python files
DB_PATH = str(Path(__file__).parent / "identifier.sqlite")
