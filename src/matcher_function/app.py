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
    # Get POSTCODE and ProductName from event
    postcode = event['POSTCODE']
    product_name = event['ProductName']
    
    # Step 1: Search in OpenSearch for matching products
    query = {
    "query": {
        "bool": {
            "must": [
                {"match": {"POSTCODE": postcode}},
                {
                    "fuzzy": {
                        "ProductName": {
                            "value": product_name,
                            "fuzziness": "AUTO"  # Automatically determines the fuzziness level
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
        # Extract POSTCODE and ProductName from the hit
        postcode = hit['_source']['POSTCODE']
        product_name = hit['_source']['ProductName']
        
        # Step 2: Retrieve full product details from DynamoDB
        product_details = get_product_details_from_dynamodb(postcode=postcode,product_name=product_name)
        if product_details:
            matched_products.append(product_details)
    
    # Send a notification with full product details if matches found
    if matched_products:
        notify_user(matched_products, event['PhoneNumber'])

def get_product_details_from_dynamodb(postcode, product_name):
    try:
        table = dynamodb.Table('ProductCatalogTable')
        response = table.get_item(Key={'POSTCODE': postcode, 'ProductName': product_name})
        if 'Item' in response:
            return {
                "POSTCODE": response['Item'].get('POSTCODE'),
                "ProductName": response['Item'].get('ProductName')
                #"reqoptiondesc and reqprice": response['Item'].get('Discount'),
                #"Availability": response['Item'].get('Availability')
            }
    except Exception as e:
        print(f"Error retrieving product details: {e}")
    return None

def notify_user(matched_products, phone_number):
    message = "Matched products:\n"
    for product in matched_products:
        message += f"Product: {product['ProductName']}\n"

    sns.publish(
        PhoneNumber=phone_number,
        Message=message,
        Subject="Product Availability Notification"
    )
