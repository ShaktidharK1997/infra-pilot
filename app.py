# app.py
from flask import Flask, request, jsonify, render_template
from transformers import pipeline
import docker
import re
import json
from typing import Dict, List, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockerManager:
    def __init__(self):
        try:
            self.client =  docker.from_env()
            logger.info("Successfully connected to Docker daemon")
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {str(e)}")
            self.client = None

    def execute_command(self, action: str, params: Dict) -> Dict:
        """Execute Docker commands based on NLP analysis"""
        try:
            if action == "list_containers":
                containers = self.client.containers.list(all=True)
                return {
                    "status": "success",
                    "data": [{"id": c.id[:12], "name": c.name, "status": c.status} 
                            for c in containers]
                }
            
            elif action == "run_container":
                container = self.client.containers.run(
                    params.get("image", "hello-world"),
                    detach=True,
                    name=params.get("name"),
                    ports=params.get("ports", {})
                )
                return {"status": "success", "container_id": container.id[:12]}
            
            elif action == "stop_container":
                container = self.client.containers.get(params["container_id"])
                container.stop()
                return {"status": "success", "message": f"Container {params['container_id']} stopped"}

        except Exception as e:
            logger.error(f"Docker operation failed: {str(e)}")
            return {"status": "error", "message": str(e)}

class NLPProcessor:
    def __init__(self):
        # Initialize the zero-shot classification pipeline
        self.classifier = pipeline("zero-shot-classification", 
                                 model="facebook/bart-large-mnli")
        
        # Define command categories and their corresponding Docker actions
        self.command_mappings = {
            "list_containers": {
                "patterns": ["show containers", "list containers", "display containers"],
                "docker_action": "list_containers"
            },
            "run_container": {
                "patterns": ["run container", "start container", "launch container"],
                "docker_action": "run_container"
            },
            "stop_container": {
                "patterns": ["stop container", "halt container", "terminate container"],
                "docker_action": "stop_container"
            }
        }

        # Entity extraction patterns
        self.entity_patterns = {
            "container_id": r"container (?:id |ID )?([a-zA-Z0-9]+)",
            "image_name": r"image (?:named? )?([a-zA-Z0-9\-\_\:\/]+)",
            "port_mapping": r"port (\d+):(\d+)",
            "container_name": r"name(?:d)? ([a-zA-Z0-9\-\_]+)"
        }

    def analyze_command(self, command: str) -> Tuple[str, Dict]:
        """Analyze the command and extract relevant information"""
        # Classify intent
        categories = list(self.command_mappings.keys())
        result = self.classifier(command, categories, 
                               hypothesis_template="This is a {} command.")
        
        intent = result['labels'][0]
        confidence = result['scores'][0]

        # Extract entities
        entities = {}
        for entity_name, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, command, re.IGNORECASE)
            if matches:
                entities[entity_name] = matches[0] if isinstance(matches[0], str) else matches[0]

        logger.info(f"Command analysis - Intent: {intent}, Confidence: {confidence}, Entities: {entities}")
        return intent, entities

app = Flask(__name__)
nlp_processor = NLPProcessor()
docker_manager = DockerManager()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_command():
    try:
        command = request.json.get('command', '')
        intent, entities = nlp_processor.analyze_command(command)
        
        # Execute Docker command based on intent
        result = docker_manager.execute_command(intent, entities)
        
        return jsonify({
            'status': 'success',
            'intent': intent,
            'entities': entities,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True)