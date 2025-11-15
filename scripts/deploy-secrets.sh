#!/bin/bash

# =============================================================================
# ONYX Production Secrets Deployment Script
# =============================================================================
# This script creates and manages Docker secrets for production deployment
# Usage: ./scripts/deploy-secrets.sh [create|list|remove|validate]
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    echo -e "${BLUE}ONYX Production Secrets Management${NC}"
    echo "====================================="
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  create   Create all required Docker secrets from user input"
    echo "  list     List existing Docker secrets"
    echo "  remove   Remove all ONYX Docker secrets"
    echo "  validate Validate that all required secrets exist"
    echo "  help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 create                    # Create all secrets interactively"
    echo "  $0 validate                  # Check all secrets exist"
    echo "  $0 list                      # List existing secrets"
    echo ""
}

# Function to validate all required secrets exist
validate_secrets() {
    echo -e "${BLUE}🔍 Validating required Docker secrets...${NC}"

    local required_secrets=(
        "postgres_password"
        "redis_password"
        "grafana_password"
        "encryption_key"
        "session_secret"
        "google_client_id"
        "google_client_secret"
        "together_api_key"
        "deepseek_api_key"
        "qdrant_api_key"
    )

    local missing_secrets=()
    local existing_secrets=()

    for secret in "${required_secrets[@]}"; do
        if docker secret ls --format "{{.Name}}" | grep -q "^${secret}$"; then
            existing_secrets+=("$secret")
            echo -e "  ${GREEN}✅ $secret${NC}"
        else
            missing_secrets+=("$secret")
            echo -e "  ${RED}❌ $secret${NC}"
        fi
    done

    echo ""
    if [ ${#missing_secrets[@]} -eq 0 ]; then
        echo -e "${GREEN}🎉 All required secrets exist!${NC}"
        echo -e "${GREEN}📊 Total secrets: ${#existing_secrets[@]}${NC}"
        return 0
    else
        echo -e "${RED}❌ Missing ${#missing_secrets[@]} required secrets${NC}"
        echo -e "${YELLOW}💡 Run '$0 create' to create missing secrets${NC}"
        return 1
    fi
}

# Function to list all Docker secrets
list_secrets() {
    echo -e "${BLUE}📋 Listing Docker secrets...${NC}"

    # Get all ONYX-related secrets
    local onyx_secrets=$(docker secret ls --format "{{.Name}}" | grep -E "postgres|redis|grafana|encryption|session|google|together|deepseek|qdrant" || true)

    if [ -z "$onyx_secrets" ]; then
        echo -e "${YELLOW}⚠️  No ONYX secrets found${NC}"
        return 0
    fi

    echo -e "${BLUE}ONYX Secrets:${NC}"
    echo "$onyx_secrets" | while read -r secret; do
        echo -e "  ${GREEN}• $secret${NC}"
    done
    echo ""

    # Get total count
    local count=$(echo "$onyx_secrets" | wc -l)
    echo -e "${BLUE}Total: $count secrets${NC}"
}

# Function to remove all ONYX secrets
remove_secrets() {
    echo -e "${YELLOW}⚠️  WARNING: This will remove ALL ONYX Docker secrets!${NC}"
    echo -e "${YELLOW}This cannot be undone and will break production deployment.${NC}"
    echo ""

    read -p "Are you sure you want to continue? (Type 'yes' to confirm): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${BLUE}❌ Operation cancelled${NC}"
        return 0
    fi

    echo -e "${BLUE}🗑️  Removing ONYX Docker secrets...${NC}"

    local onyx_secrets=$(docker secret ls --format "{{.Name}}" | grep -E "postgres|redis|grafana|encryption|session|google|together|deepseek|qdrant" || true)

    if [ -z "$onyx_secrets" ]; then
        echo -e "${YELLOW}⚠️  No ONYX secrets found to remove${NC}"
        return 0
    fi

    local removed_count=0
    echo "$onyx_secrets" | while read -r secret; do
        echo -e "  ${YELLOW}Removing: $secret${NC}"
        docker secret rm "$secret" 2>/dev/null || echo -e "  ${RED}Failed to remove: $secret${NC}"
        ((removed_count++))
    done

    echo ""
    echo -e "${GREEN}✅ Secrets removal completed${NC}"
    echo -e "${YELLOW}💡 Run '$0 create' to create fresh secrets${NC}"
}

# Function to generate secure random values
generate_password() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

generate_hex_key() {
    local length=${1:-32}
    openssl rand -hex $length
}

# Function to create secrets interactively
create_secrets() {
    echo -e "${BLUE}🔐 Creating ONYX Docker Secrets${NC}"
    echo "==================================="
    echo -e "${YELLOW}Please provide values for all required secrets.${NC}"
    echo -e "${YELLOW}These will be stored as Docker secrets for production use.${NC}"
    echo ""

    # PostgreSQL password
    echo -e "${BLUE}📊 PostgreSQL Database${NC}"
    read -s -p "Enter PostgreSQL password (or press Enter to generate): " postgres_password
    if [ -z "$postgres_password" ]; then
        postgres_password=$(generate_password 24)
        echo -e "${YELLOW}Generated: $postgres_password${NC}"
    fi
    echo "$postgres_password" | docker secret create postgres_password -

    # Redis password
    echo -e "\n${BLUE}🔴 Redis Cache${NC}"
    read -s -p "Enter Redis password (or press Enter to generate): " redis_password
    if [ -z "$redis_password" ]; then
        redis_password=$(generate_password 20)
        echo -e "${YELLOW}Generated: $redis_password${NC}"
    fi
    echo "$redis_password" | docker secret create redis_password -

    # Grafana password
    echo -e "\n${BLUE}📈 Grafana Monitoring${NC}"
    read -s -p "Enter Grafana admin password (or press Enter to generate): " grafana_password
    if [ -z "$grafana_password" ]; then
        grafana_password=$(generate_password 16)
        echo -e "${YELLOW}Generated: $grafana_password${NC}"
    fi
    echo "$grafana_password" | docker secret create grafana_password -

    # Encryption key (32-byte hex required)
    echo -e "\n${BLUE}🔐 Application Encryption${NC}"
    read -p "Enter 32-byte hex encryption key (or press Enter to generate): " encryption_key
    if [ -z "$encryption_key" ]; then
        encryption_key=$(generate_hex_key 32)
        echo -e "${YELLOW}Generated: $encryption_key${NC}"
    fi
    echo "$encryption_key" | docker secret create encryption_key -

    # Session secret
    echo -e "\n${BLUE}🎫 Session Management${NC}"
    read -s -p "Enter session secret (or press Enter to generate): " session_secret
    if [ -z "$session_secret" ]; then
        session_secret=$(generate_password 32)
        echo -e "${YELLOW}Generated: $session_secret${NC}"
    fi
    echo "$session_secret" | docker secret create session_secret -

    # Google OAuth
    echo -e "\n${BLUE}🔍 Google OAuth${NC}"
    read -p "Enter Google Client ID: " google_client_id
    echo "$google_client_id" | docker secret create google_client_id -

    read -s -p "Enter Google Client Secret: " google_client_secret
    echo "$google_client_secret" | docker secret create google_client_secret -

    # LLM API Keys
    echo -e "\n${BLUE}🤖 LLM API Keys${NC}"
    read -s -p "Enter Together AI API Key: " together_api_key
    echo "$together_api_key" | docker secret create together_api_key -

    read -s -p "Enter DeepSeek API Key: " deepseek_api_key
    echo "$deepseek_api_key" | docker secret create deepseek_api_key -

    # Qdrant API Key (optional)
    echo -e "\n${BLUE}🔍 Qdrant Vector Database${NC}"
    read -s -p "Enter Qdrant API Key (optional, press Enter to skip): " qdrant_api_key
    if [ -n "$qdrant_api_key" ]; then
        echo "$qdrant_api_key" | docker secret create qdrant_api_key -
    else
        echo "none" | docker secret create qdrant_api_key -
        echo -e "${YELLOW}⚠️  Created empty Qdrant API key secret${NC}"
    fi

    echo ""
    echo -e "${GREEN}✅ All secrets created successfully!${NC}"
    echo -e "${BLUE}🚀 You can now deploy with:${NC}"
    echo -e "${YELLOW}docker compose -f docker-compose.yaml -f docker-compose.secrets.yaml up -d${NC}"
    echo ""
    echo -e "${BLUE}📋 Created secrets:${NC}"
    list_secrets
}

# Main execution
main() {
    case "${1:-help}" in
        create)
            create_secrets
            ;;
        list)
            list_secrets
            ;;
        remove)
            remove_secrets
            ;;
        validate)
            validate_secrets
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"