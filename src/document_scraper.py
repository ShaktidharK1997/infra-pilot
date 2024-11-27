import os
import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import asyncio
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import re
from dotenv import load_dotenv
import time
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockerDocsScraper:
    def __init__(self):
        self.base_url = "https://docs.docker.com"
        self.docs_url = "https://docs.docker.com/engine/"
        
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        
        # Headers to mimic a browser request
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract targeted Docker-specific metadata"""
        text = soup.get_text().lower()
        
        # Extract commands
        code_blocks = soup.find_all('code')
        commands = [block.text.strip() for block in code_blocks 
                   if block.text.strip().startswith('docker')]
        
        # Extract prerequisites
        prereq_section = soup.find(['h2', 'h3'], string=re.compile(r'prerequisites|requirements', re.I))
        prerequisites = []
        if prereq_section:
            prereq_list = prereq_section.find_next('ul')
            if prereq_list:
                prerequisites = [li.text.strip() for li in prereq_list.find_all('li')]

        metadata = {
            'command_category': self._get_command_category(url, text),
            'component_type': self._get_component_type(url, text),
            'resource_type': self._get_resource_type(soup),
            'docker_commands': commands[:10],  # Limit to most relevant
            'prerequisites': prerequisites,
            'environment': self._get_environment_type(text),
            'os_compatibility': self._get_os_compatibility(text),
            'docker_version': self._extract_version(text),
            'last_updated': time.strftime('%Y-%m-%d')
        }
        return metadata

    def _get_command_category(self, url: str, text: str) -> str:
        categories = {
            'container': ['container', 'run', 'exec'],
            'network': ['network', 'port', 'proxy'],
            'volume': ['volume', 'storage', 'mount'],
            'image': ['image', 'build', 'registry'],
            'compose': ['compose', 'stack', 'service'],
            'system': ['daemon', 'system', 'info']
        }
        
        for category, keywords in categories.items():
            if any(k in text or k in url for k in keywords):
                return category
        return 'general'

    def _get_component_type(self, url: str, text: str) -> str:
        components = {
            'cli': ['command line', 'cli', 'command reference'],
            'daemon': ['dockerd', 'daemon', 'engine api'],
            'compose': ['docker-compose', 'compose file'],
            'swarm': ['swarm', 'service', 'node'],
            'api': ['api', 'endpoint', 'rest']
        }
        
        for comp, keywords in components.items():
            if any(k in text.lower() or k in url for k in keywords):
                return comp
        return 'general'

    def _get_resource_type(self, soup: BeautifulSoup) -> str:
        title = soup.find('h1')
        if not title:
            return 'general'
            
        title_text = title.text.lower()
        
        if any(word in title_text for word in ['how to', 'tutorial', 'guide']):
            return 'tutorial'
        elif any(word in title_text for word in ['reference', 'manual', 'command']):
            return 'reference'
        elif any(word in title_text for word in ['debug', 'troubleshoot', 'error']):
            return 'troubleshooting'
        return 'general'

    def _get_environment_type(self, text: str) -> List[str]:
        environments = []
        if any(word in text for word in ['development', 'local', 'test']):
            environments.append('development')
        if any(word in text for word in ['production', 'deploy', 'scale']):
            environments.append('production')
        return environments or ['general']

    def _get_os_compatibility(self, text: str) -> List[str]:
        os_list = []
        if any(word in text for word in ['linux', 'ubuntu', 'debian']):
            os_list.append('linux')
        if 'windows' in text:
            os_list.append('windows')
        if any(word in text for word in ['macos', 'darwin']):
            os_list.append('macos')
        return os_list or ['all']

    def _extract_version(self, text: str) -> Optional[str]:
        version_pattern = r'Docker version (\d+\.\d+)'
        match = re.search(version_pattern, text)
        return match.group(1) if match else None

    def get_page_content(self, url: str) -> str:
        """Fetch content from a URL with rate limiting and retries"""
        for attempt in range(3):  # 3 retries
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status() # Automatically checks if response has returned any error codes (4XX, 5XX)
                time.sleep(1)  # Rate limiting
                return response.text
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt == 2:  # Last attempt
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        return ""
    
    @staticmethod
    def create_chunks(paragraphs: List[str], max_size: int = 1500, overlap: int = 200) -> List[str]:
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            if current_length + len(para) > max_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    # Keep last few paragraphs for overlap
                    overlap_size = 0
                    overlap_chunks = []
                    for p in reversed(current_chunk):
                        if overlap_size + len(p) <= overlap:
                            overlap_chunks.insert(0, p)
                            overlap_size += len(p)
                        else:
                            break
                    current_chunk = overlap_chunks
                    current_length = overlap_size
                current_chunk.append(para)
                current_length += len(para)
            else:
                current_chunk.append(para)
                current_length += len(para)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks

    def extract_content(self, html_content: str) -> Dict[str, Any]:
        """Extract meaningful content from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove navigation, footer, and other non-content elements
        for element in soup.find_all(['nav', 'footer', 'script', 'style']):
            element.decompose()
        
        # Get the main content
        main_content = soup.find('main') or soup.find(class_='content')
        if not main_content:
            return None
            
        # Extract title
        title = soup.find('h1')
        title_text = title.get_text().strip() if title else ""
        
        # Extract text from paragraphs and lists
        paragraphs = []
        for elem in main_content.find_all(['p', 'li', 'h2', 'h3', 'code']):
            text = elem.get_text().strip()
            if elem.name == 'code':
                    if text:
                        paragraphs.append(text)
            elif text and len(text) > 20:
            # Filter other elements by length
                    paragraphs.append(text)
        
        #metadata extraction
        metadata = self.extract_metadata(soup, self.current_url)
        return {
            "title": title_text,
            "chunks": self.create_chunks(paragraphs),
            "url": self.current_url,
            "metadata": metadata
        }

    def collect_doc_urls(self, start_url: str) -> List[str]:
        """Collect all documentation URLs starting from a given URL"""
        try:
            content = self.get_page_content(start_url)
            soup = BeautifulSoup(content, 'html.parser')
            
            urls = set()
            # Find all links within the documentation
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(start_url, href)
                
                # Only include Docker documentation URLs
                if full_url.startswith(self.base_url) and '/engine/' in full_url:
                    urls.add(full_url)
            
            return list(urls)
            
        except Exception as e:
            logger.error(f"Error collecting URLs: {e}")
            return []

    async def embed_and_store(self, content: Dict[str, Any]) -> None:
        """Generate embeddings and store in Supabase"""
        try:
            for chunk in content['chunks']:
                # Generate embedding
                embedding = self.embedding_model.encode(chunk).tolist()
                
                 
                data = {
                    'content': chunk,
                    'metadata': {
                        'title': content['title'],
                        'url': content['url'],
                        **content['metadata']  # Include all extracted metadata
                    },
                    'embedding': embedding
                }
                
                self.supabase.table('documents').insert(data).execute()
                logger.info(f"Stored chunk from {content['title']}")
                
        except Exception as e:
            logger.error(f"Error storing content: {e}")

    async def process_url(self, url: str) -> None:
        """Process a single URL"""
        try:
            self.current_url = url
            content = self.get_page_content(url)
            if not content:
                return
                
            extracted = self.extract_content(content)
            if extracted:
                await self.embed_and_store(extracted)
                
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")

    async def scrape_and_store(self):
        """Main function to scrape Docker docs and store in Supabase"""
        try:
            # Collect URLs
            urls = self.collect_doc_urls(self.docs_url)
            logger.info(f"Found {len(urls)} documentation pages")
            
            # Process URLs concurrently
            tasks = []
            for url in urls:
                task = asyncio.create_task(self.process_url(url))
                tasks.append(task)
                await asyncio.sleep(0.5)  # Rate limiting
                
            await asyncio.gather(*tasks)
            
            logger.info("Documentation scraping and storage complete")
            
        except Exception as e:
            logger.error(f"Error in scrape_and_store: {e}")

async def main():
    scraper = DockerDocsScraper()
    await scraper.scrape_and_store()

if __name__ == "__main__":
    asyncio.run(main())

