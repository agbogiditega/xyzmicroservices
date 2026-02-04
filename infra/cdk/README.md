# CDK Deployment Guide (Exemplar Orders Service)

This guide deploys the exemplar **Orders** microservice on **AWS ECS Fargate** using **AWS CDK (Python)**.

The stack provisions:
- VPC (2 AZs, minimal)
- ECS Cluster + Fargate service behind an Application Load Balancer (ALB)
- SNS topic for order events
- Example downstream SQS queue + DLQ subscribed to the SNS topic (represents a consumer like Inventory)
- CloudWatch Logs

Important implementation details:
- The service exposes `GET /health` and the ALB target group health check is configured to use it.
- The service listens on port **8000** in all environments.
- The container image is built and published automatically during `cdk deploy` via a CDK Docker asset (no manual ECR push is required).

---

## Prerequisites

You need:
- AWS CLI v2
- Node.js 18+ (for the CDK CLI)
- AWS CDK v2 CLI
- Python 3.11+
- Docker (CDK builds the container image locally)

Verify:
```bash
aws --version
node --version
cdk --version
python3 --version
docker --version
```

Configure credentials:
```bash
aws configure
aws sts get-caller-identity
```

---

## Deploy

From the repository root:
```bash
cd infra/cdk
python3 -m venv .venv
source .venv/bin/activate   #macOS/Linux
.\.venv\Scripts\Activate.ps1  #windows
pip install -r requirements.txt
```

Bootstrap CDK (one-time per account/region):
```bash
#macOS/Linux
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGION=us-east-1
cdk bootstrap -c account=$ACCOUNT_ID -c region=$REGION

#windows
$Env:ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$Env:REGION = "us-east-1"
cdk bootstrap aws://$Env:ACCOUNT_ID/$Env:REGION

```

Deploy the stack:
```bash
#macOS/Linux
cdk deploy -c account=$ACCOUNT_ID -c region=$REGION

#windows
cdk deploy -c account=$Env:ACCOUNT_ID -c region=$Env:REGION
```

When deployment finishes, CDK prints outputs including:
- `AlbDnsName` (public URL for Orders)
- `OrderEventsTopicArn`
- `InventoryQueueUrl`
- `OrdersImageUri`

---

## Verify

Call the health endpoint:
```bash
export ALB_DNS=<paste AlbDnsName here>
curl -s http://${ALB_DNS}/health
```

Create an order:
```bash
curl -s -X POST http://${ALB_DNS}/orders   -H "Content-Type: application/json"   -d '{"sku":"SKU-123","qty":2}'
```

---

## Destroy (Cleanup)

```bash
#macOS/Linux
cdk destroy -c account=$ACCOUNT_ID -c region=$REGION

#windows
cd destroy-c account=$Env:ACCOUNT_ID -c region=$Env:REGION
```

---

## Troubleshooting

If deployment fails during asset publishing:
- Ensure Docker Desktop (or Docker Engine) is running.
- Ensure you can run `docker ps` without errors.

If the ALB target group shows unhealthy:
- Confirm `GET /health` returns HTTP 200.
- Confirm the container is listening on port 8000 (the stack sets `PORT=8000`).

If you see permission errors:
- Ensure your AWS identity can deploy CloudFormation, IAM, VPC/EC2, ECS, ELBv2, SNS, SQS, and CloudWatch Logs.
