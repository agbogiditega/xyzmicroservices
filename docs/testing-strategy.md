# Testing Strategy

## Unit Tests
Validate business rules, schemas, and transformations.
No external dependencies allowed.

## Integration Tests
Validate interaction with real services:
- Message brokers
- Databases
- AWS service emulators (where applicable)

## End-to-End Tests
Validate full workflows:
Client → API → Events → Downstream Services

## Failure Testing
- DLQ routing
- Retry behavior
- Invalid payload handling
