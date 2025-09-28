# MLflow Server deployment on AWS ECS

⚠️ **DEMO/DEVELOPMENT PURPOSES ONLY** ⚠️

This directory contains a complete MLflow server deployment on AWS ECS using Fargate, with PostgreSQL RDS backend and S3 artifact storage.

**⚠️ SECURITY WARNING**: This deployment is configured for **demonstration and development purposes only**. It includes intentional security trade-offs to enable access from Databricks Free Edition. **DO NOT USE IN PRODUCTION** without implementing the security hardening measures listed below.

## Architecture

- **ECS Fargate**: Serverless container hosting
- **Application Load Balancer**: Public access with health checks
- **RDS PostgreSQL**: Backend store for MLflow metadata
- **S3**: Artifact storage for models and files
- **ECR**: Container registry for MLflow Docker image
- **VPC**: Isolated network with public/private subnets

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed and running
- `jq` installed (for JSON parsing)

### Deploy

```bash
./deploy.sh
```

This script will:
1. Deploy the CloudFormation infrastructure
2. Build and push the Docker image to ECR
3. Create and start the ECS service
4. Output the MLflow server URL

### Access MLflow

After deployment completes, access MLflow at the provided Load Balancer URL:
```
http://mlflow-alb-xxxxxxxxx.region.elb.amazonaws.com
```

Example successful deployment URL:
```
http://MLflow-ALB-968296422.us-east-1.elb.amazonaws.com
```

### Databricks Integration

To use this MLflow server with Databricks Free Edition, set the tracking URI in your notebook:

```python
import mlflow
mlflow.set_tracking_uri("http://MLflow-ALB-968296422.us-east-1.elb.amazonaws.com")

# Now you can log experiments
with mlflow.start_run():
    mlflow.log_param("param1", 5)
    mlflow.log_metric("metric1", 0.85)
```

### Clean Up

```bash
./cleanup.sh
```

This removes all AWS resources created by the deployment.

## Configuration

### Environment Variables

The MLflow server supports these environment variables:

- `MLFLOW_BACKEND_STORE_URI`: Database connection string
- `MLFLOW_DEFAULT_ARTIFACT_ROOT`: S3 bucket for artifacts
- `MLFLOW_HOST`: Server bind address (default: 0.0.0.0)
- `MLFLOW_PORT`: Server port (default: 5000)

### Scaling

Modify `desiredCount` in the service definition to scale horizontally:

```bash
aws ecs update-service \
    --cluster mlflow-cluster \
    --service mlflow-server \
    --desired-count 2
```

### Resource Limits

Adjust CPU/memory in `task-definition.json`:
- CPU: 256, 512, 1024, 2048, 4096
- Memory: 512MB to 30GB (depends on CPU)

## Security

### ⚠️ Current Demo Configuration:
- MLflow server runs in public subnets (accessible by Databricks Free Edition)
- **Port 5000 open to internet (0.0.0.0/0)** for MLflow access
- Database access restricted to ECS security group
- S3 bucket has public access blocked
- Secrets stored in AWS Secrets Manager
- Container logs sent to CloudWatch
- **Database encryption disabled** (for demo cost savings)
- **No database backups** (for demo cost savings)

### 🔒 Production Security Hardening Required:

Before using in production, implement these security measures:

#### 1. Network Access Control
```yaml
# Replace in infrastructure.yaml
SecurityGroupIngress:
  - IpProtocol: tcp
    FromPort: 5000
    ToPort: 5000
    CidrIp: "YOUR_DATABRICKS_IP_RANGE/32"  # Instead of 0.0.0.0/0
```

#### 2. Database Security
```yaml
# Enable in infrastructure.yaml
StorageEncrypted: true        # Enable encryption
BackupRetentionPeriod: 7      # Enable backups
DeletionProtection: true      # Prevent accidental deletion
```

#### 3. Additional Security Measures
- Configure VPC endpoints for ECR/S3 access
- Enable AWS Config for compliance monitoring
- Set up CloudTrail for audit logging
- Implement AWS WAF for additional protection
- Use private ECR repositories with image scanning
- Enable GuardDuty for threat detection

#### 4. Access Control
- Create specific IAM roles for different user groups
- Implement API authentication/authorization
- Use Application Load Balancer with SSL/TLS termination
- Configure Route 53 with proper DNS controls

## Monitoring

- ECS service metrics available in CloudWatch
- Application logs in CloudWatch Logs group `/ecs/mlflow-server`
- Load balancer metrics and health checks
- RDS performance insights available

## Management Commands

### View Logs
```bash
aws logs tail /ecs/mlflow-server --follow --region us-east-1
```

### Scale Service
```bash
aws ecs update-service --cluster mlflow-cluster --service mlflow-server --desired-count 2 --region us-east-1
```

### Update Container Image
If you need to rebuild and update the Docker image:
```bash
./update-container.sh
```

## Troubleshooting

### Service Won't Start

Check ECS service events:
```bash
aws ecs describe-services --cluster mlflow-cluster --services mlflow-server --region us-east-1
```

### Container Architecture Issues

If you get "exec format error", ensure proper cross-platform build:
```bash
docker buildx build --platform linux/amd64 -t mlflow-server --push .
```

### Database Connection Issues

1. Verify RDS endpoint in task definition
2. Check security group rules
3. Validate database credentials in Secrets Manager

### Container Logs

View logs in CloudWatch or via CLI:
```bash
aws logs tail /ecs/mlflow-server --follow --region us-east-1
```

## Cost Optimization (Demo Configuration)

**⚠️ Demo Cost Savings (NOT Production Ready):**
- Database encryption disabled
- No database backups (BackupRetentionPeriod: 0)
- Minimal RDS instance size: `db.t4g.micro`
- No Multi-AZ deployment
- Basic monitoring only

**Production Considerations:**
- Enable database encryption and backups
- Use appropriate instance sizes for workload
- Consider reserved capacity for cost savings
- Implement S3 lifecycle policies for artifact storage
- Enable detailed monitoring and alerting

## Files

- `Dockerfile`: MLflow server container definition
- `infrastructure.yaml`: Complete AWS infrastructure
- `task-definition.json`: ECS task template
- `service-definition.json`: ECS service template
- `deploy.sh`: Automated deployment script
- `cleanup.sh`: Resource cleanup script
- `.dockerignore`: Docker build exclusions

## Support

For issues with MLflow itself, see the [official MLflow documentation](https://mlflow.org/docs/latest/index.html).

