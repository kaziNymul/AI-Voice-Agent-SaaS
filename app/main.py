"""
FastAPI application entry point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from app.config import settings
from app.utils.logging import setup_logging, get_logger
from app.routes import telegram, admin
from app.clients.elasticsearch_client import ElasticsearchClient

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("starting_application", environment=settings.environment)
    
    # Initialize Elasticsearch connection
    es_client = ElasticsearchClient()
    app.state.es_client = es_client
    
    # Check Elasticsearch connection
    try:
        if await es_client.ping():
            logger.info("elasticsearch_connected", url=settings.es_url)
            
            # Auto-initialize system (create indexes, load initial data)
            # Skipping auto-initialization - data loaded via provisioning script
            # logger.info("auto_initializing_system")
            # from scripts.initialize_system import initialize_system
            # await initialize_system()
            
            # Initialize learning service
            from app.services.rag_service import RAGService
            from app.services.learning_service import LearningService
            rag_service = RAGService(es_client)
            learning_service = LearningService(es_client, rag_service)
            app.state.learning_service = learning_service
            
            logger.info("system_ready_with_learning")
        else:
            logger.error("elasticsearch_connection_failed")
    except Exception as e:
        logger.error("elasticsearch_error", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("shutting_down_application")
    await es_client.close()


# Create FastAPI app
app = FastAPI(
    title="AI Customer Care System",
    description="Voice-powered AI customer care with RAG",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# Include data upload router
from app.routes import data_upload
app.include_router(data_upload.router, tags=["data"])

# Include phone router (Twilio)
try:
    from app.routes import phone
    app.include_router(phone.router, prefix="/phone", tags=["phone"])
    logger.info("phone_routes_loaded", message="Twilio phone call support enabled")
except ImportError:
    logger.warning("phone_routes_not_loaded", message="Twilio dependencies not installed")

# Include SIP router (Telecom operators: Telia, DNA, Elisa)
try:
    from app.routes import sip_routes
    from app.services.sip_trunk_service import SIPTrunkService, get_provider_config
    
    # Initialize SIP service if configured
    sip_provider = settings.sip_provider if hasattr(settings, 'sip_provider') else None
    if sip_provider:
        sip_credentials = {
            'sip_username': settings.sip_username if hasattr(settings, 'sip_username') else None,
            'sip_password': settings.sip_password if hasattr(settings, 'sip_password') else None,
            'local_ip': settings.sip_local_ip if hasattr(settings, 'sip_local_ip') else '0.0.0.0',
            'local_port': settings.sip_local_port if hasattr(settings, 'sip_local_port') else 5060,
        }
        sip_config = get_provider_config(sip_provider, sip_credentials)
        app.state.sip_service = SIPTrunkService(sip_config)
        app.include_router(sip_routes.router, prefix="/phone", tags=["sip"])
        logger.info("sip_routes_loaded", message=f"SIP trunk support enabled for {sip_provider}")
    else:
        logger.info("sip_not_configured", message="SIP trunk support available but not configured")
except ImportError as e:
    logger.warning("sip_routes_not_loaded", message="SIP dependencies not available", error=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Customer Care System",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    es_healthy = False
    try:
        es_client = app.state.es_client
        es_healthy = await es_client.ping()
    except Exception as e:
        logger.error("health_check_es_error", error=str(e))
    
    return {
        "status": "healthy" if es_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "elasticsearch": "up" if es_healthy else "down",
            "api": "up"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )
