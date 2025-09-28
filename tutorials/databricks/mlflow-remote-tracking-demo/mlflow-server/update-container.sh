#!/bin/bash

set -e

# Get the latest stack name
LATEST_STACK=$(aws cloudformation list-stacks --region us-east-1 --query 'StackSummaries[?starts_with(StackName, `mlflow-infrastructure`) && StackStatus == `CREATE_COMPLETE`].StackName' --output text | head -1)

if [[ -z "$LATEST_STACK" ]]; then
    echo "❌ No successful MLflow stack found!"
    exit 1
fi

echo "🔄 Updating container for stack: $LATEST_STACK"

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get ECR repository from the successful stack
ECR_REPO=$(aws cloudformation describe-stacks \
    --stack-name $LATEST_STACK \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ECRRepository`].OutputValue' \
    --output text)

ECS_CLUSTER=$(aws cloudformation describe-stacks \
    --stack-name $LATEST_STACK \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' \
    --output text)

echo "📦 ECR Repository: $ECR_REPO"
echo "🚀 ECS Cluster: $ECS_CLUSTER"

# Step 1: Build and push the fixed Docker image
echo "🐳 Building fixed Docker image..."

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

# Build image for x86_64 architecture
docker build --platform linux/amd64 -t mlflow-server .

# Tag image
docker tag mlflow-server:latest $ECR_REPO:latest

# Push image
docker push $ECR_REPO:latest

echo "✅ Docker image updated successfully"

# Step 2: Force ECS service deployment to pull new image
echo "🔄 Updating ECS service to use new image..."

aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service mlflow-server \
    --force-new-deployment \
    --region $REGION

echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable --cluster $ECS_CLUSTER --services mlflow-server --region $REGION

# Get load balancer URL
LB_URL=$(aws cloudformation describe-stacks \
    --stack-name $LATEST_STACK \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
    --output text)

echo ""
echo "✅ Container update completed successfully!"
echo "📊 MLflow Server URL: $LB_URL"
echo ""