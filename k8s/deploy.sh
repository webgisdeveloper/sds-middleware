#!/bin/bash
# Quick deployment script for SDS Middleware on Kubernetes (OrbStack)

set -e

echo "🚀 Starting SDS Middleware deployment to Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install OrbStack and enable Kubernetes."
    exit 1
fi

# Check if Docker image exists
if ! docker images | grep -q "sds-middleware"; then
    echo "📦 Building Docker image..."
    docker build -t sds-middleware:latest .
else
    echo "✅ Docker image found"
fi

# Create namespace
echo "📁 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Create ConfigMaps and Secrets
echo "⚙️  Creating ConfigMaps..."
kubectl apply -f k8s/configmap.yaml

# Deploy MySQL
echo "🗄️  Deploying MySQL..."
kubectl apply -f k8s/mysql.yaml

echo "⏳ Waiting for MySQL to be ready..."
kubectl wait --for=condition=ready pod -l app=mysql -n sds-middleware --timeout=120s

# Deploy Application
echo "🌐 Deploying application..."
kubectl apply -f k8s/app.yaml

echo "⏳ Waiting for application to be ready..."
kubectl wait --for=condition=ready pod -l app=sds-middleware -n sds-middleware --timeout=120s

# Get service information
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service Status:"
kubectl get services -n sds-middleware

echo ""
echo "🔗 Access the application at:"
echo "   Main App:            http://localhost:8080"
echo "   Admin Console:       http://localhost:8080/admin"
echo "   Operations Console:  http://localhost:8080/ops"
echo ""
echo "📝 View logs with:"
echo "   kubectl logs -n sds-middleware -l app=sds-middleware --tail=100 -f"
echo ""
echo "🔍 Check status with:"
echo "   kubectl get all -n sds-middleware"
