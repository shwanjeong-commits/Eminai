from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
VENDOR_DIR = ROOT_DIR / "vendor"

if VENDOR_DIR.exists():
    vendor_path = str(VENDOR_DIR)
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)
