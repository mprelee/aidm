import logging
from aidm.app import app

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    logger.info("Starting application...")
    application = app
except Exception as e:
    logger.error(f"Failed to start application: {str(e)}", exc_info=True)
    raise

# Keep it simple like their example
if __name__ == "__main__":
    app.run() 