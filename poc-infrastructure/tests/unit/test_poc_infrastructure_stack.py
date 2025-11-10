import aws_cdk as core
import aws_cdk.assertions as assertions

from poc_infrastructure.poc_infrastructure_stack import PocCvBedrockStack

# example tests. To run these tests, uncomment this file along with the example
# resource in poc_infrastructure/poc_infrastructure_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = PocCvBedrockStack(app, "poc-cv-bedrock")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
