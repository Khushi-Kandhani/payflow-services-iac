# The main ECS container cluster
resource "aws_ecs_cluster" "payflow_cluster" {
  name = "payflow-production-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECR Repositories (Where your GitHub Action will push your built Docker images)
resource "aws_ecr_repository" "order_service" {
  name                 = "payflow-order-service"
  image_tag_mutability = "MUTABLE"
}

resource "aws_ecr_repository" "payment_service" {
  name                 = "payflow-payment-service"
  image_tag_mutability = "MUTABLE"
}

resource "aws_ecr_repository" "notification_service" {
  name                 = "payflow-notification-service"
  image_tag_mutability = "MUTABLE"
}
