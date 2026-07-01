import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

class Config:
    """Base Flask configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-flask-secret-key-change-in-prod')
    
    # Database Configuration
    # Defaults to SQLite if DATABASE_URL is not specified in the environment
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'rxverify.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default-jwt-secret-key-change-in-prod')
    
    # Upload Settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'Uploads')
    # Default maximum upload size: 16MB
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    
    # Tesseract Configuration
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Apply pytesseract configuration globally
import pytesseract
if os.path.exists(Config.TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

