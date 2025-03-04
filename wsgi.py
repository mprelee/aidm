import os
import sys
from pathlib import Path

# Add the project root to the Python path
root_path = Path(__file__).parent
sys.path.append(str(root_path))

from aidm.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 