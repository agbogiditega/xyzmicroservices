# Messaging Topology

## SNS Topics
- arn:aws:sns:us-east-1:123456789012:xyz-orders-events

## SQS Queues
- xyz-inventory-queue
- xyz-payments-queue

## Subscriptions
- SNS Topic → Inventory Queue
- SNS Topic → Payments Queue

## Dead Letter Queues
- xyz-inventory-dlq
- xyz-payments-dlq

## Retry Policy
- maxReceiveCount: 5
