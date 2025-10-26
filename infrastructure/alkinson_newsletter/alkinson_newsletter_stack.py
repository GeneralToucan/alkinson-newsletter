import os
from aws_cdk import (
    Duration,
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_events as events,
    aws_events_targets as targets,
    aws_ses as ses,
    aws_iam as iam,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
)
from constructs import Construct

class AlkinsonNewsletterStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for website hosting and content storage
        self.content_bucket = s3.Bucket(
            self, "AlkinsonNewsletterBucket",
            bucket_name="alkinson-newsletter-content-apse2",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False
            ),
            removal_policy=RemovalPolicy.DESTROY,  # For development only
            auto_delete_objects=True  # For development only
        )

        # DynamoDB table for subscriber management
        self.subscribers_table = dynamodb.Table(
            self, "SubscribersTable",
            table_name="alkinson-newsletter-subscribers",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For development only
            point_in_time_recovery=True
        )

        # IAM role for Lambda functions
        lambda_role = iam.Role(
            self, "AlkinsonNewsletterLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add CloudWatch Logs permissions for API Gateway
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=["*"]
        ))
        
        # Add permissions for S3, DynamoDB, SES, and Bedrock
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            resources=[
                self.content_bucket.bucket_arn,
                f"{self.content_bucket.bucket_arn}/*"
            ]
        ))

        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            resources=[self.subscribers_table.table_arn]
        ))

        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ses:SendEmail",
                "ses:SendRawEmail",
                "ses:GetSendQuota",
                "ses:GetSendStatistics"
            ],
            resources=["*"]
        ))

        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=["*"]
        ))

        # Content Agent Lambda Function
        self.content_agent = _lambda.Function(
            self, "ContentAgentFunction",
            function_name="alkinson-newsletter-content-agent",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("../lambda/content_agent"),
            timeout=Duration.minutes(15),
            memory_size=512,
            role=lambda_role,
            environment={
                "CONTENT_BUCKET": self.content_bucket.bucket_name,
                "SUBSCRIBERS_TABLE": self.subscribers_table.table_name
            }
        )

        # Email Agent Lambda Function
        self.email_agent = _lambda.Function(
            self, "EmailAgentFunction",
            function_name="alkinson-newsletter-email-agent",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("../lambda/email_agent"),
            timeout=Duration.minutes(5),
            memory_size=256,
            role=lambda_role,
            environment={
                "CONTENT_BUCKET": self.content_bucket.bucket_name,
                "SUBSCRIBERS_TABLE": self.subscribers_table.table_name
            }
        )

        # Subscription API Lambda Functions
        self.subscribe_function = _lambda.Function(
            self, "SubscribeFunction",
            function_name="alkinson-newsletter-subscribe",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="subscribe.lambda_handler",
            code=_lambda.Code.from_asset("../lambda/subscription_api"),
            timeout=Duration.seconds(30),
            memory_size=128,
            role=lambda_role,
            environment={
                "SUBSCRIBERS_TABLE": self.subscribers_table.table_name,
                "SES_SENDER_EMAIL": os.environ.get("SES_SENDER_EMAIL", "newsletter@example.com"),
                "WEBSITE_URL": os.environ.get("WEBSITE_URL", f"https://{self.content_bucket.bucket_name}.s3-website-{self.region}.amazonaws.com")
            }
        )

        self.confirm_function = _lambda.Function(
            self, "ConfirmFunction",
            function_name="alkinson-newsletter-confirm",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="confirm.lambda_handler",
            code=_lambda.Code.from_asset("../lambda/subscription_api"),
            timeout=Duration.seconds(30),
            memory_size=128,
            role=lambda_role,
            environment={
                "SUBSCRIBERS_TABLE": self.subscribers_table.table_name
            }
        )

        self.unsubscribe_function = _lambda.Function(
            self, "UnsubscribeFunction",
            function_name="alkinson-newsletter-unsubscribe",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="unsubscribe.lambda_handler",
            code=_lambda.Code.from_asset("../lambda/subscription_api"),
            timeout=Duration.seconds(30),
            memory_size=128,
            role=lambda_role,
            environment={
                "SUBSCRIBERS_TABLE": self.subscribers_table.table_name,
                "WEBSITE_URL": os.environ.get("WEBSITE_URL", f"https://{self.content_bucket.bucket_name}.s3-website-{self.region}.amazonaws.com")
            }
        )

        # API Gateway for subscription management with security and rate limiting
        self.api = apigateway.RestApi(
            self, "AlkinsonNewsletterApi",
            rest_api_name="alkinson-newsletter-api",
            description="API for Alkinson Newsletter subscription management",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Requested-With"]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=10,  # 10 requests per second
                throttling_burst_limit=20,  # 20 concurrent requests
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            )
        )

        # Request validator for API Gateway
        request_validator = apigateway.RequestValidator(
            self, "ApiRequestValidator",
            rest_api=self.api,
            request_validator_name="alkinson-newsletter-validator",
            validate_request_body=True,
            validate_request_parameters=True
        )
        
        # API Gateway integrations with error handling
        subscribe_integration = apigateway.LambdaIntegration(
            self.subscribe_function,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
            ]
        )
        
        confirm_integration = apigateway.LambdaIntegration(
            self.confirm_function,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
            ]
        )
        
        unsubscribe_integration = apigateway.LambdaIntegration(
            self.unsubscribe_function,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
            ]
        )

        # API Gateway resources and methods with rate limiting
        api_resource = self.api.root.add_resource("api")
        
        # Subscribe endpoint with rate limiting
        subscribe_resource = api_resource.add_resource("subscribe")
        subscribe_method = subscribe_resource.add_method(
            "POST", 
            subscribe_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )
        
        # Confirm endpoint
        confirm_resource = api_resource.add_resource("confirm")
        confirm_method = confirm_resource.add_method(
            "GET", 
            confirm_integration,
            request_parameters={
                'method.request.querystring.email': True,
                'method.request.querystring.token': True
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )
        
        # Unsubscribe endpoints (both POST and GET)
        unsubscribe_resource = api_resource.add_resource("unsubscribe")
        unsubscribe_post_method = unsubscribe_resource.add_method(
            "POST", 
            unsubscribe_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )
        unsubscribe_get_method = unsubscribe_resource.add_method(
            "GET", 
            unsubscribe_integration,
            request_parameters={
                'method.request.querystring.email': True
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )

        # EventBridge rule for weekly scheduling
        self.weekly_schedule = events.Rule(
            self, "WeeklyContentSchedule",
            rule_name="alkinson-newsletter-weekly-trigger",
            description="Trigger content agent every Sunday at 6:00 AM UTC",
            schedule=events.Schedule.cron(
                minute="0",
                hour="6",
                day="*",
                month="*",
                week_day="SUN"
            )
        )

        # Add Content Agent as target for the weekly schedule
        self.weekly_schedule.add_target(targets.LambdaFunction(self.content_agent))

        # Deploy website assets to S3
        s3deploy.BucketDeployment(
            self, "DeployWebsite",
            sources=[s3deploy.Source.asset("../website")],
            destination_bucket=self.content_bucket,
            destination_key_prefix="website/"
        )

        # Deploy email templates to S3
        s3deploy.BucketDeployment(
            self, "DeployTemplates",
            sources=[s3deploy.Source.asset("../templates")],
            destination_bucket=self.content_bucket,
            destination_key_prefix="templates/"
        )