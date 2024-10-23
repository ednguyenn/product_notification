import os
import boto3
from utils import Market
import json
from selenium.webdriver.common.by import By
# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
product_table = dynamodb.Table('ProductCatalog')  # Name of the DynamoDB table

def lambda_handler(event, context):
    """
    Lambda function to scrape Woolworths catalogue based on a DynamoDB event
    and write product data to a DynamoDB table.
    """
    try:
        # Extract DynamoDB event data (Assume it's an INSERT event for new postcode requests)
        records = event.get('Records', [])
        
        for record in records:
            if record['eventName'] == 'INSERT':
                # Get the new record from DynamoDB Stream
                new_image = record['dynamodb']['NewImage']
                postcode = new_image['POSTCODE']['S']  # Assuming POSTCODE is stored as a string in DynamoDB

                # Initialize the Market bot
                bot = Market(driver_path=By.XPATH)
                
                # Land on the first page
                bot.land_first_page(url='https://www.woolworths.com.au/shop/catalogue/view#view=catalogue2&saleId=54911&areaName=VIC&page=1')
                
                # Enter the postcode from the event data
                bot.enter_postcode(postcode=postcode)
                bot.select_first_postcode_option()
                bot.click_read_catalogue_button()
                
                # Get the list of categories
                category_list = bot.get_category_list()
                
                # Iterate through each category and extract product data
                for category in category_list:
                    bot.click_category(category)
                    category_data, back_clicks = bot.extract_products_in_category()
                    
                    # Store product data directly using the new method
                    bot.store_product_data(category_data, postcode, category)

                    bot.go_back_to_category_page(back_clicks)
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Data scraped and saved for postcode: {postcode}')
        }

    except Exception as e:
        # Handle PATH errors specifically
        if 'in PATH' in str(e):
            print(
                'You are trying to run the bot from command line \n'
                'Please add to PATH your Selenium Drivers \n'
                'Windows: \n'
                '    set PATH=%PATH%;C:path-to-your-folder \n \n'
                'Linux: \n'
                '    PATH=$PATH:/path/to/your/folder/ \n'
            )
        else:
            # Log and raise any unexpected errors
            print(f"Error: {e}")
            raise

    return {
        'statusCode': 500,
        'body': json.dumps('An error occurred during the scraping process.')
    }


