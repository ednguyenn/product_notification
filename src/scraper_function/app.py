import os
import boto3
import json
import time
import tempfile 
import logging

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    handlers=[
        logging.FileHandler('app.log'),  
        logging.StreamHandler()  #log to console
    ]
)


# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
product_table = dynamodb.Table('ProductCatalogTable')  # Name of the DynamoDB table

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
                postcode = int(new_image['POSTCODE']['S'])  # Assuming POSTCODE is stored as a string in DynamoDB

                # Initialize the Market bot
                bot = Market()
                
                # Land on the first page
                bot.land_first_page(url='https://www.woolworths.com.au/shop/catalogue')
                
                # Enter the postcode from the event data
                bot.enter_postcode(postcode=postcode)
                bot.select_first_postcode_option()
                bot.click_read_catalogue_button()
                
                # Get the list of categories
                category_list = bot.get_category_list()
                
                # Iterate through each category and extract product data
                for category in category_list:
                    # Click the category to load its products
                    bot.click_category(category)

                    # Extract all products in the current category
                    category_data = bot.extract_products_in_category(category)

                    # Store the extracted product data
                    bot.store_product_data(category_data, postcode, category)

                    time.sleep(0.5)
        
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




class Market(webdriver.Chrome):
    """
    A class to automate interactions with the Woolworths online catalogue using Selenium WebDriver.
    """
    def __init__(self) -> None:

        options = webdriver.ChromeOptions()
        service = Service("/opt/chromedriver")  

        USER_AGENT: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) \
    AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"

        options.binary_location = '/opt/chrome/chrome'
        options.add_argument("--headless=new")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1080x1920")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")  # Use tempfile.mkdtemp()
        options.add_argument(f"--data-path={tempfile.mkdtemp()}")      # Use tempfile.mkdtemp()
        options.add_argument(f"--disk-cache-dir={tempfile.mkdtemp()}") # Use tempfile.mkdtemp()
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument(f"--user-agent={USER_AGENT}")

        try:
            super().__init__(options=options, service=service)
            logging.info("WebDriver initialized successfully.")
            
            # Initialize product extractor or any other related components
            self.product_extractor = ProductExtractor(self)
        except Exception as e:
            logging.error(f"Failed to initialize WebDriver: {e}")
        
    def land_first_page(self,url):
        """
        Navigate to the Woolworths URL defined in constants.
        """
        self.get(url)

    def enter_postcode(self, postcode):
        """
        Enter the postcode into the search input.
        """
        try:
            # Create a wait object
            wait = WebDriverWait(self, 10)  # Timeout after 10 seconds

            # Wait for the input element to be present and visible
            input_postcode = wait.until(
                EC.visibility_of_element_located((By.ID, 'wx-digital-catalogue-autocomplete'))
            )

            # Send the postcode to the input element
            input_postcode.send_keys(postcode)
        except Exception as e:
            # Take a screenshot if an error occurs
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            screenshot_filename = f'error_screenshot_{timestamp}.png'
            self.save_screenshot(screenshot_filename)  # Use self to call save_screenshot
            print(f"An error occurred while entering postcode: {str(e)}. Screenshot saved as '{screenshot_filename}'.")
            print(f"Page source:\n{self.page_source}")  # Print the page source for further diagnosis

    def select_first_postcode_option(self):
        """
        Select the first postcode option from the autocomplete dropdown.
        """
        select_postcode = WebDriverWait(self, 5).until(
            EC.element_to_be_clickable((By.ID, 'wx-digital-catalogue-autocomplete-item-0'))
        )
        select_postcode.click()

    def click_read_catalogue_button(self):
        """
        Click the button to read the digital catalogue.
        """
        read_catalogue_button = WebDriverWait(self, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'core-button-secondary'))
        )
        read_catalogue_button.click()

    def hover_to_toggle_categories(self):
        """
        Hover over the categories toggle to display the category list.
        """
        action = ActionChains(self)
        try:
            # Wait for the hover element to be visible
            hover_element = WebDriverWait(self, 10).until(
                EC.visibility_of_element_located((By.ID, 'sf-navcategory-button'))
            )
            
            # Perform the hover action
            action.move_to_element(hover_element).perform()

            # Wait for the category links to be present after hovering
            WebDriverWait(self, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'sf-navcategory-link'))
            )

            logging.info("Successfully hovered over the categories toggle.")
            
        except TimeoutException:
            logging.error("Timeout occurred while waiting for the categories toggle or links.")
        except Exception as e:
            logging.error(f"Error during hover: {e}")

    def click_category(self, category):
        """
        Click on a specific category from the category list.

        Args:
            category (str): The name of the category to click.
        """
        try:
            self.hover_to_toggle_categories()
            categories = WebDriverWait(self, 60).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'sf-navcategory-link'))
            )
            # Iterate over the category elements to find the one that matches the name
            for element in categories:
                if element.text == category:
                    # Wait for the element to be clickable after scrolling
                    WebDriverWait(self, 10).until(EC.element_to_be_clickable(element))
                    # Scroll the element into view
                    self.execute_script("arguments[0].click();", element)
                    time.sleep(1) # Wait for page to be fully loaded
                    logging.info(f"Clicked on category: {category}")
                    return True
        except TimeoutException:
            logging.error(f"Timeout occurred while waiting for category: {category}")
        except Exception as e:
            logging.error(f"An error occurred while clicking category: {category}. Error: {e}")
        return False

    def get_category_list(self):
        """
        Retrieve and return the list of categories.

        Returns:
            list: A list of category names.
        """
        self.hover_to_toggle_categories()
        try:
            categories = WebDriverWait(self, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'sf-navcategory-link'))
            )
            category_names = [category.text for category in categories]
            return category_names
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return []

    def click_next_page(self):
        """
        Click the button to navigate to the next page of products.

        Returns:
            bool: True if navigation to the next page was successful, False otherwise.
        """
        try:
            # Wait for the next page button to be clickable
            next_page_btn = WebDriverWait(self, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label="Next page"]'))
            )
            # Scroll to the next page button
            self.execute_script("arguments[0].scrollIntoView(true);", next_page_btn)

            time.sleep(0.5) 

            # Attempt to click the button
            self.execute_script("arguments[0].click();", next_page_btn)     
            time.sleep(0.75)    
            return True
        except TimeoutException:
            logging.info("No 'Next page' button found or it was not clickable. Reached the end of pagination.")
            return False
        except Exception as e:
            print(f"Error clicking next page: {e}")
            return False

    def extract_products_in_category(self,category):
        """
        Extract products from all pages of a category.

        Returns:
            list: A list of product data from the category.
        """
        products = []  # To store the products from all pages in the category
        try:
            while True:
                # Extract products from the current page
                page_products = self.product_extractor.get_products_from_current_page()
                print(f"Extracted {len(page_products)} products from the {category} page.")
                products.extend(page_products)

                # Check if there's a "Next page" button to click
                if not self.click_next_page():
                    return False
        except Exception as e:
            print(f"An error occurred during product extraction: {e}")
        finally:
            return products

    def store_product_data(self, product_data, postcode, category):
        try:
            for product in product_data:
                item = {
                    'ProductName': product.get('ProductName', 'NA'),
                    'POSTCODE': str(postcode),
                    'Category': str(category),
                    'Price': product.get('price', 'NA'),
                    'OptionSuffix': product.get('option_suffix', 'NA'),
                    'SalePrice': product.get('sale_price', 'NA'),
                    'RegularPrice': product.get('regular_price', 'NA'),
                    'Saving': product.get('saving', 'NA'),
                    'OfferValid': product.get('offer_valid', 'NA'),
                    'ComparativeText': product.get('comparative_text', 'NA'),
                    'SaleOption': product.get('sale_option', 'NA')
                }
                # Assuming product_table is initialized elsewhere in the class
                product_table.put_item(Item=item)
        except Exception as e:
            print(f"Error writing to DynamoDB: {e}")

class ProductExtractor:
    """
    This class is responsible for extracting data from a single product page.
    """
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def try_get_text(self, parent: WebDriver, selector: str, default: str) -> str:
        """
        Try to get the text content of an element.

        Args:
            parent (WebDriver): The parent WebDriver instance.
            selector (str): The CSS selector of the element.
            default (str): The default value to return if the element is not found.

        Returns:
            str: The text content of the element or the default value.
        """
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).text
        except:
            return default

    def try_get_attribute(self, parent: WebDriver, selector: str, attribute: str, default: str) -> str:
        """
        Try to get an attribute value of an element.

        Args:
            parent (WebDriver): The parent WebDriver instance.
            selector (str): The CSS selector of the element.
            attribute (str): The attribute to retrieve.
            default (str): The default value to return if the element is not found.

        Returns:
            str: The attribute value or the default value.
        """
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).get_attribute(attribute)
        except:
            return default

    def get_products_from_current_page(self) -> list:
        """
        Extract product data from the current page.

        Returns:
            list: A list of product data dictionaries.
        """
        try:
            products = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'sf-item-content'))
            )

            product_list = []

            for product in products:
                data = {
                    "ProductName": self.try_get_text(product, ".sf-item-heading", "NA"),
                    "price": self.try_get_text(product, ".sf-pricedisplay", "NA"),
                    "option_suffix": self.try_get_text(product, ".sf-optionsuffix", "NA"),
                    "sale_price": self.try_get_text(product, ".sf-saleoptiontext", "NA"),
                    "regular_price": self.try_get_text(product, ".sf-regprice", "NA"),
                    "regoptiondesc": self.try_get_text(product, ".sf-regoptiondesc", "NA"),
                    "saving": self.try_get_text(product, ".sf-regprice", "NA"),
                    "offer_valid": self.try_get_text(product, ".sale-dates", "NA"),
                    "comparative_text": self.try_get_text(product, ".sf-comparativeText", "NA"),
                    "sale_option": self.try_get_text(product, ".sf-saleoptiondesc", "NA")
                }
                product_list.append(data)
            return product_list

        except Exception as e:
            print(f"An error occurred: {e}")
            return []  # Return an empty list if an error occurs
