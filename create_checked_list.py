# This code shoud check urls for validity and add a scheme to the urls, then add the good urls to a new file.
#The script primarily relies on requests as it is checking for http responses.

import requests
from urllib.parse import urlparse
#Concurrent.futures allows multithreading by checking multiple urls concurrently.
from concurrent.futures import ThreadPoolExecutor, as_completed

# The below funtion takes fqdns as input and checks if they have a scheme then makes a get request.
def check_url(url):
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = 'https://' + url
#The script is more accurate if you increase the timeout but it already takes a long time. 15 seems to be a sweet spot.
        response = requests.get(url, timeout=15)
        if response.status_code == 200 or (response.status_code >= 300 and response.status_code < 400):
            return url, True  # Return the URL and True if it has a valid status code
        else:
            return url, False  # Return the URL and False if it does not have a valid status code
    except requests.exceptions.RequestException as e:
        return url, False  # Return the URL and False if an exception occurs


# The file_name is made from user input. The function below opens the file, reads each line and then returns a list of good urls.
def check_urls_multithread(file_name):
    with open(file_name, 'r') as f:
        urls = [line.strip() for line in f.readlines()]

    good_urls = []
    with ThreadPoolExecutor(max_workers=5) as executor:  # Adjust max_workers as needed
        futures = [executor.submit(check_url, url) for url in urls]
        for future in as_completed(futures):
            url, is_good = future.result()
            if is_good:
                good_urls.append(url)
            else:
                print(f"checked url:  {url}")

    return good_urls

#The maine funtion requests name of file as user input.
if __name__ == "__main__":
    file_name = input("Enter the name of the file with fqdns: ")
    checked_urls = check_urls_multithread(file_name)

    if checked_urls:
        with open('checked_urls.txt', 'w') as f:
            for url in checked_urls:
                f.write(url + '\n')
        print(f"Successfully wrote {len(checked_urls)} URLs to checked_urls.txt")
    else:
        print("URLS provided must be checked manually or can't be accessed.")
