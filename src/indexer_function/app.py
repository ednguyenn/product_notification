import os
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Get secret keys from Secret Manager 
def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Environment variables
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
REGION = os.environ['AWS_REGION']
access_key = get_secret("access_key")
secret_key = get_secret("secret_key")

# OpenSearch client
credentials = boto3.Session().get_credentials()
auth = AWS4Auth(credentials.access_key, credentials.secret_key, REGION, 'es', session_token=credentials.token)

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

INDEX_NAME = 'product-catalog-index'

def lambda_handler(event, context):
    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            new_image = record['dynamodb']['NewImage']
            document = format_document(new_image)
            product_name = document.get("ProductName")
            postcode = document.get("POSTCODE")
            
            # Index document in OpenSearch
            index_document(postcode, product_name, document)

def format_document(new_image):
    # Converts DynamoDB JSON format to regular JSON
    document = {}
    for key, value in new_image.items():
        document[key] = list(value.values())[0]  # Extracts the value from DynamoDB JSON
    return document

def index_document(postcode, product_name, document):
    # Index the document in OpenSearch
    try:
        response = client.index(
            index=INDEX_NAME,
            id=f"{postcode}-{product_name}",
            body=document
        )
        print(f"Document indexed: {response['_id']}")
    except Exception as e:
        print(f"Error indexing document: {e}")

