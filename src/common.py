# lambda/common.py

import os
import boto3
import logging
# from dotenv import load_dotenv, set_key
from pathlib import Path

# Setup logger
logger = logging.getLogger("OpensearchStack")
logger.setLevel(logging.INFO)
if not logger.handlers:
    console = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
    console.setFormatter(formatter)
    logger.addHandler(console)

# get ENVIRONMENT from environment variables
ENVIRONMENT = os.getenv('ENVIRONMENT', "local").lower()

# validate ENVIRONMENT
if ENVIRONMENT not in ["local", "dev", "sbx", "uat" , "acpt", "prod"]:
    raise ValueError(f"Invalid environment: '{ENVIRONMENT}'. "
                    "Expected 'local', 'dev', 'sbx', 'uat' , 'acpt' or 'prod'."
                    )

# Load .env if running locally
if os.getenv("ENVIRONMENT", "local").lower() == "local":
    from dotenv import load_dotenv, set_key
    logger.info("Running in local mode, setting environment varialbles ...")
    session = boto3.Session(profile_name=os.getenv("AWS_PROFILE", "sbx-sso"))
    creds = session.get_credentials().get_frozen_credentials()

    env_file = Path("src/.env")
    set_key(env_file, "AWS_ACCOUNT_ID", creds.account_id)
    set_key(env_file, "AWS_ACCESS_KEY_ID", creds.access_key)
    set_key(env_file, "AWS_SECRET_ACCESS_KEY", creds.secret_key)
    set_key(env_file, "AWS_SESSION_TOKEN", creds.token)
    set_key(env_file, "AWS_REGION", session.region_name or "us-east-1")

    load_dotenv(override=True)

def get_config():
    """Load configuration from environment variables."""
    logger.info("Loading configuration ...")
    # Load environment variables
    config = {
        "env": os.getenv("ENVIRONMENT", "local").lower(),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "account_id": os.getenv("AWS_ACCOUNT_ID"),
        "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "session_token": os.getenv("AWS_SESSION_TOKEN"),
        "region": os.getenv("AWS_REGION", "us-east-1"),
        "bucket": f"{os.getenv('AWS_BUCKET_NAME')}",
        "application": os.getenv("APPLICATION", "OpenSearch"),
        "profile": os.getenv("AWS_PROFILE", "sbx-sso"),
        "ipv4_allowed": os.getenv("IPV4_ALLOWED"),
        "es_domain": os.getenv("ES_DOMAIN_URL"),
    }

    if config["debug"]:
        logger.info("Configuration loaded:")
        for k, v in config.items():
            logger.info(f"{k.upper()} = {v}")
    return config

def get_clients(region, debug=False, profile_name=None):
    """
    Return Boto3 clients for S3 and SES.

    If debug is True and profile_name is provided, it uses that AWS profile.
    Otherwise, it falls back to environment/default credentials.
    """
    if debug and profile_name:
        session = boto3.Session(profile_name=profile_name, region_name=region)
        return session.client("s3"), session.client("ses")
    
    return boto3.client("s3", region_name=region), boto3.client("ses", region_name=region)

def send_email(ses_client, from_email, to_email, subject, body, html=False):
    try:
        message = {
            'Subject': {'Data': subject},
            'Body': {
                'Html' if html else 'Text': {'Data': body}
            }
        }

        response = ses_client.send_email(
            Source=from_email,
            Destination={'ToAddresses': [to_email]},
            Message=message
        )
        logger.info("Email sent: %s", response["MessageId"])
        return response
    except Exception as e:
        logger.error("Error sending email: %s", str(e))
        raise

def build_html_summary(env, bucket, file_summaries):
    html = f"""<html><body>
    <p><b>Environment:</b> {env}<br>
       <b>S3 bucket:</b> {bucket}</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px;">
        <thead>
            <tr>
                <th>#</th>
                <th>File</th>
                <th>Data</th>
                <th>Archived</th>
            </tr>
        </thead>
        <tbody>
    """

    for idx, entry in enumerate(file_summaries, start=1):
        html += f"""
            <tr>
                <td>{idx}</td>
                <td>{entry['file']}</td>
                <td>{entry['rows']} rows × {entry['cols']} columns</td>
                <td>{entry['archive']}</td>
            </tr>
        """

    html += f"""
        </tbody>
    </table>
    <p><b>Total processed file(s):</b> {len(file_summaries)}</p>
    </body></html>
    """
    return html