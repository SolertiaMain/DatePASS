#!/usr/bin/env python3
import os

import aws_cdk as cdk

from datepass_stack import DatePassStack

app = cdk.App()
DatePassStack(
    app,
    "DatePassStack",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION", "us-east-1")),
)
app.synth()
