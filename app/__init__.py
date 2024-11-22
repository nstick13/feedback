from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import get_config
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # Redirect to login page if not authenticated

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200 per day", "50 per hour"]
)

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # Initialize extensions with the app
    db.init_app(app)  # Initialize SQLAlchemy with the Flask app
    migrate.init_app(app, db)  # Set up Flask-Migrate for database migrations
    login_manager.init_app(app)  # Initialize Flask-Login for authentication
    limiter.init_app(app)  # Initialize Flask-Limiter

    # Add the user loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User  # Import the User model
        return User.query.get(int(user_id))  # Load user by ID

    # Force HTTPS and handle www/non-www redirects
    @app.before_request
    def before_request():
        # Only enforce HTTPS in production
        if os.environ.get('FLASK_ENV') == 'production':
            # If not HTTPS, redirect to HTTPS
            if not request.is_secure:
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

            # Redirect www to non-www
            if request.host.startswith('www.'):
                url = request.url.replace('www.', '', 1)
                return redirect(url, code=301)

    # Import and register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app