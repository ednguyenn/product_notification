#!/bin/bash

# Variables
TABLE_NAME="ProductCatalogTable"
REGION="ap-southeast-2"  

# Create the DynamoDB table
aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions \
        AttributeName=POSTCODE,AttributeType=S \
        AttributeName=ProductName,AttributeType=S \
    --key-schema \
        AttributeName=POSTCODE,KeyType=HASH \
        AttributeName=ProductName,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes '[
        {
            "IndexName": "ProductNameIndex",
            "KeySchema": [
                {"AttributeName":"ProductName","KeyType":"HASH"},
                {"AttributeName":"POSTCODE","KeyType":"RANGE"}
            ],
            "Projection":{
                "ProjectionType":"ALL"
            }
        }
    ]' \
    --region "$REGION"

# Wait for the table to be created
aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"

echo "Table $TABLE_NAME has been created successfully."
