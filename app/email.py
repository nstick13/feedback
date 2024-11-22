import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, Personalization
from flask import current_app, url_for
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_email(to_email, dynamic_data, template_id=None):
    try:
        logger.info(f"Attempting to send email to {to_email}")
        if not os.getenv('SENDGRID_API_KEY'):
            logger.error("SENDGRID_API_KEY not found in environment variables")
            return False, "SendGrid API key not configured"
            
        logger.info("Initializing SendGrid client")
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        
        logger.info("Creating mail message")
        message = Mail(
            from_email=Email('info@wdtt.io'),
            to_emails=None,
        )
        
        # Set the template ID (either verification or feedback request)
        template_id = template_id or os.getenv('SENDGRID_FEEDBACK_REQUEST_TEMPLATE')
        if not template_id:
            logger.error("No template ID provided or found in environment variables")
            return False, "Email template ID not configured"
            
        logger.info(f"Using template ID: {template_id}")
        message.template_id = template_id

        # Add personalization and dynamic data
        logger.info(f"Adding personalization with dynamic data: {dynamic_data}")
        personalization = Personalization()
        personalization.add_to(Email(to_email))
        personalization.dynamic_template_data = dynamic_data
        message.add_personalization(personalization)

        # Send the email
        logger.info("Attempting to send email via SendGrid")
        response = sg.send(message)
        logger.info(f"Email sent successfully. Status code: {response.status_code}")
        return True, f"Email sent successfully. Status: {response.status_code}"
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}", exc_info=True)
        return False, f"Error sending email: {str(e)}"

def send_verification_email(user):
    verification_url = url_for(
        'main.verify_email',
        token=user.email_verification_token,
        _external=True
    )
    
    dynamic_data = {
        'user_name': user.username,
        'verification_url': verification_url
    }
    
    return send_email(
        to_email=user.email,
        dynamic_data=dynamic_data,
        template_id='d-e6677eb93c244016aac02a1eeb18927c'
    )

def send_feedback_request_email(recipient_email, requestor_name, feedback_prompt, unique_link, personal_message=''):
    # Create the feedback URL with the unique token
    feedback_url = url_for('main.give_feedback', token=unique_link, _external=True)
    
    # Prepare dynamic template data matching SendGrid template
    dynamic_data = {
        'requestor_name': requestor_name,
        'feedback_link': feedback_url,  # Changed from feedback_url to feedback_link to match template
        'personal_message': personal_message if personal_message else None
    }
    
    return send_email(
        to_email=recipient_email,
        dynamic_data=dynamic_data,
        template_id=os.getenv('SENDGRID_FEEDBACK_REQUEST_TEMPLATE')
    )