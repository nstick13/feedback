import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, Personalization
from flask import current_app, url_for

def send_email(to_email, dynamic_data, template_id=None):
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        message = Mail(
            from_email=Email('info@wdtt.io'),
            to_emails=None,
        )
        
        # Set the template ID (either verification or feedback request)
        message.template_id = template_id or os.getenv('SENDGRID_FEEDBACK_REQUEST_TEMPLATE')

        # Add personalization and dynamic data
        personalization = Personalization()
        personalization.add_to(Email(to_email))
        personalization.dynamic_template_data = dynamic_data
        message.add_personalization(personalization)

        # Send the email
        response = sg.send(message)
        return True, f"Email sent successfully. Status: {response.status_code}"
    except Exception as e:
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