# PostgreSQL RDS to MSK CDC Infrastructure

This directory contains CloudFormation templates and scripts to deploy the infrastructure for the PostgreSQL RDS to MSK CDC tutorial.

## Infrastructure Components

The CloudFormation stack creates the following AWS resources:

1. **VPC and Network**:
   - VPC with public and private subnets
   - Internet Gateway
   - NAT Gateways for private subnet access
   - Route tables and associations

2. **PostgreSQL RDS**:
   - PostgreSQL 13.7 instance
   - Parameter group with logical replication enabled
   - Security group for database access
   - DB subnet group

3. **MSK Cluster**:
   - Kafka 2.8.1 cluster with 2 broker nodes
   - Security group for Kafka access
   - EBS volumes for broker storage

4. **S3 Bucket**:
   - Bucket for CDC events
   - Versioning enabled
   - Lifecycle rules for cost optimization

5. **IAM Roles**:
   - MSK Connect role with S3 access permissions

## Prerequisites

- AWS CLI installed and configured
- Appropriate AWS permissions to create the resources
- Sufficient AWS quota for the resources

## Security Configuration

The deployment script supports multiple ways to configure the database password securely:

### Option 1: Environment Variable
```bash
export DB_PASSWORD="your_secure_password"
./deploy.sh
```

### Option 2: .env File (Recommended)
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your password
DB_PASSWORD=your_secure_password

# Deploy
./deploy.sh
```

### Option 3: Interactive Prompt
If no password is configured, the script will prompt you to enter one.

### Option 4: Command Line Override
```bash
./deploy.sh --password "your_secure_password"
```

**Note**: The .env file is automatically ignored by git to prevent accidental password commits.

## Deployment

To deploy the infrastructure, use the provided deployment script:

```bash
./deploy.sh [options]
```

### Options

- `--stack-name NAME`: CloudFormation stack name (default: postgres-msk-cdc)
- `--environment ENV`: Environment (dev or prod) (default: dev)
- `--region REGION`: AWS region (default: us-east-1)
- `--template-file FILE`: CloudFormation template file (default: postgres-msk-cdc.yaml)
- `--help`: Show help message

### Examples

Deploy to development environment:
```bash
# Using .env file (recommended)
cp .env.example .env
# Edit .env with your password
./deploy.sh --environment dev

# Using environment variable
DB_PASSWORD="your_password" ./deploy.sh --environment dev
```

Deploy to production environment:
```bash
# Always use secure password for production
DB_PASSWORD="your_secure_production_password" ./deploy.sh --environment prod --stack-name postgres-msk-cdc-prod
```

## Environment-Specific Configurations

The stack supports different configurations for development and production environments:

| Resource | Development | Production |
|----------|-------------|------------|
| RDS Instance Class | db.t3.micro | db.t3.micro |
| RDS Multi-AZ | No | Yes |
| RDS Backup Retention | 1 day | 7 days |
| MSK Instance Type | kafka.t3.small | kafka.t3.small |

## Cleanup

To delete the stack and all resources:

```bash
aws cloudformation delete-stack --stack-name postgres-msk-cdc
```

## Troubleshooting

If the stack deployment fails, check the CloudFormation events:

```bash
aws cloudformation describe-stack-events --stack-name postgres-msk-cdc
```

Common issues:
- Insufficient permissions
- VPC or subnet CIDR conflicts
- Resource limits exceeded 