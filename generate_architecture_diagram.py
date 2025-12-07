"""
Generate beautiful architecture diagrams for AI Voice Agent SaaS
Creates PNG files showing complete system architecture with all dependencies
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Color scheme
COLORS = {
    'bg': '#FFFFFF',
    'header': '#2C3E50',
    'channel': '#3498DB',
    'audio': '#E74C3C',
    'ai': '#9B59B6',
    'database': '#1ABC9C',
    'saas': '#F39C12',
    'text': '#2C3E50',
    'border': '#BDC3C7',
    'local': '#27AE60',
    'aws': '#FF9900',
    'openai': '#10A37F',
}

def create_main_architecture():
    """Create the main system architecture diagram"""
    
    # Image size
    width = 2400
    height = 3200
    
    # Create image
    img = Image.new('RGB', (width, height), COLORS['bg'])
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts, fallback to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        section_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    y_offset = 50
    margin = 100
    
    # Title
    draw.text((width//2, y_offset), "AI Voice Agent SaaS - System Architecture", 
              fill=COLORS['header'], font=title_font, anchor="mt")
    y_offset += 100
    
    # === LAYER 1: User Interaction Channels ===
    draw_section_header(draw, margin, y_offset, width-2*margin, 80, 
                       "USER INTERACTION CHANNELS", COLORS['channel'], header_font)
    y_offset += 100
    
    # Three channels
    channel_width = (width - 2*margin - 80) // 3
    channels = [
        ("Telegram", "Text/Voice", "Polling/Webhook"),
        ("Twilio", "Voice Calls", "Webhook (Public URL)"),
        ("SIP Trunk", "Voice Calls", "Webhook (Public URL)")
    ]
    
    x = margin
    for channel, type1, type2 in channels:
        draw_box(draw, x, y_offset, channel_width, 120, COLORS['channel'], 
                channel, [type1, type2], section_font, small_font)
        # Arrow down
        draw_arrow_down(draw, x + channel_width//2, y_offset + 120, 50)
        x += channel_width + 40
    
    y_offset += 200
    
    # === LAYER 2: FastAPI Application ===
    draw_section_header(draw, margin, y_offset, width-2*margin, 80,
                       "FASTAPI APPLICATION (Port 8000)", COLORS['header'], header_font)
    y_offset += 100
    
    # Routing layer
    route_width = (width - 2*margin - 80) // 3
    routes = [
        ("/telegram", "telegram.py"),
        ("/phone", "phone.py"),
        ("/sip", "sip_routes.py")
    ]
    
    x = margin
    for route, file in routes:
        draw_box(draw, x, y_offset, route_width, 80, COLORS['header'],
                route, [file], section_font, small_font)
        # Arrow down
        draw_arrow_down(draw, x + route_width//2, y_offset + 80, 30)
        x += route_width + 40
    
    y_offset += 140
    
    # === LAYER 3: Audio Processing ===
    draw_section_header(draw, margin, y_offset, width-2*margin, 60,
                       "AUDIO PROCESSING (Voice Only)", COLORS['audio'], header_font)
    y_offset += 80
    
    # STT Section
    draw.text((margin + 20, y_offset), "Speech-to-Text (STT)", 
              fill=COLORS['text'], font=section_font)
    y_offset += 40
    
    stt_width = (width - 2*margin - 80) // 3
    stt_options = [
        ("Local Whisper", ["base model", "140MB", "Offline", "Free"], COLORS['local']),
        ("AWS Transcribe", ["Neural", "$0.024/min", "Online", "High quality"], COLORS['aws']),
        ("OpenAI Whisper", ["whisper-1", "$0.006/min", "Online", "Best quality"], COLORS['openai'])
    ]
    
    x = margin
    for name, details, color in stt_options:
        draw_box(draw, x, y_offset, stt_width, 120, color, name, details, section_font, small_font)
        x += stt_width + 40
    
    y_offset += 150
    
    # TTS Section
    draw.text((margin + 20, y_offset), "Text-to-Speech (TTS)", 
              fill=COLORS['text'], font=section_font)
    y_offset += 40
    
    tts_options = [
        ("Local MMS-TTS", ["Facebook", "Free", "Multi-language", "Offline"], COLORS['local']),
        ("AWS Polly", ["Neural", "$16/1M chars", "Online", "Natural"], COLORS['aws']),
        ("OpenAI TTS-1-HD", ["$15/1M chars", "High quality", "Low latency", "Online"], COLORS['openai'])
    ]
    
    x = margin
    for name, details, color in tts_options:
        draw_box(draw, x, y_offset, stt_width, 120, color, name, details, section_font, small_font)
        x += stt_width + 40
    
    y_offset += 150
    
    # Central arrow down
    draw_arrow_down(draw, width//2, y_offset, 50)
    y_offset += 70
    
    # === LAYER 4: AI Processing ===
    draw_section_header(draw, margin, y_offset, width-2*margin, 60,
                       "AI TEXT PROCESSING", COLORS['ai'], header_font)
    y_offset += 80
    
    # LLM Section
    draw.text((margin + 20, y_offset), "Large Language Model (Text Generation)", 
              fill=COLORS['text'], font=section_font)
    y_offset += 40
    
    llm_options = [
        ("Ollama Local", ["TinyLlama", "1GB RAM", "Free", "Offline"], COLORS['local']),
        ("AWS Bedrock", ["Claude 3 Haiku", "$0.00025/1K tok", "Fast", "Enterprise"], COLORS['aws']),
        ("OpenAI GPT-4", ["gpt-4-turbo", "$0.01/1K tok", "Best quality", "Fast"], COLORS['openai'])
    ]
    
    x = margin
    for name, details, color in llm_options:
        draw_box(draw, x, y_offset, stt_width, 120, color, name, details, section_font, small_font)
        x += stt_width + 40
    
    y_offset += 150
    
    # Embeddings Section
    draw.text((margin + 20, y_offset), "Embeddings (Vector Representation)", 
              fill=COLORS['text'], font=section_font)
    y_offset += 40
    
    emb_options = [
        ("Sentence Trans.", ["all-MiniLM", "Free", "Offline", "384d vectors"], COLORS['local']),
        ("AWS Titan", ["Titan Embeddings", "$0.0001/1K tok", "768d vectors", "Scalable"], COLORS['aws']),
        ("OpenAI Embed", ["text-embed-3-small", "$0.00002/1K tok", "1536d vectors", "Accurate"], COLORS['openai'])
    ]
    
    x = margin
    for name, details, color in emb_options:
        draw_box(draw, x, y_offset, stt_width, 120, color, name, details, section_font, small_font)
        x += stt_width + 40
    
    y_offset += 150
    
    # RAG Process
    draw_arrow_down(draw, width//2, y_offset, 50)
    y_offset += 70
    
    rag_box_height = 150
    draw_rounded_rect(draw, margin, y_offset, width-2*margin, rag_box_height, 
                     20, COLORS['ai'], COLORS['border'])
    draw.text((width//2, y_offset + 20), "RAG SERVICE (Retrieval Augmented Generation)", 
              fill='white', font=section_font, anchor="mt")
    
    rag_steps = [
        "1. User Question → Generate Embedding",
        "2. Search Vector DB for Similar Content",
        "3. Retrieve Top 3-5 Relevant Documents",
        "4. Inject Context into LLM Prompt",
        "5. LLM Generates Answer with Knowledge"
    ]
    
    step_y = y_offset + 60
    for step in rag_steps:
        draw.text((margin + 30, step_y), step, fill='white', font=small_font)
        step_y += 25
    
    y_offset += rag_box_height + 50
    
    # === LAYER 5: Vector Database ===
    draw_arrow_down(draw, width//2, y_offset, 50)
    y_offset += 70
    
    draw_section_header(draw, margin, y_offset, width-2*margin, 60,
                       "VECTOR DATABASE", COLORS['database'], header_font)
    y_offset += 80
    
    db_options = [
        ("Elasticsearch", ["Local/Docker", "Free", "Self-hosted", "8GB+ RAM", "Full control"], COLORS['local']),
        ("OpenSearch", ["AWS Managed", "$50-500/mo", "Auto-scaling", "High availability", "Enterprise"], COLORS['aws']),
        ("OpenAI Vectors", ["Cloud API", "$0.10/GB/mo", "Serverless", "No setup", "Pay-per-use"], COLORS['openai'])
    ]
    
    x = margin
    db_width = (width - 2*margin - 80) // 3
    for name, details, color in db_options:
        draw_box(draw, x, y_offset, db_width, 150, color, name, details, section_font, small_font)
        x += db_width + 40
    
    y_offset += 180
    
    # === LAYER 6: Auto-Learning ===
    draw_arrow_down(draw, width//2, y_offset, 50)
    y_offset += 70
    
    learning_height = 180
    draw_rounded_rect(draw, margin, y_offset, width-2*margin, learning_height,
                     20, COLORS['database'], COLORS['border'])
    draw.text((width//2, y_offset + 20), "AUTO-LEARNING & FEEDBACK SYSTEM", 
              fill='white', font=section_font, anchor="mt")
    
    learning_info = [
        "Every conversation stored with embeddings",
        "Searches past conversations for similar questions",
        "Reuses proven answers (similarity > 0.85)",
        "New answers stored for future learning",
        "Cross-channel learning (Telegram ↔ Phone ↔ SIP)",
        "Promoted answers become knowledge base"
    ]
    
    info_y = y_offset + 60
    for info in learning_info:
        draw.text((margin + 30, info_y), f"• {info}", fill='white', font=small_font)
        info_y += 22
    
    y_offset += learning_height + 50
    
    # === LAYER 7: SaaS Platform ===
    draw_arrow_down(draw, width//2, y_offset, 50)
    y_offset += 70
    
    draw_section_header(draw, margin, y_offset, width-2*margin, 60,
                       "OPTIONAL: SAAS PLATFORM (Port 5000)", COLORS['saas'], header_font)
    y_offset += 80
    
    # PostgreSQL + Dashboard
    saas_width = (width - 2*margin - 40) // 2
    
    # PostgreSQL
    pg_details = [
        "Customer accounts",
        "Bot configurations",
        "Analytics data",
        "Document metadata",
        "Conversation logs"
    ]
    draw_box(draw, margin, y_offset, saas_width, 140, COLORS['saas'],
            "PostgreSQL Database", pg_details, section_font, small_font)
    
    # Flask Dashboard
    dash_details = [
        "Customer signup",
        "Data upload (PDF/CSV)",
        "Analytics dashboard",
        "Isolated per customer",
        "Auto-provision bots"
    ]
    draw_box(draw, margin + saas_width + 40, y_offset, saas_width, 140, COLORS['saas'],
            "Flask Web Dashboard", dash_details, section_font, small_font)
    
    y_offset += 160
    
    # Footer
    draw.text((width//2, y_offset + 20), 
              "Production-ready AI Customer Care • Telegram • Twilio • SIP Trunk • RAG • Auto-learning",
              fill=COLORS['border'], font=small_font, anchor="mt")
    
    # Save
    img.save('docs/architecture-main.png', 'PNG', quality=95, optimize=True)
    print("✅ Created: docs/architecture-main.png")


def create_deployment_comparison():
    """Create deployment paths comparison diagram"""
    
    width = 2400
    height = 2000
    
    img = Image.new('RGB', (width, height), COLORS['bg'])
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        section_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        title_font = header_font = section_font = text_font = ImageFont.load_default()
    
    y_offset = 50
    margin = 80
    
    # Title
    draw.text((width//2, y_offset), "Deployment Options Comparison", 
              fill=COLORS['header'], font=title_font, anchor="mt")
    y_offset += 100
    
    # Three deployment columns
    col_width = (width - 2*margin - 80) // 3
    deployments = [
        ("LOCAL DEVELOPMENT", COLORS['local'], [
            "Docker Containers:",
            "• Elasticsearch:8.8.0",
            "• Ollama/ollama:latest",
            "• Customer-care-bot",
            "• Voice-service (optional)",
            "",
            "AI Services:",
            "• Whisper (140MB)",
            "• MMS-TTS",
            "• TinyLlama (1GB)",
            "• Sentence-Transformers",
            "",
            "Channels:",
            "✅ Telegram (polling)",
            "⚠️ Twilio (needs ngrok)",
            "⚠️ SIP (needs ngrok)",
            "",
            "Cost: $0/month",
            "Setup: 5 minutes",
            "RAM: 8GB minimum"
        ]),
        ("AWS CLOUD", COLORS['aws'], [
            "AWS Services:",
            "• Bedrock (Claude 3)",
            "• Transcribe (Neural)",
            "• Polly (Neural voices)",
            "• OpenSearch (Vector DB)",
            "• Titan Embeddings",
            "",
            "Infrastructure:",
            "• EC2 t3.medium",
            "• Load Balancer",
            "• Route 53 DNS",
            "• Certificate Manager",
            "",
            "Channels:",
            "✅ Telegram (webhook)",
            "✅ Twilio (webhook)",
            "✅ SIP (webhook)",
            "",
            "Cost: ~$20-40/month",
            "Per call: ~$0.02",
            "Scalability: Excellent"
        ]),
        ("OPENAI CLOUD", COLORS['openai'], [
            "OpenAI Services:",
            "• GPT-4 Turbo",
            "• Whisper API",
            "• TTS-1-HD",
            "• text-embedding-3-small",
            "",
            "Infrastructure:",
            "• Any cloud (AWS/DO)",
            "• Nginx + SSL",
            "• Domain with HTTPS",
            "• Elasticsearch (Docker)",
            "",
            "Channels:",
            "✅ Telegram (webhook)",
            "✅ Twilio (webhook)",
            "✅ SIP (webhook)",
            "",
            "Cost: ~$20-50/month",
            "Per call: ~$0.02-0.05",
            "Quality: Best"
        ])
    ]
    
    x = margin
    for title, color, details in deployments:
        # Header
        draw_rounded_rect(draw, x, y_offset, col_width, 60, 15, color, COLORS['border'])
        draw.text((x + col_width//2, y_offset + 30), title, 
                 fill='white', font=header_font, anchor="mm")
        
        # Content box
        content_y = y_offset + 70
        content_height = 850
        draw_rounded_rect(draw, x, content_y, col_width, content_height, 15, 
                         'white', color, border_width=3)
        
        # Details
        detail_y = content_y + 20
        for detail in details:
            if detail == "":
                detail_y += 10
                continue
            
            if detail.endswith(":"):
                font = section_font
                color_text = color
            elif detail.startswith("✅") or detail.startswith("⚠️"):
                font = text_font
                color_text = COLORS['text']
            elif detail.startswith("Cost:") or detail.startswith("Per call:"):
                font = section_font
                color_text = COLORS['header']
            else:
                font = text_font
                color_text = COLORS['text']
            
            draw.text((x + 20, detail_y), detail, fill=color_text, font=font)
            detail_y += 25
        
        x += col_width + 40
    
    y_offset += 950
    
    # Recommendation section
    draw_section_header(draw, margin, y_offset, width-2*margin, 50,
                       "CHOOSE YOUR PATH", COLORS['header'], header_font)
    y_offset += 70
    
    recommendations = [
        ("Testing/Development", "→ Local Development", COLORS['local']),
        ("Startup/MVP", "→ OpenAI Cloud", COLORS['openai']),
        ("Enterprise/Scale", "→ AWS Cloud", COLORS['aws']),
        ("Best Quality", "→ OpenAI Cloud", COLORS['openai']),
        ("Budget Conscious", "→ Local Development", COLORS['local']),
        ("Privacy Critical", "→ Local Development", COLORS['local'])
    ]
    
    rec_width = (width - 2*margin - 40) // 2
    rec_x = margin
    rec_row = 0
    
    for use_case, recommendation, color in recommendations:
        rec_y = y_offset + (rec_row // 2) * 60
        rec_col_x = rec_x if rec_row % 2 == 0 else rec_x + rec_width + 40
        
        draw_rounded_rect(draw, rec_col_x, rec_y, rec_width, 50, 10, color, COLORS['border'])
        draw.text((rec_col_x + 20, rec_y + 25), 
                 f"{use_case} {recommendation}", fill='white', font=text_font, anchor="lm")
        
        rec_row += 1
    
    # Save
    img.save('docs/architecture-deployments.png', 'PNG', quality=95, optimize=True)
    print("✅ Created: docs/architecture-deployments.png")


def draw_rounded_rect(draw, x, y, width, height, radius, fill, outline, border_width=2):
    """Draw a rounded rectangle"""
    draw.rectangle([x + radius, y, x + width - radius, y + height], fill=fill)
    draw.rectangle([x, y + radius, x + width, y + height - radius], fill=fill)
    draw.pieslice([x, y, x + 2*radius, y + 2*radius], 180, 270, fill=fill)
    draw.pieslice([x + width - 2*radius, y, x + width, y + 2*radius], 270, 360, fill=fill)
    draw.pieslice([x, y + height - 2*radius, x + 2*radius, y + height], 90, 180, fill=fill)
    draw.pieslice([x + width - 2*radius, y + height - 2*radius, x + width, y + height], 0, 90, fill=fill)
    
    # Draw outline
    draw.arc([x, y, x + 2*radius, y + 2*radius], 180, 270, fill=outline, width=border_width)
    draw.arc([x + width - 2*radius, y, x + width, y + 2*radius], 270, 360, fill=outline, width=border_width)
    draw.arc([x, y + height - 2*radius, x + 2*radius, y + height], 90, 180, fill=outline, width=border_width)
    draw.arc([x + width - 2*radius, y + height - 2*radius, x + width, y + height], 0, 90, fill=outline, width=border_width)
    draw.line([x + radius, y, x + width - radius, y], fill=outline, width=border_width)
    draw.line([x + radius, y + height, x + width - radius, y + height], fill=outline, width=border_width)
    draw.line([x, y + radius, x, y + height - radius], fill=outline, width=border_width)
    draw.line([x + width, y + radius, x + width, y + height - radius], fill=outline, width=border_width)


def draw_box(draw, x, y, width, height, color, title, details, title_font, detail_font):
    """Draw a component box"""
    draw_rounded_rect(draw, x, y, width, height, 10, color, COLORS['border'], 2)
    
    # Title
    draw.text((x + width//2, y + 20), title, fill='white', font=title_font, anchor="mt")
    
    # Details
    detail_y = y + 50
    for detail in details:
        draw.text((x + width//2, detail_y), detail, fill='white', font=detail_font, anchor="mt")
        detail_y += 20


def draw_section_header(draw, x, y, width, height, text, color, font):
    """Draw a section header"""
    draw_rounded_rect(draw, x, y, width, height, 15, color, COLORS['border'], 3)
    draw.text((x + width//2, y + height//2), text, fill='white', font=font, anchor="mm")


def draw_arrow_down(draw, x, y, length):
    """Draw a downward arrow"""
    draw.line([x, y, x, y + length], fill=COLORS['border'], width=4)
    draw.polygon([x, y + length, x - 10, y + length - 15, x + 10, y + length - 15], 
                fill=COLORS['border'])


if __name__ == "__main__":
    # Create docs directory
    os.makedirs('docs', exist_ok=True)
    
    print("🎨 Generating architecture diagrams...")
    print("=" * 60)
    
    create_main_architecture()
    create_deployment_comparison()
    
    print("=" * 60)
    print("✅ All diagrams created successfully!")
    print("\nGenerated files:")
    print("  📊 docs/architecture-main.png (Complete system architecture)")
    print("  📊 docs/architecture-deployments.png (Deployment comparison)")
    print("\nYou can now add these to your README.md!")
