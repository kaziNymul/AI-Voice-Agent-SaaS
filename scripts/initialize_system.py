"""
Startup initialization script - Pre-loads knowledge base
"""
import asyncio
from pathlib import Path
from app.clients.elasticsearch_client import ElasticsearchClient
from app.services.rag_service import RAGService
from app.services.learning_service import LearningService
from app.utils.logging import setup_logging, get_logger
from app.config import settings

setup_logging()
logger = get_logger(__name__)


async def initialize_system():
    """Initialize the system on startup"""
    
    logger.info("system_initialization_starting")
    
    es_client = ElasticsearchClient()
    
    try:
        # Step 1: Check Elasticsearch connection
        logger.info("checking_elasticsearch_connection")
        if not await es_client.ping():
            logger.error("elasticsearch_not_reachable")
            return False
        logger.info("elasticsearch_connected")
        
        # Step 2: Create main knowledge base index if needed
        logger.info("ensuring_knowledge_base_index")
        await es_client.create_index()
        
        # Step 3: Check if knowledge base is empty
        doc_count = await es_client.count_documents()
        logger.info("knowledge_base_status", document_count=doc_count)
        
        if doc_count == 0:
            logger.warning("knowledge_base_empty_loading_initial_data")
            
            # Import and run ingestion
            from scripts.ingest_docs import ingest_sample_data
            await ingest_sample_data()
            
            # Check again
            doc_count = await es_client.count_documents()
            logger.info("knowledge_base_loaded", document_count=doc_count)
        else:
            logger.info("knowledge_base_already_populated", document_count=doc_count)
        
        # Step 4: Initialize learning system
        logger.info("initializing_learning_system")
        rag_service = RAGService(es_client)
        learning_service = LearningService(es_client, rag_service)
        
        await learning_service.ensure_learning_index()
        
        # Get learning stats
        stats = await learning_service.get_learning_stats()
        logger.info("learning_system_ready", **stats)
        
        # Step 5: Pre-load any documents from data/raw if they exist
        data_dir = Path("data/raw")
        if data_dir.exists():
            txt_files = list(data_dir.glob("*.txt"))
            md_files = list(data_dir.glob("*.md"))
            all_files = txt_files + md_files
            
            if all_files:
                logger.info(
                    "found_unprocessed_documents",
                    count=len(all_files),
                    files=[f.name for f in all_files[:5]]
                )
                
                # You can auto-ingest these files
                # For now, just log them
                logger.info(
                    "documents_ready_for_ingestion",
                    message="Run: docker compose exec app python scripts/ingest_docs.py --path data/raw"
                )
        
        logger.info("system_initialization_complete")
        return True
        
    except Exception as e:
        logger.error("system_initialization_failed", error=str(e))
        return False
    finally:
        await es_client.close()


if __name__ == "__main__":
    success = asyncio.run(initialize_system())
    exit(0 if success else 1)
