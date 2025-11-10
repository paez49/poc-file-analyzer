#!/usr/bin/env python3
import os

import aws_cdk as cdk

from poc_infrastructure.poc_infrastructure_stack import PocCvBedrockStack


app = cdk.App()
PocCvBedrockStack(
    app,
    "PocCvBedrockStack",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="us-east-2"),
)

app.synth()
