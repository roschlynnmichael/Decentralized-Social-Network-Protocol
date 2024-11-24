import logging
from app import app, socketio, db, create_database_if_not_exists

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

        # Update SocketIO CORS settings
        socketio.init_app(app, cors_allowed_origins="*")

        logger.info("Starting SocketIO server...")
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=5000, 
                    debug=True)
        
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=True)
        raise
