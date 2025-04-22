import boto3
import requests
from requests_aws4auth import AWS4Auth
import os
import json
import datetime
from common import (
    get_config, 
    logger,
    )
import json

cfg = get_config()

credentials = boto3.Session().get_credentials()
service = 'es'
awsauth = AWS4Auth(
    credentials.access_key, 
    credentials.secret_key, 
    cfg["region"], 
    service, 
    session_token=credentials.token,
)

index = 'lambda-s3-index'
type = 'lambda-type'
host = cfg["es_domain"]
if not host.startswith("http"):
    host = f"https://{host}"
url = f"{host}/{index}/_doc"     # replace /{type} with /_doc for OpenSearch 7.x+

headers = { "Content-Type": "application/json" }

s3 = boto3.client('s3')
bucket = cfg["bucket"]

# Lambda execution starts here
def handler(event, context):
    body = json.loads(event["body"])
    sensorID = body['sensorID']
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    temperature = body['temperature']
        
    document = { "sensorID": sensorID, "timestamp": timestamp, "temperature": temperature }
    print(document)
    # post to S3 for storage
    s3.put_object(Body=json.dumps(document).encode(), Bucket=bucket, Key=sensorID+"-"+timestamp+".json")
    # post to amazon elastic search for indexing and kibana use
    r = requests.post(url, auth=awsauth, json=document, headers=headers)
    print(r)
    response = "Data Uploaded"

    return {
        "statusCode": 200,
        "headers": { "Content-Type": "application/json" },
        "body": json.dumps({
            "Response": response,
            "sensorID": sensorID,
            "temperature": temperature
        })
    }

# local testing
if __name__ == "__main__":
    event = {
        "httpMethod": "POST",
        "resource": "/sensor",
        "path": "/sensor",
        "headers": { ... },        
        "body": json.dumps({
            "sensorID": "sensor1",
            "temperature": 25.0
        }),
        "isBase64Encoded": False,
    }
    context = None
    response = handler(event, context)
    print(response)