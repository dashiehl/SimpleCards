from pathlib import Path

APP_NAME = "SimpleCards"

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "flashcards.db"
IMPORTS_DIR = ROOT_DIR / "imports"
SCHEMA_PATH = Path(__file__).resolve().parent / "db" / "schema.sql"

DATA_DIR.mkdir(exist_ok=True)
IMPORTS_DIR.mkdir(exist_ok=True)
