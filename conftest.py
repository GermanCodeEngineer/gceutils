import sys
from pathlib import Path

# Add src directory to Python path for tests
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
