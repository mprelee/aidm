import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from aidm.app import app  # Changed back to direct import

if __name__ == '__main__':
    app.run(debug=True)  # Changed back to direct app.run 