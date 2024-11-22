import os
from openai import OpenAI
from datetime import datetime
from flask import current_app
import time
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_on_error(max_retries=3, base_delay=1):
    """Decorator to retry functions on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    delay = base_delay * (2 ** (retries - 1))  # Exponential backoff
                    logger.warning(f"Attempt {retries} failed, retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class FeedbackCoach:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.assistant_id = os.getenv('OPENAI_FEEDBACKCOACH_ASSISTANT_ID')
        if not self.assistant_id:
            raise ValueError("OPENAI_FEEDBACKCOACH_ASSISTANT_ID environment variable is not set")

    @retry_on_error()
    def create_thread(self):
        """Create a new conversation thread"""
        try:
            thread = self.client.beta.threads.create()
            logger.info(f"Created new thread: {thread.id}")
            return thread.id
        except Exception as e:
            logger.error(f"Error creating thread: {str(e)}")
            raise

    @retry_on_error()
    def add_message(self, thread_id, message):
        """Add a user message to the thread"""
        try:
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            logger.info(f"Added message to thread {thread_id}")
        except Exception as e:
            logger.error(f"Error adding message to thread {thread_id}: {str(e)}")
            raise

    @retry_on_error()
    def check_conversation_readiness(self, thread_id):
        """Check if the conversation has enough information for a feedback request"""
        try:
            # Add a system message asking to evaluate conversation completeness
            self.add_message(
                thread_id,
                "SYSTEM: Please evaluate if we have gathered enough specific information about the feedback request. "
                "Consider: (1) The specific context or situation, (2) Clear focus areas for feedback, "
                "(3) Any relevant background or constraints. "
                "If we have enough information, end your response with '**Complete: True**'. "
                "If we need more information, ask a specific follow-up question."
            )
            
            return self.get_assistant_response(thread_id)
        except Exception as e:
            logger.error(f"Error checking conversation readiness: {str(e)}")
            raise

    @retry_on_error()
    def get_assistant_response(self, thread_id, timeout=60):
        """Run the assistant and get its response with timeout"""
        try:
            # Create and wait for the run to complete
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    logger.error(f"Assistant response timeout for thread {thread_id}")
                    raise TimeoutError("Assistant response timeout")

                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'failed':
                    logger.error(f"Assistant run failed for thread {thread_id}")
                    raise Exception("Assistant run failed")
                elif run_status.status == 'expired':
                    logger.error(f"Assistant run expired for thread {thread_id}")
                    raise Exception("Assistant run expired")
                
                time.sleep(1)  # Poll every second

            # Get the latest message
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            latest_message = messages.data[0]
            response = latest_message.content[0].text.value

            # Log the raw response
            logger.info(f"Raw assistant response: {response}")

            # Check if the response indicates conversation completion
            # Look for both "**Complete: True**" and ", Complete: True"
            conversation_complete = "**Complete: True**" in response or ", Complete: True" in response
            logger.info(f"Conversation complete: {conversation_complete}")
            
            if conversation_complete:
                # Remove all completion markers
                response = response.replace("**Complete: True**", "").replace(", Complete: True", "").replace(", Complete: False", "").strip()
                logger.info(f"Cleaned response: {response}")

            logger.info(f"Got response from assistant for thread {thread_id}")
            return {
                'message': response,
                'conversation_complete': conversation_complete
            }

        except Exception as e:
            logger.error(f"Error getting assistant response for thread {thread_id}: {str(e)}")
            raise

    @retry_on_error()
    def get_conversation_summary(self, thread_id):
        """Get a summary of the conversation for the feedback request"""
        try:
            # Add a system message asking for a summary
            self.add_message(
                thread_id,
                "SYSTEM: Please provide a clear, structured summary of the feedback request. "
                "Include key areas to focus on and any specific aspects mentioned. "
                "Format it in markdown with appropriate headers and bullet points."
            )
            
            # Get the summary response
            response_data = self.get_assistant_response(thread_id)
            return response_data['message']
            
        except Exception as e:
            logger.error(f"Error getting conversation summary: {str(e)}")
            raise

def init_feedback_coach():
    """Initialize the FeedbackCoach singleton"""
    if not hasattr(current_app, 'feedback_coach'):
        current_app.feedback_coach = FeedbackCoach()
    return current_app.feedback_coach
