import os
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service



class Market(webdriver.Chrome):
    """
    A class to automate interactions with the Woolworths online catalogue using Selenium WebDriver.
    """
    def __init__(self, driver_path: str) -> None:
        self.driver_path = driver_path  # Ensure driver_path is initialized
        os.environ['PATH'] += os.pathsep + self.driver_path

        options = webdriver.ChromeOptions()

        service = Service("/opt/chromedriver")  # Corrected import usage
        options.binary_location = '/opt/chrome/chrome'
        options.add_argument("--headless=new")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280x1696")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument(f"--user-data-dir={mkdtemp()}")
        options.add_argument(f"--data-path={mkdtemp()}")
        options.add_argument(f"--disk-cache-dir={mkdtemp()}")
        options.add_argument("--remote-debugging-port=9222")

        chrome = webdriver.Chrome(options=options, service=service)
        # Initialize product extractor or any other related components
        self.product_extractor = ProductExtractor(self)
        
    def land_first_page(self,url):
        """
        Navigate to the Woolworths URL defined in constants.
        """
        self.get(url)

    def enter_postcode(self,postcode):
        """
        Enter the postcode into the search input.
        """
        input_postcode = self.find_element('id', 'wx-digital-catalogue-autocomplete')
        input_postcode.send_keys(postcode)

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
            hover_element = WebDriverWait(self, 10).until(
                EC.visibility_of_element_located((By.ID, 'sf-navcategory-button'))
            )
            action.move_to_element(hover_element).perform()
            WebDriverWait(self, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'sf-navcategory-link'))
            )
        except Exception as e:
            print(f"Error during hover: {e}")

    def click_category(self, category):
        """
        Click on a specific category from the category list.

        Args:
            category (str): The name of the category to click.
        """
        try:
            self.hover_to_toggle_categories()
            categories = WebDriverWait(self, 30).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'sf-navcategory-link'))
            )
            for element in categories:
                if element.text == category:
                    element.click()
                    break
        except TimeoutError:
            print(f"Timeout occurred while waiting for category: {category}")
        except Exception as e:
            print(f"An error occurred while clicking category: {category}. Error: {e}")

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
            next_page_btn = WebDriverWait(self, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[aria-label="Next page"]'))
            )
            next_page_btn.click()
            time.sleep(2)  # Allow page to fully load before extraction
            return True
        except Exception as e:
            print(f"Error clicking next page: {e}")
            return False

    def extract_products_in_category(self):
        """
        Extract products from all pages of a category.

        Returns:
            tuple: A list of product data and the number of pages navigated.
        """
        products = []
        pages_navigated = 0  # Counter to track the number of pages navigated
        try:
            while True:
                page_products = self.product_extractor.get_products_from_current_page()
                print(f"Extracted {len(page_products)} products from page {pages_navigated + 1}")
                products.extend(page_products)
                if not self.click_next_page():
                    break
                pages_navigated += 1  # Increment the counter each time we navigate to the next page
        except Exception as e:
            print(f"An error occurred during product extraction: {e}")
        finally:
            return products, pages_navigated

    def go_back_to_category_page(self, pages_navigated):
        """
        Navigate back to the category page.

        Args:
            pages_navigated (int): The number of pages navigated.
        """
        for _ in range(pages_navigated + 1):  # Go back the number of pages navigated plus one more to reach the category page
            self.back()
            time.sleep(2)  # Wait for the page to fully load

    def store_product_data(self, product_data, postcode, category):
        try:
            for product in product_data:
                item = {
                    'ProductName': product.get('ProductName', 'NA'),
                    'Postcode': postcode,
                    'Category': category,
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
                self.product_table.put_item(Item=item)
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
