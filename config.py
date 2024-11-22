import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    
    # Handle Heroku postgres://... vs postgresql://... URL formats
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url or 'postgresql://postgres:@localhost/feedback_app'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost/feedback_app_test'
    # Disable email sending during tests
    SENDGRID_API_KEY = None
    
def get_config(config_name):
    configs = {
        'development': Config,
        'testing': TestConfig,
        'production': Config
    }
    return configs.get(config_name, Config)