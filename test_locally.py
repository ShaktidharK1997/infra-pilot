import os
import json
from lambda_function import lambda_handler
from unittest.mock import MagicMock
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mock DynamoDB for local testing
class MockDynamoDB:
    def __init__(self):
        self.conversations = {}

    def get_item(self, Key):
        conversation_id = Key['id']
        if conversation_id in self.conversations:
            return {'Item': self.conversations[conversation_id]}
        return {}

    def put_item(self, Item):
        self.conversations[Item['id']] = Item

# Setup mock DynamoDB
mock_dynamodb = MockDynamoDB()
boto3.resource = MagicMock(return_value=MagicMock(
    Table=MagicMock(return_value=MagicMock(
        get_item=mock_dynamodb.get_item,
        put_item=mock_dynamodb.put_item
    ))
))

def simulate_request(message, conversation_id=None):
    """Simulate an API Gateway request to the Lambda function"""
    event = {
        'body': json.dumps({
            'message': message,
            'conversation_id': conversation_id
        })
    }
    
    # Call Lambda handler
    response = lambda_handler(event, None)
    
    # Print response
    print("\nRequest:")
    print(f"Message: {message}")
    print(f"Conversation ID: {conversation_id}")
    print("\nResponse:")
    print(json.dumps(json.loads(response['body']), indent=2))
    
    # Return conversation ID for next request
    return json.loads(response['body']).get('conversation_id')

def main():
    try:
        # Check for required environment variables
        required_env_vars = ['GOOGLE_API_KEY', 'CONVERSATIONS_TABLE']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            print("Please create a .env file with the required variables.")
            return

        print("=== InfraPilot Local Testing ===")
        print("Type 'exit' to quit")
        print()

        conversation_id = None
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() == 'exit':
                break
                
            if user_input:
                conversation_id = simulate_request(user_input, conversation_id)
            
    except KeyboardInterrupt:
        print("\nTesting session ended by user")
    except Exception as e:
        print(f"\nError during testing: {str(e)}")

if __name__ == "__main__":
    main()