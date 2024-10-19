#!/bin/bash

# Variables
TABLE_NAME="UniquePostcodesTable"
REGION="ap-southeast-2"  # Replace with your AWS region, e.g., us-east-1

# Create the DynamoDB table with streams enabled
aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions AttributeName=POSTCODE,AttributeType=S \
    --key-schema AttributeName=POSTCODE,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_IMAGE \
    --region "$REGION"

# Wait for the table to be created
aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"

echo "Table $TABLE_NAME has been created successfully with DynamoDB Streams enabled."
