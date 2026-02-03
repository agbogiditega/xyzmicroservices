#!/usr/bin/env python3
import aws_cdk as cdk
from xyz_orders_stack import XyzOrdersStack

app = cdk.App()

XyzOrdersStack(
    app,
    "XyzOrdersDev",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()
