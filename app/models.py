from app import db
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from flask import current_app

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True)
    email_verification_sent_at = db.Column(db.DateTime)
    
    # New profile fields
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    company = db.Column(db.String(100))
    role = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = datetime.utcnow()
        return self.email_verification_token

    def verify_email(self):
        self.email_verified = True
        self.email_verification_token = None
        self.email_verification_sent_at = None

    @property
    def verification_token_expired(self):
        if self.email_verification_sent_at:
            expiration_time = self.email_verification_sent_at + timedelta(hours=24)
            return datetime.utcnow() > expiration_time
        return True

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

class FeedbackRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requestor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_recipient = db.Column(db.String(80), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    unique_link = db.Column(db.String(200), nullable=True)
    session_data = db.Column(db.Text, nullable=True)  # For OpenAI session insights
    feedback_prompt = db.Column(db.Text, nullable=True)  # Summary of AI-generated prompt

    def __repr__(self):
        return f'<FeedbackRequest {self.request_recipient}>'