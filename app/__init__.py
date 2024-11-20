from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # Redirect to login page if not authenticated

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with the app
    db.init_app(app)  # Initialize SQLAlchemy with the Flask app
    migrate.init_app(app, db)  # Set up Flask-Migrate for database migrations
    login_manager.init_app(app)  # Initialize Flask-Login for authentication

    # Add the user loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User  # Import the User model
        return User.query.get(int(user_id))  # Load user by ID

    # Import and register blueprints
    from .routes import main
    app.register_blueprint(main)

    return app