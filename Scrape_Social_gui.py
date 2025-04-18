# social_scraper_gui.py
import sys
import csv
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QProgressBar, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal

# --- Import your refactored functions ---
# Assume you've refactored your scripts into modules like 'url_checker.py' and 'scraper.py'
# from url_checker import check_urls_multithread_gui # Modified for GUI progress
# from scraper import scrape_for_socials_gui, validate_social_links_gui # Modified for GUI progress

# Placeholder for actual refactored functions (replace with real imports)
def check_urls_multithread_gui(urls_or_file, progress_callback):
    print(f"Placeholder: Checking {urls_or_file}")
    # Simulate work and progress
    checked = []
    total = len(urls_or_file) if isinstance(urls_or_file, list) else 5 # Guess if file
    for i, url in enumerate(urls_or_file if isinstance(urls_or_file, list) else ["fqdn1.com", "fqdn2.com"]):
         import time; time.sleep(0.5)
         status = "OK" if i % 2 == 0 else "Failed"
         progress_callback.emit(i + 1, total, f"Checking {url}... {status}")
         if status == "OK":
             checked.append(f"https://{url}")
    return checked

def scrape_for_socials_gui(checked_urls, progress_callback, result_callback):
    print(f"Placeholder: Scraping {len(checked_urls)} URLs")
    total = len(checked_urls)
    for i, url in enumerate(checked_urls):
        import time; time.sleep(1)
        progress_callback.emit(i + 1, total, f"Scraping {url}...")
        # Simulate finding links
        found_links = [f"https://facebook.com/{url.split('//')[1]}", f"https://twitter.com/{url.split('//')[1]}"]
        for link in found_links:
            result_callback.emit(url, link) # Emit each found link associated with its source FQDN
    progress_callback.emit(total, total, "Scraping complete.")


def validate_social_links_gui(social_links_map, progress_callback, result_callback):
    print(f"Placeholder: Validating {len(social_links_map)} links")
    all_links = list(social_links_map.keys())
    total = len(all_links)
    for i, link in enumerate(all_links):
        import time; time.sleep(0.7)
        status = "OK" if i % 3 != 0 else "Error: Page Not Found"
        progress_callback.emit(i + 1, total, f"Validating {link}...")
        result_callback.emit(link, status) # Emit validation result
    progress_callback.emit(total, total, "Validation complete.")
# --- End Placeholder ---


# Worker Threads for Long Operations
class CheckWorker(QThread):
    progress = Signal(int, int, str) # current, total, message
    finished = Signal(list) # List of good URLs

    def __init__(self, fqdns_or_file):
        super().__init__()
        self.fqdns_or_file = fqdns_or_file

    def run(self):
        good_urls = check_urls_multithread_gui(self.fqdns_or_file, self.progress)
        self.finished.emit(good_urls)

class ScrapeWorker(QThread):
    progress = Signal(int, int, str) # current, total, message
    found_link = Signal(str, str) # original_fqdn, social_link
    finished = Signal()

    def __init__(self, urls_to_scrape):
        super().__init__()
        self.urls_to_scrape = urls_to_scrape

    def run(self):
        scrape_for_socials_gui(self.urls_to_scrape, self.progress, self.found_link)
        self.finished.emit()

class ValidateWorker(QThread):
    progress = Signal(int, int, str) # current, total, message
    validation_result = Signal(str, str) # social_link, status
    finished = Signal()

    def __init__(self, social_links_map):
        super().__init__()
        self.social_links_map = social_links_map

    def run(self):
        validate_social_links_gui(self.social_links_map, self.progress, self.validation_result)
        self.finished.emit()

# Main GUI Window
class SocialScraperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Media Link Scraper")
        self.setGeometry(100, 100, 1000, 700) # x, y, width, height

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- Input Area ---
        self.input_layout = QHBoxLayout()
        self.import_button = QPushButton("Import FQDN File")
        self.import_button.clicked.connect(self.import_file)
        self.fqdn_input_label = QLabel("Or Type FQDNs (one per line):")
        self.fqdn_text_area = QTextEdit()
        self.fqdn_text_area.setPlaceholderText("example.com\nanother.org\n...")
        self.start_scrape_button = QPushButton("Start Scraping FQDNs")
        self.start_scrape_button.clicked.connect(self.start_scraping)

        self.input_controls_layout = QVBoxLayout()
        self.input_controls_layout.addWidget(self.import_button)
        self.input_controls_layout.addWidget(self.start_scrape_button)

        self.input_layout.addLayout(self.input_controls_layout)
        self.input_layout.addWidget(self.fqdn_input_label)
        self.input_layout.addWidget(self.fqdn_text_area)
        self.layout.addLayout(self.input_layout)

        # --- Progress Area ---
        self.progress_label = QLabel("Progress:")
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("Status: Idle")
        self.layout.addWidget(self.progress_label)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_label)

        # --- Results Area (Found Links) ---
        self.results_label = QLabel("Found Social Links (CSV Format):")
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Source FQDN", "Social Media Link"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.results_label)
        self.layout.addWidget(self.results_table)

        # --- Add & Validate Area ---
        self.add_validate_layout = QHBoxLayout()
        self.add_link_button = QPushButton("Add Link Manually")
        self.add_link_button.clicked.connect(self.add_link_manually) # Simple popup needed
        self.validate_button = QPushButton("Validate All Social Links")
        self.validate_button.clicked.connect(self.start_validation)
        self.add_validate_layout.addWidget(self.add_link_button)
        self.add_validate_layout.addWidget(self.validate_button)
        self.layout.addLayout(self.add_validate_layout)

        # --- Validation Results Area ---
        self.validation_label = QLabel("Validation Results (CSV Format):")
        self.validation_table = QTableWidget()
        self.validation_table.setColumnCount(3) # Add Source FQDN here
        self.validation_table.setHorizontalHeaderLabels(["Source FQDN", "Social Media Link", "Status"])
        self.validation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.validation_label)
        self.layout.addWidget(self.validation_table)

        # --- Final Output & Save ---
        self.save_button = QPushButton("Save All Results to CSV")
        self.save_button.clicked.connect(self.save_results)
        self.layout.addWidget(self.save_button)

        # --- Member variables ---
        self.checked_urls = []
        self.social_links_map = {} # { social_link: source_fqdn }
        self.validation_results = {} # { social_link: status }

        self.check_worker = None
        self.scrape_worker = None
        self.validate_worker = None


    def update_progress(self, current, total, message):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setMaximum(1) # Indeterminate or hide
            self.progress_bar.setValue(0)
        self.status_label.setText(f"Status: {message}")

    def import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import FQDN List", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.fqdn_text_area.clear() # Clear text area if importing
            try:
                with open(file_path, 'r') as f:
                    # Start check worker with the file path
                    self.status_label.setText(f"Status: Starting check for file {os.path.basename(file_path)}...")
                    self.reset_ui_for_new_run()
                    self.check_worker = CheckWorker(file_path) # Pass filename directly
                    self.check_worker.progress.connect(self.update_progress)
                    self.check_worker.finished.connect(self.on_check_finished)
                    self.check_worker.start()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {e}")

    def start_scraping(self):
        fqdns = self.fqdn_text_area.toPlainText().strip().split('\n')
        fqdns = [f.strip() for f in fqdns if f.strip()]
        if not fqdns:
             QMessageBox.warning(self, "Input Needed", "Please type FQDNs or import a file.")
             return

        self.status_label.setText("Status: Starting check for typed FQDNs...")
        self.reset_ui_for_new_run()
        self.check_worker = CheckWorker(fqdns) # Pass list of FQDNs
        self.check_worker.progress.connect(self.update_progress)
        self.check_worker.finished.connect(self.on_check_finished)
        self.check_worker.start()

    def on_check_finished(self, good_urls):
        self.checked_urls = good_urls
        self.status_label.setText(f"Status: URL check complete. Found {len(good_urls)} accessible URLs. Starting scrape...")
        if not good_urls:
            QMessageBox.information(self, "No URLs", "No accessible URLs found to scrape.")
            self.progress_bar.setValue(0)
            return

        # Start scraping immediately after checking
        self.scrape_worker = ScrapeWorker(self.checked_urls)
        self.scrape_worker.progress.connect(self.update_progress)
        self.scrape_worker.found_link.connect(self.add_social_link_to_table)
        self.scrape_worker.finished.connect(lambda: self.status_label.setText("Status: Scraping finished."))
        self.scrape_worker.start()

    def add_social_link_to_table(self, source_fqdn, social_link):
        if social_link not in self.social_links_map: # Avoid duplicates in map
            self.social_links_map[social_link] = source_fqdn
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)
            self.results_table.setItem(row_position, 0, QTableWidgetItem(source_fqdn))
            self.results_table.setItem(row_position, 1, QTableWidgetItem(social_link))

    def add_link_manually(self):
        # Implement a QInputDialog or custom dialog to get Source FQDN and Social Link
        # Then call add_social_link_to_table() with the input
        print("Placeholder: Add link manually dialog")
        # Example: self.add_social_link_to_table("manual-input.com", "https://facebook.com/manual")

    def start_validation(self):
        if not self.social_links_map:
            QMessageBox.warning(self, "No Links", "No social links found or added to validate.")
            return

        self.status_label.setText("Status: Starting validation...")
        self.validation_table.setRowCount(0) # Clear previous validation results
        self.validation_results.clear()

        self.validate_worker = ValidateWorker(self.social_links_map)
        self.validate_worker.progress.connect(self.update_progress)
        self.validate_worker.validation_result.connect(self.add_validation_result_to_table)
        self.validate_worker.finished.connect(lambda: self.status_label.setText("Status: Validation finished."))
        self.validate_worker.start()

    def add_validation_result_to_table(self, social_link, status):
        self.validation_results[social_link] = status
        source_fqdn = self.social_links_map.get(social_link, "N/A") # Get source FQDN

        row_position = self.validation_table.rowCount()
        self.validation_table.insertRow(row_position)
        self.validation_table.setItem(row_position, 0, QTableWidgetItem(source_fqdn))
        self.validation_table.setItem(row_position, 1, QTableWidgetItem(social_link))
        self.validation_table.setItem(row_position, 2, QTableWidgetItem(status))


    def reset_ui_for_new_run(self):
         self.results_table.setRowCount(0)
         self.validation_table.setRowCount(0)
         self.social_links_map.clear()
         self.validation_results.clear()
         self.checked_urls = []
         self.progress_bar.setValue(0)

    def save_results(self):
        if not self.validation_results:
             QMessageBox.warning(self, "No Data", "No validation results to save. Run validation first.")
             return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Source FQDN', 'Social Media Link', 'Validation Status'])
                    # Iterate through validation results table or stored data
                    for row in range(self.validation_table.rowCount()):
                        source = self.validation_table.item(row, 0).text()
                        link = self.validation_table.item(row, 1).text()
                        status = self.validation_table.item(row, 2).text()
                        writer.writerow([source, link, status])
                QMessageBox.information(self, "Success", f"Results saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = SocialScraperApp()
    main_window.show()
    sys.exit(app.exec())
