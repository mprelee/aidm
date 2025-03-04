import sys
from pathlib import Path
import os
sys.path.append(str(Path(__file__).parent))

from aidm.app import app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 