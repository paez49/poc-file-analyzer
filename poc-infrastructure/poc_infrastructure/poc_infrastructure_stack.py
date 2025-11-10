from aws_cdk import (
    Stack,
    Duration,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_lambda_event_sources as event_sources,
    aws_sqs as sqs,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    BundlingOptions,
    RemovalPolicy,
)
from constructs import Construct


class PocCvBedrockStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # S3 buckets
        input_bucket = s3.Bucket(
            self,
            "InputCVBucket",
            bucket_name="cv-input-bucket-poc",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        output_bucket = s3.Bucket(
            self,
            "OutputCVBucket",
            bucket_name="cv-output-bucket-poc",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # SQS queue
        queue = sqs.Queue(
            self, "CVProcessingQueue", visibility_timeout=Duration.seconds(180)
        )

        # Lambda layer
        pypdf_layer = _lambda.LayerVersion(
            self,
            "PyPdfLayer",
            code=_lambda.Code.from_asset(
                "lambda/file-processor",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output/python"
                        " && if [ -d src ]; then cp -r src/* /asset-output/python/; fi",
                    ],
                ),
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="pypdf layer",
        )

        # Lambda function
        processor_fn = _lambda.Function(
            self,
            "CVProcessorLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda.handler",
            code=_lambda.Code.from_asset("lambda/file-processor"),
            timeout=Duration.seconds(180),
            memory_size=1024,
            layers=[pypdf_layer],
            environment={"OUTPUT_BUCKET": output_bucket.bucket_name},
        )

        # Grant permissions
        input_bucket.grant_read(processor_fn)
        output_bucket.grant_write(processor_fn)
        queue.grant_consume_messages(processor_fn)

        # Add Bedrock policy
        processor_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "textract:*"], resources=["*"]
            )
        )

        # Add SQS event source
        processor_fn.add_event_source(event_sources.SqsEventSource(queue))

        # Add S3 event notification
        notification = s3n.SqsDestination(queue)
        input_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, notification)
