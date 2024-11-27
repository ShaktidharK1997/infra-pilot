from typing import Dict, Any, List
import re
from bs4 import BeautifulSoup
import time


class DockerMetadata:
    """Dedicated class for Docker-specific metadata extraction"""
    
    @staticmethod
    def extract_command_metadata(text: str) -> Dict[str, Any]:
        """Extract command-related metadata"""
        command_patterns = {
            'build': r'docker\s+build|Dockerfile',
            'run': r'docker\s+run|container\s+execution',
            'compose': r'docker-compose|docker\s+compose',
            'swarm': r'docker\s+swarm|service\s+deployment',
            'network': r'docker\s+network|container\s+networking',
            'volume': r'docker\s+volume|data\s+persistence',
            'security': r'docker\s+secret|security\s+context'
        }
        
        commands = []
        for cmd, pattern in command_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                commands.append(cmd)
                
        return commands

    @staticmethod
    def extract_resource_type(text: str) -> List[str]:
        """Identify Docker resource types mentioned"""
        resources = {
            'container': r'container[s]?\b',
            'image': r'image[s]?\b',
            'volume': r'volume[s]?\b',
            'network': r'network[s]?\b',
            'service': r'service[s]?\b',
            'stack': r'stack[s]?\b',
            'secret': r'secret[s]?\b'
        }
        
        found_resources = []
        for resource, pattern in resources.items():
            if re.search(pattern, text, re.IGNORECASE):
                found_resources.append(resource)
                
        return found_resources

    @staticmethod
    def extract_environment_context(text: str) -> List[str]:
        """Determine relevant environment contexts"""
        environments = {
            'production': r'production|prod\b',
            'development': r'development|dev\b',
            'testing': r'testing|test\b',
            'staging': r'staging|stage\b',
            'local': r'local\s+environment|localhost'
        }
        
        contexts = []
        for env, pattern in environments.items():
            if re.search(pattern, text, re.IGNORECASE):
                contexts.append(env)
                
        return contexts

    @staticmethod
    def determine_complexity(text: str) -> str:
        """Determine content complexity level"""
        advanced_terms = {
            'orchestration', 'swarm', 'kubernetes', 'security', 
            'optimization', 'scaling', 'load balancing', 'clustering'
        }
        intermediate_terms = {
            'networking', 'volumes', 'compose', 'dockerfile', 
            'multi-container', 'deployment'
        }
        
        text_lower = text.lower()
        advanced_count = sum(1 for term in advanced_terms if term in text_lower)
        intermediate_count = sum(1 for term in intermediate_terms if term in text_lower)
        
        if advanced_count >= 2:
            return 'advanced'
        elif intermediate_count >= 2:
            return 'intermediate'
        return 'beginner'

    @staticmethod
    def extract_prerequisites(text: str) -> List[str]:
        """Extract prerequisites and dependencies"""
        prereq_patterns = {
            'docker_engine': r'requires\s+Docker\s+Engine|Docker\s+version',
            'compose': r'requires\s+Docker\s+Compose|Compose\s+version',
            'linux': r'requires\s+Linux|Linux\s+kernel',
            'memory': r'(\d+)\s*(GB|MB)\s+RAM|memory\s+requirement',
            'disk': r'(\d+)\s*(GB|MB)\s+disk\s+space',
            'root': r'root\s+privileges|sudo\s+access'
        }
        
        prerequisites = []
        for prereq, pattern in prereq_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                prerequisites.append(prereq)
                
        return prerequisites

class DockerDocsScraper:
    def __init__(self):
        # Previous initialization code remains the same
        self.metadata_extractor = DockerMetadata()
        
    def extract_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract content with enhanced metadata"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove non-content elements
        for element in soup.find_all(['nav', 'footer', 'script', 'style']):
            element.decompose()
        
        main_content = soup.find('main') or soup.find(class_='content')
        if not main_content:
            return None
            
        content_text = main_content.get_text()
        
        # Extract comprehensive metadata
        metadata = {
            'url': url,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'commands': self.metadata_extractor.extract_command_metadata(content_text),
            'resource_types': self.metadata_extractor.extract_resource_type(content_text),
            'environments': self.metadata_extractor.extract_environment_context(content_text),
            'complexity': self.metadata_extractor.determine_complexity(content_text),
            'prerequisites': self.metadata_extractor.extract_prerequisites(content_text)
        }
        
        # Extract chunks with consistent size
        chunks = self.create_chunks(content_text)
        
        return {
            'chunks': chunks,
            'metadata': metadata
        }

    async def update_existing_records(self):
        """Update existing records with new metadata"""
        try:
            # Fetch all existing records
            response = self.supabase.table('documents').select('id', 'content').execute()
            records = response.data
            
            for record in records:
                # Extract new metadata for existing content
                metadata = {
                    'commands': self.metadata_extractor.extract_command_metadata(record['content']),
                    'resource_types': self.metadata_extractor.extract_resource_type(record['content']),
                    'environments': self.metadata_extractor.extract_environment_context(record['content']),
                    'complexity': self.metadata_extractor.determine_complexity(record['content']),
                    'prerequisites': self.metadata_extractor.extract_prerequisites(record['content'])
                }
                
                # Update the record with new metadata
                self.supabase.table('documents').update({
                    'metadata': metadata
                }).eq('id', record['id']).execute()
                
                logger.info(f"Updated metadata for record {record['id']}")
                await asyncio.sleep(0.1)  # Rate limiting
                
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")