import os
import pandas as pd

from market.market import Market
from market.constant import *

def main():
    """
    Main function to run the web scraping bot for Woolworths online catalogue.
    """
    try:
        # Initialize the Market bot
        bot = Market()  # Prevent the browser from quitting automatically
        
        # Land on the first page
        bot.land_first_page(url=WOOLWORTH_URL)
        
        # Enter the desired postcode to scrape data
        bot.enter_postcode(postcode=POSTCODE)
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
        
        # Create a DataFrame from the extracted data
        df = pd.DataFrame(full_data)
        
        # Define the folder path to save the CSV file
        folder_path = 'data'
        
        # Create the folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        
        # Define the CSV file path
        file_path = os.path.join(folder_path, 'rawproducts.csv')
        
        # Save the DataFrame to a CSV file
        df.to_csv(file_path, index=False)
        
        print(f"Data saved to {file_path}")
        
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
            raise

if __name__ == "__main__":
    main()