#!/bin/bash

# =============================================================================
# ONYX Database Seeding Script
# =============================================================================
# This script initializes the ONYX database with sample data for development
# and testing purposes
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yaml"

# Utility functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    header "Waiting for PostgreSQL to be ready"
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Attempt $attempt/$max_attempts: Checking PostgreSQL connection..."
        
        if docker compose exec -T postgres pg_isready -U manus >/dev/null 2>&1; then
            success "PostgreSQL is ready"
            return 0
        fi
        
        log "PostgreSQL not ready, waiting 2 seconds..."
        sleep 2
        ((attempt++))
    done
    
    error "PostgreSQL failed to become ready after $max_attempts attempts"
    return 1
}

# Check if database has existing data
check_existing_data() {
    header "Checking Existing Data"
    
    local user_count=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ' || echo "0")
    local force_flag="${1:-}"
    
    if [[ "$user_count" -gt 0 ]]; then
        log "Found $user_count existing users in database"
        
        if [[ "$force_flag" == "--force" ]]; then
            warning "Force flag provided, clearing existing data..."
            clear_database
        else
            warning "Database already contains data. Use --force to clear and reseed."
            return 1
        fi
    else
        log "Database is empty, proceeding with seeding"
    fi
    
    return 0
}

# Clear existing data
clear_database() {
    header "Clearing Existing Data"
    
    log "Clearing messages..."
    docker compose exec -T postgres psql -U manus -d manus -c "DELETE FROM messages;" >/dev/null 2>&1 || true
    
    log "Clearing conversations..."
    docker compose exec -T postgres psql -U manus -d manus -c "DELETE FROM conversations;" >/dev/null 2>&1 || true
    
    log "Clearing user memories..."
    docker compose exec -T postgres psql -U manus -d manus -c "DELETE FROM user_memories;" >/dev/null 2>&1 || true
    
    log "Clearing users..."
    docker compose exec -T postgres psql -U manus -d manus -c "DELETE FROM users;" >/dev/null 2>&1 || true
    
    success "Database cleared"
}

# Create sample users
create_sample_users() {
    header "Creating Sample Users"
    
    # Create test users
    local users=(
        "demo@example.com|Demo User|demo_google_123"
        "developer@example.com|Developer User|dev_google_456"
        "admin@example.com|Admin User|admin_google_789"
    )
    
    for user_info in "${users[@]}"; do
        IFS='|' read -r email display_name google_id <<< "$user_info"
        
        log "Creating user: $email"
        
        docker compose exec -T postgres psql -U manus -d manus -c "
            INSERT INTO users (email, display_name, google_id, created_at, updated_at) 
            VALUES ('$email', '$display_name', '$google_id', NOW(), NOW())
            ON CONFLICT (email) DO NOTHING;
        " >/dev/null 2>&1
        
        success "Created user: $display_name"
    done
}

# Create sample conversations
create_sample_conversations() {
    header "Creating Sample Conversations"
    
    # Get user IDs
    local demo_user_id=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT id FROM users WHERE email = 'demo@example.com';" 2>/dev/null | tr -d ' ')
    local dev_user_id=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT id FROM users WHERE email = 'developer@example.com';" 2>/dev/null | tr -d ' ')
    
    if [[ -z "$demo_user_id" ]]; then
        error "Demo user not found"
        return 1
    fi
    
    # Create conversations for demo user
    local conversations=(
        "$demo_user_id|Project Planning Discussion"
        "$demo_user_id|Technical Architecture Review"
        "$demo_user_id|API Integration Questions"
    )
    
    for conv_info in "${conversations[@]}"; do
        IFS='|' read -r user_id title <<< "$conv_info"
        
        log "Creating conversation: $title"
        
        docker compose exec -T postgres psql -U manus -d manus -c "
            INSERT INTO conversations (user_id, title, created_at, updated_at) 
            VALUES ('$user_id', '$title', NOW(), NOW());
        " >/dev/null 2>&1
        
        success "Created conversation: $title"
    done
    
    # Create conversation for developer user
    if [[ -n "$dev_user_id" ]]; then
        log "Creating conversation for developer user"
        
        docker compose exec -T postgres psql -U manus -d manus -c "
            INSERT INTO conversations (user_id, title, created_at, updated_at) 
            VALUES ('$dev_user_id', 'Debugging Session', NOW(), NOW());
        " >/dev/null 2>&1
        
        success "Created conversation: Debugging Session"
    fi
}

# Create sample messages
create_sample_messages() {
    header "Creating Sample Messages"
    
    # Get conversation IDs
    local conv_ids=($(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT id FROM conversations ORDER BY created_at LIMIT 3;" 2>/dev/null | tr -d ' '))
    
    if [[ ${#conv_ids[@]} -eq 0 ]]; then
        error "No conversations found"
        return 1
    fi
    
    # Sample messages for first conversation (Project Planning)
    local conv1_id="${conv_ids[0]}"
    local messages_conv1=(
        "$conv1_id|user|I need help planning the architecture for our new AI platform. Can you provide some guidance?"
        "$conv1_id|assistant|I'd be happy to help you plan the architecture for your AI platform! Let me break down the key components you should consider:

1. **Frontend Layer**: A modern web interface for user interactions
2. **API Gateway**: Central entry point for all requests
3. **Core Services**: Modular microservices for different functionalities
4. **Data Layer**: Combination of relational and vector databases
5. **AI/ML Layer**: LLM integration and processing services

What specific aspects would you like to dive deeper into first?"
        "$conv1_id|user|Great breakdown! Let's start with the data layer. What's the best approach for handling both structured data and vector embeddings?"
        "$conv1_id|assistant|Excellent question! For a hybrid data approach, I recommend:

**Structured Data (PostgreSQL)**:
- User management and authentication
- Conversation history and metadata
- System configuration and settings

**Vector Data (Qdrant)**:
- Document embeddings for semantic search
- Conversation context vectors
- User preference and behavior patterns

**Integration Strategy**:
- Use PostgreSQL as the primary database
- Store vector IDs in PostgreSQL that reference Qdrant
- Implement a caching layer (Redis) for frequently accessed data

This gives you ACID compliance for critical data while providing fast vector similarity search. Would you like me to elaborate on any of these components?"
    )
    
    for msg_info in "${messages_conv1[@]}"; do
        IFS='|' read -r conv_id role content <<< "$msg_info"
        
        log "Adding message to conversation 1"
        
        # Properly escape single quotes in content by doubling them
        local escaped_content=$(echo "$content" | sed "s/'/''/g")
        
        docker compose exec -T postgres psql -U manus -d manus -c "
            INSERT INTO messages (conversation_id, role, content, created_at) 
            VALUES ('$conv_id', '$role', '$escaped_content', NOW());
        " 2>&1 || echo "ERROR: Failed to insert message"
    done
    
    # Sample messages for second conversation (Technical Architecture)
    local conv2_id="${conv_ids[1]}"
    local messages_conv2=(
        "$conv2_id|user|What are the best practices for implementing OAuth2 authentication in a microservices architecture?"
        "$conv2_id|assistant|For OAuth2 in microservices, here are the key best practices:

**Centralized Authentication**:
- Use an OAuth2 provider (Google, Auth0, or self-hosted)
- Implement a centralized authentication service
- Use JWT tokens for stateless authentication

**Token Management**:
- Access tokens: Short-lived (15-60 minutes)
- Refresh tokens: Long-lived with secure storage
- Implement token rotation and revocation

**Service Communication**:
- Use API Gateway for token validation
- Implement service-to-service authentication
- Use mTLS for internal service communication

**Security Considerations**:
- Store tokens securely (httpOnly cookies)
- Implement CSRF protection
- Use secure headers (HSTS, CSP, etc.)

Would you like me to provide specific implementation examples for any of these areas?"
    )
    
    for msg_info in "${messages_conv2[@]}"; do
        IFS='|' read -r conv_id role content <<< "$msg_info"
        
        log "Adding message to conversation 2"
        
        # Properly escape single quotes in content by doubling them
        local escaped_content=$(echo "$content" | sed "s/'/''/g")
        
        docker compose exec -T postgres psql -U manus -d manus -c "
            INSERT INTO messages (conversation_id, role, content, created_at) 
            VALUES ('$conv_id', '$role', '$escaped_content', NOW());
        " >/dev/null 2>&1
    done
    
    success "Sample messages created"
}

# Create sample user memories
create_sample_memories() {
    header "Creating Sample User Memories"
    
    # Get user IDs
    local demo_user_id=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT id FROM users WHERE email = 'demo@example.com';" 2>/dev/null | tr -d ' ')
    
    if [[ -z "$demo_user_id" ]]; then
        error "Demo user not found"
        return 1
    fi
    
    # Sample memories
    local memories=(
        "$demo_user_id|preference|The user prefers TypeScript over JavaScript for frontend development"
        "$demo_user_id|preference|The user is working on a microservices architecture project"
        "$demo_user_id|context|The user has experience with Docker and Kubernetes"
        "$demo_user_id|context|The user is interested in AI/ML integration"
        "$demo_user_id|instruction|Always provide code examples in TypeScript when possible"
        "$demo_user_id|instruction|Focus on security best practices in recommendations"
    )
    
    for memory_info in "${memories[@]}"; do
        IFS='|' read -r user_id memory_type content <<< "$memory_info"
        
        log "Adding memory: $memory_type"
        
        docker compose exec -T postgres psql -U manus -d manus -c "
            INSERT INTO user_memories (user_id, memory_type, content, created_at, updated_at) 
            VALUES ('$user_id', '$memory_type', E'$content', NOW(), NOW());
        " >/dev/null 2>&1
    done
    
    success "Sample user memories created"
}

# Verify seeded data
verify_seeding() {
    header "Verifying Seeded Data"
    
    local user_count=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
    local conv_count=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT COUNT(*) FROM conversations;" 2>/dev/null | tr -d ' ')
    local msg_count=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT COUNT(*) FROM messages;" 2>/dev/null | tr -d ' ')
    local memory_count=$(docker compose exec -T postgres psql -U manus -d manus -t -c "SELECT COUNT(*) FROM user_memories;" 2>/dev/null | tr -d ' ')
    
    success "Database seeding verification:"
    echo "  • Users: $user_count"
    echo "  • Conversations: $conv_count"
    echo "  • Messages: $msg_count"
    echo "  • User Memories: $memory_count"
    
    if [[ "$user_count" -gt 0 && "$conv_count" -gt 0 && "$msg_count" -gt 0 ]]; then
        success "Database seeding completed successfully!"
        return 0
    else
        error "Database seeding may have failed - some tables are empty"
        return 1
    fi
}

# Display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --force    Clear existing data before seeding"
    echo "  --help     Show this help message"
    echo
    echo "This script seeds the ONYX database with sample data for development and testing."
    echo "It creates sample users, conversations, messages, and user memories."
}

# Main execution
main() {
    local force_flag=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force_flag="--force"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    log "Starting database seeding process"
    
    # Run seeding steps
    local steps=(
        "wait_for_postgres"
        "check_existing_data ${force_flag:-}"
        "create_sample_users"
        "create_sample_conversations"
        "create_sample_messages"
        "create_sample_memories"
        "verify_seeding"
    )
    
    for step in "${steps[@]}"; do
        if ! eval $step; then
            error "Database seeding failed at step: $step"
            exit 1
        fi
    done
    
    success "Database seeding completed successfully!"
    
    echo
    echo "🎉 Sample data is now available in your ONYX database!"
    echo
    echo "Sample Users Created:"
    echo "  • demo@example.com (Demo User)"
    echo "  • developer@example.com (Developer User)"
    echo "  • admin@example.com (Admin User)"
    echo
    echo "You can now:"
    echo "  1. Start the application: docker compose up -d"
    echo "  2. Visit http://localhost:3000"
    echo "  3. Test with the sample data"
    echo
}

# Handle script interruption
trap 'error "Database seeding interrupted by user"; exit 130' INT

# Run main function
main "$@"