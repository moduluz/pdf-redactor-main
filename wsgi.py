import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - waitress - %(levelname)s - %(message)s'
)
logger = logging.getLogger('waitress')

# Set environment variable for production secret key if not already set
if 'SECRET_KEY' not in os.environ:
    os.environ['SECRET_KEY'] = os.urandom(24).hex()
    logger.info("Generated new SECRET_KEY for session security")

# Import the flask app
from flask.app import app

if __name__ == '__main__':
    from waitress import serve
    
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting production server on http://{host}:{port}")
    serve(app, host=host, port=port, threads=4)
