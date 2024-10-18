# src/layers/common_layer/python/common/utils.py

import json
import os
import uuid
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Get the table name from environment variables or default to 'UserRequests'
USER_REQUESTS_TABLE = os.environ.get('USER_REQUESTS_TABLE', 'UserRequests')

# Initialize the DynamoDB table
user_requests_table = dynamodb.Table(USER_REQUESTS_TABLE)

def submit_new_request(event, context):
    """
    Handles the submission of a new user request.
    """
    try:
        body = json.loads(event.get('body', '{}'))

        # Validate inputs
        postcode = body.get('Postcode')
        product_name = body.get('ProductName')
        discount = body.get('Discount')
        phone_number = body.get('PhoneNumber')

        if not all([postcode, product_name, discount, phone_number]):
            return respond(400, {'message': 'Missing required parameters: Postcode, ProductName, Discount, PhoneNumber'})

        # Generate a unique RequestID
        request_id = str(uuid.uuid4())

        # Create the item to store in DynamoDB
        item = {
            'RequestID': request_id,
            'Postcode': str(postcode),
            'ProductName': product_name,
            'Discount': Decimal(str(discount)),
            'PhoneNumber': phone_number,
            'Timestamp': Decimal(str(context.get_remaining_time_in_millis()))
        }

        # Store the request in the UserRequests table
        user_requests_table.put_item(Item=item)

        return respond(200, {'message': 'Request submitted successfully', 'RequestID': request_id})
    except Exception as e:
        print(f"Error submitting new request: {e}")
        return respond(500, {'message': 'Internal server error'})

def list_requests(event):
    """
    Lists all current user requests.
    """
    try:
        # Scan the UserRequests table to get all items
        response = user_requests_table.scan()
        items = response.get('Items', [])
        return respond(200, items)
    except Exception as e:
        print(f"Error listing requests: {e}")
        return respond(500, {'message': 'Internal server error'})

def delete_request(event):
    """
    Deletes a user request by RequestID.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        request_id = body.get('RequestID')

        if not request_id:
            return respond(400, {'message': 'Missing required parameter: RequestID'})

        # Delete the request from the UserRequests table
        user_requests_table.delete_item(Key={'RequestID': request_id})

        return respond(200, {'message': 'Request deleted successfully'})
    except Exception as e:
        print(f"Error deleting request: {e}")
        return respond(500, {'message': 'Internal server error'})

def update_request(event):
    """
    Updates a user request by RequestID.
    Only ProductName, Discount, and PhoneNumber can be updated.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        request_id = body.get('RequestID')

        if not request_id:
            return respond(400, {'message': 'Missing required parameter: RequestID'})

        # Fields that can be updated
        allowed_fields = ['ProductName', 'Discount', 'PhoneNumber']
        update_expression = 'SET '
        expression_attribute_values = {}
        has_updates = False

        for field in allowed_fields:
            if field in body and body[field] is not None:
                has_updates = True
                update_expression += f"{field} = :{field.lower()}, "
                value = body[field]
                if field == 'Discount':
                    value = Decimal(str(value))
                expression_attribute_values[f":{field.lower()}"] = value

        if not has_updates:
            return respond(400, {'message': 'No valid fields to update'})

        # Remove trailing comma and space
        update_expression = update_expression.rstrip(', ')

        # Update the request in the UserRequests table
        user_requests_table.update_item(
            Key={'RequestID': request_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='UPDATED_NEW'
        )

        return respond(200, {'message': 'Request updated successfully'})
    except Exception as e:
        print(f"Error updating request: {e}")
        return respond(500, {'message': 'Internal server error'})

def respond(status_code, body):
    """
    Helper function to format the HTTP response.
    """
    return {
        'statusCode': status_code,
        'body': json.dumps(body, cls=DecimalEncoder),
        'headers': {
            'Content-Type': 'application/json'
        }
    }

class DecimalEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder to handle Decimal types from DynamoDB.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert decimal instances to float
            return float(obj)
        return super(DecimalEncoder, self).default(obj)
