from app import app, socketio, db, create_database_if_not_exists
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        logger.info("Starting application initialization...")
        
        # Initialize database within app context
        with app.app_context():
            logger.info("Initializing database...")
            create_database_if_not_exists(app)
            db.create_all()
            logger.info("Database initialization completed")

        logger.info("Starting SocketIO server...")
        # Simplified run configuration
        socketio.run(app, 
                    host='0.0.0.0',  # Changed from 0.0.0.0 to localhost
                    port=5000,
                    allow_unsafe_werkzeug=True)  # Added this parameter
        
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=True)
        raise