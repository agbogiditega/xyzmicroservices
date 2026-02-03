from pathlib import Path

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_logs as logs,
    aws_iam as iam,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_sns_subscriptions as subs,
    aws_ecr_assets as ecr_assets,
)
from constructs import Construct


class XyzOrdersStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        project = "xyz"
        env_name = "dev"
        name_prefix = f"{project}-{env_name}"

        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=1,  # keep minimal/cost-light for exemplar
        )

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, cluster_name=f"{name_prefix}-cluster")

        # Messaging (SNS -> SQS exemplar consumer queue)
        order_events_topic = sns.Topic(self, "OrderEventsTopic", topic_name=f"{name_prefix}-order-events")

        inventory_dlq = sqs.Queue(self, "InventoryDLQ", queue_name=f"{name_prefix}-inventory-dlq")
        inventory_q = sqs.Queue(
            self,
            "InventoryQueue",
            queue_name=f"{name_prefix}-inventory",
            dead_letter_queue=sqs.DeadLetterQueue(queue=inventory_dlq, max_receive_count=5),
        )
        order_events_topic.add_subscription(subs.SqsSubscription(inventory_q, raw_message_delivery=True))

        log_group = logs.LogGroup(
            self,
            "OrdersLogGroup",
            log_group_name=f"/ecs/{name_prefix}/orders",
            retention=logs.RetentionDays.TWO_WEEKS,
        )

        task_role = iam.Role(
            self,
            "OrdersTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        order_events_topic.grant_publish(task_role)

        # Build & publish the container image automatically during `cdk deploy`.
        repo_root = Path(__file__).resolve().parents[2]  # infra/cdk -> infra -> repo root
        image_asset = ecr_assets.DockerImageAsset(
            self,
            "OrdersImage",
            directory=str(repo_root),
            file="services/orders_service/Dockerfile",
            # Prevent runaway asset staging and reduce build context size
            exclude=[
                "infra/cdk/cdk.out",
                "**/cdk.out",
                "**/.venv",
                "**/__pycache__",
                "**/*.pyc",
                "**/.pytest_cache",
                ".git",
            ],
        )

        # ✅ Explicit task definition so we can pin ARM64 and fix "exec format error"
        task_def = ecs.FargateTaskDefinition(
            self,
            "OrdersTaskDef",
            cpu=512,
            memory_limit_mib=1024,
            task_role=task_role,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )

        container = task_def.add_container(
            "OrdersContainer",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            environment={
                "PORT": "8000",
                "MESSAGE_BACKEND": "sns",
                "ORDER_EVENTS_TOPIC_ARN": order_events_topic.topic_arn,
                "AWS_REGION": Stack.of(self).region,
            },
            logging=ecs.LogDriver.aws_logs(stream_prefix="ecs", log_group=log_group),
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8000))

        # ALB + Fargate
        fargate = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "OrdersService",
            cluster=cluster,
            public_load_balancer=True,
            desired_count=1,
            task_definition=task_def,
            health_check_grace_period=Duration.seconds(30),
        )

        # Expect a /health endpoint
        fargate.target_group.configure_health_check(path="/health")

        CfnOutput(self, "AlbDnsName", value=fargate.load_balancer.load_balancer_dns_name)
        CfnOutput(self, "OrderEventsTopicArn", value=order_events_topic.topic_arn)
        CfnOutput(self, "InventoryQueueUrl", value=inventory_q.queue_url)
        CfnOutput(self, "OrdersImageUri", value=image_asset.image_uri)
