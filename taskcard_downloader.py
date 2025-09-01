#!/usr/bin/env python3
"""
TaskCard Downloader - Downloads all files and content from a TaskCard board
"""

import os
import time
import json
import requests
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskCardDownloader:
    def __init__(self, url, download_folder="taskcard_download"):
        self.url = url
        self.download_folder = download_folder
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Set download directory
        prefs = {
            "download.default_directory": os.path.abspath(self.download_folder),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise
    
    def create_folder_structure(self):
        """Create the download folder structure"""
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
            logger.info(f"Created download folder: {self.download_folder}")
        
        # Create subfolders
        subfolders = ["cards", "images", "documents", "metadata"]
        for folder in subfolders:
            folder_path = os.path.join(self.download_folder, folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                logger.info(f"Created subfolder: {folder_path}")
    
    def wait_for_page_load(self, timeout=30):
        """Wait for the page to fully load"""
        try:
            # Wait for the main content to load
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait a bit more for dynamic content
            time.sleep(5)
            logger.info("Page loaded successfully")
            return True
        except TimeoutException:
            logger.error("Page load timeout")
            return False
    
    def extract_card_data(self):
        """Extract all card data from the board"""
        cards_data = []
        
        try:
            # Look for different possible card selectors
            card_selectors = [
                ".card",
                ".taskcard", 
                "[data-card]",
                ".board-card",
                ".tc-card"
            ]
            
            cards = []
            for selector in card_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    cards = elements
                    logger.info(f"Found {len(cards)} cards using selector: {selector}")
                    break
            
            if not cards:
                # If no cards found with standard selectors, get all divs and filter
                all_divs = self.driver.find_elements(By.TAG_NAME, "div")
                logger.info(f"No cards found with standard selectors, checking {len(all_divs)} div elements")
                
                # Look for divs that might contain card content
                for div in all_divs:
                    class_name = div.get_attribute("class") or ""
                    if any(keyword in class_name.lower() for keyword in ["card", "task", "item"]):
                        cards.append(div)
            
            logger.info(f"Processing {len(cards)} potential cards")
            
            for i, card in enumerate(cards):
                try:
                    card_data = {
                        "id": i + 1,
                        "title": "",
                        "description": "",
                        "images": [],
                        "files": [],
                        "html_content": card.get_attribute("innerHTML")
                    }
                    
                    # Try to extract title
                    title_selectors = ["h1", "h2", "h3", ".title", ".card-title", ".header"]
                    for selector in title_selectors:
                        try:
                            title_element = card.find_element(By.CSS_SELECTOR, selector)
                            card_data["title"] = title_element.text.strip()
                            break
                        except NoSuchElementException:
                            continue
                    
                    # Try to extract description/content
                    content_selectors = ["p", ".description", ".content", ".card-content", ".body"]
                    for selector in content_selectors:
                        try:
                            content_elements = card.find_elements(By.CSS_SELECTOR, selector)
                            content_text = " ".join([elem.text.strip() for elem in content_elements if elem.text.strip()])
                            if content_text:
                                card_data["description"] = content_text
                                break
                        except NoSuchElementException:
                            continue
                    
                    # Extract images
                    try:
                        images = card.find_elements(By.TAG_NAME, "img")
                        for img in images:
                            src = img.get_attribute("src")
                            if src and src.startswith("http"):
                                card_data["images"].append(src)
                    except Exception as e:
                        logger.warning(f"Error extracting images from card {i+1}: {e}")
                    
                    # Extract file links
                    try:
                        links = card.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            href = link.get_attribute("href")
                            if href and (href.startswith("http") or href.startswith("/")):
                                card_data["files"].append({
                                    "url": href,
                                    "text": link.text.strip()
                                })
                    except Exception as e:
                        logger.warning(f"Error extracting files from card {i+1}: {e}")
                    
                    cards_data.append(card_data)
                    logger.info(f"Extracted data for card {i+1}: {card_data['title'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error processing card {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting card data: {e}")
        
        return cards_data
    
    def download_file(self, url, folder, filename):
        """Download a file from URL"""
        try:
            if not url.startswith("http"):
                url = urljoin(self.url, url)
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            filepath = os.path.join(folder, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
    
    def save_card_content(self, cards_data):
        """Save card content and download files"""
        for card in cards_data:
            card_id = card["id"]
            
            # Save card metadata
            card_filename = f"card_{card_id:03d}.json"
            card_filepath = os.path.join(self.download_folder, "metadata", card_filename)
            
            with open(card_filepath, 'w', encoding='utf-8') as f:
                json.dump(card, f, indent=2, ensure_ascii=False)
            
            # Save card content as text
            content_filename = f"card_{card_id:03d}_content.txt"
            content_filepath = os.path.join(self.download_folder, "cards", content_filename)
            
            with open(content_filepath, 'w', encoding='utf-8') as f:
                f.write(f"Title: {card['title']}\n\n")
                f.write(f"Description: {card['description']}\n\n")
                f.write("Images:\n")
                for img in card['images']:
                    f.write(f"  - {img}\n")
                f.write("\nFiles:\n")
                for file_info in card['files']:
                    f.write(f"  - {file_info['text']}: {file_info['url']}\n")
            
            # Download images
            for i, img_url in enumerate(card['images']):
                img_extension = img_url.split('.')[-1].split('?')[0] or 'jpg'
                img_filename = f"card_{card_id:03d}_img_{i+1:02d}.{img_extension}"
                self.download_file(img_url, os.path.join(self.download_folder, "images"), img_filename)
            
            # Download files
            for i, file_info in enumerate(card['files']):
                file_url = file_info['url']
                file_text = file_info['text']
                
                # Try to determine file extension from URL or use generic extension
                parsed_url = urlparse(file_url)
                if '.' in parsed_url.path:
                    file_extension = parsed_url.path.split('.')[-1]
                else:
                    file_extension = 'bin'
                
                # Clean filename
                safe_filename = "".join(c for c in file_text if c.isalnum() or c in (' ', '.', '_')).rstrip()
                if not safe_filename:
                    safe_filename = f"file_{i+1}"
                
                file_filename = f"card_{card_id:03d}_{safe_filename}.{file_extension}"
                self.download_file(file_url, os.path.join(self.download_folder, "documents"), file_filename)
    
    def run(self):
        """Main execution method"""
        try:
            logger.info("Starting TaskCard download process")
            
            # Setup
            self.create_folder_structure()
            self.setup_driver()
            
            # Load page
            logger.info(f"Loading page: {self.url}")
            self.driver.get(self.url)
            
            if not self.wait_for_page_load():
                logger.error("Failed to load page")
                return False
            
            # Take a screenshot for debugging
            screenshot_path = os.path.join(self.download_folder, "page_screenshot.png")
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Extract and save page source
            page_source_path = os.path.join(self.download_folder, "page_source.html")
            with open(page_source_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Page source saved: {page_source_path}")
            
            # Extract card data
            logger.info("Extracting card data")
            cards_data = self.extract_card_data()
            
            if not cards_data:
                logger.warning("No cards found - the page structure might be different than expected")
                # Save the page source for manual inspection
                return False
            
            # Save card content and download files
            logger.info(f"Processing {len(cards_data)} cards")
            self.save_card_content(cards_data)
            
            # Create summary
            summary = {
                "url": self.url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_cards": len(cards_data),
                "cards_summary": [{"id": card["id"], "title": card["title"]} for card in cards_data]
            }
            
            summary_path = os.path.join(self.download_folder, "download_summary.json")
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Download completed successfully! Files saved to: {self.download_folder}")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()

def main():
    url = "https://bra.taskcards.app/#/board/197a9f8e-261c-4f17-b63c-6fabb238900a?token=5ee65483-7b65-472d-b4ca-90bc485df408"
    
    downloader = TaskCardDownloader(url)
    success = downloader.run()
    
    if success:
        print(f"✅ Download erfolgreich abgeschlossen! Dateien gespeichert in: {downloader.download_folder}")
    else:
        print("❌ Download fehlgeschlagen. Überprüfen Sie die Logs für Details.")

if __name__ == "__main__":
    main()