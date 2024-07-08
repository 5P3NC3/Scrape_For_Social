import requests
from bs4 import BeautifulSoup #scrapes and parses html
import csv
import warnings
from datetime import datetime #not necessary for script just wanted to name my csv file the Month day hour
from selenium import webdriver # Automates a webdriver so it's not popping a chrome page open over and over again.
from selenium.webdriver.chrome.options import Options # lets you customize how your using the automated chrome browser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time # necessary for time delays i.e. sleep
import os
import concurrent.futures


#This ignores warnings, not necessary for script but keeps screen from being cluttered.

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', message='urllib3.connectionpool')


#Below function scrapes social media urls from urls in file.
def scrape_urls(url, csv_writer):
    try:

# This requests.get sends the get reuests to urls. if it doesn't get a 200 it produces an error but all urls passed to this script should be 200
        response = requests.get(url, verify=False, timeout=20)
        if response.status_code == 200:

            #after it gets a 200 it parses the html. soup.find is whats actually looking for links.
            #href is "hypertext reference" it specifically locates urls and looks like this: <a href="https://www.example.com">Click here</a>
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            #set() is just where you store your links that you scraped
            filtered_links = set()
            # now if social media links are found they are added to the filtered link set
            # if the original link contained a social link it is also added to the set.
            # Scraping is against twitters terms of service, however the script still works with twitter just add twitter to the list when you want.
            for link in links:
                href = link['href']
                for domain in ['youtube', 'facebook', 'linkedin', 'instagram', 'flickr', 'twitter']:
                    if domain in href:
                        filtered_links.add(href)
                        break
            for domain in ['youtube', 'facebook', 'linkedin', 'instagram', 'flickr', 'twitter']:
                if domain in url:
                    filtered_links.add(url)
                    break
            return list(filtered_links)
        #If the below errors print, there is a problem with the list being passed to the script.
        else:
            csv_writer.writerow([f"ERROR ERROR ERROR: {response.status_code} for URL {url}"])
            return []
    except requests.exceptions.RequestException as e:
        csv_writer.writerow([f"ERROR ERROR ERROR: {e} for URL {url}"])
        return []


def read_urls_from_file(file_path):
    urls = [] #Empty list for urls from file
    with open(file_path, 'r') as file: # works with csv file or just text file
        reader = csv.reader(file)
        for row in reader:
            urls.append(row[0]) #0 is first line in file
    return urls


def main():
    if os.path.exists("checked_urls.txt"):
        print("\n\n\n\nNow we will scrape the URLS from checked_urls.txt")
        with open("checked_urls.txt", "r") as file:
            urls = [line.strip() for line in file]
    else:
        # Input must be file with one url on each line with a full scheme
        file_path = input("Enter the file path containing the URLs to scrape: ").strip()
        urls = read_urls_from_file(file_path)



    error_messages = [
        r"This content isn't available right now",
        r"This account doesn’t exist",
        "This LinkedIn Page isn’t available",
        "The Page you're searching for no longer exists.",
        "The link you followed may be broken, or the page may have been removed.",
        "Go back to Instagram.",
        "Sorry, this page isn't available",
        "Page not found",
        "Account suspended"
    ]

    timestamp = datetime.now().strftime("%m-%d_%H")
    csv_file_name = f"output_{timestamp}.csv"

    with open(csv_file_name, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        all_scraped_links = []
        for url in urls:
            print(f"Scraping links from {url}:")
            csv_writer.writerow([f"Scraping links from {url}:"])
            scraped_links = scrape_urls(url, csv_writer)
            all_scraped_links.extend(scraped_links) #adds scraped links to the list created in "all_scraped_links = []"
            for link in scraped_links:
                print(link)
                csv_writer.writerow([link])

        print("\nNow checking status of these links:")
        csv_writer.writerow(["\nNow checking status of these links:"])
        csv_writer.writerow(['URL', 'Status'])

#These options allow the browser to run the background and run a bit smoother.
        options = Options()
        options.add_argument('--headless')#Run in background in invisible window
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')#less secure but faster. fine for it being automated.
        options.add_argument('--window-size=1920,1080')

        driver = webdriver.Chrome(options=options)# creates the chrome instance

        for link in all_scraped_links:
            try:
                response = requests.get(link)
                if response.status_code == 404:
                    error_message = f"ERROR ERROR ERROR: 404 Response for URL {link}"
                    print(error_message)
                    csv_writer.writerow([link, error_message])
                    continue

                driver.get(link)
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                #time.sleep(15)  #needs to be long enough for java script to generate text.
                page_source = driver.page_source #This includes the html and the generated text from the java script.
                error_found = False
                for error in error_messages:
                    if error in page_source:
                        error_found = True
                        error_message = f"ERROR ERROR ERROR: '{error}' found on {link}"
                        print(error_message)
                        csv_writer.writerow([link, error_message])
                        break
                if not error_found:
                    no_error_message = f"no error found on {link}"
                    print(no_error_message)
                    csv_writer.writerow([link, no_error_message])
            except Exception as e:
                error_message = f"ERROR ERROR ERROR: {e} for URL {link}"
                print(error_message)
                csv_writer.writerow([link, error_message])

        driver.quit() #close browser instance

        print("\n")
    print(f"Output written to {csv_file_name}")


if __name__ == "__main__":
    main()
