output "backend_ecr_url" {
  description = "Push the backend image here."
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_url" {
  description = "Push the frontend image here."
  value       = aws_ecr_repository.frontend.repository_url
}

output "cluster_name" {
  description = "EKS cluster name (use with: aws eks update-kubeconfig)."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "exchange_secret_arn" {
  description = "Secrets Manager ARN holding exchange credentials."
  value       = aws_secretsmanager_secret.exchange.arn
}
