import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    unique_postcodes_table = dynamodb.Table('UniquePostcodes')

    for record in event['Records']:
        # Check if the event is an INSERT operation
        if record['eventName'] == 'INSERT':
            new_image = record['dynamodb']['NewImage']
            postcode = new_image['POSTCODE']['S']

            try:
                # Check if the postcode already exists in UniquePostcodes table
                response = unique_postcodes_table.get_item(
                    Key={'POSTCODE': postcode}
                )

                if 'Item' not in response:
                    # Postcode does not exist, add it to UniquePostcodes table
                    unique_postcodes_table.put_item(
                        Item={'POSTCODE': postcode}
                    )
                    print(f"Added new postcode: {postcode} to UniquePostcodes table.")
                else:
                    print(f"Postcode {postcode} already exists in UniquePostcodes table.")
            except ClientError as e:
                print(f"Error accessing UniquePostcodes table: {e.response['Error']['Message']}")
        else:
            print(f"Event {record['eventName']} is not an INSERT operation. Skipping.")

    return {
        'statusCode': 200,
        'body': json.dumps('UniquePostcodes table updated successfully.')
    }
