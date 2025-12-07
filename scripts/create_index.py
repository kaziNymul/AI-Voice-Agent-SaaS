#!/usr/bin/env python3
"""
Script to create Elasticsearch index with proper vector mapping
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.elasticsearch_client import ElasticsearchClient
from app.config import settings
from app.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def create_index():
    """Create the Elasticsearch index"""
    es_client = ElasticsearchClient()
    
    try:
        # Check connection
        if not await es_client.ping():
            logger.error("elasticsearch_not_reachable", url=settings.elasticsearch_url)
            return False
        
        logger.info("elasticsearch_connected", url=settings.elasticsearch_url)
        
        # Create index
        logger.info("creating_index", index_name=settings.elasticsearch_index_name)
        success = await es_client.create_index()
        
        if success:
            logger.info("index_created_successfully", index_name=settings.elasticsearch_index_name)
            
            # Get document count
            count = await es_client.count_documents()
            logger.info("index_status", document_count=count)
            
            return True
        else:
            logger.error("index_creation_failed")
            return False
            
    except Exception as e:
        logger.error("create_index_error", error=str(e))
        return False
    finally:
        await es_client.close()


async def delete_and_recreate_index():
    """Delete existing index and recreate it"""
    es_client = ElasticsearchClient()
    
    try:
        if not await es_client.ping():
            logger.error("elasticsearch_not_reachable")
            return False
        
        # Delete if exists
        logger.warning("deleting_existing_index", index_name=settings.elasticsearch_index_name)
        await es_client.delete_index()
        
        # Recreate
        logger.info("recreating_index")
        success = await es_client.create_index()
        
        if success:
            logger.info("index_recreated_successfully")
            return True
        else:
            logger.error("index_recreation_failed")
            return False
            
    except Exception as e:
        logger.error("recreate_index_error", error=str(e))
        return False
    finally:
        await es_client.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create Elasticsearch index for vector search")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete existing index and recreate it"
    )
    
    args = parser.parse_args()
    
    if args.recreate:
        print("⚠️  Warning: This will DELETE all existing data in the index!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
        
        success = asyncio.run(delete_and_recreate_index())
    else:
        success = asyncio.run(create_index())
    
    sys.exit(0 if success else 1)
