import logging
import os
from aidm.app import app

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    logger.info("Starting application...")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Directory contents: {os.listdir()}")
    
    # Make sure templates are found
    logger.info(f"Template directory: {os.path.join(os.getcwd(), 'aidm', 'templates')}")
    logger.info(f"Template exists: {os.path.exists(os.path.join(os.getcwd(), 'aidm', 'templates', 'index.html'))}")
    
    application = app
    logger.info("Application initialized successfully")
except Exception as e:
    logger.error(f"Failed to start application: {str(e)}", exc_info=True)
    raise

# Export the application
app = application

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 