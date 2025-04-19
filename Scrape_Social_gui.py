#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog, scrolledtext
import queue
import threading
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

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
                for domain in ['youtube', 'facebook', 'linkedin', 'instagram', 'flickr', 'twitter']:
                    if domain in href:
                        filtered_links.add(href)
                        break
            for domain in ['youtube', 'facebook', 'linkedin', 'instagram', 'flickr', 'twitter']:
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

# Function to check the status of social media links
def check_social_media_link(link_tuple, driver, error_messages, message_queue):
    fqdn, link = link_tuple
    try:
        response = requests.get(link)
        if response.status_code == 404:
            status = "ERROR: 404 Response"
            message_queue.put(f"{link}: {status}")
            return fqdn, link, status
        driver.get(link)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        page_source = driver.page_source
        for error in error_messages:
            if error in page_source:
                status = f"ERROR: '{error}' found"
                message_queue.put(f"{link}: {status}")
                return fqdn, link, status
        status = "OK"
        message_queue.put(f"{link}: {status}")
        return fqdn, link, status
    except Exception as e:
        status = f"ERROR: {e}"
        message_queue.put(f"{link}: {status}")
        return fqdn, link, status

def check_social_media_links(link_tuples, message_queue):
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
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
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

        self.fqdn_label = tk.Label(root, text="Enter FQDNs (one per line) or import a file:")
        self.fqdn_label.pack(pady=5)
        self.fqdn_text = scrolledtext.ScrolledText(root, height=10)
        self.fqdn_text.pack(pady=5)

        self.import_button = tk.Button(root, text="Import File", command=self.import_file)
        self.import_button.pack(pady=5)

        self.scrape_fqdn_button = tk.Button(root, text="Scrape FQDNs", command=self.scrape_fqdns)
        self.scrape_fqdn_button.pack(pady=5)

        self.progress_label = tk.Label(root, text="Progress and Results:")
        self.progress_label.pack(pady=5)
        self.progress_text = scrolledtext.ScrolledText(root, height=20)
        self.progress_text.pack(pady=5)

        self.add_links_label = tk.Label(root, text="Add more social media links (one per line):")
        self.add_links_label.pack(pady=5)
        self.add_links_text = scrolledtext.ScrolledText(root, height=5)
        self.add_links_text.pack(pady=5)

        self.scrape_social_button = tk.Button(root, text="Scrape Social Media Links", command=self.scrape_social_links)
        self.scrape_social_button.pack(pady=5)

        self.message_queue = queue.Queue()
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
        timestamp = datetime.now().strftime("%m-%d_%H")
        csv_file_name = f"found_social_links_{timestamp}.csv"
        with open(csv_file_name, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['FQDN', 'Social Link'])
            for fqdn, link in social_links:
                csv_writer.writerow([fqdn, link])
        self.progress_text.insert(tk.END, f"\nSaved found social media links to {csv_file_name}\n")
        self.progress_text.insert(tk.END, "Found social media links in CSV format:\n")
        self.progress_text.insert(tk.END, "FQDN,Social Link\n")
        for fqdn, link in social_links:
            self.progress_text.insert(tk.END, f"{fqdn},{link}\n")
        self.social_links = social_links  # Store for later use

    def scrape_social_links(self):
        added_links = self.add_links_text.get(1.0, tk.END).strip().split('\n')
        added_tuples = [("User Added", link) for link in added_links if link.strip()]
        all_link_tuples = self.social_links + added_tuples
        threading.Thread(target=self.run_scrape_social_links, args=(all_link_tuples,), daemon=True).start()

    def run_scrape_social_links(self, link_tuples):
        self.progress_text.insert(tk.END, "\nChecking social media links...\n")
        status_list = check_social_media_links(link_tuples, self.message_queue)
        timestamp = datetime.now().strftime("%m-%d_%H")
        csv_file_name = f"social_links_status_{timestamp}.csv"
        with open(csv_file_name, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(['FQDN', 'Social Link', 'Status'])
            for fqdn, link, status in status_list:
                csv_writer.writerow([fqdn, link, status])
        self.progress_text.insert(tk.END, f"\nSaved status to {csv_file_name}\n")
        self.progress_text.insert(tk.END, "All data in CSV format:\n")
        self.progress_text.insert(tk.END, "FQDN,Social Link,Status\n")
        for fqdn, link, status in status_list:
            self.progress_text.insert(tk.END, f"{fqdn},{link},{status}\n")

    def check_queue(self):
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.progress_text.insert(tk.END, message + '\n')
                self.progress_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScrapeApp(root)
    root.mainloop()
