import requests
from bs4 import BeautifulSoup
import csv
import warnings
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Ignore warnings about SSL certificate verifications
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', message='urllib3.connectionpool')

# List of error messages to detect
error_messages = [
    "This content isn't available right now",
    "This account doesn't exist",  # Expected for X.com non-existent profiles
    "Something went wrong",
    "This LinkedIn Page isn’t available",
    "The Page you're searching for no longer exists.",
    "The link you followed may be broken, or the page may have been removed.",
    "Go back to Instagram.",
    "Sorry, this page isn't available",
    "Page not found",
    "Account suspended",
    "https://www.linkedin.com/company/unavailable/"
]

# CSV file naming with timestamp
timestamp = datetime.now().strftime("%m-%d_%H")
csv_file_name = f"output_{timestamp}.csv"

scraped_links = [
    "https://www.facebook.com/exampleperson11111",
    "https://www.linkedin.com/company/unavailable/",
    "https://www.instagram.com/exampleperson1111",
    "https://www.flickr.com/photos/example",
    "https://x.com/exampleperson1111111"
]

with open(csv_file_name, 'w', newline='', encoding='utf-8') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['URL', 'Status'])

    # Configure Selenium with headless Chrome
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    driver = webdriver.Chrome(options=options)

    for link in scraped_links:
        try:
            # Check HTTP status code
            response = requests.get(link)
            if response.status_code == 404:
                print(f"ERROR ERROR ERROR: 404 Response for URL {link}")
                csv_writer.writerow([link, '404 Error'])
                continue

            # Load page with Selenium
            driver.get(link)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Add delay for X.com to allow dynamic content to load
            if "x.com" in link:
                time.sleep(5)  # Wait 5 seconds for JavaScript to execute

            # Get page source after delay
            page_source = driver.page_source
            page_source_lower = page_source.lower()


            # Check for error messages
            error_found = False
            for error in error_messages:
                if error.lower() in page_source_lower:
                    error_found = True
                    error_message_found = f"ERROR ERROR ERROR: '{error}' found on {link}"
                    print(error_message_found)
                    csv_writer.writerow([link, error])
                    break

            if not error_found:
                no_errors_found = f"no errors found on {link}"
                print(no_errors_found)
                csv_writer.writerow([link, 'No Error'])

        except (requests.exceptions.RequestException, Exception) as e:
            error_request = f"ERROR ERROR ERROR: {e} for URL {link}"
            print(error_request)
            csv_writer.writerow([link, 'Exception'])

    driver.quit()
    print("\n")

print(f"Output written to {csv_file_name}")
