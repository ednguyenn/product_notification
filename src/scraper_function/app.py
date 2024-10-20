import os
import boto3
import json
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

UNIQUE_POSTCODES_TABLE = os.environ.get('UNIQUE_POSTCODES_TABLE', 'UniquePostcodesTable')
FUNCTION_NAME = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'ScraperFunction')
IS_LOCAL = os.environ.get('AWS_SAM_LOCAL') == 'true'

def lambda_handler(event, context):
    print(f"IS_LOCAL: {IS_LOCAL}")  # Debug print
    
    if 'Records' in event:
        # Triggered by DynamoDB Stream
        for record in event['Records']:
            if record['eventName'] == 'INSERT':
                postcode = record['dynamodb']['NewImage']['POSTCODE']['S']
                perform_scraping(postcode)
    else:
        # Triggered by EventBridge or self-invocation
        table = dynamodb.Table(UNIQUE_POSTCODES_TABLE)
        last_update = get_last_update_time(table)
        
        if last_update is None or datetime.now() - last_update > timedelta(days=7):
            # No updates in the last 7 days, perform scraping for all postcodes
            response = table.scan()
            for item in response['Items']:
                perform_scraping(item['POSTCODE'])
        else:
            # There was a recent update, wait for the next scheduled trigger
            print("Update detected within the last 7 days. Waiting for next scheduled trigger.")
    
    # Self-trigger for the next run (only in AWS environment)
    if not IS_LOCAL:
        print("Attempting to self-invoke (AWS environment)")
        try:
            lambda_client.invoke(
                FunctionName=FUNCTION_NAME,
                InvocationType='Event'
            )
        except Exception as e:
            print(f"Error invoking function: {e}")
    else:
        print("Running locally, skipping self-invocation")

    return {
        'statusCode': 200,
        'body': json.dumps('Scraping process completed')
    }

def perform_scraping(postcode):
    # Implement your scraping logic here
    print(f"Scraping for postcode: {postcode}")

def get_last_update_time(table):
    response = table.scan(
        Limit=1,
        ScanIndexForward=False
    )
    if response['Items']:
        return datetime.fromtimestamp(response['Items'][0].get('LastUpdateTime', 0))
    return None

# For local testing
if __name__ == "__main__":
    test_event = {
        "Records": [
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "POSTCODE": {"S": "3220"}
                    }
                }
            }
        ]
    }
    lambda_handler(test_event, None)
