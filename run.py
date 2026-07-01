import os
from routes import create_app
from database import db

# Instantiate the Flask application via the factory method
app = create_app()

if __name__ == '__main__':
    # Initialize the database tables within the app context if they don't already exist
    with app.app_context():
        print("Initializing database tables...")
        try:
            db.create_all()
            print("Database tables initialized successfully.")
        except Exception as e:
            print(f"Error initializing database: {e}")
            print("Verify your connection string in config.py or the .env file.")

    # Retrieve port and host from environment, or default to localhost:5000
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"Starting RxVerify Flask server on http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)
