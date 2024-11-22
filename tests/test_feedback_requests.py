import json
import pytest
from app.models import FeedbackRequest
from app import db

def test_submit_feedback_request_success(auth_client, test_feedback_request):
    """Test successful submission of a feedback request"""
    data = {
        'request_id': test_feedback_request.id,
        'recipients': ['recipient1@example.com', 'recipient2@example.com'],
        'personal_message': 'Please provide feedback'
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['success'] is True
    assert 'Successfully sent' in response_data['message']
    
    # Check database
    requests = FeedbackRequest.query.filter_by(
        requestor_id=test_feedback_request.requestor_id
    ).all()
    assert len(requests) == 3  # Original + 2 new requests
    
    # Check the new requests
    new_requests = [r for r in requests if r.id != test_feedback_request.id]
    for request in new_requests:
        assert request.status == 'pending'
        assert request.personal_message == 'Please provide feedback'
        assert request.feedback_prompt == test_feedback_request.feedback_prompt
        assert request.unique_link is not None

def test_submit_feedback_request_no_recipients(auth_client, test_feedback_request):
    """Test feedback request submission with no recipients"""
    data = {
        'request_id': test_feedback_request.id,
        'recipients': [],
        'personal_message': 'Please provide feedback'
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['success'] is False
    assert 'No recipients provided' in response_data['message']

def test_submit_feedback_request_unauthorized(client, test_feedback_request):
    """Test feedback request submission without authentication"""
    data = {
        'request_id': test_feedback_request.id,
        'recipients': ['recipient@example.com'],
        'personal_message': 'Please provide feedback'
    }
    
    response = client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 401  # Unauthorized

def test_submit_feedback_request_invalid_id(auth_client):
    """Test feedback request submission with invalid request ID"""
    data = {
        'request_id': 99999,  # Non-existent ID
        'recipients': ['recipient@example.com'],
        'personal_message': 'Please provide feedback'
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 404

def test_start_feedback_conversation(auth_client):
    """Test starting a new feedback conversation"""
    response = auth_client.post('/api/start-feedback-conversation')
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['success'] is True
    assert 'request_id' in response_data
    assert 'message' in response_data
    
    # Verify request was created in database
    request = FeedbackRequest.query.get(response_data['request_id'])
    assert request is not None
    assert request.status == 'draft'

def test_submit_feedback_request_invalid_email(auth_client, test_feedback_request):
    """Test feedback request submission with invalid email format"""
    data = {
        'request_id': test_feedback_request.id,
        'recipients': ['invalid-email', 'another.invalid@'],
        'personal_message': 'Please provide feedback'
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['success'] is False
    assert 'Invalid email format' in response_data['message']

def test_submit_feedback_request_too_many_recipients(auth_client, test_feedback_request):
    """Test feedback request submission with too many recipients"""
    # Create list of 51 valid email addresses
    recipients = [f'recipient{i}@example.com' for i in range(51)]
    data = {
        'request_id': test_feedback_request.id,
        'recipients': recipients,
        'personal_message': 'Please provide feedback'
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['success'] is False
    assert 'Too many recipients' in response_data['message']

def test_submit_feedback_request_long_message(auth_client, test_feedback_request):
    """Test feedback request submission with too long personal message"""
    data = {
        'request_id': test_feedback_request.id,
        'recipients': ['recipient@example.com'],
        'personal_message': 'a' * 1001  # Assuming 1000 char limit
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['success'] is False
    assert 'Personal message too long' in response_data['message']

def test_submit_feedback_request_duplicate_recipients(auth_client, test_feedback_request):
    """Test feedback request submission with duplicate recipients"""
    data = {
        'request_id': test_feedback_request.id,
        'recipients': ['same@example.com', 'same@example.com'],
        'personal_message': 'Please provide feedback'
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['success'] is True
    
    # Verify only one request was created for the duplicate email
    requests = FeedbackRequest.query.filter_by(
        requestor_id=test_feedback_request.requestor_id
    ).all()
    new_requests = [r for r in requests if r.id != test_feedback_request.id]
    assert len(new_requests) == 1

def test_submit_feedback_request_malformed_json(auth_client, test_feedback_request):
    """Test feedback request submission with malformed JSON"""
    response = auth_client.post(
        '/api/submit-feedback-request',
        data='{"bad_json":',
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['success'] is False
    assert 'Invalid request format' in response_data['message']

def test_submit_feedback_request_missing_fields(auth_client, test_feedback_request):
    """Test feedback request submission with missing required fields"""
    # Missing recipients
    data = {
        'request_id': test_feedback_request.id,
        'personal_message': 'Please provide feedback'
    }
    
    response = auth_client.post(
        '/api/submit-feedback-request',
        data=json.dumps(data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['success'] is False
    assert 'Missing required field' in response_data['message']
