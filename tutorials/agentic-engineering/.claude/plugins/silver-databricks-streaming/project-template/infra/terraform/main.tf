terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- Data sources ---

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_vpc" "default" {
  default = true
}

# --- Security Group ---

resource "aws_security_group" "cdc_stack" {
  name_prefix = "${var.project_name}-"
  description = "Allow SSH, Kafka, and Postgres access for CDC tutorial"
  vpc_id      = data.aws_vpc.default.id

  # SSH
  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Kafka / Redpanda (external listener)
  dynamic "ingress" {
    for_each = var.databricks_nat_cidrs
    content {
      description = "Kafka access from Databricks"
      from_port   = 19092
      to_port     = 19092
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # Postgres (for seeding and verification)
  ingress {
    description = "Postgres access"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Debezium Connect REST API
  ingress {
    description = "Debezium Connect REST API"
    from_port   = 8083
    to_port     = 8083
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Redpanda Console UI
  ingress {
    description = "Redpanda Console UI"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # All outbound
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "${var.project_name}-sg"
    Project = var.project_name
  }
}

# --- EC2 Instance ---

resource "aws_instance" "cdc_stack" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.cdc_stack.id]

  user_data = file("${path.module}/user-data.sh")

  root_block_device {
    volume_size = 30  # GB — AMI minimum is 30GB; enough for Redpanda + Postgres data
    volume_type = "gp3"
  }

  tags = {
    Name    = "${var.project_name}-cdc"
    Project = var.project_name
  }
}

# --- OpenSearch Domain ---

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# NOTE: OpenSearch is public-access (no VPC attachment) so Databricks serverless
# can reach it, and the EC2-based PySpark sink can also reach it.
# In production with VPC-based OpenSearch, use a managed cluster with VPC
# peering/PrivateLink instead of serverless pipelines for the sink.

resource "aws_opensearch_domain" "gold" {
  count          = var.enable_opensearch ? 1 : 0
  domain_name    = "${var.project_name}-gold"
  engine_version = "OpenSearch_2.13"

  cluster_config {
    instance_type  = var.opensearch_instance_type
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10  # GB — sufficient for Gold table indices
    volume_type = "gp3"
  }

  node_to_node_encryption {
    enabled = true
  }

  encrypt_at_rest {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = var.opensearch_master_user
      master_user_password = var.opensearch_master_password
    }
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "*" }
      Action    = "es:*"
      Resource  = "arn:aws:es:${var.aws_region}:*:domain/${var.project_name}-gold/*"
    }]
  })

  tags = {
    Name    = "${var.project_name}-opensearch"
    Project = var.project_name
  }
}
