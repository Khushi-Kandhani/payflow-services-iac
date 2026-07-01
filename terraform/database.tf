# Security Group to lock down Postgres access
resource "aws_security_group" "db_sg" {
  name        = "payflow-db-sg"
  description = "Allow inbound PostgreSQL traffic from VPC"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "PostgreSQL access from inside VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Subnet Group tells AWS where the DB can physically live
resource "aws_db_subnet_group" "db_subnet_group" {
  name       = "payflow-db-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

# The managed PostgreSQL instance (Rectified for Perfect 10 Security)
resource "aws_db_instance" "postgres" {
  identifier             = "payflow-db-production"
  allocated_storage      = 20
  max_allocated_storage  = 100
  engine                 = "postgres"
  engine_version         = "16.1"
  instance_class         = "db.t4g.micro" 
  db_name                = "payflow_db"
  username               = "postgres"
  
  # Dynamic Reference: Pulls the random string straight from Secrets Manager
  password               = aws_secretsmanager_secret_version.db_password_val.secret_string
  
  db_subnet_group_name   = aws_db_subnet_group.db_subnet_group.name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  skip_final_snapshot    = true
}

output "db_endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "The database connection string endpoint"
}
