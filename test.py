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

# Ignore warnings about the SSL cert verifications
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', message='urllib3.connectionpool')

error_messages = [
    r"This content isn't available right now",
    r"This account doesn’t exist",
    "This LinkedIn Page isn’t available",
    "The Page you're searching for no longer exists.",
    "The link you followed may be broken, or the page may have been removed.",
    "Go back to Instagram.",
    "Sorry, this page isn't available",
    "Page not found",
    "Account suspended",
    "https://www.linkedin.com/company/unavailable/"
]

# The csv file is named output{month-day_hour}
timestamp = datetime.now().strftime("%m-%d_%H")
csv_file_name = f"output_{timestamp}.csv"

scraped_links = [
    "https://www.facebook.com/elliott.ediebroken",
    "https://www.linkedin.com/company/sustainment-management-system-sms",
    "https://www.instagram.com/joebidennnnnnnnnNN/",
    "https://www.flickr.com/photos/xtechsearchh/"

]

with open(csv_file_name, 'w', newline='', encoding='utf-8') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['URL', 'Status'])

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)

    for link in scraped_links:
        try:
            response = requests.get(link)
            if response.status_code == 404:
                print(f"ERROR ERROR ERROR: 404 Response for URL {link}")
                csv_writer.writerow([link, '404 Error'])
                continue

            driver.get(link)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            #time.sleep(15)  # Adjust sleep time as needed

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            error_message = soup.find('div', {'class': 'error-message'})

            # Check if any error message from the list is found in the page source
            error_found = False
            for error in error_messages:
                if error in page_source:
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
