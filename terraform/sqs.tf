# Work queue: one order_created message per order, consumed only by
# payment-service to trigger processing. This drives the pipeline.
resource "aws_sqs_queue" "order_created" {
  name                      = "order-created-production"
  message_retention_seconds = 86400 # 1 day retention
  receive_wait_time_seconds = 20    # Enable long polling natively
  visibility_timeout_seconds = 30   # Should exceed the worker's processing time per order

  tags = {
    Environment = "production"
    Project     = "payflow"
  }
}

# Event log: every service publishes order_created and payment_completed
# events here. Consumed only by notification-service. Kept separate from
# order_created so the two consumers don't compete for the same messages.
resource "aws_sqs_queue" "order_events" {
  name                      = "order-events-production"
  message_retention_seconds = 86400 # 1 day retention
  receive_wait_time_seconds = 20    # Enable long polling natively

  tags = {
    Environment = "production"
    Project     = "payflow"
  }
}

output "order_created_queue_url" {
  value       = aws_sqs_queue.order_created.id
  description = "The URL of the order-created work queue (consumed by payment-service)"
}

output "sqs_queue_url" {
  value       = aws_sqs_queue.order_events.id
  description = "The URL of the order-events log queue (consumed by notification-service)"
}
