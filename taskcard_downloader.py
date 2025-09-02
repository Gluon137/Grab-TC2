#!/usr/bin/env python3
"""
TaskCard Downloader - Downloads all files and content from a TaskCard board
"""

import os
import time
import json
import requests
import re
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
    def __init__(self, url, download_folder="taskcard_download", headless=True):
        self.url = url
        self.download_folder = download_folder
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        if self.headless:
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
        
        # Make browser more human-like
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
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
            
            # Wait specifically for TaskCards to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".board-card"))
                )
                logger.info("TaskCards detected")
            except TimeoutException:
                logger.warning("TaskCards not detected within timeout, continuing anyway")
            
            # Wait a bit more for dynamic content and attachments to load
            time.sleep(8)
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
                    
                    # Extract title from TaskCard specific structure
                    try:
                        # Look for title in header area with contenteditable
                        header_contenteditable = card.find_elements(By.CSS_SELECTOR, ".board-card-header .contenteditable")
                        if header_contenteditable:
                            card_data["title"] = header_contenteditable[0].text.strip()
                    except:
                        pass
                    
                    # Fallback title selectors
                    if not card_data["title"]:
                        title_selectors = ["h1", "h2", "h3", ".title", ".card-title", ".header"]
                        for selector in title_selectors:
                            try:
                                title_element = card.find_element(By.CSS_SELECTOR, selector)
                                card_data["title"] = title_element.text.strip()
                                break
                            except NoSuchElementException:
                                continue
                    
                    # Extract content from TaskCard specific structure
                    try:
                        # Look for content in content area with contenteditable
                        content_contenteditable = card.find_elements(By.CSS_SELECTOR, ".board-card-content .contenteditable")
                        if content_contenteditable:
                            # Join all contenteditable content
                            content_texts = []
                            for content_elem in content_contenteditable:
                                text = content_elem.text.strip()
                                if text:
                                    content_texts.append(text)
                            card_data["description"] = "\n".join(content_texts)
                    except:
                        pass
                    
                    # Fallback content selectors
                    if not card_data["description"]:
                        content_selectors = ["p", ".description", ".content", ".card-content", ".body", ".board-card-content"]
                        for selector in content_selectors:
                            try:
                                content_elements = card.find_elements(By.CSS_SELECTOR, selector)
                                content_text = " ".join([elem.text.strip() for elem in content_elements if elem.text.strip()])
                                if content_text:
                                    card_data["description"] = content_text
                                    break
                            except NoSuchElementException:
                                continue
                    
                    # Extract all text content as fallback
                    if not card_data["title"] and not card_data["description"]:
                        all_text = card.text.strip()
                        if all_text:
                            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                            if lines:
                                card_data["title"] = lines[0]
                                if len(lines) > 1:
                                    card_data["description"] = "\n".join(lines[1:])
                    
                    # Extract images
                    try:
                        images = card.find_elements(By.TAG_NAME, "img")
                        for img in images:
                            src = img.get_attribute("src")
                            if src and src.startswith("http"):
                                card_data["images"].append(src)
                    except Exception as e:
                        logger.warning(f"Error extracting images from card {i+1}: {e}")
                    
                    # Extract file links and buttons (TaskCards specific)
                    try:
                        # Look for links
                        links = card.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            href = link.get_attribute("href")
                            if href and (href.startswith("http") or href.startswith("/")):
                                card_data["files"].append({
                                    "url": href,
                                    "text": link.text.strip(),
                                    "element": link,
                                    "type": "link"
                                })
                        
                        # Look for file upload buttons or attachments (TaskCards specific)
                        file_buttons = card.find_elements(By.CSS_SELECTOR, "[data-v-file], .file-attachment, .attachment, button[title*='datei'], button[title*='file']")
                        for button in file_buttons:
                            onclick = button.get_attribute("onclick") or ""
                            data_url = button.get_attribute("data-url") or ""
                            title = button.get_attribute("title") or button.text.strip()
                            
                            if data_url or onclick:
                                card_data["files"].append({
                                    "url": data_url or "javascript:" + onclick,
                                    "text": title,
                                    "element": button,
                                    "type": "attachment"
                                })
                        
                        # Look for TaskCards-specific file attachments - focus on clickable containers
                        pdf_containers = card.find_elements(By.CSS_SELECTOR, ".q-my-sm.border.cursor-pointer, .q-img.overflow-hidden")
                        for container in pdf_containers:
                            try:
                                # Find the filename from the container or its children
                                filename = "attachment"
                                
                                # Look for aria-label or filename in the container
                                aria_label = container.get_attribute("aria-label") or ""
                                if aria_label and (".pdf" in aria_label.lower() or ".pptx" in aria_label.lower() or ".docx" in aria_label.lower()):
                                    filename = aria_label
                                else:
                                    # Look for filename in the container's text or child elements
                                    parent = container.find_element(By.XPATH, "..")  # Get parent container
                                    filename_elem = parent.find_elements(By.CSS_SELECTOR, "b, .q-item__label, span")
                                    for elem in filename_elem:
                                        text = elem.text.strip()
                                        if text and (".pdf" in text.lower() or ".pptx" in text.lower() or ".docx" in text.lower() or ".xlsx" in text.lower()):
                                            filename = text
                                            break
                                
                                # Only add if we found a valid document filename
                                if filename != "attachment" and any(ext in filename.lower() for ext in [".pdf", ".pptx", ".docx", ".xlsx"]):
                                    card_data["files"].append({
                                        "url": "",  # Will be extracted by clicking
                                        "text": filename,
                                        "element": container,
                                        "type": "taskcard_pdf_container"
                                    })
                            except Exception as e:
                                logger.debug(f"Error processing PDF container: {e}")
                                pass
                        
                        # Look for PowerPoint/document items in TaskCards format
                        ppt_items = card.find_elements(By.CSS_SELECTOR, ".q-item--clickable, .mdi-microsoft-powerpoint")
                        for item in ppt_items:
                            try:
                                # Get the parent item element
                                parent = item if "q-item--clickable" in (item.get_attribute("class") or "") else item.find_element(By.XPATH, "../..")
                                filename_elem = parent.find_elements(By.CSS_SELECTOR, ".q-item__label")
                                if filename_elem:
                                    filename = filename_elem[0].text.strip()
                                    if filename and (".pptx" in filename.lower() or ".pdf" in filename.lower() or ".docx" in filename.lower()):
                                        card_data["files"].append({
                                            "url": "",  # Will be extracted by clicking
                                            "text": filename,
                                            "element": parent,
                                            "type": "taskcard_clickable"
                                        })
                            except:
                                pass
                        
                        # Look for any other clickable elements that might contain files
                        clickable_elements = card.find_elements(By.CSS_SELECTOR, "[role='button'], .clickable, .file-item")
                        for elem in clickable_elements:
                            data_attrs = [elem.get_attribute(attr) for attr in ['data-file', 'data-attachment', 'data-download']]
                            if any(data_attrs):
                                card_data["files"].append({
                                    "url": next(attr for attr in data_attrs if attr) or "",
                                    "text": elem.text.strip() or "File attachment",
                                    "element": elem,
                                    "type": "clickable"
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
    
    def get_file_extension_from_content(self, response):
        """Determine file extension from response headers and content"""
        # Check Content-Type header first
        content_type = response.headers.get('content-type', '').lower()
        
        # Common MIME type to extension mappings
        mime_extensions = {
            'application/pdf': 'pdf',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/vnd.ms-excel': 'xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'application/vnd.ms-powerpoint': 'ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
            'text/plain': 'txt',
            'text/html': 'html',
            'text/css': 'css',
            'application/javascript': 'js',
            'application/json': 'json',
            'application/xml': 'xml',
            'text/xml': 'xml',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/svg+xml': 'svg',
            'application/zip': 'zip',
            'application/x-rar-compressed': 'rar',
            'application/x-7z-compressed': '7z'
        }
        
        # First try to get extension from content type
        for mime_type, ext in mime_extensions.items():
            if mime_type in content_type:
                return ext
        
        # Check Content-Disposition header for filename
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                if '.' in filename:
                    return filename.split('.')[-1].lower()
            except:
                pass
        
        # Check file signature (magic numbers) from content
        content = response.content[:20] if response.content else b''
        
        if content.startswith(b'%PDF'):
            return 'pdf'
        elif content.startswith(b'PK\x03\x04'):
            # Could be docx, xlsx, pptx (they're all ZIP-based)
            # We'll need more sophisticated detection for these
            if b'word/' in response.content[:1000]:
                return 'docx'
            elif b'xl/' in response.content[:1000]:
                return 'xlsx'
            elif b'ppt/' in response.content[:1000]:
                return 'pptx'
            else:
                return 'zip'
        elif content.startswith(b'\xd0\xcf\x11\xe0'):
            # Old Microsoft Office format
            return 'doc'  # Could also be xls or ppt, but doc is most common
        elif content.startswith(b'\x89PNG'):
            return 'png'
        elif content.startswith(b'\xff\xd8\xff'):
            return 'jpg'
        elif content.startswith(b'GIF8'):
            return 'gif'
        elif content.startswith(b'<html') or content.startswith(b'<!DOCTYPE'):
            return 'html'
        
        return None

    def download_file(self, url, folder, filename_base):
        """Download a file from URL with proper extension detection"""
        try:
            if not url.startswith("http"):
                url = urljoin(self.url, url)
            
            response = requests.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Try to determine the correct file extension
            file_extension = None
            
            # First, try to get extension from URL
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            if '.' in url_path and not url_path.endswith('/'):
                potential_ext = url_path.split('.')[-1].lower()
                # Check if it's a reasonable extension (not too long)
                if len(potential_ext) <= 5 and potential_ext.isalnum():
                    file_extension = potential_ext
            
            # If no extension from URL, try to detect from response
            if not file_extension:
                file_extension = self.get_file_extension_from_content(response)
            
            # Fall back to 'bin' if we can't determine the extension
            if not file_extension:
                file_extension = 'bin'
            
            # Create filename with proper extension
            filename = f"{filename_base}.{file_extension}"
            filepath = os.path.join(folder, filename)
            
            # Handle filename too long error
            if len(filepath) > 255:  # Most filesystems have 255 char limit
                # Truncate the base filename but keep the extension
                max_base_length = 200 - len(folder) - len(file_extension) - 2  # -2 for '.' and '/'
                filename_base_truncated = filename_base[:max_base_length]
                filename = f"{filename_base_truncated}.{file_extension}"
                filepath = os.path.join(folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
    
    def export_as_json(self, cards_data):
        """Export all card data as consolidated JSON"""
        # Create consolidated JSON with all cards
        consolidated_data = {
            "export_info": {
                "url": self.url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_cards": len(cards_data)
            },
            "cards": []
        }
        
        for card in cards_data:
            # Create a serializable copy of card data
            card_for_json = {
                "id": card["id"],
                "title": card["title"],
                "description": card["description"],
                "images": card["images"],
                "files": [{"url": f["url"], "text": f["text"], "type": f.get("type", "link")} for f in card["files"]],
                "html_content": card["html_content"]
            }
            consolidated_data["cards"].append(card_for_json)
        
        # Save consolidated JSON
        json_filepath = os.path.join(self.download_folder, "taskcard_export.json")
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Consolidated JSON export saved: {json_filepath}")

    def save_card_content(self, cards_data):
        """Save card content and download files"""
        for card in cards_data:
            card_id = card["id"]
            
            # Save card metadata (remove non-serializable elements)
            card_filename = f"card_{card_id:03d}.json"
            card_filepath = os.path.join(self.download_folder, "metadata", card_filename)
            
            # Create a serializable copy of card data
            card_for_json = {
                "id": card["id"],
                "title": card["title"],
                "description": card["description"],
                "images": card["images"],
                "files": [{"url": f["url"], "text": f["text"], "type": f.get("type", "link")} for f in card["files"]],
                "html_content": card["html_content"]
            }
            
            with open(card_filepath, 'w', encoding='utf-8') as f:
                json.dump(card_for_json, f, indent=2, ensure_ascii=False)
            
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
                img_filename_base = f"card_{card_id:03d}_img_{i+1:02d}"
                self.download_file(img_url, os.path.join(self.download_folder, "images"), img_filename_base)
            
            # Download files with TaskCards-specific handling
            for i, file_info in enumerate(card['files']):
                file_url = file_info['url']
                file_text = file_info['text']
                file_type = file_info.get('type', 'link')
                
                # Skip javascript URLs for now
                if file_url.startswith('javascript:'):
                    logger.info(f"Skipping javascript URL: {file_text}")
                    continue
                
                # Clean filename base (remove problematic characters)
                safe_filename = "".join(c for c in file_text if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
                if not safe_filename:
                    safe_filename = f"file_{i+1}"
                
                # Remove any existing extension from safe_filename to avoid double extensions
                if '.' in safe_filename:
                    safe_filename = '.'.join(safe_filename.split('.')[:-1])
                
                file_filename_base = f"card_{card_id:03d}_{safe_filename}"
                
                # For TaskCards attachments, handle different types
                if file_type == 'taskcard_attachment' and file_url:
                    # Direct download from extracted background-image URL (usually preview images)
                    logger.info(f"Downloading TaskCard attachment: {file_text}")
                    self.download_file(file_url, os.path.join(self.download_folder, "documents"), file_filename_base)
                elif file_type in ['attachment', 'clickable', 'taskcard_clickable', 'taskcard_pdf_container'] and 'element' in file_info:
                    try:
                        logger.info(f"Attempting to click file element: {file_text}")
                        element = file_info['element']
                        
                        # Scroll element into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(1)
                        
                        # Try to click the element
                        element.click()
                        time.sleep(3)  # Wait for potential file dialog or redirect
                        
                        # Check if any new tabs opened or downloads started
                        original_window = self.driver.current_window_handle
                        all_windows = self.driver.window_handles
                        
                        if len(all_windows) > 1:
                            # Switch to new tab to get the actual file URL
                            for window_handle in all_windows:
                                if window_handle != original_window:
                                    self.driver.switch_to.window(window_handle)
                                    new_url = self.driver.current_url
                                    logger.info(f"Found new tab with URL: {new_url}")
                                    
                                    # Download from the new URL
                                    self.download_file(new_url, os.path.join(self.download_folder, "documents"), file_filename_base)
                                    
                                    # Close the new tab and return to original
                                    self.driver.close()
                                    self.driver.switch_to.window(original_window)
                                    break
                        else:
                            # No new tab opened - check for download started
                            # Try to get the download URL from browser's network activity or check for download
                            logger.info(f"No new tab opened for {file_text}, attempting alternative methods")
                            
                            # For PDF containers, try to find the download URL from the page's network requests
                            if file_type == 'taskcard_pdf_container':
                                # Get performance logs to find the download URL
                                try:
                                    logs = self.driver.get_log('performance')
                                    for log in logs[-10:]:  # Check recent logs
                                        message = json.loads(log['message'])
                                        if message.get('message', {}).get('method') == 'Network.responseReceived':
                                            url = message.get('message', {}).get('params', {}).get('response', {}).get('url', '')
                                            if 'taskcards.s3' in url and 'attachment' in url:
                                                logger.info(f"Found download URL in network logs: {url}")
                                                self.download_file(url, os.path.join(self.download_folder, "documents"), file_filename_base)
                                                break
                                except:
                                    pass
                            
                            # Fallback: try original URL if available
                            if file_url:
                                self.download_file(file_url, os.path.join(self.download_folder, "documents"), file_filename_base)
                            
                    except Exception as e:
                        logger.warning(f"Failed to click element for {file_text}: {e}")
                        # Fallback to direct download
                        self.download_file(file_url, os.path.join(self.download_folder, "documents"), file_filename_base)
                else:
                    # Regular link download
                    self.download_file(file_url, os.path.join(self.download_folder, "documents"), file_filename_base)
    
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
            
            # Export consolidated JSON
            logger.info("Exporting consolidated JSON")
            self.export_as_json(cards_data)
            
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