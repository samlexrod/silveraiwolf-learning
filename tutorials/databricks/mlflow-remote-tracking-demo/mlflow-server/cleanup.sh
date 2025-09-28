#!/bin/bash

set -e

# Configuration
STACK_NAME="mlflow-infrastructure"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🧹 Starting MLflow ECS cleanup..."
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Stack Name: $STACK_NAME"

# Get ECR repository name before deleting the stack
ECR_REPO=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ECRRepository`].OutputValue' \
    --output text 2>/dev/null || echo "")

ECS_CLUSTER=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' \
    --output text 2>/dev/null || echo "")

ARTIFACTS_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucket`].OutputValue' \
    --output text 2>/dev/null || echo "")

# Stop ECS service if it exists
if [[ -n "$ECS_CLUSTER" ]]; then
    echo "🛑 Stopping ECS service..."
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service mlflow-server \
        --desired-count 0 \
        --region $REGION 2>/dev/null || echo "Service not found or already stopped"

    # Wait for tasks to stop
    echo "⏳ Waiting for tasks to stop..."
    aws ecs wait services-stable --cluster $ECS_CLUSTER --services mlflow-server --region $REGION 2>/dev/null || echo "Service wait skipped"

    # Delete service
    echo "🗑️ Deleting ECS service..."
    aws ecs delete-service \
        --cluster $ECS_CLUSTER \
        --service mlflow-server \
        --region $REGION 2>/dev/null || echo "Service not found"
fi

# Empty S3 bucket if it exists
if [[ -n "$ARTIFACTS_BUCKET" ]]; then
    echo "🗂️ Emptying S3 artifacts bucket..."
    aws s3 rm s3://$ARTIFACTS_BUCKET --recursive 2>/dev/null || echo "Bucket not found or already empty"
fi

# Delete all images from ECR repository
if [[ -n "$ECR_REPO" ]]; then
    echo "🐳 Deleting ECR images..."
    REPO_NAME=$(echo $ECR_REPO | cut -d'/' -f2)
    aws ecr list-images --repository-name $REPO_NAME --region $REGION --query 'imageIds[*]' --output json > /tmp/images.json 2>/dev/null || echo "[]" > /tmp/images.json

    if [[ $(cat /tmp/images.json | jq '. | length') -gt 0 ]]; then
        aws ecr batch-delete-image \
            --repository-name $REPO_NAME \
            --image-ids file:///tmp/images.json \
            --region $REGION 2>/dev/null || echo "No images to delete"
    fi
    rm -f /tmp/images.json
fi

# Delete CloudFormation stack
echo "☁️ Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION

echo "⏳ Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION

echo ""
echo "✅ MLflow ECS cleanup completed successfully!"
echo ""
echo "🗑️ All resources have been deleted:"
echo "  - ECS Service and Tasks"
echo "  - ECS Cluster"
echo "  - Application Load Balancer"
echo "  - RDS Database"
echo "  - S3 Artifacts Bucket"
echo "  - ECR Repository and Images"
echo "  - VPC and Networking Components"
echo "  - IAM Roles and Policies"
echo "  - CloudWatch Log Groups"
echo ""
echo "💡 Note: This cleanup script removes ALL resources created by the deployment."