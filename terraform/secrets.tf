# 1. Create a secret resource wrapper in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name        = "payflow-production-db-password-v2"
  description = "Managed password for the PayFlow RDS PostgreSQL instance"
  
  # Automatically cleans up old secrets if you tear down the infrastructure
  recovery_window_in_days = 0 
}

# 2. Generate a secure, random 16-character string to use as the password
resource "random_password" "postgres_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# 3. Store that generated random password securely inside the secret wrapper
resource "aws_secretsmanager_secret_version" "db_password_val" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.postgres_password.result
}
