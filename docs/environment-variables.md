# Environment Variables

## Application
MESSAGE_BACKEND=rabbitmq|sqs
AWS_REGION=us-east-1

## Messaging
SNS_TOPIC_ARN=arn:aws:sns:...
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/...

## Local Testing
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

## Secrets
Secrets are stored in AWS Secrets Manager:
- /xyz/orders/db-password
- /xyz/shared/api-keys
