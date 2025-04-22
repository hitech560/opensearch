#!/usr/bin/env python3
import os
import aws_cdk as cdk
from opensearch.opensearch_stack import OpensearchStack
from src.common import (
    get_config, 
    # get_clients,
    logger,
    )
# import logging

# # Configure logging
# logger = logging.getLogger("OpensearchStack")
# logger.setLevel(logging.INFO)
# if not logger.handlers:
#     console = logging.StreamHandler()
#     formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
#     console.setFormatter(formatter)
#     logger.addHandler(console)

# # get ENVIRONMENT from environment variables
# ENVIRONMENT = os.getenv('ENVIRONMENT', "local").lower()

# # validate ENVIRONMENT
# if ENVIRONMENT not in ["local", "dev", "sbx", "uat" , "acpt", "prod"]:
#     raise ValueError(f"Invalid environment: '{ENVIRONMENT}'. "
#                     "Expected 'local', 'dev', 'sbx', 'uat' , 'acpt' or 'prod'."
#                     )

# if ENVIRONMENT == "local":
#     # load local environment variables
#     logger.info("Running in local environment ...")
#     from dotenv import load_dotenv, set_key
#     from pathlib import Path
#     import boto3

#     logger.info("Setting environment varialbles ...")

#     # retrieve session details and update .env file then reload to ensure AWS connection valid
#     session = boto3.Session(profile_name=os.getenv("AWS_PROFILE", "sbx-sso"))
#     creds = session.get_credentials().get_frozen_credentials()

#     env_file = Path(".env")
#     set_key(env_file, "AWS_ACCESS_KEY_ID", creds.access_key)
#     set_key(env_file, "AWS_SECRET_ACCESS_KEY", creds.secret_key)
#     set_key(env_file, "AWS_SESSION_TOKEN", creds.token)
#     set_key(env_file, "AWS_REGION", session.region_name or "us-east-1")

#     load_dotenv(override=True)

cfg = get_config()

# # get other environment variables
# DEBUG = os.getenv('DEBUG', "False").lower() == "true"
# # BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

# ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')
# APPLICATION = os.getenv('application', "OpenSearch")
# ENVIRONMENT = os.getenv('ENVIRONMENT')
# AWS_REGION = os.getenv('AWS_REGION', "us-east-1")

# BUCKET_NAME = f"datalakes-week2-{ENVIRONMENT}"

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
