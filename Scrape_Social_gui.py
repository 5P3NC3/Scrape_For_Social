#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog, scrolledtext
import queue
import threading
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import warnings

# Ignore warnings about SSL certificate verifications
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', message='urllib3.connectionpool')

# Function to check if URLs are accessible
def check_url(url, message_queue):
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = 'https://' + url
        response = requests.get(url, timeout=15)
        status_code = response.status_code
        message_queue.put(f"Checked {url}: status code {status_code}")
        if status_code == 200 or (300 <= status_code < 400):
            return url, True
        else:
            return url, False
    except requests.exceptions.RequestException as e:
        message_queue.put(f"Error checking {url}: {e}")
        return url, False


def check_urls(url_list, message_queue):
    good_urls = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check_url, url, message_queue) for url in url_list if url.strip()]
        for future in as_completed(futures):
            url, is_good = future.result()
            if is_good:
                good_urls.append(url)
    return good_urls

# Function to scrape social media links from URLs
def scrape_urls(url, message_queue):
    try:
        response = requests.get(url, verify=False, timeout=20)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            filtered_links = set()
            for link in links:
                href = link['href']
                for domain in ['youtube', 'facebook', 'linkedin', 'instagram', 'flickr', 'twitter', 'x.com']:
                    if domain in href:
                        filtered_links.add(href)
                        break
            for domain in ['youtube', 'facebook', 'linkedin', 'instagram', 'flickr', 'twitter', 'x.com']:
                if domain in url:
                    filtered_links.add(url)
                    break
            message_queue.put(f"Scraped {url}: found {len(filtered_links)} social links")
            return list(filtered_links)
        else:
            message_queue.put(f"Error scraping {url}: status code {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        message_queue.put(f"Error scraping {url}: {e}")
        return []


def find_social_media_links(url_list, message_queue):
    social_links = []
    for url in url_list:
        links = scrape_urls(url, message_queue)
        for link in links:
            social_links.append((url, link))
    return social_links

# Function to check the status of a single social media link
def check_social_media_link(link_tuple, driver, error_messages, message_queue):
    fqdn, link = link_tuple
    try:
        link = link.strip()
        # Quick 404 check via requests
        try:
            resp = requests.get(link, timeout=20)
            if resp.status_code == 404:
                status = "ERROR: 404 Response"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status
        except requests.exceptions.RequestException:
            pass

        # Selenium-based check
        driver.get(link)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        current_url = driver.current_url

        # Twitter / X check
        if "x.com" in link.lower() or "twitter.com" in link.lower():
            time.sleep(5)
            if re.search(r'(twitter|x)\.com/[^/]+', link.lower()):
                try:
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']"))
                    )
                except:
                    status = "ERROR: X/Twitter account likely doesn't exist"
                    message_queue.put(f"{link}: {status}")
                    return fqdn, link, status

        page_source = driver.page_source
        page_source_lower = page_source.lower()

        # LinkedIn specific checks
        if "linkedin.com" in link.lower():
            if "page-not-found" in current_url or "company/unavailable" in current_url:
                status = "ERROR: LinkedIn page not found"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status
            if "login" in current_url and "/in/" in link:
                status = "OK: LinkedIn profile (requires login)"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status

        # Instagram specific checks
        if "instagram.com" in link.lower():
            if "page not found" in page_source_lower or "sorry, this page isn't available" in page_source_lower:
                status = "ERROR: Instagram page not found"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status
            try:
                driver.find_element(By.XPATH, "//header[@class]")
                status = "OK"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status
            except:
                if "instagram.com/accounts/login" in current_url:
                    status = "OK: Private Instagram profile"
                    message_queue.put(f"{link}: {status}")
                    return fqdn, link, status

        # Facebook specific checks
        if "facebook.com" in link.lower():
            for pattern in [
                "isn't available right now",
                "this content isn't available right now",
                "this page has been removed",
                "this content isn't available at the moment"
            ]:
                if pattern in page_source_lower:
                    status = "ERROR: Facebook page not available"
                    message_queue.put(f"{link}: {status}")
                    return fqdn, link, status
            if current_url == "https://www.facebook.com/" and current_url != link:
                status = "ERROR: Facebook page not found (redirected to homepage)"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status

        # YouTube specific checks
        if "youtube.com" in link.lower():
            if any(x in link.lower() for x in ['/channel/', '/user/', '/c/']):
                if "this page isn't available" in page_source_lower or "404" in page_source_lower:
                    status = "ERROR: YouTube channel not found"
                    message_queue.put(f"{link}: {status}")
                    return fqdn, link, status

        # Generic error message checks
        for error in error_messages:
            err = error.lower()
            if f" {err} " in f" {page_source_lower} " or f"{err}." in page_source_lower or f"{err}," in page_source_lower:
                status = f"ERROR: '{error}' found"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status

        # If no errors found
        status = "OK"
        message_queue.put(f"{link}: {status}")
        return fqdn, link, status

    except Exception as e:
        status = f"ERROR: {e}"
        message_queue.put(f"{link}: {status}")
        return fqdn, link, status

# Function to check multiple social media links
def check_social_media_links(link_tuples, message_queue):
    error_messages = [
        "This content isn't available right now",
        "This account doesn't exist",
        "Something went wrong",
        "This LinkedIn Page isn't available",
        "The Page you're searching for no longer exists.",
        "The link you followed may be broken, or the page may have been removed.",
        "Go back to Instagram.",
        "Sorry, this page isn't available",
        "Page not found",
        "Account suspended",
        "https://www.linkedin.com/company/unavailable/",
        "couldn't find any content",
        "we didn't find that page",
        "this profile doesn't exist",
        "isn't available",
        "this user is private",
        "this page is private",
        "this account is no longer active",
        "account terminated"
    ]
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    status_list = []
    for link_tuple in link_tuples:
        fqdn, link, status = check_social_media_link(link_tuple, driver, error_messages, message_queue)
        status_list.append((fqdn, link, status))
    driver.quit()
    return status_list

# GUI Application
class ScrapeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Social Media Link Scraper")
        self.root.geometry("800x700")

        self.fqdn_label = tk.Label(root, text="Enter FQDNs (one per line) or import a file:")
        self.fqdn_label.pack(pady=5)
        self.fqdn_text = scrolledtext.ScrolledText(root, height=10)
        self.fqdn_text.pack(pady=5, fill=tk.X, padx=10)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)
        self.import_button = tk.Button(button_frame, text="Import File", command=self.import_file)
        self.import_button.pack(side=tk.LEFT, padx=5)
        self.scrape_fqdn_button = tk.Button(button_frame, text="Scrape FQDNs", command=self.scrape_fqdns)
        self.scrape_fqdn_button.pack(side=tk.LEFT, padx=5)

        self.progress_label = tk.Label(root, text="Progress and Results:")
        self.progress_label.pack(pady=5)
        self.progress_text = scrolledtext.ScrolledText(root, height=20)
        self.progress_text.pack(pady=5, fill=tk.BOTH, expand=True, padx=10)

        self.add_links_label = tk.Label(root, text="Add more social media links (one per line):")
        self.add_links_label.pack(pady=5)
        self.add_links_text = scrolledtext.ScrolledText(root, height=5)
        self.add_links_text.pack(pady=5, fill=tk.X, padx=10)

        self.scrape_social_button = tk.Button(root, text="Scrape Social Media Links", command=self.scrape_social_links)
        self.scrape_social_button.pack(pady=10)

        self.message_queue = queue.Queue()
        self.social_links = []
        self.check_queue()

    def import_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            with open(file_path, 'r') as f:
                content = f.read()
            self.fqdn_text.delete(1.0, tk.END)
            self.fqdn_text.insert(tk.END, content)

    def scrape_fqdns(self):
        fqdn_list = self.fqdn_text.get(1.0, tk.END).strip().split('\n')
        threading.Thread(target=self.run_scrape_fqdns, args=(fqdn_list,), daemon=True).start()

    def run_scrape_fqdns(self, fqdn_list):
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.insert(tk.END, "Checking URLs...\n")
        good_urls = check_urls(fqdn_list, self.message_queue)
        self.progress_text.insert(tk.END, f"Found {len(good_urls)} accessible URLs.\n")
        self.progress_text.insert(tk.END, "Scraping for social media links...\n")
        social_links = find_social_media_links(good_urls, self.message_queue)
        timestamp = datetime.now().strftime("%Y-%m-%d")
        csv_file_name = f"found_social_links_{timestamp}.csv"
        with open(csv_file_name, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['FQDN', 'Social Link'])
            for fqdn, link in social_links:
                writer.writerow([fqdn, link])
        self.progress_text.insert(tk.END, f"\nSaved found social media links to {csv_file_name}\n")
        for fqdn, link in social_links:
            self.progress_text.insert(tk.END, f"{fqdn},{link}\n")
        self.social_links = social_links

    def scrape_social_links(self):
        added_links = self.add_links_text.get(1.0, tk.END).strip().split('\n')
        added_tuples = [("User Added", link) for link in added_links if link.strip()]
        all_link_tuples = self.social_links + added_tuples
        if not all_link_tuples:
            self.progress_text.insert(tk.END, "\nNo links to check. Please scrape FQDNs first or add links manually.\n")
            return
        threading.Thread(target=self.run_scrape_social_links, args=(all_link_tuples,), daemon=True).start()

    def run_scrape_social_links(self, link_tuples):
        self.progress_text.insert(tk.END, "\nChecking social media links...\n")
        status_list = check_social_media_links(link_tuples, self.message_queue)
        error_count = sum(1 for _, _, status in status_list if "ERROR" in status or "WARNING" in status)
        ok_count = len(status_list) - error_count
        self.progress_text.insert(tk.END, f"\nSummary: {ok_count} links OK, {error_count} links with issues\n")
        timestamp = datetime.now().strftime("%Y-%m-%d")
        csv_file_name = f"social_links_status_{timestamp}.csv"
        with open(csv_file_name, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['FQDN', 'Social Link', 'Status'])
            for fqdn, link, status in status_list:
                writer.writerow([fqdn, link, status])
        self.progress_text.insert(tk.END, f"\nSaved status to {csv_file_name}\n")
        for fqdn, link, status in status_list:
            self.progress_text.insert(tk.END, f"{fqdn},{link},{status}\n")

    def check_queue(self):
        try:
            while True:
                msg = self.message_queue.get_nowait()
                self.progress_text.insert(tk.END, msg + '\n')
                self.progress_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScrapeApp(root)
    root.mainloop()
