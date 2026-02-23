#!/bin/bash
# Cleanup script for SDS Middleware on Kubernetes

set -e

echo "🧹 Cleaning up SDS Middleware from Kubernetes..."

# Delete all resources in the namespace
echo "🗑️  Deleting all resources..."
kubectl delete namespace sds-middleware --ignore-not-found=true

echo "⏳ Waiting for namespace to be deleted..."
kubectl wait --for=delete namespace/sds-middleware --timeout=60s 2>/dev/null || true

echo "✅ Cleanup complete!"
echo ""
echo "💡 To redeploy, run: ./k8s/deploy.sh"
