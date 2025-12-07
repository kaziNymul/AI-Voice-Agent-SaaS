"""
SaaS Dashboard Backend - Flask API
Manages customer signup, bot provisioning, and multi-tenant routing
"""

import os
import sys

# Load environment variables from root .env or .env.ultralight (backward compatibility)
env_files = ['.env', '.env.ultralight']
for env_file in env_files:
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Don't overwrite existing env vars (Docker env takes precedence)
                    if key not in os.environ:
                        os.environ[key] = value
        break

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'sqlite:///test_saas.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'change-this-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/customer_uploads')
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB max file size

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    company_name = db.Column(db.String(200))
    password_hash = db.Column(db.String(200), nullable=False)
    subscription_tier = db.Column(db.String(50), default='free')  # free, pro, enterprise
    api_key = db.Column(db.String(100), unique=True)  # For API access
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bots = db.relationship('Bot', backref='customer', lazy=True, cascade='all, delete-orphan')
    analytics = db.relationship('Analytics', backref='customer', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'company_name': self.company_name,
            'subscription_tier': self.subscription_tier,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'bot_count': len([b for b in self.bots if b.status == 'active'])
        }

class Bot(db.Model):
    __tablename__ = 'bots'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    
    # Bot identification
    bot_name = db.Column(db.String(200))
    bot_username = db.Column(db.String(100))  # Telegram username
    phone_number = db.Column(db.String(20))   # Twilio phone number
    
    # Credentials
    telegram_token = db.Column(db.String(200))
    twilio_sid = db.Column(db.String(100))
    
    # Container info
    container_id = db.Column(db.String(100), unique=True)
    container_port = db.Column(db.Integer)
    
    # Data
    elasticsearch_index = db.Column(db.String(100))
    data_file_path = db.Column(db.String(500))
    data_row_count = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, paused, deleted, error
    telephony_type = db.Column(db.String(20))  # telegram, twilio, sip
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'bot_name': self.bot_name,
            'bot_username': self.bot_username,
            'phone_number': self.phone_number,
            'status': self.status,
            'telephony_type': self.telephony_type,
            'data_row_count': self.data_row_count,
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'webhook_url': f"https://{os.getenv('PLATFORM_DOMAIN', 'yourplatform.com')}/customers/{self.customer_id}/webhook"
        }

class Analytics(db.Model):
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bots.id'), nullable=False, index=True)
    
    date = db.Column(db.Date, default=datetime.utcnow, index=True)
    message_count = db.Column(db.Integer, default=0)
    call_count = db.Column(db.Integer, default=0)
    avg_response_time = db.Column(db.Float, default=0)  # seconds
    satisfaction_score = db.Column(db.Float, default=0)  # 0-5
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Subscription limits
SUBSCRIPTION_LIMITS = {
    'free': {
        'max_bots': 1,
        'max_messages_per_month': 1000,
        'max_data_rows': 500,
        'phone_numbers': False
    },
    'pro': {
        'max_bots': 5,
        'max_messages_per_month': 10000,
        'max_data_rows': 5000,
        'phone_numbers': True
    },
    'enterprise': {
        'max_bots': 999,
        'max_messages_per_month': 999999,
        'max_data_rows': 999999,
        'phone_numbers': True
    }
}

# Routes

@app.route('/')
def index():
    """Serve main dashboard page"""
    return render_template('index.html')

@app.route('/dashboard')
@jwt_required(optional=True)
def dashboard():
    """Serve dashboard page for logged-in users"""
    return render_template('dashboard.html')

# Authentication APIs

@app.route('/api/signup', methods=['POST'])
def signup():
    """Register a new customer"""
    try:
        data = request.json
        
        # Validate input
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        # Check if user exists
        if Customer.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create customer
        customer = Customer(
            email=data['email'],
            company_name=data.get('company', ''),
            password_hash=generate_password_hash(data['password']),
            subscription_tier='free'
        )
        
        db.session.add(customer)
        db.session.commit()
        
        logger.info(f"New customer signup: {customer.email}")
        
        # Generate JWT token
        token = create_access_token(identity=customer.id)
        
        return jsonify({
            'message': 'Signup successful',
            'token': token,
            'customer': customer.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Signup failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login existing customer"""
    try:
        data = request.json
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        customer = Customer.query.filter_by(email=data['email']).first()
        
        if not customer or not check_password_hash(customer.password_hash, data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not customer.is_active:
            return jsonify({'error': 'Account deactivated'}), 403
        
        token = create_access_token(identity=customer.id)
        
        logger.info(f"Customer login: {customer.email}")
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'customer': customer.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current logged-in user info"""
    customer_id = get_jwt_identity()
    customer = Customer.query.get(customer_id)
    
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    
    return jsonify({'customer': customer.to_dict()})

# Bot Management APIs

@app.route('/api/customers/<int:customer_id>/upload-data', methods=['POST'])
@jwt_required()
def upload_data(customer_id):
    """Upload Q&A data file"""
    try:
        # Verify ownership
        if get_jwt_identity() != customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = ['.csv', '.json']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Only {", ".join(allowed_extensions)} files allowed'}), 400
        
        # Save file
        filename = f"customer_{customer_id}_data{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Count rows
        try:
            import pandas as pd
            if file_ext == '.csv':
                df = pd.read_csv(filepath)
            else:
                df = pd.read_json(filepath)
            row_count = len(df)
        except:
            row_count = 0
        
        logger.info(f"Customer {customer_id} uploaded data: {row_count} rows")
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filepath': filepath,
            'filename': file.filename,
            'row_count': row_count
        }), 200
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/customers/<int:customer_id>/create-bot', methods=['POST'])
@jwt_required()
def create_bot(customer_id):
    """Create and provision a new bot automatically"""
    try:
        # Verify ownership
        if get_jwt_identity() != customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Check subscription limits
        active_bots = Bot.query.filter_by(customer_id=customer_id, status='active').count()
        limits = SUBSCRIPTION_LIMITS[customer.subscription_tier]
        
        if active_bots >= limits['max_bots']:
            return jsonify({
                'error': f'Bot limit reached ({limits["max_bots"]}). Upgrade your plan.',
                'current_tier': customer.subscription_tier
            }), 403
        
        data = request.json
        bot_name = data.get('bot_name', f"{customer.company_name} Support Bot")
        telephony_type = data.get('telephony_type', 'telegram')  # telegram or twilio
        
        # Check if phone numbers allowed
        if telephony_type == 'twilio' and not limits['phone_numbers']:
            return jsonify({
                'error': 'Phone numbers not available in free tier. Upgrade to Pro.',
                'current_tier': customer.subscription_tier
            }), 403
        
        # Find uploaded data file
        data_file = None
        for ext in ['.csv', '.json']:
            path = os.path.join(app.config['UPLOAD_FOLDER'], f"customer_{customer_id}_data{ext}")
            if os.path.exists(path):
                data_file = path
                break
        
        if not data_file:
            return jsonify({'error': 'No data file found. Upload data first.'}), 400
        
        # Import provisioner
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from automation.provision_customer import CustomerProvisioner
        
        # Provision bot automatically
        logger.info(f"Starting bot provisioning for customer {customer_id}")
        
        provisioner = CustomerProvisioner(
            customer_id=customer_id,
            company_name=bot_name,
            data_file=data_file,
            telephony_type=telephony_type
        )
        
        result = provisioner.provision()
        
        # Save bot to database
        bot = Bot(
            customer_id=customer_id,
            bot_name=bot_name,
            bot_username=result.get('bot_username'),
            phone_number=result.get('phone_number'),
            telegram_token=result.get('telegram_token'),
            twilio_sid=result.get('twilio_sid'),
            container_id=result.get('container_id'),
            container_port=result.get('container_port'),
            elasticsearch_index=f"customer_{customer_id}_qa",
            data_file_path=data_file,
            data_row_count=result.get('data_row_count', 0),
            status='active',
            telephony_type=telephony_type
        )
        
        db.session.add(bot)
        db.session.commit()
        
        logger.info(f"Bot created successfully: {bot.id} for customer {customer_id}")
        
        return jsonify({
            'message': 'Bot created successfully! It\'s live now.',
            'bot': bot.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Bot creation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Bot creation failed: {str(e)}'}), 500

@app.route('/api/customers/<int:customer_id>/bots', methods=['GET'])
@jwt_required()
def get_customer_bots(customer_id):
    """Get all bots for a customer"""
    try:
        # Verify ownership
        if get_jwt_identity() != customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        bots = Bot.query.filter_by(customer_id=customer_id).order_by(Bot.created_at.desc()).all()
        
        return jsonify({
            'bots': [bot.to_dict() for bot in bots],
            'count': len(bots)
        }), 200
        
    except Exception as e:
        logger.error(f"Get bots error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve bots'}), 500

@app.route('/api/customers/<int:customer_id>/bots/<int:bot_id>', methods=['GET'])
@jwt_required()
def get_bot(customer_id, bot_id):
    """Get specific bot details"""
    try:
        # Verify ownership
        if get_jwt_identity() != customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        bot = Bot.query.filter_by(id=bot_id, customer_id=customer_id).first()
        
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        return jsonify({'bot': bot.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Get bot error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve bot'}), 500

@app.route('/api/customers/<int:customer_id>/bots/<int:bot_id>', methods=['DELETE'])
@jwt_required()
def delete_bot(customer_id, bot_id):
    """Delete a bot and stop its container"""
    try:
        # Verify ownership
        if get_jwt_identity() != customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        bot = Bot.query.filter_by(id=bot_id, customer_id=customer_id).first()
        
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Stop and remove container
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(bot.container_id)
            container.stop()
            container.remove()
            logger.info(f"Container stopped and removed: {bot.container_id}")
        except Exception as e:
            logger.warning(f"Failed to stop container: {str(e)}")
        
        # Mark as deleted
        bot.status = 'deleted'
        db.session.commit()
        
        logger.info(f"Bot deleted: {bot_id} for customer {customer_id}")
        
        return jsonify({'message': 'Bot deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Delete bot error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete bot'}), 500

# Analytics APIs

@app.route('/api/customers/<int:customer_id>/analytics', methods=['GET'])
@jwt_required()
def get_analytics(customer_id):
    """Get analytics for customer's bots"""
    try:
        # Verify ownership
        if get_jwt_identity() != customer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get date range
        days = int(request.args.get('days', 7))
        
        # TODO: Implement real analytics from container logs or analytics DB
        # For now, return mock data
        
        return jsonify({
            'total_messages': 1523,
            'today_messages': 87,
            'avg_response_time': 2.3,
            'satisfaction_rate': 92,
            'top_questions': [
                {'question': 'How do I reset my password?', 'count': 45},
                {'question': 'What are your hours?', 'count': 38},
                {'question': 'How do I contact support?', 'count': 32}
            ],
            'messages_by_day': [
                {'date': '2025-12-01', 'count': 234},
                {'date': '2025-12-02', 'count': 198},
                {'date': '2025-12-03', 'count': 267},
                {'date': '2025-12-04', 'count': 245},
                {'date': '2025-12-05', 'count': 289},
                {'date': '2025-12-06', 'count': 290}
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve analytics'}), 500

# Webhook Routing (Multi-tenant)

@app.route('/customers/<int:customer_id>/webhook', methods=['POST', 'GET'])
def customer_webhook(customer_id):
    """Route webhooks to customer's container"""
    try:
        bot = Bot.query.filter_by(customer_id=customer_id, status='active').first()
        
        if not bot:
            logger.warning(f"No active bot for customer {customer_id}")
            return jsonify({'error': 'Bot not found'}), 404
        
        # Forward to customer's container
        import requests
        
        # Use localhost with mapped port since dashboard runs on host
        url = f"http://localhost:{bot.container_port}/telegram/webhook"
        
        if request.method == 'POST':
            response = requests.post(
                url,
                json=request.json,
                headers={'X-Customer-ID': str(customer_id)}
            )
        else:
            response = requests.get(
                url,
                params=request.args,
                headers={'X-Customer-ID': str(customer_id)}
            )
        
        # Update last_active
        bot.last_active = datetime.utcnow()
        db.session.commit()
        
        return response.content, response.status_code, dict(response.headers)
        
    except Exception as e:
        logger.error(f"Webhook routing error: {str(e)}")
        return jsonify({'error': 'Webhook failed'}), 500

# Health check

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'saas-dashboard',
        'timestamp': datetime.utcnow().isoformat()
    })

# Database initialization

def init_db():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Run app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting SaaS Dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
