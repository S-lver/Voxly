import os

class Config:
    # Secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # FIXED: Database configuration (this replaces your old SQLite URI)
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///instance/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ============================================
    # YOUR ORIGINAL CONFIG SETTINGS GO HERE
    # ============================================
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    
    # Gemini API settings
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'your-gemini-api-key-here'
    GEMINI_MODEL = 'gemini-1.5-flash'  # or whatever model you use
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Any other config settings you had
    # ... 
    # ... keep ALL your original settings here
    # ...
