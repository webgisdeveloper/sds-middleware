#!/bin/bash

# Docker deployment script for SDS Middleware

echo "=================================="
echo "🐳 SDS Middleware Docker Deployment"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Parse command line arguments
COMMAND=${1:-up}

case $COMMAND in
    up)
        echo "🚀 Starting services..."
        echo ""
        docker compose up -d --build
        
        echo ""
        echo "⏳ Waiting for services to be healthy..."
        sleep 10
        
        # Check service status
        echo ""
        docker compose ps
        
        echo ""
        echo "=================================="
        echo "✨ Services Started!"
        echo "=================================="
        echo ""
        echo "📊 Access Points:"
        echo "   Admin Console:      http://localhost:8080/admin/"
        echo "   Operations Console: http://localhost:8080/ops/"
        echo "   API:                http://localhost:8080/"
        echo "   Database:           localhost:3306"
        echo ""
        echo "🔑 Default Credentials:"
        echo "   Admin Secret:       admin-secret-2026"
        echo "   Operations Secret:  ops-secret-2026"
        echo "   DB User:            dbtester"
        echo "   DB Password:        supersecret"
        echo ""
        echo "📝 View logs:"
        echo "   docker compose logs -f"
        echo ""
        echo "🛑 Stop services:"
        echo "   ./docker-deploy.sh down"
        ;;
        
    down)
        echo "🛑 Stopping services..."
        docker compose down
        echo "✅ Services stopped"
        ;;
        
    restart)
        echo "🔄 Restarting services..."
        docker compose restart
        echo "✅ Services restarted"
        ;;
        
    logs)
        echo "📝 Showing logs (Ctrl+C to exit)..."
        docker compose logs -f
        ;;
        
    rebuild)
        echo "🔨 Rebuilding and restarting services..."
        docker compose down
        docker compose build --no-cache
        docker compose up -d
        echo "✅ Services rebuilt and restarted"
        ;;
        
    status)
        echo "📊 Service Status:"
        docker compose ps
        ;;
        
    clean)
        echo "🧹 Cleaning up..."
        echo ""
        read -p "⚠️  This will remove all containers, volumes, and data. Continue? (y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v
            echo "✅ Cleanup complete"
        else
            echo "❌ Cleanup cancelled"
        fi
        ;;
        
    shell)
        SERVICE=${2:-app}
        echo "🐚 Opening shell in $SERVICE container..."
        docker compose exec $SERVICE /bin/bash
        ;;
        
    storage)
        echo "💾 Storage Information:"
        echo ""
        echo "📁 Storage directory (bind mount):"
        echo "   Host: $(pwd)/storages"
        echo "   Container: /app/storages"
        echo ""
        echo "📊 Current storage usage:"
        du -sh storages/caches storages/jobs 2>/dev/null
        echo ""
        echo "🐳 Container view:"
        docker compose exec app ls -lh /app/storages 2>/dev/null
        echo ""
        docker compose exec app du -h /app/storages/caches /app/storages/jobs 2>/dev/null
        ;;
        
    *)
        echo "Usage: ./docker-deploy.sh [command]"
        echo ""
        echo "Commands:"
        echo "  up         Start all services (default)"
        echo "  down       Stop all services"
        echo "  restart    Restart all services"
        echo "  logs       View service logs"
        echo "  rebuild    Rebuild and restart services"
        echo "  status     Show service status"
        echo "  clean      Remove all containers and volumes"
        echo "  shell      Open shell in container (default: app)"
        echo "  storage    Show storage volume information"
        echo ""
        echo "Examples:"
        echo "  ./docker-deploy.sh up"
        echo "  ./docker-deploy.sh logs"
        echo "  ./docker-deploy.sh shell app"
        echo "  ./docker-deploy.sh shell db"
        exit 1
        ;;
esac
