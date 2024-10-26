import json
import os
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Get secret keys from Secret Manager 
def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

access_key = get_secret("access_key")
secret_key = get_secret("secret_key")

# Environment variables
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
REGION = os.environ['AWS_REGION']
sns_topic_arn = os.environ['SNS_TOPIC_ARN']

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
user_requests_table = dynamodb.Table('UserRequestsTable')

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


def lambda_handler(event, context):
    # Check if triggered by DynamoDB stream or EventBridge weekly schedule
    if 'Records' in event:  # Triggered by DynamoDB Stream
        for record in event['Records']:
            if record['eventName'] == 'INSERT':
                new_record = record['dynamodb']['NewImage']
                process_new_request(new_record)
    
    elif event.get("TriggerType") == "weekly":  # Triggered by EventBridge
        process_existing_requests()

def process_new_request(new_record):
    # Extract POSTCODE, ProductName, and PhoneNumber from the new record
    postcode = new_record['POSTCODE']['S']
    product_name = new_record['ProductName']['S']
    phone_number = new_record.get('PhoneNumber', {}).get('S', None)

    # Search OpenSearch for matching products
    matched_products = search_product_in_opensearch(postcode, product_name)
    
    if matched_products and phone_number:
        # Send notification to user if matched products found
        notify_user(matched_products, phone_number)

def process_existing_requests():
    try:
        # Scan DynamoDB for all user requests
        response = user_requests_table.scan()
        requests = response.get('Items', [])
        
        for request in requests:
            postcode = request['POSTCODE']['S']
            product_name = request['ProductName']['S']
            phone_number = request.get('PhoneNumber', {}).get('S', None)
            
            # Search OpenSearch for matching products
            matched_products = search_product_in_opensearch(postcode, product_name)
            
            if matched_products and phone_number:
                # Send notification to user if matched products found
                notify_user(matched_products, phone_number)
                
    except Exception as e:
        print(f"Error processing existing requests: {e}")


def search_product_in_opensearch(postcode, product_name):
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"POSTCODE": postcode}},
                    {
                        "fuzzy": {
                            "ProductName": {
                                "value": product_name,
                                "fuzziness": "AUTO"
                            }
                        }
                    }
                ]
            }
        }
    }

    response = client.search(
        body=query,
        index="product_catalog_index"
    )
    
    matched_products = []
    for hit in response['hits']['hits']:
        product = hit['_source']
        matched_products.append(product)
    
    return matched_products


def notify_user(matched_products, phone_number):
    message = "Matched products:\n"
    for product in matched_products:
        message += f"Product: {product['ProductName']}, Postcode: {product['POSTCODE']}\n"
        
    sns.publish(
        PhoneNumber=phone_number,
        Message=message,
        Subject="Product Availability Notification"
    )