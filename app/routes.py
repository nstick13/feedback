from flask import Blueprint, render_template, redirect, url_for
from .email import send_email, send_verification_email
from app.models import FeedbackRequest, User, db
from flask import jsonify
from flask_login import login_user, login_required, current_user, logout_user
from flask import request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
import traceback

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html')

@main.route('/auth', methods=['GET'])
def auth():
    return render_template('auth.html')

@main.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    print(f"Login attempt - Username: {username}")
    
    user = User.query.filter_by(username=username).first()
    print(f"User found: {user is not None}")
    
    if user:
        if not user.email_verified:
            return jsonify({
                'success': False,
                'message': 'Please verify your email before logging in. Check your inbox for the verification link.'
            })
            
        password_check = user.check_password(password)
        print(f"Password check result: {password_check}")
        if password_check:
            login_user(user)
            return jsonify({'success': True, 'redirect': url_for('main.dashboard')})
    
    return jsonify({'success': False, 'message': 'Invalid username or password'})

@main.route('/signup', methods=['POST'])
def signup():
    data = request.form
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Username already exists'})
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'message': 'Email already exists'})
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name']
    )
    user.set_password(data['password'])
    
    # Generate and send verification email
    token = user.generate_verification_token()
    
    try:
        db.session.add(user)
        db.session.commit()
        send_verification_email(user.email, token)
        return jsonify({'success': True, 'message': 'Account created successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})

@main.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    
    if not user:
        return render_template('auth.html', error="Invalid verification link.")
    
    if user.verification_token_expired:
        # Generate new token and send new verification email
        user.generate_verification_token()
        db.session.commit()
        send_verification_email(user)
        return render_template('auth.html', 
            error="Verification link expired. A new verification email has been sent.")
    
    user.verify_email()
    db.session.commit()
    
    return render_template('auth.html', 
        success="Email verified successfully! You can now log in.")

@main.route('/resend-verification')
@login_required
def resend_verification():
    if current_user.email_verified:
        return jsonify({'success': False, 'message': 'Email already verified'})
    
    current_user.generate_verification_token()
    db.session.commit()
    
    success, message = send_verification_email(current_user)
    if success:
        return jsonify({
            'success': True,
            'message': 'Verification email sent! Please check your inbox.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Error sending verification email. Please try again later.'
        })

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@main.route('/submit-feedback-request', methods=['POST'])
def submit_feedback_request():
    from flask import request, jsonify
    from app.models import FeedbackRequest, db
    from datetime import datetime, timedelta
    from .email import send_email

    # Parse JSON data from the frontend
    data = request.get_json()
    # Debugging: Log the received data
    print("Received Data:", data)
    recipient_name = data.get('recipient')
    recipient_email = data.get('email')
    # Debugging: Log specific fields
    print("Recipient Name:", recipient_name)
    print("Recipient Email:", recipient_email)

    # Check if recipient_email is provided
    if not recipient_email:
        return jsonify({"error": "Recipient email is required"}), 400

    # Dynamic data for the email
    dynamic_data = {
        'requestor_name': 'Nathan',  # Replace with logged-in user later
        'feedback_link': 'https://example.com/feedback/123',  # Replace with a real link later
    }

    # Create a new feedback request
    feedback_request = FeedbackRequest(
        requestor_id=1,  # Replace with actual user ID when authentication is implemented
        request_recipient=recipient_name,
        recipient_email=recipient_email,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30),  # Default expiration in 30 days
        unique_link=f"https://your-app.com/feedback/willreplacelater",  # Replace with actual link generation logic
    )

    # Save the request to the database
    try:
        db.session.add(feedback_request)
        db.session.commit()
        email_status = send_email(recipient_email, dynamic_data)
        if "Status: 202" in email_status:
            return jsonify({"status": "success", "message": "Feedback request sent successfully!"}), 201
        else:
            print("Unexpected Email Status Response:", email_status)  # Debugging log
        return jsonify({"status": "error", "message": f"Email failed with response: {email_status}"}), 400
    except Exception as e:
        print("Error in submit-feedback-request:", str(e))  # Log error details
        db.session.rollback()
        return jsonify({"status": "error", "message": "Database or server error occurred."}), 500

@main.route('/dashboard')
@login_required
def dashboard():
    from app.models import FeedbackRequest
    # Fetch pending and completed feedback requests for the logged-in user
    pending_requests = FeedbackRequest.query.filter_by(status="pending").all()
    completed_requests = FeedbackRequest.query.filter_by(status="complete").all()

    return render_template(
        'dashboard.html',
        pending_requests=pending_requests,
        completed_requests=completed_requests
    )

@main.route('/feedback/<int:request_id>', methods=['GET'])
def view_feedback(request_id):
    # Query the database for the feedback request
    feedback_request = FeedbackRequest.query.get_or_404(request_id)
    
    # Prepare the data to be returned as JSON
    feedback_data = {
        "id": feedback_request.id,
        "recipient": feedback_request.request_recipient,
        "date": feedback_request.created_at.strftime('%Y-%m-%d'),
        "status": feedback_request.status
    }

    # Return the data as JSON
    return jsonify(feedback_data)

@main.route('/request-feedback')
def request_feedback():
    return render_template('request_feedback.html')

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            current_user.first_name = request.form.get('first_name')
            current_user.last_name = request.form.get('last_name')
            current_user.company = request.form.get('company')
            current_user.role = request.form.get('role')
            
            # Handle password change if requested
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            if current_password and new_password:
                if not current_user.check_password(current_password):
                    return jsonify({'success': False, 'message': 'Current password is incorrect'})
                current_user.set_password(new_password)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Profile updated successfully'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'An error occurred while updating your profile'})
    
    return render_template('profile.html')