# Kubernetes Deployment on OrbStack (Mac)

This guide helps you deploy the SDS Middleware application to Kubernetes using OrbStack on your Mac laptop.

## Prerequisites

1. **OrbStack**: Install OrbStack from https://orbstack.dev/
2. **kubectl**: Should be included with OrbStack
3. **Docker image**: Build the application Docker image locally

## Step 1: Enable Kubernetes in OrbStack

1. Open OrbStack
2. Go to Settings → Kubernetes
3. Enable Kubernetes and wait for it to start
4. Verify Kubernetes is running:
   ```bash
   kubectl cluster-info
   kubectl get nodes
   ```

## Step 2: Build the Docker Image

Build the Docker image locally (OrbStack shares Docker images with Kubernetes):

```bash
docker build -t sds-middleware:latest .
```

Verify the image is built:
```bash
docker images | grep sds-middleware
```

## Step 3: Prepare MySQL Init Script (Optional)

If you have a custom MySQL initialization script, copy it to the ConfigMap:

```bash
# Edit k8s/configmap.yaml and add your init.sql content
# Or copy from your localtest directory
cat localtest/init.sql
```

## Step 4: Deploy to Kubernetes

Deploy the application in the following order:

### 1. Create Namespace
```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Create ConfigMaps and Secrets
```bash
kubectl apply -f k8s/configmap.yaml
```

### 3. Deploy MySQL Database
```bash
kubectl apply -f k8s/mysql.yaml
```

Wait for MySQL to be ready:
```bash
kubectl wait --for=condition=ready pod -l app=mysql -n sds-middleware --timeout=120s
```

### 4. Deploy Application
```bash
kubectl apply -f k8s/app.yaml
```

Wait for the app to be ready:
```bash
kubectl wait --for=condition=ready pod -l app=sds-middleware -n sds-middleware --timeout=120s
```

## Step 5: Access the Application

### Check Service Status
```bash
kubectl get services -n sds-middleware
```

### Get the LoadBalancer IP/Port
With OrbStack, the LoadBalancer service should automatically get an external IP:

```bash
kubectl get service sds-middleware-service -n sds-middleware
```

You should see something like:
```
NAME                      TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
sds-middleware-service    LoadBalancer   10.96.X.X       localhost     8080:XXXXX/TCP   1m
```

### Access the Application
Open your browser and navigate to:
- **Main App**: http://localhost:8080
- **Admin Console**: http://localhost:8080/admin
- **Operations Console**: http://localhost:8080/ops

### Port Forward (Alternative)
If LoadBalancer doesn't work, use port-forward:
```bash
kubectl port-forward -n sds-middleware service/sds-middleware-service 8080:8080
```

## Monitoring and Troubleshooting

### View All Resources
```bash
kubectl get all -n sds-middleware
```

### Check Pod Status
```bash
kubectl get pods -n sds-middleware
```

### View Application Logs
```bash
# App logs
kubectl logs -n sds-middleware -l app=sds-middleware --tail=100 -f

# MySQL logs
kubectl logs -n sds-middleware -l app=mysql --tail=100 -f
```

### Describe Resources (for debugging)
```bash
# Describe app pod
kubectl describe pod -n sds-middleware -l app=sds-middleware

# Describe MySQL pod
kubectl describe pod -n sds-middleware -l app=mysql
```

### Execute Commands in Pods
```bash
# Access app container shell
kubectl exec -it -n sds-middleware deployment/sds-middleware-app -- /bin/bash

# Access MySQL CLI
kubectl exec -it -n sds-middleware deployment/mysql -- mysql -u dbtester -psupersecret my_app_db
```

### Check Database Connectivity
```bash
# Test from app pod to database
kubectl exec -it -n sds-middleware deployment/sds-middleware-app -- nc -zv db 3306
```

## Updating the Application

### Rebuild and Update Image
```bash
# Rebuild the Docker image
docker build -t sds-middleware:latest .

# Restart the deployment to use the new image
kubectl rollout restart deployment/sds-middleware-app -n sds-middleware

# Watch the rollout status
kubectl rollout status deployment/sds-middleware-app -n sds-middleware
```

## Scaling

### Scale Application Replicas
```bash
kubectl scale deployment/sds-middleware-app -n sds-middleware --replicas=3
```

### View Scaled Pods
```bash
kubectl get pods -n sds-middleware -l app=sds-middleware
```

## Cleanup

### Delete All Resources
```bash
kubectl delete namespace sds-middleware
```

### Delete Specific Resources
```bash
# Delete app only
kubectl delete -f k8s/app.yaml

# Delete MySQL only
kubectl delete -f k8s/mysql.yaml

# Delete ConfigMaps
kubectl delete -f k8s/configmap.yaml
```

## Persistent Storage Notes

- **MySQL Data**: Stored in PersistentVolumeClaim (survives pod restarts)
- **App Storages/Logs**: Using emptyDir (temporary, lost on pod restart)

### To Persist App Data (Optional)
Edit `k8s/app.yaml` and replace `emptyDir: {}` with PersistentVolumeClaims:

```yaml
volumes:
- name: storages
  persistentVolumeClaim:
    claimName: app-storages-pvc
- name: logs
  persistentVolumeClaim:
    claimName: app-logs-pvc
```

Then create the PVCs first.

## Configuration Changes

### Update Environment Variables
Edit `k8s/configmap.yaml` and apply:
```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/sds-middleware-app -n sds-middleware
```

### Update MySQL Credentials
Edit `k8s/mysql.yaml` (secret section) and apply:
```bash
kubectl apply -f k8s/mysql.yaml
kubectl rollout restart deployment/mysql -n sds-middleware
kubectl rollout restart deployment/sds-middleware-app -n sds-middleware
```

## Quick Deployment Script

For convenience, you can deploy everything at once:

```bash
# Deploy all resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/mysql.yaml
kubectl apply -f k8s/app.yaml

# Wait for everything to be ready
kubectl wait --for=condition=ready pod --all -n sds-middleware --timeout=180s

# Show service endpoints
kubectl get services -n sds-middleware
```

## OrbStack-Specific Features

OrbStack provides several conveniences:

1. **Automatic LoadBalancer**: LoadBalancer services automatically get `localhost` endpoint
2. **Shared Docker Images**: Images built with Docker are automatically available to Kubernetes
3. **Fast Startup**: Lightweight and fast compared to other Kubernetes solutions
4. **Resource Efficiency**: Lower resource usage on Mac

## Troubleshooting OrbStack

### Kubernetes Not Starting
```bash
# Restart OrbStack
# From OrbStack menu: Quit OrbStack, then restart

# Or from terminal
orb stop
orb start
```

### Image Not Found
Make sure the image was built locally:
```bash
docker images | grep sds-middleware
```

If missing, rebuild:
```bash
docker build -t sds-middleware:latest .
```

### Context Issues
Ensure kubectl is using OrbStack context:
```bash
kubectl config current-context
kubectl config use-context orbstack
```

## Additional Resources

- [OrbStack Documentation](https://docs.orbstack.dev/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
