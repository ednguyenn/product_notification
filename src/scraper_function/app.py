import os
from utils import Market
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    try:
        dynamodb = boto3.resource('dynamodb')

        product_table_name = 'ProductCatalogTable'
        product_table = dynamodb.Table(product_table_name)

        # Ensure WOOLWORTH_URL is set as an environment variable
        WOOLWORTH_URL = os.getenv('WOOLWORTH_URL')
        if not WOOLWORTH_URL:
            raise Exception("WOOLWORTH_URL environment variable not set.")

        # Process records from DynamoDB Stream
        for record in event['Records']:
            if record['eventName'] == 'INSERT':
                # Extract the postcode from the new image
                new_image = record['dynamodb']['NewImage']
                postcode = new_image['POSTCODE']['S']

                print(f"Processing postcode: {postcode}")

                # Perform scraping for this postcode
                print(f"Scraping data for postcode {postcode}...")
                try:
                    # Initialize the Market bot
                    bot = Market()

                    # Land on the first page
                    bot.land_first_page(url=WOOLWORTH_URL)

                    # Enter the desired postcode to scrape data
                    bot.enter_postcode(postcode=postcode)
                    bot.select_first_postcode_option()
                    bot.click_read_catalogue_button()

                    # Get the list of categories
                    category_list = bot.get_category_list()

                    # Initialize an empty list to hold all product data
                    full_data = []

                    # Iterate through each category and extract product data
                    for category in category_list:
                        bot.click_category(category)
                        category_data, back_clicks = bot.extract_products_in_category()
                        full_data.extend(category_data)
                        bot.go_back_to_category_page(back_clicks)

                    # Save data to DynamoDB
                    with product_table.batch_writer() as batch:
                        for item in full_data:
                            item['POSTCODE'] = postcode
                            item['ProductID'] = item.get('ProductID', item.get('ProductName', 'Unknown'))
                            item['ProductName'] = item.get('ProductName', 'Unknown')
                            # Ensure all attribute values are strings
                            item = {str(k): str(v) for k, v in item.items()}
                            batch.put_item(Item=item)

                    print(f"Data for postcode {postcode} saved to DynamoDB table {product_table_name}")
                except Exception as e:
                    print(f"Error scraping data for postcode {postcode}: {e}")
                    continue  # Skip to the next record
            else:
                print(f"Event {record['eventName']} is not an INSERT operation. Skipping.")

        return {
            'statusCode': 200,
            'body': json.dumps('Scraping completed.')
        }

    except Exception as e:
        print("Error:", e)
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }