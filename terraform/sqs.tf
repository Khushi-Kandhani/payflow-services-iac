resource "aws_sqs_queue" "order_events" {
  name                      = "order-events-production"
  message_retention_seconds = 86400 # 1 day retention
  receive_wait_time_seconds = 20    # Enable long polling natively

  tags = {
    Environment = "production"
    Project     = "payflow"
  }
}

output "sqs_queue_url" {
  value       = aws_sqs_queue.order_events.id
  description = "The URL of the production SQS Queue"
}
