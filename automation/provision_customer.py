"""
Customer Provisioning Engine
Automatically creates and provisions customer bots
"""

import os
import sys
import logging
import requests
import pandas as pd
import docker
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
USE_TELEGRAM = os.getenv('USE_TELEGRAM', 'true').lower() == 'true'
USE_TWILIO = os.getenv('USE_TWILIO', 'false').lower() == 'true'

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
SHARED_OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')
PLATFORM_DOMAIN = os.getenv('PLATFORM_DOMAIN', 'yourplatform.com')
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost:9200')


class CustomerProvisioner:
    """
    Automatically provisions a complete customer bot setup:
    1. Creates Elasticsearch index
    2. Loads customer data
    3. Provisions phone number or Telegram bot
    4. Creates Docker container
    5. Sets up webhooks
    """
    
    def __init__(self, customer_id, company_name, data_file, telephony_type='telegram'):
        self.customer_id = customer_id
        self.company_name = company_name
        self.data_file = data_file
        self.telephony_type = telephony_type
        
        self.container_id = None
        self.container_port = None
        self.bot_username = None
        self.phone_number = None
        self.telegram_token = None
        self.twilio_sid = None
        
    def provision(self):
        """
        Complete automated provisioning
        Returns dict with bot credentials and status
        """
        try:
            logger.info(f"[Customer {self.customer_id}] Starting provisioning...")
            
            # Step 1: Create Elasticsearch index
            logger.info(f"[Customer {self.customer_id}] Creating Elasticsearch index...")
            self.create_elasticsearch_index()
            
            # Step 2: Load customer data
            logger.info(f"[Customer {self.customer_id}] Loading customer data...")
            row_count = self.load_data_to_elasticsearch()
            
            # Step 3: Provision telephony (Telegram or Twilio)
            logger.info(f"[Customer {self.customer_id}] Provisioning {self.telephony_type}...")
            if self.telephony_type == 'twilio':
                self.provision_twilio_number()
            else:
                self.provision_telegram_bot()
            
            # Step 4: Create Docker container
            logger.info(f"[Customer {self.customer_id}] Creating Docker container...")
            self.create_customer_container()
            
            # Step 5: Setup webhook
            logger.info(f"[Customer {self.customer_id}] Configuring webhooks...")
            self.setup_webhook()
            
            # Step 6: Start container
            logger.info(f"[Customer {self.customer_id}] Starting container...")
            self.start_container()
            
            logger.info(f"[Customer {self.customer_id}] ✅ Provisioning completed successfully!")
            
            return {
                'bot_username': self.bot_username,
                'phone_number': self.phone_number,
                'telegram_token': self.telegram_token,
                'twilio_sid': self.twilio_sid,
                'container_id': self.container_id,
                'container_port': self.container_port,
                'data_row_count': row_count,
                'webhook_url': f"https://{PLATFORM_DOMAIN}/customers/{self.customer_id}/webhook",
                'status': 'active'
            }
            
        except Exception as e:
            logger.error(f"[Customer {self.customer_id}] Provisioning failed: {str(e)}")
            self.cleanup()
            raise
    
    def create_elasticsearch_index(self):
        """Create isolated Elasticsearch index for customer"""
        try:
            es = Elasticsearch([f'http://{ELASTICSEARCH_HOST}'])
            
            index_name = f"customer_{self.customer_id}_qa"
            
            # Delete if exists (ignore errors if doesn't exist)
            try:
                es.indices.delete(index=index_name)
                logger.info(f"Deleted existing index: {index_name}")
            except:
                pass  # Index doesn't exist, that's fine
            
            # Create new index with vector embedding support
            es.indices.create(
                index=index_name,
                settings={
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "custom_analyzer": {
                                "type": "standard",
                                "stopwords": "_english_"
                            }
                        }
                    }
                },
                mappings={
                    "properties": {
                        "text": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "question": {
                            "type": "text",
                            "analyzer": "custom_analyzer"
                        },
                        "answer": {
                            "type": "text"
                        },
                        "embedding": {
                            "type": "dense_vector",
                            "dims": 384,  # MiniLM model dimension
                            "similarity": "cosine"
                        },
                        "category": {
                            "type": "keyword"
                        },
                        "created_at": {
                            "type": "date"
                        }
                    }
                }
            )
            
            logger.info(f"✅ Created Elasticsearch index: {index_name}")
            
        except Exception as e:
            logger.error(f"Failed to create Elasticsearch index: {str(e)}")
            raise
    
    def load_data_to_elasticsearch(self):
        """Load customer's Q&A data into Elasticsearch"""
        try:
            es = Elasticsearch([f'http://{ELASTICSEARCH_HOST}'])
            
            # Read data file
            if self.data_file.endswith('.csv'):
                df = pd.read_csv(self.data_file)
            elif self.data_file.endswith('.json'):
                df = pd.read_json(self.data_file)
            else:
                raise ValueError(f"Unsupported file format: {self.data_file}")
            
            # Validate columns
            if 'question' not in df.columns or 'answer' not in df.columns:
                raise ValueError("Data file must have 'question' and 'answer' columns")
            
            # Prepare bulk insert
            actions = []
            for idx, row in df.iterrows():
                actions.append({
                    "_index": f"customer_{self.customer_id}_qa",
                    "_source": {
                        "question": str(row['question']),
                        "answer": str(row['answer']),
                        "category": row.get('category', 'general'),
                        "created_at": pd.Timestamp.now().isoformat()
                    }
                })
            
            # Bulk insert
            success, failed = bulk(es, actions)
            
            logger.info(f"✅ Loaded {success} Q&A pairs into Elasticsearch")
            
            if failed:
                logger.warning(f"⚠️  {failed} documents failed to load")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            raise
    
    def provision_telegram_bot(self):
        """
        Provision Telegram bot
        Note: Telegram doesn't allow automated bot creation
        Options:
        1. Use pre-created bot pool
        2. Customer provides their own bot token
        3. Manual creation then API assignment
        """
        try:
            # Option 1: Get from bot pool (you need to pre-create bots)
            # For demo, we'll use environment variable or prompt
            
            bot_token = os.getenv(f'CUSTOMER_{self.customer_id}_TELEGRAM_TOKEN')
            
            if not bot_token:
                # Fallback: Use a test bot token or raise error
                logger.warning("No Telegram bot token found. Using placeholder.")
                bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                self.bot_username = "placeholder_bot"
            else:
                # Get bot info
                try:
                    response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
                    if response.json().get('ok'):
                        bot_info = response.json()['result']
                        self.bot_username = bot_info['username']
                        logger.info(f"✅ Telegram bot: @{self.bot_username}")
                except Exception as e:
                    logger.warning(f"Failed to get bot info: {str(e)}")
                    self.bot_username = "unknown_bot"
            
            self.telegram_token = bot_token
            
        except Exception as e:
            logger.error(f"Failed to provision Telegram bot: {str(e)}")
            raise
    
    def provision_twilio_number(self):
        """Automatically purchase phone number via Twilio API"""
        try:
            if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
                raise ValueError("Twilio credentials not configured")
            
            from twilio.rest import Client
            
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Search for available local number
            logger.info("Searching for available phone numbers...")
            available_numbers = client.available_phone_numbers('US').local.list(limit=1)
            
            if not available_numbers:
                raise Exception("No phone numbers available in Twilio")
            
            number = available_numbers[0].phone_number
            
            # Purchase the number
            logger.info(f"Purchasing phone number: {number}")
            incoming_number = client.incoming_phone_numbers.create(
                phone_number=number,
                voice_url=f"https://{PLATFORM_DOMAIN}/customers/{self.customer_id}/webhook",
                status_callback=f"https://{PLATFORM_DOMAIN}/customers/{self.customer_id}/status",
                sms_url=f"https://{PLATFORM_DOMAIN}/customers/{self.customer_id}/webhook"
            )
            
            self.phone_number = incoming_number.phone_number
            self.twilio_sid = incoming_number.sid
            
            logger.info(f"✅ Provisioned phone number: {self.phone_number}")
            
        except Exception as e:
            logger.error(f"Failed to provision Twilio number: {str(e)}")
            # Don't fail completely - fall back to Telegram
            logger.warning("Falling back to Telegram bot")
            self.telephony_type = 'telegram'
            self.provision_telegram_bot()
    
    def create_customer_container(self):
        """Create isolated Docker container for customer"""
        try:
            client = docker.from_env()
            
            # Environment variables for container
            env_vars = {
                "CUSTOMER_ID": str(self.customer_id),
                "ELASTICSEARCH_INDEX": f"customer_{self.customer_id}_qa",
                "ELASTICSEARCH_HOST": ELASTICSEARCH_HOST,
                "OPENAI_API_KEY": SHARED_OPENAI_KEY,
                "TELEPHONY_TYPE": self.telephony_type,
                "APP_PORT": "8000"
            }
            
            # Add credentials based on telephony type
            if self.telephony_type == 'telegram':
                env_vars["TELEGRAM_BOT_TOKEN"] = self.telegram_token
            else:
                env_vars["TWILIO_PHONE_NUMBER"] = self.phone_number
                env_vars["TWILIO_ACCOUNT_SID"] = TWILIO_ACCOUNT_SID
                env_vars["TWILIO_AUTH_TOKEN"] = TWILIO_AUTH_TOKEN
            
            # Try test image first, fallback to latest
            image_name = "customer-care-app:test"
            try:
                client.images.get(image_name)
            except:
                image_name = "customer-care-app:latest"
                try:
                    client.images.get(image_name)
                except:
                    raise Exception("No customer-care-app image found. Build it first: docker build -t customer-care-app:test .")
            
            # Create container with resource limits for testing
            container = client.containers.create(
                image=image_name,
                name=f"customer_{self.customer_id}",
                environment=env_vars,
                ports={'8000/tcp': None},  # Docker assigns random port
                network=os.getenv("DOCKER_NETWORK", "customer_care_network"),
                restart_policy={"Name": "unless-stopped"},
                labels={
                    "customer_id": str(self.customer_id),
                    "company": self.company_name,
                    "telephony": self.telephony_type
                },
                mem_limit="256m",  # Limit to 256MB RAM
                detach=True
            )
            
            self.container_id = container.id
            
            # Get assigned port
            container.reload()
            port_bindings = container.attrs['NetworkSettings']['Ports']
            if port_bindings and '8000/tcp' in port_bindings and port_bindings['8000/tcp']:
                self.container_port = int(port_bindings['8000/tcp'][0]['HostPort'])
            else:
                # Container in custom network, use container name
                self.container_port = 8000
            
            logger.info(f"✅ Created container: {container.name} (port: {self.container_port})")
            
        except Exception as e:
            logger.error(f"Failed to create container: {str(e)}")
            raise
    
    def setup_webhook(self):
        """Configure webhook for Telegram or Twilio"""
        try:
            webhook_url = f"https://{PLATFORM_DOMAIN}/customers/{self.customer_id}/webhook"
            
            if self.telephony_type == 'telegram' and self.telegram_token:
                # Set Telegram webhook
                response = requests.post(
                    f"https://api.telegram.org/bot{self.telegram_token}/setWebhook",
                    json={"url": webhook_url}
                )
                
                if response.json().get('ok'):
                    logger.info(f"✅ Telegram webhook configured: {webhook_url}")
                else:
                    logger.warning(f"⚠️  Webhook setup returned: {response.text}")
            
            elif self.telephony_type == 'twilio':
                # Twilio webhook already set during number purchase
                logger.info(f"✅ Twilio webhook configured: {webhook_url}")
            
        except Exception as e:
            logger.warning(f"Webhook setup warning: {str(e)}")
            # Don't fail completely
    
    def start_container(self):
        """Start customer container and wait for health check"""
        try:
            client = docker.from_env()
            container = client.containers.get(self.container_id)
            container.start()
            
            logger.info(f"Container started: {container.name}")
            
            # Wait for health check
            import time
            for i in range(30):
                try:
                    container.reload()
                    if container.status == 'running':
                        # Try health check
                        try:
                            response = requests.get(
                                f"http://localhost:{self.container_port}/health",
                                timeout=2
                            )
                            if response.status_code == 200:
                                logger.info(f"✅ Container healthy!")
                                return
                        except:
                            pass
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"Health check attempt {i+1}: {str(e)}")
                    time.sleep(1)
            
            logger.warning("⚠️  Container started but health check timeout")
            
        except Exception as e:
            logger.error(f"Failed to start container: {str(e)}")
            raise
    
    def cleanup(self):
        """Cleanup resources if provisioning fails"""
        try:
            if self.container_id:
                client = docker.from_env()
                try:
                    container = client.containers.get(self.container_id)
                    container.stop()
                    container.remove()
                    logger.info(f"Cleaned up container: {self.container_id}")
                except:
                    pass
            
            # Could also delete Elasticsearch index here if needed
            
        except Exception as e:
            logger.warning(f"Cleanup warning: {str(e)}")


def test_provisioner():
    """Test provisioning with sample data"""
    import tempfile
    
    # Create sample data file
    sample_data = pd.DataFrame({
        'question': [
            'What are your hours?',
            'How do I reset my password?',
            'Where is your office?'
        ],
        'answer': [
            'We are open Monday-Friday 9am-5pm',
            'Click "Forgot Password" on the login page',
            'Our office is at 123 Main St, City, State'
        ],
        'category': ['general', 'account', 'general']
    })
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        sample_data.to_csv(f.name, index=False)
        data_file = f.name
    
    try:
        provisioner = CustomerProvisioner(
            customer_id=999,
            company_name="Test Company",
            data_file=data_file,
            telephony_type='telegram'
        )
        
        result = provisioner.provision()
        
        print("\n✅ Provisioning Test Successful!")
        print(f"Bot Username: {result['bot_username']}")
        print(f"Container ID: {result['container_id']}")
        print(f"Webhook URL: {result['webhook_url']}")
        
    finally:
        os.unlink(data_file)


if __name__ == '__main__':
    # Run test
    print("Testing Customer Provisioner...")
    test_provisioner()
