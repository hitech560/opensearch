from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    Duration,
    RemovalPolicy,
    Annotations,
    aws_opensearchservice as opensearch,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_apigateway as apigateway,
)
from constructs import Construct

class OpensearchStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 environment: str,
                 bucket_name: str, 
                 ipv4_allowed: str,
                 **kwargs,
                 ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Setting up: 
        # Create IAM role for OpenSearch
        # and assign policies: AmazonS3FullAccess and AmazonESFullAccess
        role = iam.Role(
            self, "data-lake-week-2-role",
            role_name=f"data-lake-week-2-role-{environment}",
            description="IAM role for Lambda to access OpenSearch, S3, etc.",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonESFullAccess"),
            ], 
        )

        # Task 1: Creating an Amazon OpenSearch Service cluster
        # Create a public OpenSearch domain
        domain_name = f"water-temp-domain-{environment}"
        resource = f"arn:aws:es:{self.region}:{self.account}:domain/{domain_name}/*"
        domain = opensearch.Domain(
            self, "WaterTempDomainSbx",
            domain_name=domain_name,
            version=opensearch.EngineVersion.OPENSEARCH_2_17,
            capacity=opensearch.CapacityConfig(
                data_node_instance_type="m7g.medium.search",
                data_nodes=3,
                master_nodes=3,
                multi_az_with_standby_enabled=True  # ✅ Correct way to enable standby
            ),
            zone_awareness=opensearch.ZoneAwarenessConfig(
                enabled=True,
                availability_zone_count=3,
            ),
            ebs=opensearch.EbsOptions(
                volume_size=10,
                volume_type=ec2.EbsDeviceVolumeType.GP3,
            ),
            removal_policy=RemovalPolicy.DESTROY, # Destroy by default, for production use RETAIN
            enforce_https=True,
            node_to_node_encryption=True,
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            access_policies=[   # 👇 No VPC = public access
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AnyPrincipal()],
                    actions=["es:*"],
                    resources=[resource],
                    conditions={
                        "IpAddress": {
                            "aws:SourceIp": ipv4_allowed
                        }
                    }
                ),
                # lambda permission to access OpenSearch
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.ArnPrincipal(role.role_arn)],
                    actions=["es:ESHttpPut", "es:ESHttpPost", "es:ESHttpGet"],
                    resources=[resource],
                ),
            ],
            fine_grained_access_control=None,  # ❌ Not enabled
        )

        # Task 2: Creating an S3 bucket with versioning and lifecycle rules
        # Create an S3 bucket for storing data :)
        bucket = s3.Bucket(
            self, "OpensearchBucket",
            bucket_name=bucket_name,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireOldVersions",
                    expiration=Duration.days(30),
                    noncurrent_version_expiration=Duration.days(7),
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                ),
                s3.LifecycleRule(
                    id="DeleteMarkers",
                    prefix="",
                    enabled=True,
                    expired_object_delete_marker=True,
                ),
            ],
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            server_access_logs_prefix=f"{bucket_name}_",
            server_access_logs_bucket=s3.Bucket.from_bucket_name(
                self, 
                "AccessLogsBucket", 
                f"aws-controltower-{self.account}-{self.region}-s3-logs",
                ),
        )
        # Add bucket policy to allow OpenSearch to access the bucket
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(role.role_arn)],
                # actions=["s3:GetObject", "s3:PutObject"],
                actions=["s3:*", ],
                resources=[f"{bucket.bucket_arn}/*"],
            )
        )
        # Acknowledge  and suppress CDK warning for access logs policy
        Annotations.of(bucket).acknowledge_warning(
            id="@aws-cdk/aws-s3:accessLogsPolicyNotAdded",
            message="Target logging bucket is imported and already has correct permissions"
        )

        # Task 3: Creating the Lambda function
        # handler is lambda.handler with environment variables:
        # AWS_BUCKET_NAME, ENVIRONMENT, ES_DOMAIN_URL
        # The Lambda function is in src/lambda.py
        # assign the role to the lambda function
        # Create lambda layer with requests and AWS4Auth, creating via bundling option
        # Define the Lambda Layer
        lambda_layer = _lambda.LayerVersion(
            self, "WaterTempLambdaLayer",
            code=_lambda.Code.from_asset("src",
                bundling=dict(
                    user="root",
                    image=_lambda.Runtime.PYTHON_3_13.bundling_image,
                    command=[
                        "bash", "-c",
                        """
                        python -m pip install --upgrade pip --root-user-action=ignore &&
                        pip install --no-cache -r requirements.txt -t /asset-output/python --root-user-action=ignore #&&
                        # unzip -qo pyodbc-mssql-lambdaplayer.zip -d /asset-output
                        """
                    ],
                ),
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            layer_version_name=f"water-temp-function-{environment}-lambda-layer",
            description="Lambda Layer with Requests, etc.",
        )
        # Create the Lambda function
        lambda_function = _lambda.Function(
            self, "WaterTempFunction",
            function_name=f"water-temp-function-{environment}",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="lambda.handler",
            code=_lambda.Code.from_asset("src"),
            environment={
                "AWS_BUCKET_NAME": bucket.bucket_name,
                "ENVIRONMENT": environment,
                "ES_DOMAIN_URL": domain.domain_endpoint,
            },
            role=role,
            memory_size=128,
            timeout=Duration.seconds(30),
            log_retention=logs.RetentionDays.ONE_MONTH,
            # log_retention_retry_attempts=3,
            layers=[lambda_layer],
        )

        # Task 5: Create a REST API
        # create a REST API in Amazon API Gateway to receive data from the sensors
        # and send it to the Lambda function
        api = apigateway.LambdaRestApi(
            self, "WaterTempApiV2",
            rest_api_name=f"water-temp-api-{environment}",
            description="API for water temperature sensor data",
            handler=lambda_function,
            default_method_options={
                "authorization_type": apigateway.AuthorizationType.NONE,
                "api_key_required": False,
            },
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_methods=["POST"],
                allow_origins=["*"],
                max_age=Duration.seconds(3600)
            ),
            proxy=True,
        )
