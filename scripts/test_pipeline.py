#!/usr/bin/env python3
"""
Test the complete pipeline end-to-end
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.elasticsearch_client import ElasticsearchClient
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.config import settings
from app.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def test_rag_pipeline():
    """Test the RAG pipeline with sample queries"""
    
    print("\n" + "="*60)
    print("Testing RAG Pipeline")
    print("="*60 + "\n")
    
    es_client = ElasticsearchClient()
    
    try:
        # Check Elasticsearch connection
        print("1. Checking Elasticsearch connection...")
        if not await es_client.ping():
            print("❌ Elasticsearch not reachable")
            return False
        print("✅ Elasticsearch connected")
        
        # Check document count
        count = await es_client.count_documents()
        print(f"✅ Index has {count} documents\n")
        
        if count == 0:
            print("⚠️  Warning: No documents in index. Run 'python scripts/ingest_docs.py --sample' first")
            return False
        
        # Initialize services
        rag_service = RAGService(es_client)
        llm_service = LLMService()
        
        # Test queries
        test_queries = [
            "How do I reset my password?",
            "What are your business hours?",
            "How can I get a refund?",
            "How do I track my order?"
        ]
        
        print("2. Testing RAG retrieval and LLM responses:\n")
        
        for i, query in enumerate(test_queries, 1):
            print(f"{'─'*60}")
            print(f"Query {i}: {query}")
            print(f"{'─'*60}")
            
            # Retrieve context
            print("  → Retrieving context from Elasticsearch...")
            context = await rag_service.retrieve_context(query, top_k=3)
            
            print(f"  ✅ Found {len(context.documents)} relevant documents:")
            for j, doc in enumerate(context.documents, 1):
                print(f"     [{j}] Score: {doc.score:.3f} | {doc.text[:80]}...")
            
            # Generate response
            print("  → Generating LLM response...")
            response = await llm_service.generate_response(
                question=query,
                context_documents=context.documents
            )
            
            print(f"  ✅ LLM Response ({response.tokens_used} tokens):")
            print(f"     {response.answer}\n")
        
        print("="*60)
        print("✅ All tests passed!")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        logger.error("test_pipeline_error", error=str(e))
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        await es_client.close()


async def test_embedding():
    """Test embedding generation"""
    print("\n" + "="*60)
    print("Testing Embedding Generation")
    print("="*60 + "\n")
    
    es_client = ElasticsearchClient()
    rag_service = RAGService(es_client)
    
    try:
        test_text = "How do I reset my password?"
        print(f"Text: {test_text}")
        
        print("Generating embedding...")
        embedding = await rag_service.generate_embedding(test_text)
        
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   First 10 values: {embedding[:10]}")
        print(f"   Vector magnitude: {sum(x*x for x in embedding)**0.5:.3f}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        await es_client.close()


async def test_elasticsearch():
    """Test Elasticsearch connection and index"""
    print("\n" + "="*60)
    print("Testing Elasticsearch")
    print("="*60 + "\n")
    
    es_client = ElasticsearchClient()
    
    try:
        # Ping
        print("1. Testing connection...")
        if await es_client.ping():
            print("✅ Elasticsearch is reachable\n")
        else:
            print("❌ Elasticsearch not reachable\n")
            return False
        
        # Document count
        print("2. Checking index...")
        count = await es_client.count_documents()
        print(f"✅ Index: {settings.elasticsearch_index_name}")
        print(f"✅ Document count: {count}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        await es_client.close()


async def main():
    """Run all tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the AI customer care pipeline")
    parser.add_argument("--es", action="store_true", help="Test Elasticsearch only")
    parser.add_argument("--embedding", action="store_true", help="Test embedding generation only")
    parser.add_argument("--rag", action="store_true", help="Test full RAG pipeline")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if not any([args.es, args.embedding, args.rag, args.all]):
        args.all = True
    
    results = []
    
    if args.all or args.es:
        results.append(await test_elasticsearch())
    
    if args.all or args.embedding:
        results.append(await test_embedding())
    
    if args.all or args.rag:
        results.append(await test_rag_pipeline())
    
    # Summary
    if all(results):
        print("\n🎉 All tests passed!\n")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
