# XYZ Corporation - AWS Native Distributed Microservices Testing Framework

## Overview
This repository contains an AWS native automated testing framework for a distributed microservices platform developed in python. The platform serves as the backbone for multiple client-facing applications and is designed to run on AWS using managed infrastructure.

The testing framework ensures:
* Reliability through automated validation at every commit
* Scalability by testing service boundaries and async workflows
* Maintainability through standardized test patterns and documentation

It supports unit, integration and end-to-end (E2E) testing across services communicating via REST APIs and message queues and is fully integrated with AWS backed CI/CD pipeline.

## Prerequisites
* Python 3.11+
* Docker Desktop
* AWS CLIv2
* Least privilege IAM permissions for ECS, ECR, CloudWatch Logs, Secrets Manager and CI

## Core Technology Stack

| Layer | Technology |
| -------- | ------- |
| Language | Python 3.11 |
| API Framework | FastAPI |
| Messaging | RabbitMQ (local), Amazon SQS/SNS |
| Compute | Amazon ECS (Fargate) |
| CI/CD | GitHub --> AWS |
| Secrets | AWS Secrets Manager |
| Log & Metrics | Amazon CloudWatch |
| Tracing | AWS X-Ray |
| Container Registry | Amazon ECR |

## Local Development Setup
1. Clone the repository
```
git clone https://github.com/xyz-corp/xyz-microservices.git
cd xyz-microservices
```
2. Create and activate virtual environment
```
python -m venv .venv
source .venv/bin/activate     # macOS/Linux
.\.venv\Scripts\Activate.ps1       # windows
```
3. Install dependencies
```
# macOS/Linux
./.venv/bin/python -m pip install -U pip
./.venv/bin/python -m pip install -e ".[test]"

# windows
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e ".[test]"
```
This installs:
* Runtime dependencies (pika, uvicorn, fastapi, pydantic)
* Testing dependencies (pytest, pytest-cov, httpx, testcontainers)
* Coverage tools  
  
## Running Services Locally
### Start RabbitMQ (Docker)
```
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3.12-management
```
Management UI: http://localhost:15672  
Default credentials: guest / guest

### Run a service (i.e. Orders Service)
```
python -m uvicorn services.orders_service.app.main:app --reload --port 8000
```
API docs available at: http://localhost:8000/docs

### Testing Strategy Overview
Detailed  documentation is available in: [Testing Strategy](./docs/testing-strategy.md)

### Test Levels
| Test Type | Purpose | Location |
| -------- | ------- | -------- |
| Unit | Validate business logic | services/**/tests/unit |
| Integration | Validate service and dependencies | services/**/tests/integration | 
| End-to-End | Validate cross service workflows | tests/e2e |

## Running Tests Locally
### Run all tests
```
pytest --cov=services/orders_service/app --cov-report=term-missing --cov-report=xml --cov-fail-under=80
```

**Note: It is expected observe and overall failure when running only unit & intergation as the Total coverage will be < 80%. `publisher.py` is not execised by unit test**
### Run only unit tests
```
pytest services/**/tests/unit
```

### Run integration tests (Docker required)  
**Note:** Integration tests use testcontainers to automatically spin up RabbitMQ containers. Ensure Docker Desktop is running before executing these tests.
```
pytest services/**/tests/integration
```

### Run E2E tests
```
pytest tests/e2e
```

## Test Coverage
Generate coverage report:
```
pytest --cov --cov-report=term-missing --cov-report=xml
```
Outputs:
* Console coverage summary
* coverage.xml for CI/CD reporting tools

## CI/CD Pipeline Behavior
The GitHub actions pipeline automatically executes on:
* Pull requests
* Pushes to main

CI Steps
1. Checkout code
2. Install dependencies
3. Run unit, integration and E2E tests
4. Generate coverage reports
5. Upload coverage artifacts

CI configuration file:
```
.github/workflows/ci.yml
```

## Environment Variables
| Variable | Description | Default |
|---|---|---|
|RABBITMQ_URL | AMQP connection string | amqp://guest:guest@localhost:5672 |
| AWS_REGION | AWS region | us-east-1 |
| SQS_QUEUE_URL | AWS SQS queue | arn:aws:sqs:us-east-1:123456789012:queue_name |
|SNS_TOPIC_ARN | AWS SNS TOpic | arn:aws:sns:us-east-1:123456789012:my_topic_name |
| AWS_ROLE_ARN | CI IAM Role | arn:aws:iam::123456789012:role/cirole |

## Contribution Guidelines
1. Write unit tests for all new business logic
2. Add integration tests for external dependencies
3. Ensure E2E coverage for critical workflows
4. Maintain > 80% code coverage
5. All tests must pass before merge


## Troubleshooting

### Import Errors
If you encounter `ModuleNotFoundError`, ensure you're running commands from the project root and have installed the package in editable mode:
```
./.venv/bin/python -m pip install -e ".[test]"
```

### RabbitMQ Connection Issues
If integration tests fail with connection errors, verify Docker is running:
docker ps | grep rabbitmq


## Testing prerequisites and troubleshooting

Integration and E2E tests use **testcontainers**, which requires Docker to be running.

Before running tests locally:
- Make sure Docker Desktop is running (`docker ps` works).
- Stop any local processes using the same ports (the test suite dynamically selects ports, but a running Orders service or RabbitMQ may still interfere depending on your environment).
- If you previously started RabbitMQ on port 5672, stop it before running integration tests. Integration tests spin up their own RabbitMQ container automatically.

Common issues:
- **Port conflicts**: Stop any locally running services, then rerun tests.
- **Docker not running**: Start Docker Desktop and rerun tests.
- **Slow startup**: On first run, pulling container images may take longer.


## Build the Orders container image

Build from the repository root (the Dockerfile expects the repo-root build context so it can copy `pyproject.toml`):

```bash
docker build -f services/orders_service/Dockerfile -t xyz-orders:latest .
docker run --rm -p 8000:8000 -e PORT=8000 xyz-orders:latest
curl -s http://127.0.0.1:8000/health
```

## Deploying Infrastructure with AWS CDK 
AWS CDK and CLI installation and configuration instruction can be found [here](.infra/cdk/README.md)