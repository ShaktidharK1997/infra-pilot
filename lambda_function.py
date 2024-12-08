from typing import Dict, Optional
import json
import os
import logging
import boto3
import google.generativeai as genai
from datetime import datetime

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS and Gemini
dynamodb = boto3.resource('dynamodb')
conversations_table = dynamodb.Table(os.environ['CONVERSATIONS_TABLE'])

genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
model = genai.GenerativeModel('gemini-pro')
embedder = genai.GenerativeModel('embedding-001')

# Define intents with their required info
INTENTS = {
    'DEPLOY_EC2': {
        'description': 'Deploy Docker on EC2',
        'slots': {
            'instance_type': 'What EC2 instance type do you want to use?',
            'region': 'Which AWS region should the instance be deployed in?',
            'image_name': "What's the name of your Docker image?"
        }
    },
    'DEPLOY_K8S': {
        'description': 'Deploy Docker on Kubernetes',
        'slots': {
            'cluster_name': 'What should we name the Kubernetes cluster?',
            'node_count': 'How many worker nodes do you need?',
            'node_type': 'What instance type for the worker nodes?'
        }
    }
    # Add other intents here
}

def get_conversation_state(conversation_id: str) -> Dict:
    """Get conversation state from DynamoDB"""
    try:
        response = conversations_table.get_item(Key={'id': conversation_id})
        return response.get('Item', {'id': conversation_id, 'state': 'START', 'slots': {}})
    except Exception as e:
        logger.error(f"Failed to get conversation state: {e}")
        return {'id': conversation_id, 'state': 'START', 'slots': {}}

def save_conversation_state(state: Dict):
    """Save conversation state to DynamoDB"""
    try:
        state['updated_at'] = datetime.utcnow().isoformat()
        conversations_table.put_item(Item=state)
    except Exception as e:
        logger.error(f"Failed to save conversation state: {e}")

def detect_intent(text: str) -> Optional[str]:
    """Detect intent using Gemini embeddings"""
    try:
        # Get embedding for user input
        user_embedding = embedder.embed_content(text)
        
        # Get embeddings for intent descriptions
        best_match = None
        highest_score = 0
        
        for intent_id, intent_info in INTENTS.items():
            intent_embedding = embedder.embed_content(intent_info['description'])
            score = user_embedding.similarity(intent_embedding)
            
            if score > highest_score and score > 0.7:  # Confidence threshold
                highest_score = score
                best_match = intent_id
        
        return best_match
    except Exception as e:
        logger.error(f"Intent detection failed: {e}")
        return None

def generate_response(state: Dict, user_input: str) -> Dict:
    """Generate appropriate response based on conversation state"""
    try:
        current_state = state.get('state', 'START')
        current_intent = state.get('current_intent')
        slots = state.get('slots', {})

        if current_state == 'START':
            # Detect intent for new conversation
            intent = detect_intent(user_input)
            if not intent:
                return {
                    'message': "I'm not sure what you'd like to do. Could you please be more specific?",
                    'state': state
                }
            
            # Update state with new intent
            state['current_intent'] = intent
            state['state'] = 'COLLECTING_SLOTS'
            state['slots'] = {}
            
            # Ask for first slot
            first_slot = next(iter(INTENTS[intent]['slots']))
            return {
                'message': INTENTS[intent]['slots'][first_slot],
                'state': state
            }

        elif current_state == 'COLLECTING_SLOTS':
            # Store the answer to the previous slot
            pending_slots = [s for s in INTENTS[current_intent]['slots'] if s not in slots]
            if pending_slots:
                slots[pending_slots[0]] = user_input
                state['slots'] = slots
                
                # Check if we need more slots
                pending_slots = [s for s in INTENTS[current_intent]['slots'] if s not in slots]
                if pending_slots:
                    next_slot = pending_slots[0]
                    return {
                        'message': INTENTS[current_intent]['slots'][next_slot],
                        'state': state
                    }
                
            # All slots collected, generate response
            state['state'] = 'COMPLETE'
            
            # Use Gemini to generate infrastructure code
            prompt = f"""Generate infrastructure code for:
            Intent: {current_intent}
            Configuration:
            {json.dumps(slots, indent=2)}
            
            Return only the infrastructure code without any explanation."""
            
            response = model.generate_content(prompt)
            
            return {
                'message': "Here's your infrastructure code:\n\n" + response.text,
                'state': state
            }

    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return {
            'message': "I encountered an error. Please try again.",
            'state': state
        }

def lambda_handler(event, context):
    """AWS Lambda handler"""
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        message = body.get('message')
        conversation_id = body.get('conversation_id')

        if not message:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'No message provided'
                })
            }

        # Get conversation state
        state = get_conversation_state(conversation_id)
        
        # Generate response
        response = generate_response(state, message)
        
        # Save updated state
        save_conversation_state(response['state'])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': response['message'],
                'conversation_id': response['state']['id']
            })
        }

    except Exception as e:
        logger.error(f"Lambda handler failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }