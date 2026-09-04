import sys
from pathlib import Path

# Add project root to sys.path so `app` package can be imported
sys.path.insert(0, str(Path(__file__).parent))

from app.api.main import app
