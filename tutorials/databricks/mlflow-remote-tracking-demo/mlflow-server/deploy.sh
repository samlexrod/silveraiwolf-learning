#!/bin/bash

set -e

# Configuration
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
STACK_NAME="mlflow-infrastructure-$TIMESTAMP"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Starting MLflow ECS deployment..."
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Stack Name: $STACK_NAME"

# Step 1: Deploy CloudFormation infrastructure
echo "📦 Deploying CloudFormation infrastructure..."
# Generate a valid RDS password (alphanumeric only, 16 chars)
DB_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16)

aws cloudformation deploy \
    --template-file infrastructure.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION \
    --parameter-overrides \
        DBPassword=$DB_PASSWORD

# Wait for stack to complete
echo "⏳ Waiting for CloudFormation stack to complete..."
aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION || \
aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $REGION

# Get stack outputs
ECR_REPO=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ECRRepository`].OutputValue' \
    --output text)

DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
    --output text)

ARTIFACTS_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ArtifactsBucket`].OutputValue' \
    --output text)

ECS_CLUSTER=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSCluster`].OutputValue' \
    --output text)

PRIVATE_SUBNETS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnets`].OutputValue' \
    --output text)

SECURITY_GROUP=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroup`].OutputValue' \
    --output text)

TARGET_GROUP=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ALBTargetGroup`].OutputValue' \
    --output text)

TASK_EXECUTION_ROLE=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`TaskExecutionRole`].OutputValue' \
    --output text)

MLFLOW_TASK_ROLE=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`MLflowTaskRole`].OutputValue' \
    --output text)

echo "✅ Infrastructure deployed successfully"
echo "ECR Repository: $ECR_REPO"
echo "Database Endpoint: $DB_ENDPOINT"
echo "Artifacts Bucket: $ARTIFACTS_BUCKET"

# Step 2: Build and push Docker image
echo "🐳 Building and pushing Docker image..."

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

# Build image for x86_64 architecture
docker build --platform linux/amd64 -t mlflow-server .

# Tag image
docker tag mlflow-server:latest $ECR_REPO:latest

# Push image
docker push $ECR_REPO:latest

echo "✅ Docker image pushed successfully"

# Step 3: Update task definition with actual values
echo "📝 Creating ECS task definition..."

# Create updated task definition
cat > task-definition-updated.json << EOF
{
  "family": "mlflow-server",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "runtimePlatform": {
    "cpuArchitecture": "X86_64",
    "operatingSystemFamily": "LINUX"
  },
  "executionRoleArn": "$TASK_EXECUTION_ROLE",
  "taskRoleArn": "$MLFLOW_TASK_ROLE",
  "containerDefinitions": [
    {
      "name": "mlflow-server",
      "image": "$ECR_REPO:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MLFLOW_BACKEND_STORE_URI",
          "value": "postgresql://mlflow_user@$DB_ENDPOINT:5432/mlflow"
        },
        {
          "name": "MLFLOW_DEFAULT_ARTIFACT_ROOT",
          "value": "s3://$ARTIFACTS_BUCKET/artifacts"
        },
        {
          "name": "MLFLOW_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "MLFLOW_PORT",
          "value": "5000"
        }
      ],
      "secrets": [
        {
          "name": "PGPASSWORD",
          "valueFrom": "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:mlflow/db-password:password::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mlflow-server",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "essential": true,
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:5000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register task definition
TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://task-definition-updated.json \
    --region $REGION \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ Task definition registered: $TASK_DEF_ARN"

# Step 4: Create ECS service
echo "🚀 Creating ECS service..."

IFS=',' read -ra SUBNET_ARRAY <<< "$PRIVATE_SUBNETS"

# Get public subnets for Databricks Free Edition access
PUBLIC_SUBNETS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnets`].OutputValue' \
    --output text)

IFS=',' read -ra PUBLIC_SUBNET_ARRAY <<< "$PUBLIC_SUBNETS"

aws ecs create-service \
    --cluster $ECS_CLUSTER \
    --service-name mlflow-server \
    --task-definition mlflow-server \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${PUBLIC_SUBNET_ARRAY[0]},${PUBLIC_SUBNET_ARRAY[1]}],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=$TARGET_GROUP,containerName=mlflow-server,containerPort=5000 \
    --health-check-grace-period-seconds 300 \
    --enable-execute-command \
    --region $REGION

echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable --cluster $ECS_CLUSTER --services mlflow-server --region $REGION

# Get load balancer URL
LB_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
    --output text)

echo ""
echo "🎉 MLflow server deployment completed successfully!"
echo ""
echo "📊 MLflow Server URL: $LB_URL"
echo "🗄️  Database Endpoint: $DB_ENDPOINT"
echo "📦 Artifacts Bucket: $ARTIFACTS_BUCKET"
echo ""
echo "🔧 To update the deployment:"
echo "  1. Make changes to your code"
echo "  2. Run: docker build -t mlflow-server . && docker tag mlflow-server:latest $ECR_REPO:latest && docker push $ECR_REPO:latest"
echo "  3. Run: aws ecs update-service --cluster $ECS_CLUSTER --service mlflow-server --force-new-deployment --region $REGION"
echo ""
echo "🗑️  To clean up resources:"
echo "  aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"