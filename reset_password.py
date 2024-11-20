from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='nstick13').first()
    if user:
        user.password_hash = generate_password_hash('Chinook1!')
        db.session.commit()
        print("Password successfully reset for nstick13")
    else:
        print("User nstick13 not found")
