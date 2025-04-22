#!/usr/bin/env python3
import os
import aws_cdk as cdk
from opensearch.opensearch_stack import OpensearchStack
from src.common import (
    get_config, 
    logger,
    )

cfg = get_config()

DEBUG = cfg["debug"]
BUCKET_NAME = cfg["bucket"]
ACCOUNT_ID = cfg["account_id"]
APPLICATION = cfg["application"]
ENVIRONMENT = cfg["env"]
AWS_REGION = cfg["region"]
IPV4_ALLOWED = cfg["ipv4_allowed"]

# Define the qualifier based on the environment
environment_qualifiers = {
    "sbx": "tciedasbx0",
    "dev": "tciedadev",
    "uat": "openweather",
    "acpt": "openweather",
    "prod": "tciedaprod"
}
qualifier = environment_qualifiers.get(ENVIRONMENT)

if not qualifier:
    logger.error(f"Invalid environment: '{ENVIRONMENT}'. Expected a known environment.")
    raise ValueError(f"Invalid environment: '{ENVIRONMENT}'.")

if ENVIRONMENT == "sbx":
     file_assets_bucket_name = f"cdk-{qualifier}-assets-{ACCOUNT_ID}-{AWS_REGION}" 
else:
    file_assets_bucket_name = f"deployment-{ACCOUNT_ID}-{AWS_REGION}"

app = cdk.App()

OpensearchStack(app, "OpensearchStack",

    synthesizer=cdk.DefaultStackSynthesizer(
        qualifier=qualifier,
        file_assets_bucket_name=file_assets_bucket_name
    ),
    env=cdk.Environment(
        account=ACCOUNT_ID,
        region=AWS_REGION
    ),
    bucket_name=BUCKET_NAME,
    environment=ENVIRONMENT,
    ipv4_allowed=IPV4_ALLOWED,
)

cdk.Tags.of(app).add("environment", ENVIRONMENT)
cdk.Tags.of(app).add("application", APPLICATION.capitalize())

app.synth()
