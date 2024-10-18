#!/bin/bash

# Variables
TABLE_NAME="UniquePostcodes"
REGION="ap-southeast-2"  

# Create the DynamoDB table
aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions \
        AttributeName=POSTCODE,AttributeType=S \
    --key-schema \
        AttributeName=POSTCODE,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION"

# Wait for the table to be created
aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"

echo "Table $TABLE_NAME has been created successfully."
