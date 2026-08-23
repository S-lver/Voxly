import os

class Config:
    # Secret key for sessions and security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    
    # Render uses 'postgres://', but SQLAlchemy needs 'postgresql://'
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Use PostgreSQL in production, SQLite for local development
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///instance/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Ensure upload directory exists
    @staticmethod
    def init_directories():
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        if not Config.SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
            # For SQLite, ensure instance directory exists
            instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
            os.makedirs(instance_dir, exist_ok=True)
