# Makefile for AI Voice Customer Care
# Usage: make [target]

.PHONY: help gui setup local aws openai clean logs stop

SHELL := /bin/bash
DEPLOYMENT ?= local

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

help:
	@echo ""
	@echo "$(BLUE)AI Voice Customer Care - Deployment Commands$(NC)"
	@echo "=============================================="
	@echo ""
	@echo "$(GREEN)🎯 Easiest Way (Recommended):$(NC)"
	@echo "  make web-ui        - 🌐 Web-based setup wizard (browser UI)"
	@echo "  ./setup.sh         - 💻 Command-line wizard (CLI)"
	@echo ""
	@echo "$(GREEN)Quick Deploy (if .env configured):$(NC)"
	@echo "  make local         - Deploy with free local AI models"
	@echo "  make aws           - Deploy with AWS services (Bedrock, Transcribe, Polly)"
	@echo "  make openai        - Deploy with OpenAI services (GPT-4, Whisper, TTS)"
	@echo "  make saas          - Deploy multi-tenant SaaS platform"
	@echo ""
	@echo "$(GREEN)Management:$(NC)"
	@echo "  make logs          - View logs for current deployment"
	@echo "  make stop          - Stop all services"
	@echo "  make clean         - Remove all containers and volumes"
	@echo ""
	@echo "$(GREEN)Local Testing (Webhooks):$(NC)"
	@echo "  make ngrok         - Start ngrok tunnel for local webhook testing"
	@echo "  make ngrok-setup   - Install and configure ngrok"
	@echo ""

web-ui:
	@echo "$(BLUE)🌐 Launching Web-Based Setup Wizard...$(NC)"
	@if ! command -v python3 &> /dev/null; then \
		echo "$(YELLOW)⚠️  Python 3 is required. Please install Python 3.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Starting web server on http://localhost:8080$(NC)"
	@echo "$(BLUE)📱 Open your browser to http://localhost:8080$(NC)"
	@echo ""
	@python3 setup_web_ui.py

local:
	@echo "$(GREEN)Deploying with local AI models...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠️  .env file not found. Copying from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠️  Please edit .env file and set TELEGRAM_BOT_TOKEN$(NC)"; \
		exit 1; \
	fi
	@cd deployments/local && ./setup.sh
	@echo "$(GREEN)✅ Local deployment complete!$(NC)"
	@echo "$(BLUE)Access your bot at: http://localhost:8001$(NC)"

aws:
	@echo "$(GREEN)Deploying with AWS services...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠️  .env file not found. Copying from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠️  Please edit .env and set AWS credentials$(NC)"; \
		exit 1; \
	fi
	@cd deployments/aws && ./setup.sh
	@echo "$(GREEN)✅ AWS deployment complete!$(NC)"
	@echo "$(BLUE)Access your bot at: http://localhost:8001$(NC)"

openai:
	@echo "$(GREEN)Deploying with OpenAI services...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠️  .env file not found. Copying from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠️  Please edit .env and set OPENAI_API_KEY$(NC)"; \
		exit 1; \
	fi
	@cd deployments/openai && ./setup.sh
	@echo "$(GREEN)✅ OpenAI deployment complete!$(NC)"
	@echo "$(BLUE)Access your bot at: http://localhost:8001$(NC)"saas:
	@echo "$(GREEN)Deploying SaaS platform...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)⚠️  .env file not found. Copying from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠️  Please edit .env and set SaaS variables$(NC)"; \
		exit 1; \
	fi
	@cd deployments/saas && ./setup.sh
	@echo "$(GREEN)✅ SaaS platform deployed!$(NC)"
	@echo "$(BLUE)Access dashboard at: http://localhost:5000$(NC)"

logs:
	@echo "$(BLUE)Viewing logs...$(NC)"
	@if [ -f deployments/local/docker-compose.yml ] && docker-compose -f deployments/local/docker-compose.yml ps | grep -q Up; then \
		cd deployments/local && docker-compose logs -f; \
	elif [ -f deployments/aws/docker-compose.yml ] && docker-compose -f deployments/aws/docker-compose.yml ps | grep -q Up; then \
		cd deployments/aws && docker-compose logs -f; \
	elif [ -f deployments/openai/docker-compose.yml ] && docker-compose -f deployments/openai/docker-compose.yml ps | grep -q Up; then \
		cd deployments/openai && docker-compose logs -f; \
	else \
		echo "$(YELLOW)No running deployment found$(NC)"; \
	fi

stop:
	@echo "$(YELLOW)Stopping all deployments...$(NC)"
	@-cd deployments/local && docker-compose down 2>/dev/null || true
	@-cd deployments/aws && docker-compose down 2>/dev/null || true
	@-cd deployments/openai && docker-compose down 2>/dev/null || true
	@echo "$(GREEN)✅ All deployments stopped$(NC)"

clean:
	@echo "$(YELLOW)Cleaning up all deployments...$(NC)"
	@-cd deployments/local && docker-compose down -v 2>/dev/null || true
	@-cd deployments/aws && docker-compose down -v 2>/dev/null || true
	@-cd deployments/openai && docker-compose down -v 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

test-local:
	@echo "$(BLUE)Testing local deployment...$(NC)"
	@curl -s http://localhost:8001/health | jq . || echo "$(YELLOW)Bot not responding$(NC)"

test-rag:
	@echo "$(BLUE)Testing RAG retrieval...$(NC)"
	@curl -s -X POST "http://localhost:8001/admin/test-rag?query=test" | jq . || echo "$(YELLOW)RAG test failed$(NC)"

ngrok:
	@echo "$(BLUE)🌐 Starting ngrok tunnel for local testing...$(NC)"
	@echo ""
	@./scripts/start_ngrok.sh 8000

ngrok-setup:
	@echo "$(BLUE)📥 Setting up ngrok...$(NC)"
	@./scripts/setup_ngrok.sh

.DEFAULT_GOAL := help
