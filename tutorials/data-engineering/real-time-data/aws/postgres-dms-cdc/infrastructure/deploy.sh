#!/bin/bash
set -e

# Default values
STACK_NAME="postgres-dms-cdc"
ENVIRONMENT="dev"
REGION="us-east-1"
TEMPLATE_FILE="postgres-dms-cdc.yaml"

# Load environment variables from .env file if it exists
if [[ -f ".env" ]]; then
    source .env
fi

# Set default password only if not provided via environment variable
if [[ -z "$DB_PASSWORD" ]]; then
    echo "⚠️  No DB_PASSWORD environment variable found."
    echo "   For production use, set DB_PASSWORD environment variable or create a .env file"
    echo "   For tutorial purposes, you can use the default password or enter your own."
    read -s -p "Enter database password (or press Enter for default '12345678'): " DB_PASSWORD
    echo
    
    # Use default if user didn't enter anything
    if [[ -z "$DB_PASSWORD" ]]; then
        DB_PASSWORD="12345678"
        echo "Using default password for tutorial purposes"
    fi
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --stack-name)
      STACK_NAME="$2"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --template-file)
      TEMPLATE_FILE="$2"
      shift 2
      ;;
    --password)
      DB_PASSWORD="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --stack-name NAME       CloudFormation stack name (default: postgres-dms-cdc)"
      echo "  --environment ENV       Environment (dev or prod) (default: dev)"
      echo "  --region REGION         AWS region (default: us-east-1)"
      echo "  --template-file FILE    CloudFormation template file (default: postgres-dms-cdc.yaml)"
      echo "  --password PASSWORD     Database password (overrides environment variable)"
      echo "  --help                  Show this help message"
      echo ""
      echo "Password Configuration:"
      echo "  - Set DB_PASSWORD environment variable"
      echo "  - Create a .env file with DB_PASSWORD=your_password"
      echo "  - Use --password option to override"
      echo "  - Interactive prompt if no password is provided"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
  echo "Error: Environment must be either 'dev' or 'prod'"
  exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo "Error: AWS CLI is not installed"
  exit 1
fi

# Check if template file exists
if [[ ! -f "$TEMPLATE_FILE" ]]; then
  echo "Error: Template file '$TEMPLATE_FILE' not found"
  exit 1
fi

# Deploy the CloudFormation stack
echo "Deploying CloudFormation stack '$STACK_NAME' in environment '$ENVIRONMENT'..."

# Debug output
echo "Debug: Stack Name = '$STACK_NAME'"
echo "Debug: Environment = '$ENVIRONMENT'"
echo "Debug: Region = '$REGION'"
echo "Debug: Template File = '$TEMPLATE_FILE'"
echo "Debug: Using password: '$DB_PASSWORD'"

aws cloudformation deploy \
  --template-file "$TEMPLATE_FILE" \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    Environment="$ENVIRONMENT" \
    DBPassword="$DB_PASSWORD" \
  --capabilities CAPABILITY_IAM \
  --region "$REGION"

# Check if deployment was successful
if [[ $? -eq 0 ]]; then
  echo "✅ Stack deployment completed successfully"
  
  # Get stack outputs
  echo "Stack outputs:"
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs" \
    --output table \
    --region "$REGION"
else
  echo "❌ Stack deployment failed"
  exit 1
fi 