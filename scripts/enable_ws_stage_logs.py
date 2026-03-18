import boto3


def main() -> None:
    session = boto3.Session(profile_name="noma", region_name="us-east-1")
    apigw = session.client("apigatewayv2")

    api_id = "3vdnaldxj0"
    stage_name = "production"
    log_group_arn = "arn:aws:logs:us-east-1:158711196499:log-group:/aws/apigateway/websocket/noma_prod_websocket"

    fmt = (
        '{"requestId":"$context.requestId",'
        '"ip":"$context.identity.sourceIp",'
        '"routeKey":"$context.routeKey",'
        '"eventType":"$context.eventType",'
        '"status":$context.status,'
        '"integrationStatus":"$context.integration.status",'
        '"integrationError":"$context.integrationErrorMessage",'
        '"errorMessage":"$context.error.message",'
        '"connectionId":"$context.connectionId"}'
    )

    resp = apigw.update_stage(
        ApiId=api_id,
        StageName=stage_name,
        DefaultRouteSettings={
            "LoggingLevel": "INFO",
            "DataTraceEnabled": True,
            "DetailedMetricsEnabled": True,
        },
        AccessLogSettings={"DestinationArn": log_group_arn, "Format": fmt},
    )
    print("updated-stage", resp.get("StageName"), "deployment", resp.get("DeploymentId"))


if __name__ == "__main__":
    main()

