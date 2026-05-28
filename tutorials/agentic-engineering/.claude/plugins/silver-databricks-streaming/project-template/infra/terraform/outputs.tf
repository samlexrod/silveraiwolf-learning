output "public_ip" {
  description = "Public IP of the CDC EC2 instance"
  value       = aws_instance.cdc_stack.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ${var.key_path} ec2-user@${aws_instance.cdc_stack.public_ip}"
}

output "kafka_bootstrap_servers" {
  description = "Kafka bootstrap servers (Redpanda external listener)"
  value       = "${aws_instance.cdc_stack.public_ip}:19092"
}

output "postgres_host" {
  description = "PostgreSQL connection host"
  value       = "${aws_instance.cdc_stack.public_ip}:5432"
}

output "debezium_api" {
  description = "Debezium Connect REST API URL"
  value       = "http://${aws_instance.cdc_stack.public_ip}:8083"
}

output "redpanda_console" {
  description = "Redpanda Console UI URL — browse topics, messages, consumer groups"
  value       = "http://${aws_instance.cdc_stack.public_ip}:8080"
}

output "key_path" {
  description = "Path to the SSH private key"
  value       = var.key_path
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint (HTTPS)"
  value       = var.enable_opensearch ? "https://${aws_opensearch_domain.gold[0].endpoint}" : "not provisioned — set enable_opensearch = true"
}

output "opensearch_dashboard" {
  description = "OpenSearch Dashboards URL"
  value       = var.enable_opensearch ? "https://${aws_opensearch_domain.gold[0].endpoint}/_dashboards" : "not provisioned"
}
