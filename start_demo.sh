#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# OpMech-GraphRAG Demo Startup Script
# ═══════════════════════════════════════════════════════════════════════════
# This script starts all required services for the OpMech-GraphRAG demo:
#   1. Neo4j (via Docker)
#   2. vLLM Server (LLM inference)
#   3. Backend API (FastAPI)
#   4. Frontend (Next.js)
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/home/divyansh/AIF_FInal_Project"
cd "$PROJECT_DIR"

# Configuration
NEO4J_PORT=7687
NEO4J_HTTP_PORT=7474
VLLM_PORT=8001
BACKEND_PORT=8000
FRONTEND_PORT=3000
VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-7B-Instruct}"

# Log file directory
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# ═══════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════

print_header() {
    echo ""
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════${NC}"
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

clear_port() {
    local port=$1
    local service=$2
    if check_port $port; then
        print_warning "Port $port is in use. Clearing it for $service..."
        fuser -k $port/tcp 2>/dev/null || true
        # Also try with lsof + kill for better compatibility
        local pids=$(lsof -t -i :$port 2>/dev/null)
        if [ -n "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi
        sleep 2
        if check_port $port; then
            print_error "Failed to clear port $port. Please manually stop the process."
            return 1
        fi
        print_success "Port $port cleared successfully"
    fi
    return 0
}

wait_for_port() {
    local port=$1
    local service=$2
    local max_attempts=${3:-60}
    local attempt=1

    print_step "Waiting for $service on port $port..."
    while [ $attempt -le $max_attempts ]; do
        if check_port $port; then
            print_success "$service is ready on port $port"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    print_error "Timeout waiting for $service on port $port"
    return 1
}

wait_for_url() {
    local url=$1
    local service=$2
    local max_attempts=${3:-60}
    local attempt=1

    print_step "Waiting for $service at $url..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "200\|404\|301\|302"; then
            print_success "$service is responding at $url"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    print_error "Timeout waiting for $service at $url"
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════
# Cleanup Function
# ═══════════════════════════════════════════════════════════════════════════

cleanup() {
    print_header "Shutting Down Services"

    # Kill processes by port
    for port in $FRONTEND_PORT $BACKEND_PORT $VLLM_PORT; do
        if check_port $port; then
            print_step "Stopping service on port $port..."
            fuser -k $port/tcp 2>/dev/null || true
        fi
    done

    # Stop Docker containers
    print_step "Stopping Docker containers..."
    if docker compose version &> /dev/null; then
        docker compose down 2>/dev/null || true
    elif docker-compose version &> /dev/null; then
        docker-compose down 2>/dev/null || true
    fi
    docker stop moe-graph-neo4j 2>/dev/null || true

    print_success "All services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ═══════════════════════════════════════════════════════════════════════════
# Service Start Functions
# ═══════════════════════════════════════════════════════════════════════════

start_neo4j() {
    print_header "Starting Neo4j Database"

    # Clear ports if in use
    clear_port $NEO4J_PORT "Neo4j Bolt" || return 1
    clear_port $NEO4J_HTTP_PORT "Neo4j HTTP" || return 1

    # Stop any existing Neo4j container
    docker stop moe-graph-neo4j 2>/dev/null || true
    docker rm moe-graph-neo4j 2>/dev/null || true

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_warning "Please install Docker or start Neo4j manually"
        print_warning "You can run Neo4j with: docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:5.15.0-community"
        return 1
    fi

    print_step "Starting Neo4j via Docker Compose..."

    # Try docker compose (v2) first, then docker-compose (v1)
    if docker compose version &> /dev/null; then
        docker compose up -d neo4j
    elif docker-compose version &> /dev/null; then
        docker-compose up -d neo4j
    else
        print_warning "Docker Compose not available. Starting Neo4j container directly..."
        docker run -d \
            --name moe-graph-neo4j \
            -p 7474:7474 \
            -p 7687:7687 \
            -e NEO4J_AUTH=neo4j/password123 \
            -e "NEO4J_PLUGINS=[\"apoc\"]" \
            neo4j:5.15.0-community 2>/dev/null || \
        docker start moe-graph-neo4j 2>/dev/null || \
        print_error "Failed to start Neo4j container"
    fi

    wait_for_url "http://localhost:$NEO4J_HTTP_PORT" "Neo4j" 60

    print_success "Neo4j is running"
    echo -e "  ${BLUE}Browser:${NC} http://localhost:$NEO4J_HTTP_PORT"
    echo -e "  ${BLUE}Bolt:${NC} bolt://localhost:$NEO4J_PORT"
    echo -e "  ${BLUE}Credentials:${NC} neo4j / password123"
}

start_vllm() {
    print_header "Starting vLLM Server"

    # Clear port if in use
    clear_port $VLLM_PORT "vLLM" || return 1

    print_step "Starting vLLM with model: $VLLM_MODEL"
    print_warning "This may take a few minutes to load the model..."

    # Activate virtual environment and start vLLM
    (
        source "$PROJECT_DIR/.venv/bin/activate"
        python -m vllm.entrypoints.openai.api_server \
            --model "$VLLM_MODEL" \
            --port "$VLLM_PORT" \
            --tensor-parallel-size 1 \
            --gpu-memory-utilization 0.85 \
            --max-model-len 4096 \
            --trust-remote-code \
            > "$LOG_DIR/vllm.log" 2>&1
    ) &

    wait_for_url "http://localhost:$VLLM_PORT/v1/models" "vLLM" 180

    print_success "vLLM is running"
    echo -e "  ${BLUE}API:${NC} http://localhost:$VLLM_PORT/v1"
    echo -e "  ${BLUE}Model:${NC} $VLLM_MODEL"
    echo -e "  ${BLUE}Log:${NC} $LOG_DIR/vllm.log"
}

start_backend() {
    print_header "Starting Backend API"

    # Clear port if in use
    clear_port $BACKEND_PORT "Backend API" || return 1

    print_step "Starting FastAPI backend..."

    # Activate virtual environment and start backend
    (
        source "$PROJECT_DIR/.venv/bin/activate"
        export VLLM_API_BASE="http://localhost:$VLLM_PORT/v1"
        cd "$PROJECT_DIR"
        python -m uvicorn src.api.main:app \
            --host 0.0.0.0 \
            --port $BACKEND_PORT \
            --reload \
            > "$LOG_DIR/backend.log" 2>&1
    ) &

    wait_for_url "http://localhost:$BACKEND_PORT" "Backend API" 30

    print_success "Backend API is running"
    echo -e "  ${BLUE}API:${NC} http://localhost:$BACKEND_PORT"
    echo -e "  ${BLUE}Docs:${NC} http://localhost:$BACKEND_PORT/docs"
    echo -e "  ${BLUE}Log:${NC} $LOG_DIR/backend.log"
}

start_frontend() {
    print_header "Starting Frontend"

    # Clear port if in use
    clear_port $FRONTEND_PORT "Frontend" || return 1

    print_step "Starting Next.js frontend..."

    (
        cd "$PROJECT_DIR/frontend"
        npm run dev > "$LOG_DIR/frontend.log" 2>&1
    ) &

    wait_for_url "http://localhost:$FRONTEND_PORT" "Frontend" 60

    print_success "Frontend is running"
    echo -e "  ${BLUE}URL:${NC} http://localhost:$FRONTEND_PORT"
    echo -e "  ${BLUE}Demo:${NC} http://localhost:$FRONTEND_PORT/demo"
    echo -e "  ${BLUE}Log:${NC} $LOG_DIR/frontend.log"
}

# ═══════════════════════════════════════════════════════════════════════════
# Status Function
# ═══════════════════════════════════════════════════════════════════════════

show_logs() {
    local service="${1:-backend}"
    local log_file="$LOG_DIR/${service}.log"

    if [ ! -f "$log_file" ]; then
        print_error "Log file not found: $log_file"
        echo "Available logs:"
        ls -la "$LOG_DIR"/*.log 2>/dev/null || echo "  No log files found"
        return 1
    fi

    print_header "Tailing $service logs"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    tail -f "$log_file"
}

show_all_logs() {
    print_header "Tailing all service logs"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""

    # Tail all logs simultaneously with prefixes
    tail -f "$LOG_DIR/backend.log" 2>/dev/null | sed 's/^/[BACKEND] /' &
    tail -f "$LOG_DIR/vllm.log" 2>/dev/null | sed 's/^/[VLLM] /' &
    tail -f "$LOG_DIR/frontend.log" 2>/dev/null | sed 's/^/[FRONTEND] /' &

    # Wait for interrupt
    wait
}

show_status() {
    print_header "Service Status"

    echo ""
    echo -e "${CYAN}Service          Port    Status${NC}"
    echo "───────────────────────────────────────"

    # Neo4j
    if check_port $NEO4J_PORT; then
        echo -e "Neo4j            $NEO4J_PORT    ${GREEN}● Running${NC}"
    else
        echo -e "Neo4j            $NEO4J_PORT    ${RED}○ Stopped${NC}"
    fi

    # vLLM
    if check_port $VLLM_PORT; then
        echo -e "vLLM             $VLLM_PORT    ${GREEN}● Running${NC}"
    else
        echo -e "vLLM             $VLLM_PORT    ${RED}○ Stopped${NC}"
    fi

    # Backend
    if check_port $BACKEND_PORT; then
        echo -e "Backend API      $BACKEND_PORT    ${GREEN}● Running${NC}"
    else
        echo -e "Backend API      $BACKEND_PORT    ${RED}○ Stopped${NC}"
    fi

    # Frontend
    if check_port $FRONTEND_PORT; then
        echo -e "Frontend         $FRONTEND_PORT    ${GREEN}● Running${NC}"
    else
        echo -e "Frontend         $FRONTEND_PORT    ${RED}○ Stopped${NC}"
    fi

    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════

main() {
    print_header "OpMech-GraphRAG Demo Launcher"

    echo ""
    echo -e "${CYAN}Project:${NC} $PROJECT_DIR"
    echo -e "${CYAN}vLLM Model:${NC} $VLLM_MODEL"
    echo ""

    case "${1:-start}" in
        start)
            start_neo4j
            start_vllm
            start_backend
            start_frontend

            print_header "All Services Started Successfully!"
            show_status

            echo ""
            echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
            echo -e "${GREEN}  OpMech-GraphRAG Demo is ready!${NC}"
            echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
            echo ""
            echo -e "  ${CYAN}Homepage:${NC}  http://localhost:$FRONTEND_PORT"
            echo -e "  ${CYAN}Demo Page:${NC} http://localhost:$FRONTEND_PORT/demo"
            echo -e "  ${CYAN}API Docs:${NC}  http://localhost:$BACKEND_PORT/docs"
            echo -e "  ${CYAN}Neo4j:${NC}     http://localhost:$NEO4J_HTTP_PORT"
            echo ""
            echo -e "  ${YELLOW}Press Ctrl+C to stop all services${NC}"
            echo ""

            # Keep script running
            while true; do
                sleep 60
            done
            ;;
        stop)
            cleanup
            ;;
        status)
            show_status
            ;;
        neo4j)
            start_neo4j
            ;;
        vllm)
            start_vllm
            ;;
        backend)
            start_backend
            ;;
        frontend)
            start_frontend
            ;;
        logs)
            if [ "${2:-}" = "all" ]; then
                show_all_logs
            else
                show_logs "${2:-backend}"
            fi
            ;;
        *)
            echo "Usage: $0 {start|stop|status|logs|neo4j|vllm|backend|frontend}"
            echo ""
            echo "Commands:"
            echo "  start     - Start all services (default)"
            echo "  stop      - Stop all services"
            echo "  status    - Show service status"
            echo "  logs [svc]- Tail logs for service (backend|frontend|vllm|all, default: backend)"
            echo "  neo4j     - Start only Neo4j"
            echo "  vllm      - Start only vLLM"
            echo "  backend   - Start only Backend API"
            echo "  frontend  - Start only Frontend"
            echo ""
            echo "Environment variables:"
            echo "  VLLM_MODEL - vLLM model to use (default: Qwen/Qwen2.5-7B-Instruct)"
            exit 1
            ;;
    esac
}

main "$@"
