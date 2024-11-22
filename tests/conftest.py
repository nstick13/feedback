import os
import pytest
from app import create_app, db
from app.models import User, FeedbackRequest
from flask_login import login_user

@pytest.fixture
def app():
    app = create_app('testing')
    
    # Create test database and tables
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            email='test@example.com',
            username='testuser',  
            first_name='Test',
            last_name='User'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def auth_client(client, test_user, app):
    with client:
        with client.session_transaction() as sess:
            # Log in the user
            with app.test_request_context():
                login_user(test_user)
                # Get the user id from the session
                if '_user_id' in sess:
                    sess['_user_id'] = test_user.id
    return client

@pytest.fixture
def test_feedback_request(app, test_user):
    with app.app_context():
        feedback_request = FeedbackRequest(
            requestor_id=test_user.id,
            feedback_prompt="Test feedback prompt",
            status="draft"
        )
        db.session.add(feedback_request)
        db.session.commit()
        return feedback_request