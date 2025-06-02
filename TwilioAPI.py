from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from dotenv import load_dotenv
import os

# Load environment variables once at module level
load_dotenv()
TWILIO_CLIENT = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
MESSAGING_SID = os.getenv('TWILIO_MESSAGING_SERVICE_SID')

def send_message(recipient: str, message: str):
    try:
        msg = TWILIO_CLIENT.messages.create(
            messaging_service_sid=MESSAGING_SID,
            body=message,
            to=recipient
        )
        return msg.sid
    except TwilioRestException as e:
        raise Exception(f"Failed to send message: {str(e)}")

if __name__ == "__main__":
    try:
        sid = send_message('+19052263054', 'message')
        print(f"Message sent with SID: {sid}")
    except Exception as e:
        print(f"Error: {str(e)}") 