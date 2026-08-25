import os
import logging

class Config:
    # Secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # ============================================
    # DATABASE CONFIGURATION - FIXED
    # ============================================
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    # Debug: Print what we're getting (will show in Render logs)
    print(f"🔍 DATABASE_URL from env: {database_url}")
    
    # Fix for Render's postgres:// vs SQLAlchemy's postgresql://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        print(f"✅ Fixed postgres:// to postgresql://")
    
    # Fallback to SQLite for local development
    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
        print(f"✅ Using PostgreSQL: {database_url[:20]}...")  # Only show first 20 chars
    else:
        # Use absolute path for SQLite fallback
        instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(instance_path, "app.db")}'
        print(f"⚠️ Using SQLite fallback: {SQLALCHEMY_DATABASE_URI}")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    
    # Gemini API settings
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'your-gemini-api-key-here'
    GEMINI_MODEL = 'gemini-1.5-flash'
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
