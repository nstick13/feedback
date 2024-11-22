from flask import Blueprint, render_template, redirect, url_for
from .email import send_email, send_verification_email, send_feedback_request_email
from app.models import FeedbackRequest, User, db, FeedbackTemplate
from flask import jsonify
from flask_login import login_user, login_required, current_user, logout_user
from flask import request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
import traceback
from .ai_services import init_feedback_coach
from . import limiter
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length, Optional, EqualTo
from datetime import datetime, timedelta
import secrets
import os
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html')

@main.route('/auth', methods=['GET'])
def auth():
    return render_template('auth.html')

@main.route('/login', methods=['GET'])
def login_page():
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
        send_verification_email(user)
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
@login_required
def submit_feedback_request():
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        recipient_email = data.get('recipient_email')
        personal_message = data.get('personal_message')

        # Get the existing feedback request
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        
        # Verify ownership
        if feedback_request.requestor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        # Update the feedback request
        feedback_request.recipient_email = recipient_email
        feedback_request.status = 'pending'
        feedback_request.expires_at = datetime.utcnow() + timedelta(days=30)
        feedback_request.unique_link = f"https://wdtt.io/feedback/{feedback_request.id}"  # You'll need to update this with your actual domain

        # Send email
        dynamic_data = {
            'requestor_name': current_user.full_name,
            'feedback_link': feedback_request.unique_link,
            'personal_message': personal_message if personal_message else ''
        }

        db.session.commit()
        
        email_status = send_email(recipient_email, dynamic_data)
        if "Status: 202" in email_status:
            return jsonify({
                'success': True,
                'message': 'Feedback request sent successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to send email: {email_status}'
            }), 500

    except Exception as e:
        print(f"Error in submit_feedback_request: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request'
        }), 500

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
@login_required
def request_feedback():
    return render_template('request_feedback.html')

@main.route('/feedback-conversation')
@login_required
def feedback_conversation():
    return render_template('feedback_conversation.html')

@main.route('/api/start-feedback-conversation', methods=['POST'])
@login_required
@limiter.limit("10 per hour")
def start_feedback_conversation():
    try:
        coach = init_feedback_coach()
        thread_id = coach.create_thread()
        
        # Store thread_id in session for later use
        feedback_request = FeedbackRequest(
            requestor_id=current_user.id,
            request_recipient='',  # Will be filled later
            recipient_email='',    # Will be filled later
            status='draft',
            session_data=thread_id
        )
        db.session.add(feedback_request)
        db.session.commit()
        
        # Get initial response from assistant
        response_data = coach.get_assistant_response(thread_id)
        logger.info(f"Initial assistant response: {response_data}")
        
        return jsonify({
            'success': True,
            'message': response_data['message'],
            'request_id': feedback_request.id
        })
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to start conversation'
        }), 500

@main.route('/api/send-message', methods=['POST'])
@login_required
@limiter.limit("30 per hour")
def send_message():
    try:
        data = request.json
        request_id = data.get('request_id')
        message = data.get('message')
        
        # Log incoming request
        logger.info(f"Received message request - ID: {request_id}, Message: {message}")
        
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        if feedback_request.requestor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        thread_id = feedback_request.session_data
        coach = init_feedback_coach()
        
        # Send message and get response
        coach.add_message(thread_id, message)
        response_data = coach.get_assistant_response(thread_id)
        
        # Only check readiness if the initial response wasn't already complete
        if not response_data['conversation_complete']:
            readiness_data = coach.check_conversation_readiness(thread_id)
            if readiness_data['conversation_complete']:
                response_data = readiness_data
        
        # Log response data
        logger.info(f"Response data being sent to frontend: {response_data}")
        
        return jsonify({
            'success': True,
            'message': response_data['message'],
            'conversation_complete': response_data['conversation_complete']
        })
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to send message'
        }), 500

@main.route('/api/finish-conversation', methods=['POST'])
@login_required
@limiter.limit("10 per hour")
def finish_conversation():
    try:
        data = request.json
        request_id = data.get('request_id')
        
        # Log request data
        logger.info(f"Finishing conversation for request ID: {request_id}")
        
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        if feedback_request.requestor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        thread_id = feedback_request.session_data
        coach = init_feedback_coach()
        
        # Get final summary from AI
        response_data = coach.get_assistant_response(thread_id)
        
        # Store only the message part as the feedback prompt
        feedback_request.feedback_prompt = response_data['message']
        db.session.commit()
        
        # Return success with summary
        return jsonify({
            'success': True,
            'summary': response_data['message']
        })
        
    except Exception as e:
        logger.error(f"Error finishing conversation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to finish conversation'
        }), 500

@main.route('/api/submit-feedback-request', methods=['POST'])
@login_required
def submit_ai_feedback_request():
    try:
        data = request.json
        request_id = data.get('request_id')
        recipients = data.get('recipients', [])
        personal_message = data.get('personal_message', '')
        
        if not recipients:
            return jsonify({'success': False, 'message': 'No recipients provided'})
            
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        if feedback_request.requestor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
            
        # Create a new feedback request for each recipient
        success_count = 0
        error_messages = []
        
        for recipient_email in recipients:
            try:
                # Create unique link
                unique_link = secrets.token_urlsafe(32)
                
                # Create new request
                new_request = FeedbackRequest(
                    requestor_id=current_user.id,
                    request_recipient="Recipient",  # This could be updated if we collect names
                    recipient_email=recipient_email,
                    feedback_prompt=feedback_request.feedback_prompt,
                    status="pending",
                    expires_at=datetime.utcnow() + timedelta(days=7),
                    unique_link=unique_link,
                    personal_message=personal_message
                )
                db.session.add(new_request)
                db.session.flush()  # Get the ID without committing
                
                # Send email
                if os.getenv('SENDGRID_API_KEY') and os.getenv('SENDGRID_FEEDBACK_REQUEST_TEMPLATE'):
                    success, message = send_feedback_request_email(
                        recipient_email=recipient_email,
                        requestor_name=current_user.full_name,
                        feedback_prompt=feedback_request.feedback_prompt,
                        unique_link=unique_link,
                        personal_message=personal_message
                    )
                    if success:
                        success_count += 1
                    else:
                        error_messages.append(f"Failed to send email to {recipient_email}: {message}")
                        
            except Exception as e:
                error_messages.append(f"Error processing {recipient_email}: {str(e)}")
                continue
        
        # Commit all successful requests
        db.session.commit()
        
        # Return response with status
        if success_count == len(recipients):
            return jsonify({
                'success': True,
                'message': f"Successfully sent {success_count} feedback requests"
            })
        elif success_count > 0:
            return jsonify({
                'success': True,
                'message': f"Sent {success_count} out of {len(recipients)} requests. Errors: {'; '.join(error_messages)}"
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Failed to send any requests. Errors: {'; '.join(error_messages)}"
            })
            
    except Exception as e:
        logger.error(f"Error submitting feedback request: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to submit feedback request'
        }), 500

@main.route('/api/save-feedback-template', methods=['POST'])
@login_required
def save_feedback_template():
    try:
        data = request.json
        request_id = data.get('request_id')
        
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        if feedback_request.requestor_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
            
        # Save as template (you might want to create a separate Template model)
        template = FeedbackTemplate(
            user_id=current_user.id,
            prompt=feedback_request.feedback_prompt,
            created_at=datetime.utcnow()
        )
        db.session.add(template)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving template: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to save template'
        }), 500

@main.route('/give-feedback/<token>')
def give_feedback(token):
    """Handle the feedback giving process"""
    try:
        # Find the feedback request by unique_link
        feedback_request = FeedbackRequest.query.filter_by(unique_link=token).first_or_404()
        
        # Check if request is expired
        if feedback_request.expires_at and feedback_request.expires_at < datetime.utcnow():
            return render_template('error.html', message="This feedback request has expired.")
        
        # Check if feedback is already submitted
        if feedback_request.status == 'completed':
            return render_template('error.html', message="This feedback has already been submitted.")
            
        # Initialize feedback conversation with the prompt
        coach = init_feedback_coach()
        thread_id = coach.create_thread()
        
        # Add initial context message
        requestor = User.query.get(feedback_request.requestor_id)
        initial_prompt = (
            f"You are helping provide feedback to {requestor.full_name}. "
            f"Here is their feedback request:\n\n"
            f"{feedback_request.feedback_prompt}\n\n"
            "Please guide me through providing thoughtful, specific feedback. "
            "Ask me questions to gather detailed examples and context that will make the feedback more valuable. "
            "Focus on being constructive and actionable. "
            "When you feel we have gathered enough detailed feedback, summarize it and end with '**Complete: True**'."
        )
        coach.add_message(thread_id, initial_prompt)
        
        # Store thread_id in session
        feedback_request.feedback_thread_id = thread_id
        db.session.commit()
        
        # Get initial AI response
        response = coach.get_assistant_response(thread_id)
        
        # Prepare context for the feedback conversation
        context = {
            'request_id': feedback_request.id,
            'requestor_name': requestor.full_name,
            'feedback_prompt': feedback_request.feedback_prompt,
            'initial_message': response['message']
        }
        
        return render_template('feedback_conversation.html', context=context)
        
    except Exception as e:
        logger.error(f"Error handling feedback request: {str(e)}")
        return render_template('error.html', message="An error occurred processing this feedback request.")

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    from flask_wtf import FlaskForm
    from wtforms import StringField, PasswordField
    from wtforms.validators import DataRequired, Length, Optional, EqualTo
    
    class ProfileForm(FlaskForm):
        first_name = StringField('First Name', validators=[DataRequired()])
        last_name = StringField('Last Name', validators=[DataRequired()])
        company = StringField('Company', validators=[Optional()])
        role = StringField('Role', validators=[Optional()])
        current_password = PasswordField('Current Password', validators=[Optional()])
        new_password = PasswordField('New Password', validators=[
            Optional(),
            Length(min=8, message='New password must be at least 8 characters long')
        ])
        confirm_password = PasswordField('Confirm Password', validators=[
            Optional(),
            EqualTo('new_password', message='Passwords must match')
        ])
    
    form = ProfileForm()
    
    if request.method == 'POST':
        if not form.validate_on_submit():
            errors = []
            for field, field_errors in form.errors.items():
                errors.extend(field_errors)
            return jsonify({'success': False, 'message': ' '.join(errors)})
            
        try:
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.company = form.company.data
            current_user.role = form.role.data
            current_user.updated_at = datetime.utcnow()
            
            # Handle password change if requested
            if form.new_password.data:
                if not current_user.check_password(form.current_password.data):
                    return jsonify({'success': False, 'message': 'Current password is incorrect'})
                current_user.set_password(form.new_password.data)
            
            db.session.commit()
            return jsonify({'success': True, 'message': 'Profile updated successfully'})
            
        except Exception as e:
            print(f"Error updating profile: {str(e)}")
            db.session.rollback()
            return jsonify({'success': False, 'message': 'An error occurred while updating your profile'})
    
    return render_template('profile.html', form=form)