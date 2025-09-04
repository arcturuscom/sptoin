#!/bin/bash

# Universal Deployment Script - Build Once, Run Everywhere
# Supports LOCAL/DEV/STAGING/PROD environments

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="spam-to-inbox"
VERSION=$(date +"%Y%m%d_%H%M%S")

# Default values
TARGET_ENV=""
OPERATION=""
VALIDATE_ONLY=false
FORCE_DEPLOY=false
BACKUP_CURRENT=true

print_banner() {
    echo -e "${BLUE}"
    echo "================================================================"
    echo "🚀 SPAM-TO-INBOX DEPLOYMENT SCRIPT"
    echo "   Build Once, Run Everywhere"
    echo "================================================================"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 <environment> <operation> [options]"
    echo ""
    echo "Environments:"
    echo "  local     - Local development (direct connection, dry-run)"
    echo "  dev       - Development (free proxies, debug logging)"
    echo "  staging   - Pre-production (SmartProxy, safety measures)"
    echo "  prod      - Production (full security, live processing)"
    echo ""
    echo "Operations:"
    echo "  setup     - Initialize environment configuration"
    echo "  validate  - Validate environment readiness"
    echo "  deploy    - Deploy and configure for environment"
    echo "  start     - Start the service"
    echo "  stop      - Stop the service"
    echo "  status    - Check service status"
    echo "  logs      - Show recent logs"
    echo ""
    echo "Options:"
    echo "  --validate-only    Only validate, don't deploy"
    echo "  --force           Force deployment without confirmation"
    echo "  --no-backup       Skip backup of current configuration"
    echo "  --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 local setup                    # Setup local development"
    echo "  $0 dev deploy --validate-only     # Validate dev deployment"
    echo "  $0 staging deploy                 # Deploy to staging"
    echo "  $0 prod deploy --force            # Force production deployment"
}

validate_environment() {
    local env=$1
    echo -e "${BLUE}🔍 Validating $env environment...${NC}"
    
    # Use Python environment manager for validation
    if python3 env_manager.py --validate "$env"; then
        echo -e "${GREEN}✅ Environment validation passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Environment validation failed${NC}"
        return 1
    fi
}

setup_environment() {
    local env=$1
    echo -e "${BLUE}⚙️  Setting up $env environment...${NC}"
    
    # Create missing configuration files
    if python3 env_manager.py --create-configs "$env"; then
        echo -e "${GREEN}✅ Configuration files created${NC}"
    else
        echo -e "${RED}❌ Failed to create configuration files${NC}"
        return 1
    fi
    
    # Set environment marker
    if python3 env_manager.py --set-env "$env"; then
        echo -e "${GREEN}✅ Environment marker set${NC}"
    else
        echo -e "${RED}❌ Failed to set environment marker${NC}"
        return 1
    fi
    
    # Environment-specific setup
    case $env in
        "local")
            setup_local_environment
            ;;
        "dev")
            setup_dev_environment
            ;;
        "staging")
            setup_staging_environment
            ;;
        "prod")
            setup_prod_environment
            ;;
    esac
}

setup_local_environment() {
    echo -e "${BLUE}🏠 Local environment setup...${NC}"
    
    # Ensure test accounts exist
    if [ ! -f "config/test_accounts.csv" ] || [ ! -s "config/test_accounts.csv" ]; then
        echo -e "${YELLOW}📝 Creating sample test accounts...${NC}"
        cat > config/test_accounts.csv << EOF
email,password,app_password
# REPLACE WITH YOUR REAL TEST ACCOUNTS
# your_test@hotmail.com,your_password,
# another_test@outlook.com,another_password,app_password_if_2fa
EOF
        echo -e "${YELLOW}⚠️  Edit config/test_accounts.csv with your real test accounts${NC}"
    fi
    
    echo -e "${GREEN}✅ Local environment ready${NC}"
}

setup_dev_environment() {
    echo -e "${BLUE}🛠️  Development environment setup...${NC}"
    
    # Setup free proxies configuration
    if [ ! -f "config/free_proxies.json" ]; then
        echo -e "${BLUE}📝 Creating free proxy configuration...${NC}"
        cp config/free_proxies.json.example config/free_proxies.json 2>/dev/null || true
    fi
    
    # Test free proxies
    echo -e "${BLUE}🔍 Testing free proxies...${NC}"
    python3 test_free_proxies.py --test-manual --save-working config/working_proxies.json || {
        echo -e "${YELLOW}⚠️  Some proxy tests failed, but continuing...${NC}"
    }
    
    echo -e "${GREEN}✅ Development environment ready${NC}"
}

setup_staging_environment() {
    echo -e "${BLUE}🎭 Staging environment setup...${NC}"
    
    # Check for SmartProxy credentials
    if [ -z "$SMARTPROXY_USERNAME" ] || [ -z "$SMARTPROXY_PASSWORD" ]; then
        echo -e "${YELLOW}⚠️  SmartProxy credentials not set${NC}"
        echo -e "${BLUE}   Set SMARTPROXY_USERNAME and SMARTPROXY_PASSWORD environment variables${NC}"
        echo -e "${BLUE}   Or add them to your .bashrc/.zshrc:${NC}"
        echo -e "${BLUE}     export SMARTPROXY_USERNAME=your_username${NC}"
        echo -e "${BLUE}     export SMARTPROXY_PASSWORD=your_password${NC}"
    fi
    
    # Ensure staging accounts exist
    if [ ! -f "config/accounts_staging.csv" ] || grep -q "staging_secure_pass" "config/accounts_staging.csv" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Update config/accounts_staging.csv with real staging accounts${NC}"
    fi
    
    echo -e "${GREEN}✅ Staging environment ready${NC}"
}

setup_prod_environment() {
    echo -e "${BLUE}🏭 Production environment setup...${NC}"
    
    # Strict validation for production
    if [ -z "$SMARTPROXY_USERNAME" ] || [ -z "$SMARTPROXY_PASSWORD" ]; then
        echo -e "${RED}❌ Production requires SmartProxy credentials${NC}"
        echo -e "${RED}   Set SMARTPROXY_USERNAME and SMARTPROXY_PASSWORD environment variables${NC}"
        return 1
    fi
    
    # Check production accounts
    if [ ! -f "config/accounts_prod.csv" ]; then
        if [ -f "config/accounts_prod.csv.example" ]; then
            echo -e "${YELLOW}📝 Copying production accounts template...${NC}"
            cp config/accounts_prod.csv.example config/accounts_prod.csv
        fi
        echo -e "${RED}❌ Configure config/accounts_prod.csv with real production accounts${NC}"
        return 1
    fi
    
    # Production security checks
    if grep -q "real_secure_password" "config/accounts_prod.csv" 2>/dev/null; then
        echo -e "${RED}❌ Production accounts file contains example passwords${NC}"
        echo -e "${RED}   Update config/accounts_prod.csv with real credentials${NC}"
        return 1
    fi
    
    # Create production backup directory
    mkdir -p "backups/prod"
    
    echo -e "${GREEN}✅ Production environment ready${NC}"
}

backup_current_config() {
    local env=$1
    
    if [ "$BACKUP_CURRENT" = false ]; then
        echo -e "${BLUE}⏭️  Skipping backup as requested${NC}"
        return 0
    fi
    
    echo -e "${BLUE}💾 Creating backup of current configuration...${NC}"
    
    local backup_dir="backups/${env}_${VERSION}"
    mkdir -p "$backup_dir"
    
    # Backup configuration files
    [ -f "config/.env_marker" ] && cp "config/.env_marker" "$backup_dir/"
    [ -f "config/environment_${env}.json" ] && cp "config/environment_${env}.json" "$backup_dir/"
    [ -f "config/accounts_${env}.csv" ] && cp "config/accounts_${env}.csv" "$backup_dir/"
    
    echo -e "${GREEN}✅ Backup created: $backup_dir${NC}"
}

deploy_to_environment() {
    local env=$1
    
    echo -e "${PURPLE}🚀 Deploying to $env environment...${NC}"
    
    # Create backup
    backup_current_config "$env"
    
    # Setup environment
    setup_environment "$env"
    
    # Install/update dependencies
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    pip3 install -r requirements.txt --quiet
    
    # Create logs directory
    mkdir -p logs
    
    # Set proper permissions
    chmod +x deploy.sh
    chmod +x run.sh
    chmod +x env_manager.py
    chmod +x test_free_proxies.py
    
    echo -e "${GREEN}✅ Deployment to $env completed${NC}"
}

start_service() {
    local env=$1
    
    echo -e "${BLUE}▶️  Starting service in $env environment...${NC}"
    
    # Check if already running
    if pgrep -f "main_unified.py" > /dev/null; then
        echo -e "${YELLOW}⚠️  Service already running${NC}"
        return 1
    fi
    
    # Set environment variable
    export SPAM_TO_INBOX_ENV="$env"
    
    # Start service in background
    nohup python3 src/main_unified.py > logs/service.out 2>&1 &
    local pid=$!
    
    echo "$pid" > .service_pid
    echo -e "${GREEN}✅ Service started with PID: $pid${NC}"
    
    # Wait a moment and check if it's still running
    sleep 2
    if ! kill -0 "$pid" 2>/dev/null; then
        echo -e "${RED}❌ Service failed to start${NC}"
        return 1
    fi
}

stop_service() {
    echo -e "${BLUE}⏹️  Stopping service...${NC}"
    
    if [ -f ".service_pid" ]; then
        local pid=$(cat .service_pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo -e "${GREEN}✅ Service stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  Service not running${NC}"
        fi
        rm -f .service_pid
    else
        # Try to find and kill by process name
        local pid=$(pgrep -f "main_unified.py" | head -1)
        if [ -n "$pid" ]; then
            kill "$pid"
            echo -e "${GREEN}✅ Service stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  No service found running${NC}"
        fi
    fi
}

check_service_status() {
    local env=$1
    
    echo -e "${BLUE}📊 Checking service status...${NC}"
    
    # Check if process is running
    if pgrep -f "main_unified.py" > /dev/null; then
        local pid=$(pgrep -f "main_unified.py" | head -1)
        echo -e "${GREEN}✅ Service running (PID: $pid)${NC}"
        
        # Show environment info
        python3 env_manager.py --current
        
        return 0
    else
        echo -e "${RED}❌ Service not running${NC}"
        return 1
    fi
}

show_logs() {
    local env=$1
    
    echo -e "${BLUE}📋 Recent logs for $env environment...${NC}"
    echo "=" * 50
    
    if [ -f "logs/spam-to-inbox.log" ]; then
        tail -50 "logs/spam-to-inbox.log"
    else
        echo -e "${YELLOW}⚠️  No log file found${NC}"
    fi
    
    if [ -f "logs/service.out" ]; then
        echo -e "\n${BLUE}Service output:${NC}"
        tail -20 "logs/service.out"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --validate-only)
            VALIDATE_ONLY=true
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --no-backup)
            BACKUP_CURRENT=false
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        local|dev|staging|prod)
            if [ -z "$TARGET_ENV" ]; then
                TARGET_ENV=$1
            else
                echo -e "${RED}❌ Multiple environments specified${NC}"
                exit 1
            fi
            shift
            ;;
        setup|validate|deploy|start|stop|status|logs)
            if [ -z "$OPERATION" ]; then
                OPERATION=$1
            else
                echo -e "${RED}❌ Multiple operations specified${NC}"
                exit 1
            fi
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Main execution
print_banner

# Validate required arguments
if [ -z "$TARGET_ENV" ] || [ -z "$OPERATION" ]; then
    echo -e "${RED}❌ Environment and operation are required${NC}"
    print_usage
    exit 1
fi

# Change to script directory
cd "$SCRIPT_DIR"

echo -e "${PURPLE}🎯 Target: $TARGET_ENV${NC}"
echo -e "${PURPLE}🔧 Operation: $OPERATION${NC}"
echo ""

# Execute operation
case $OPERATION in
    "setup")
        setup_environment "$TARGET_ENV"
        ;;
    "validate")
        validate_environment "$TARGET_ENV"
        ;;
    "deploy")
        if validate_environment "$TARGET_ENV"; then
            if [ "$VALIDATE_ONLY" = true ]; then
                echo -e "${GREEN}✅ Validation-only completed${NC}"
                exit 0
            fi
            
            # Production deployment confirmation
            if [ "$TARGET_ENV" = "prod" ] && [ "$FORCE_DEPLOY" = false ]; then
                echo -e "${RED}⚠️  PRODUCTION DEPLOYMENT${NC}"
                echo -e "${RED}   This will deploy to LIVE production environment${NC}"
                read -p "Are you sure? (type 'DEPLOY' to confirm): " confirm
                if [ "$confirm" != "DEPLOY" ]; then
                    echo -e "${BLUE}🛑 Deployment cancelled${NC}"
                    exit 0
                fi
            fi
            
            deploy_to_environment "$TARGET_ENV"
        else
            exit 1
        fi
        ;;
    "start")
        start_service "$TARGET_ENV"
        ;;
    "stop")
        stop_service
        ;;
    "status")
        check_service_status "$TARGET_ENV"
        ;;
    "logs")
        show_logs "$TARGET_ENV"
        ;;
    *)
        echo -e "${RED}❌ Unknown operation: $OPERATION${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Operation completed successfully${NC}"