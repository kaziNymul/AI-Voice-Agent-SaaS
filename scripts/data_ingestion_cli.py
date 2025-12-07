#!/usr/bin/env python3
"""
Interactive CLI for data ingestion into vector database.
Users can point to their data files and automatically populate the knowledge base.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.elasticsearch_client import ElasticsearchClient
from app.services.rag_service import RAGService
from app.config import get_settings
import structlog

logger = structlog.get_logger()


class DataIngestionCLI:
    """Interactive CLI for ingesting user data into vector database."""
    
    def __init__(self):
        self.settings = get_settings()
        self.es_client = None
        self.rag_service = None
        self.supported_formats = ['.txt', '.json', '.csv', '.md']
        
    async def initialize(self):
        """Initialize services."""
        print("\n🚀 Initializing Customer Care AI System...")
        print("=" * 60)
        
        self.es_client = ElasticsearchClient(self.settings.elasticsearch_url)
        await self.es_client.connect()
        
        # Check connection
        if not await self.es_client.ping():
            print("❌ Error: Cannot connect to Elasticsearch")
            print(f"   Make sure Elasticsearch is running at {self.settings.elasticsearch_url}")
            print("   Run: docker compose up -d elasticsearch")
            sys.exit(1)
        
        print("✅ Connected to Elasticsearch")
        
        self.rag_service = RAGService(self.es_client, self.settings)
        
        # Ensure index exists
        await self.rag_service.ensure_index()
        print(f"✅ Index '{self.settings.elasticsearch_index_name}' ready")
        print()
        
    def print_welcome(self):
        """Print welcome message."""
        print("\n" + "=" * 60)
        print("  📚 Customer Care AI - Data Ingestion Tool")
        print("=" * 60)
        print("\nThis tool will help you load your data into the vector database.")
        print("Supported formats: TXT, JSON, CSV, Markdown")
        print()
        
    def get_data_location(self) -> str:
        """Prompt user for data location."""
        print("📂 Data Location")
        print("-" * 60)
        print("Enter the path to your data:")
        print("  - Single file: /path/to/file.txt")
        print("  - Directory: /path/to/data/folder")
        print("  - Press Enter to use default: ./data/raw/")
        print()
        
        while True:
            location = input("Path: ").strip()
            
            # Use default if empty
            if not location:
                location = "./data/raw/"
                print(f"Using default: {location}")
            
            # Convert to absolute path
            path = Path(location).resolve()
            
            if path.exists():
                return str(path)
            else:
                print(f"❌ Path not found: {path}")
                print("Please enter a valid path or press Ctrl+C to exit.\n")
    
    def scan_files(self, location: str) -> List[Path]:
        """Scan for supported files."""
        path = Path(location)
        files = []
        
        if path.is_file():
            if path.suffix.lower() in self.supported_formats:
                files.append(path)
        else:
            for ext in self.supported_formats:
                files.extend(path.rglob(f"*{ext}"))
        
        return sorted(files)
    
    def confirm_files(self, files: List[Path]) -> bool:
        """Show files and confirm ingestion."""
        print("\n📄 Found Files")
        print("-" * 60)
        
        if not files:
            print("❌ No supported files found!")
            print(f"Supported formats: {', '.join(self.supported_formats)}")
            return False
        
        print(f"Found {len(files)} file(s):\n")
        for i, file in enumerate(files, 1):
            size = file.stat().st_size / 1024  # KB
            print(f"  {i}. {file.name} ({size:.1f} KB)")
        
        print()
        response = input("Proceed with ingestion? (y/n): ").strip().lower()
        return response in ['y', 'yes']
    
    async def read_file_content(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read and parse file content based on format."""
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.txt' or ext == '.md':
                return await self._read_text_file(file_path)
            elif ext == '.json':
                return await self._read_json_file(file_path)
            elif ext == '.csv':
                return await self._read_csv_file(file_path)
            else:
                logger.warning(f"Unsupported format: {ext}")
                return []
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []
    
    async def _read_text_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read plain text or markdown file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by double newlines to separate sections
        sections = [s.strip() for s in content.split('\n\n') if s.strip()]
        
        documents = []
        for i, section in enumerate(sections):
            if len(section) > 50:  # Skip very short sections
                documents.append({
                    'content': section,
                    'metadata': {
                        'source': file_path.name,
                        'section': i + 1,
                        'type': 'text'
                    }
                })
        
        return documents
    
    async def _read_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read JSON file with Q&A pairs or documents."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        documents = []
        
        # Handle different JSON structures
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    # Q&A format
                    if 'question' in item and 'answer' in item:
                        content = f"Q: {item['question']}\nA: {item['answer']}"
                    # Direct content
                    elif 'content' in item:
                        content = item['content']
                    # Generic dict - convert to text
                    else:
                        content = json.dumps(item, indent=2)
                    
                    documents.append({
                        'content': content,
                        'metadata': {
                            'source': file_path.name,
                            'index': i,
                            'type': 'json',
                            **{k: v for k, v in item.items() if k not in ['content', 'question', 'answer']}
                        }
                    })
        elif isinstance(data, dict):
            # Single document
            content = data.get('content', json.dumps(data, indent=2))
            documents.append({
                'content': content,
                'metadata': {
                    'source': file_path.name,
                    'type': 'json'
                }
            })
        
        return documents
    
    async def _read_csv_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read CSV file with Q&A pairs or data."""
        import csv
        
        documents = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Try Q&A format
                if 'question' in row and 'answer' in row:
                    content = f"Q: {row['question']}\nA: {row['answer']}"
                # Try content column
                elif 'content' in row:
                    content = row['content']
                # Combine all columns
                else:
                    content = '\n'.join(f"{k}: {v}" for k, v in row.items() if v)
                
                if content.strip():
                    documents.append({
                        'content': content,
                        'metadata': {
                            'source': file_path.name,
                            'row': i + 1,
                            'type': 'csv'
                        }
                    })
        
        return documents
    
    async def ingest_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest documents into vector database."""
        print("\n⚙️  Processing Documents")
        print("-" * 60)
        
        total = len(documents)
        success = 0
        failed = 0
        
        print(f"Processing {total} documents...\n")
        
        for i, doc in enumerate(documents, 1):
            try:
                # Generate embedding
                embedding = await self.rag_service.generate_embedding(doc['content'])
                
                # Index document
                await self.es_client.index_document(
                    index=self.settings.elasticsearch_index_name,
                    document={
                        'content': doc['content'],
                        'embedding': embedding,
                        'metadata': doc['metadata']
                    }
                )
                
                success += 1
                
                # Progress indicator
                if i % 10 == 0 or i == total:
                    print(f"Progress: {i}/{total} documents processed", end='\r')
                
            except Exception as e:
                failed += 1
                logger.error(f"Failed to index document {i}: {e}")
        
        print()  # New line after progress
        
        return {
            'total': total,
            'success': success,
            'failed': failed
        }
    
    def print_summary(self, stats: Dict[str, Any]):
        """Print ingestion summary."""
        print("\n✅ Ingestion Complete!")
        print("=" * 60)
        print(f"Total documents:    {stats['total']}")
        print(f"Successfully added: {stats['success']}")
        print(f"Failed:             {stats['failed']}")
        print("=" * 60)
        
        if stats['success'] > 0:
            print("\n🎉 Your knowledge base is ready!")
            print("   Start the service with: docker compose up -d")
            print("   Test with Telegram or use the API endpoints")
        
        print()
    
    async def run(self):
        """Run the CLI tool."""
        try:
            self.print_welcome()
            await self.initialize()
            
            # Get data location
            location = self.get_data_location()
            
            # Scan files
            files = self.scan_files(location)
            
            # Confirm
            if not self.confirm_files(files):
                print("\n❌ Ingestion cancelled.")
                return
            
            # Read and process all files
            print("\n📖 Reading Files")
            print("-" * 60)
            
            all_documents = []
            for file in files:
                print(f"Reading {file.name}...", end=' ')
                docs = await self.read_file_content(file)
                all_documents.extend(docs)
                print(f"✓ ({len(docs)} documents)")
            
            if not all_documents:
                print("\n❌ No valid documents found to ingest.")
                return
            
            # Ingest
            stats = await self.ingest_documents(all_documents)
            
            # Summary
            self.print_summary(stats)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Ingestion cancelled by user.")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.exception("Ingestion failed")
        finally:
            if self.es_client:
                await self.es_client.close()


async def main():
    """Main entry point."""
    cli = DataIngestionCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
