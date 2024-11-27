import os
from dotenv import load_dotenv
from supabase import create_client
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
import google.generativeai as genai
from google.generativeai import GenerationConfig
from typing import Dict, Any, List
import json
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchMetadata(BaseModel):
    """Metadata structure for search filtering"""
    command_category: List[str] = Field(
        default=[],
        description="Docker command categories like container, network, volume, image, compose, system"
    )
    component_type: List[str] = Field(
        default=[],
        description="Component types like cli, daemon, compose, swarm, api"
    )
    resource_type: List[str] = Field(
        default=[],
        description="Resource types like tutorial, reference, troubleshooting"
    )
    environment: List[str] = Field(
        default=[],
        description="Environment types like development, production"
    )
    os_compatibility: List[str] = Field(
        default=[],
        description="OS types like linux, windows, macos"
    )

class VectorSearch:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not all([supabase_url, supabase_key, gemini_api_key]):
            raise ValueError("Missing required credentials")
            
        # Initialize Supabase client
        self.supabase = create_client(supabase_url, supabase_key)
        
        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.llm = genai.GenerativeModel('gemini-pro')
        
        # Initialize embedding model
        logger.info("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        logger.info("Model loaded successfully")
    
    def extract_search_metadata(self, query: str) -> Dict[str, Any]:
        """Extract metadata filters from the search query using Gemini"""
        try:
            system_prompt = """Extract metadata from the search query and return a raw JSON object with no formatting, markdown, or extra characters:
            {
                "command_category": ["container"|"network"|"volume"|"image"|"compose"|"system"],
                "component_type": ["cli"|"daemon"|"compose"|"swarm"|"api"],
                "resource_type": ["tutorial"|"reference"|"troubleshooting"],
                "environment": ["development"|"production"],
                "os_compatibility": ["linux"|"windows"|"macos"]
            }

            -Return only the JSON object itself 
            -no code blocks, no newlines (\n) before or after, no additional text.
            -the value must be a list of [str] as described in the example even for a single value"""
            prompt = f"{system_prompt}\n\nQuery: {query}"
            response = response = self.llm.generate_content(prompt)
            #logger.info("Model response: ", response.text)
            
            # Parse the response into SearchMetadata
            parsed = SearchMetadata.model_validate_json((response.text).strip().replace('\n',''))
            return parsed.model_dump(exclude_none=True)
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings for the input text"""
        try:
            embedding = self.embedding_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def build_metadata_filter(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build Supabase filter from extracted metadata"""
        filter_conditions = {}
    
        for key, values in metadata.items():
            if values:  # Only add non-empty filters
                if isinstance(values, list):
                    filter_conditions[key] = values
                else:
                    filter_conditions[key] = [values]
        
        return filter_conditions

    async def search_similar_documents(
        self,
        query: str,
        match_threshold: float = 0.7,
        match_count: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using both semantic search and metadata filtering"""
        try:
            #logger.info("Extracting metadata from query...")
            metadata = self.extract_search_metadata(query)
            metadata_filter = self.build_metadata_filter(metadata)
            
            logger.info(f"Generated metadata filter: {metadata_filter}")
            #logger.info(f"Generating embedding for query: {query[:100]}...")
            
            query_embedding = self.generate_embedding(query)
            
            #logger.info("Searching for similar documents...")
            result = self.supabase.rpc(
                'match_documents_with_filters',  
                {
                    'query_embedding': query_embedding,
                    'match_threshold': match_threshold,
                    'match_count': match_count,
                    'filter_conditions': metadata_filter
                }
            ).execute()
            
            logger.info(f"Found {len(result.data)} matches")
            return result.data
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise

async def main():
    try:
        vector_search = VectorSearch()
        
        # Example queries with implicit metadata
        queries = [
            "Install Docker Compose on Windows"
        ]
        
        for query in queries:
            print(f"\nSearching for: '{query}'")
            results = await vector_search.search_similar_documents(
                query,
                match_threshold=0.6,
                match_count=2
            )
            
            if results:
                print("\nMatching documents found:")
                print("-" * 80)
                for idx, result in enumerate(results, 1):
                    print(f"\nMatch {idx} (Similarity: {result['similarity']:.4f})")
                    print("-" * 40)
                    print(f"Content: {result['content']}...")
                    if result.get('metadata'):
                        print(f"\nMetadata: {result['metadata']}")
                    print("-" * 40)
            else:
                print("\nNo matching documents found.")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())