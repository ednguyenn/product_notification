#!/bin/bash

# Set your variables
AWS_REGION="<ap-southeast-2>"
ACCOUNT_ID="<211125652748>"
REPO_NAME="scraper-function"
IMAGE_NAME="scraper-function"

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME ./src/scraper_function

# Log in to Amazon ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag the Docker image
echo "Tagging Docker image..."
docker tag $IMAGE_NAME:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

# Push the Docker image to ECR
echo "Pushing Docker image to ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest

echo "Docker image pushed to ECR successfully!"
