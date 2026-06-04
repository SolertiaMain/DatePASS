from __future__ import annotations

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigateway,
    aws_certificatemanager as acm,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class DatePassStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        table = dynamodb.Table(
            self,
            "Invitations",
            table_name="DatePassInvitations",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        bucket = s3.Bucket(
            self,
            "PassBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        wallet_secret = secretsmanager.Secret(
            self,
            "WalletSecret",
            secret_name="datepass/apple-wallet",
            description="Apple Wallet certificates, identifiers and DatePass creator API key",
        )

        event_bus = events.EventBus(self, "InvitationEvents", event_bus_name="DatePassEvents")

        fn = lambda_.DockerImageFunction(
            self,
            "DatePassApi",
            code=lambda_.DockerImageCode.from_image_asset("."),
            architecture=lambda_.Architecture.X86_64,
            memory_size=1024,
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": table.table_name,
                "BUCKET_NAME": bucket.bucket_name,
                "WALLET_SECRET_ARN": wallet_secret.secret_arn,
                "PRESIGNED_URL_TTL_SECONDS": "900",
                "EVENT_BUS_NAME": event_bus.event_bus_name,
                "CORS_ALLOW_ORIGINS": os.getenv("DATEPASS_CORS_ALLOW_ORIGINS", ""),
            },
        )
        table.grant_read_write_data(fn)
        bucket.grant_read_write(fn)
        wallet_secret.grant_read(fn)
        event_bus.grant_put_events_to(fn)
        fn.add_to_role_policy(iam.PolicyStatement(actions=["s3:GetObject"], resources=[bucket.arn_for_objects("passes/*")]))

        api = apigateway.LambdaRestApi(
            self,
            "Api",
            handler=fn,
            proxy=True,
            deploy_options=apigateway.StageOptions(stage_name="prod", tracing_enabled=True, metrics_enabled=True),
        )
        fn.add_environment("API_BASE_URL", os.getenv("DATEPASS_API_BASE_URL", api.url))

        domain_name = os.getenv("DATEPASS_DOMAIN_NAME")
        certificate_arn = os.getenv("DATEPASS_ACM_CERTIFICATE_ARN")
        hosted_zone_id = os.getenv("DATEPASS_HOSTED_ZONE_ID")
        hosted_zone_name = os.getenv("DATEPASS_HOSTED_ZONE_NAME")
        if all([domain_name, certificate_arn, hosted_zone_id, hosted_zone_name]):
            certificate = acm.Certificate.from_certificate_arn(self, "ApiCertificate", certificate_arn)
            custom_domain = apigateway.DomainName(
                self,
                "CustomDomain",
                domain_name=domain_name,
                certificate=certificate,
                endpoint_type=apigateway.EndpointType.EDGE,
            )
            apigateway.BasePathMapping(self, "BasePathMapping", domain_name=custom_domain, rest_api=api)
            zone = route53.HostedZone.from_hosted_zone_attributes(
                self, "HostedZone", hosted_zone_id=hosted_zone_id, zone_name=hosted_zone_name
            )
            route53.ARecord(
                self,
                "AliasRecord",
                zone=zone,
                record_name=domain_name,
                target=route53.RecordTarget.from_alias(route53_targets.ApiGatewayDomain(custom_domain)),
            )
            CfnOutput(self, "PublicUrl", value=f"https://{domain_name}")
        else:
            CfnOutput(self, "PublicUrl", value=api.url)

        CfnOutput(self, "WalletSecretArn", value=wallet_secret.secret_arn)
        CfnOutput(self, "PassBucketName", value=bucket.bucket_name)
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "EventBusName", value=event_bus.event_bus_name)
