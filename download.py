import requests
import os
from datetime import datetime
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd

class TradewegGiltDownloader:
    def __init__(self, username=None, password=None, download_dir="./downloads"):
        self.username = username or os.getenv('TRADEWEB_USERNAME')
        self.password = password or os.getenv('TRADEWEB_PASSWORD')
        self.download_dir = download_dir
        self.base_url = "https://reports.tradeweb.com"
        self.login_url = "https://reports.tradeweb.com/account/login/?ReturnUrl=%2f"
        self.gilt_url = "https://reports.tradeweb.com/closing-prices/gilts/"
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = os.path.join(self.download_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"gilts_downloader_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_driver(self):
        """Setup Chrome driver with enhanced stealth options"""
        chrome_options = Options()
        # Keep headless mode disabled for debugging the popup
        # chrome_options.add_argument("--headless")  
        
        # Enhanced stealth options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set download preferences
        prefs = {
            "download.default_directory": os.path.abspath(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Execute stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
        return driver
    
    def inspect_login_page(self, driver):
        """Inspect the login page to understand its structure"""
        try:
            print("Inspecting login page structure...")
            driver.get(self.login_url)
            time.sleep(5)  # Wait longer for page load
            
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            
            # Check for any redirects or blocks
            if "blocked" in driver.page_source.lower() or "access denied" in driver.page_source.lower():
                print("⚠️  Site may be blocking automated access")
            
            # Look for common login field patterns
            login_selectors = [
                ("ID 'username'", By.ID, "username"),
                ("ID 'Username'", By.ID, "Username"),
                ("ID 'user'", By.ID, "user"),
                ("ID 'email'", By.ID, "email"),
                ("ID 'Email'", By.ID, "Email"),
                ("ID 'login'", By.ID, "login"),
                ("Name 'username'", By.NAME, "username"),
                ("Name 'Username'", By.NAME, "Username"),
                ("Name 'user'", By.NAME, "user"),
                ("Name 'email'", By.NAME, "email"),
                ("Name 'Email'", By.NAME, "Email"),
                ("Type 'email'", By.XPATH, "//input[@type='email']"),
                ("Type 'text'", By.XPATH, "//input[@type='text']"),
                ("Class containing 'user'", By.XPATH, "//input[contains(@class, 'user')]"),
                ("Class containing 'email'", By.XPATH, "//input[contains(@class, 'email')]"),
                ("Class containing 'login'", By.XPATH, "//input[contains(@class, 'login')]"),
            ]
            
            print("\nLooking for username/email fields:")
            found_username = None
            for desc, by_type, selector in login_selectors:
                try:
                    element = driver.find_element(by_type, selector)
                    print(f"  ✓ Found {desc}: {element.tag_name} - placeholder: '{element.get_attribute('placeholder')}'")
                    if not found_username:
                        found_username = (by_type, selector)
                except:
                    print(f"  ✗ Not found: {desc}")
            
            # Look for password fields
            password_selectors = [
                ("ID 'password'", By.ID, "password"),
                ("ID 'Password'", By.ID, "Password"),
                ("ID 'pass'", By.ID, "pass"),
                ("Name 'password'", By.NAME, "password"),
                ("Name 'Password'", By.NAME, "Password"),
                ("Type 'password'", By.XPATH, "//input[@type='password']"),
            ]
            
            print("\nLooking for password fields:")
            found_password = None
            for desc, by_type, selector in password_selectors:
                try:
                    element = driver.find_element(by_type, selector)
                    print(f"  ✓ Found {desc}: {element.tag_name}")
                    if not found_password:
                        found_password = (by_type, selector)
                except:
                    print(f"  ✗ Not found: {desc}")
            
            # Look for submit buttons
            submit_selectors = [
                ("Submit button", By.XPATH, "//button[@type='submit']"),
                ("Input submit", By.XPATH, "//input[@type='submit']"),
                ("Login button text", By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign in') or contains(text(), 'Log in')]"),
                ("Input login value", By.XPATH, "//input[@value='Login' or @value='Sign in' or @value='Log in']"),
                ("Any button", By.XPATH, "//button"),
                ("Any input button", By.XPATH, "//input[@type='button']"),
            ]
            
            print("\nLooking for submit buttons:")
            found_submit = None
            for desc, by_type, selector in submit_selectors:
                try:
                    elements = driver.find_elements(by_type, selector)
                    if elements:
                        print(f"  ✓ Found {desc}: {len(elements)} element(s)")
                        if not found_submit and elements:
                            found_submit = (by_type, selector)
                            print(f"    First element text: '{elements[0].text}'")
                except:
                    print(f"  ✗ Not found: {desc}")
            
            # Check for forms
            forms = driver.find_elements(By.XPATH, "//form")
            print(f"\nFound {len(forms)} form(s) on page")
            
            # Check if we're already on a different login provider (SSO)
            if "sso" in driver.current_url.lower() or "oauth" in driver.current_url.lower():
                print("\n⚠️  Detected SSO/OAuth redirect - manual login may be required")
            
            # Save page source for manual inspection
            with open(os.path.join(self.download_dir, "login_page_source.html"), "w", encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"\n💾 Saved page source to: {os.path.join(self.download_dir, 'login_page_source.html')}")
            
            return found_username, found_password, found_submit
            
        except Exception as e:
            print(f"Error inspecting page: {e}")
            return None, None, None
    
    def login(self, driver):
        """Login to Tradeweb using the exact form structure"""
        try:
            print("Navigating to login page...")
            driver.get(self.login_url)
            time.sleep(5)
            
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            
            # Use the exact IDs from the HTML structure
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "MainContent_LoginUser_UserName"))
            )
            print("Found username field")
            
            password_field = driver.find_element(By.ID, "MainContent_LoginUser_Password")
            print("Found password field")
            
            login_button = driver.find_element(By.ID, "MainContent_LoginUser_LoginButton")
            print("Found login button")
            
            # Fill credentials
            print("Filling credentials...")
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            time.sleep(2)  # Brief pause before clicking
            
            # Click the login button
            print("Clicking login button...")
            login_button.click()
            
            # Wait for response
            time.sleep(5)
            print(f"After login attempt - URL: {driver.current_url}")
            
            # Check if we're still on login page (login failed)
            if "/account/login/" in driver.current_url:
                print("Still on login page - checking for errors...")
                
                # Check for validation error messages
                try:
                    username_error = driver.find_element(By.ID, "MainContent_LoginUser_UserNameRequired")
                    if username_error.is_displayed():
                        print(f"Username error: {username_error.text}")
                except:
                    pass
                
                try:
                    password_error = driver.find_element(By.ID, "MainContent_LoginUser_PasswordRequired")
                    if password_error.is_displayed():
                        print(f"Password error: {password_error.text}")
                except:
                    pass
                
                # Check for general error messages
                try:
                    error_elements = driver.find_elements(By.CLASS_NAME, "error")
                    for error in error_elements:
                        if error.is_displayed():
                            print(f"Error message: {error.text}")
                except:
                    pass
                
                return False
            else:
                print("Login appears successful (redirected from login page)")
                return True
            
        except Exception as e:
            print(f"Login failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def download_gilt_csv(self, driver):
        """Navigate to gilts page and download XML/CSV using the exact export button"""
        try:
            print("Navigating to gilts page...")
            driver.get(self.gilt_url)
            
            # Wait for page to load
            time.sleep(5)
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            
            # Save page source for debugging first
            with open(os.path.join(self.download_dir, "gilts_page_source.html"), "w", encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"💾 Saved gilts page source for debugging")
            
            # Wait for the export button to be present
            try:
                export_button = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, "MainContent_MainContent_ExportButton"))
                )
                print("Found Export button")
            except Exception as e:
                print(f"Could not find Export button: {e}")
                
                # Try alternative selectors for export button
                alternative_selectors = [
                    ("Export button text", By.XPATH, "//input[@value='Export' or @value='export']"),
                    ("Button with Export text", By.XPATH, "//button[contains(text(), 'Export')]"),
                    ("Any export element", By.XPATH, "//*[contains(text(), 'Export') or contains(@title, 'Export')]"),
                    ("Download button", By.XPATH, "//input[@value='Download' or @value='download']"),
                ]
                
                print("Trying alternative selectors for export button:")
                for desc, by_type, selector in alternative_selectors:
                    try:
                        elements = driver.find_elements(by_type, selector)
                        if elements:
                            print(f"  ✓ Found {desc}: {len(elements)} element(s)")
                            export_button = elements[0]
                            break
                    except Exception as alt_e:
                        print(f"  ✗ {desc} failed: {alt_e}")
                else:
                    return None
            
            # Wait for any data loading to complete (look for table or data indicators)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//table | //div[contains(@class, 'data')] | //div[contains(@class, 'grid')]"))
                )
                print("Data appears to be loaded")
            except:
                print("No data table detected, but proceeding with export...")
            
            # Scroll the export button into view
            driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
            time.sleep(2)
            
            # Ensure the button is clickable
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "MainContent_MainContent_ExportButton"))
                )
                print("Export button is clickable")
            except:
                print("Export button may not be fully clickable, but attempting anyway...")
            
            print("Clicking Export button...")
            
            # The button has both onclick JavaScript and postback - try JavaScript click first
            try:
                # Try JavaScript click to trigger the onclick event
                driver.execute_script("arguments[0].click();", export_button)
                print("Clicked export button using JavaScript")
                
                # Wait for confirmation dialog to appear
                time.sleep(3)
                
                # Look for and handle the confirmation dialog
                try:
                    # Wait for the popup window to fully appear
                    time.sleep(5)
                    print("Looking for confirmation popup dialog...")
                    
                    # Based on the HTML you provided, look for the specific structure
                    # First try to find the RadWindow container
                    radwindow = None
                    try:
                        radwindow = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "RadWindow"))
                        )
                        print("Found RadWindow container")
                    except:
                        print("RadWindow container not found")
                    
                    # Look for the specific OK button with the onclick function from your HTML
                    ok_button = None
                    ok_selectors = [
                        "//a[contains(@onclick, \"$find('confirm\") and contains(@onclick, '.close(true)')]",
                        "//a[contains(@onclick, '.close(true)')]",
                        "//div[contains(@class, 'rwDialogPopup')]//a[contains(@onclick, 'close(true)')]",
                        "//div[contains(@class, 'radconfirm')]//a[contains(@onclick, 'close(true)')]",
                        "//a[contains(@class, 'rwPopupButton') and contains(@onclick, 'close(true)')]",
                        "//span[text()='OK']/parent::span/parent::a",
                        "//span[contains(@class, 'rwInnerSpan') and text()='OK']/parent::*/parent::a"
                    ]
                    
                    for i, selector in enumerate(ok_selectors):
                        try:
                            print(f"Trying selector {i+1}: {selector}")
                            ok_button = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            print(f"✅ Found OK button with selector {i+1}")
                            break
                        except Exception as e:
                            print(f"❌ Selector {i+1} failed: {e}")
                            continue
                    
                    if ok_button:
                        print("Attempting to click OK button...")
                        try:
                            # Try JavaScript click first (more reliable for RadWindow)
                            driver.execute_script("arguments[0].click();", ok_button)
                            print("✅ Clicked OK button with JavaScript")
                        except Exception as js_e:
                            print(f"JavaScript click failed: {js_e}")
                            try:
                                ok_button.click()
                                print("✅ Clicked OK button with regular click")
                            except Exception as regular_e:
                                print(f"Regular click failed: {regular_e}")
                        
                        time.sleep(5)
                    else:
                        print("❌ Could not find OK button with any selector")
                        
                except Exception as dialog_e:
                    print(f"Error handling confirmation dialog: {dialog_e}")
                    
                # Alternative approaches for RadWindow popup
                try:
                    # Method 1: Try to call ExportButton_Ok function directly  
                    print("Trying to call ExportButton_Ok function directly...")
                    driver.execute_script("window.ExportButton_Ok(true);")
                    print("Called ExportButton_Ok function directly")
                    time.sleep(3)
                except Exception as js_e:
                    print(f"Direct function call failed: {js_e}")
                    
                    # Method 2: Try to find and close the RadWindow
                    try:
                        print("Trying to close RadWindow directly...")
                        driver.execute_script("""
                            var radWindows = Telerik.Web.UI.RadWindow.GetRadWindowManager();
                            if (radWindows) {
                                var windows = radWindows.getActiveWindow();
                                if (windows) {
                                    windows.close(true);
                                }
                            }
                        """)
                        print("Attempted to close RadWindow")
                        time.sleep(3)
                    except Exception as rad_e:
                        print(f"RadWindow close failed: {rad_e}")
                        
                        # Method 3: Look for the specific RadWindow OK button structure
                        try:
                            print("Looking for RadWindow OK button...")
                            # Wait for the popup to appear and try to click OK
                            time.sleep(2)
                            ok_button = driver.find_element(By.XPATH, "//div[contains(@class, 'radconfirm')]//a[contains(@onclick, 'close(true)')]")
                            if ok_button:
                                driver.execute_script("arguments[0].click();", ok_button)
                                print("Clicked RadWindow OK button")
                                time.sleep(3)
                        except Exception as rad_ok_e:
                            print(f"RadWindow OK button click failed: {rad_ok_e}")
                            
                            # Method 4: Press Enter key (often works for OK dialogs)
                            try:
                                print("Trying to press Enter key...")
                                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.RETURN)
                                print("Pressed Enter key")
                                time.sleep(3)
                            except Exception as enter_e:
                                print(f"Enter key failed: {enter_e}")
                
            except Exception as e:
                print(f"JavaScript click failed: {e}")
                try:
                    # Fallback to regular click
                    export_button.click()
                    print("Clicked export button using regular click")
                    time.sleep(3)
                    
                    # Handle dialog for regular click too
                    try:
                        ok_button = driver.find_element(By.XPATH, "//a[contains(@onclick, 'ExportButton_Ok') or contains(text(), 'OK')]")
                        ok_button.click()
                        print("Clicked OK on confirmation dialog after regular click")
                        time.sleep(2)
                    except:
                        print("No confirmation dialog after regular click")
                        
                except Exception as e2:
                    print(f"Regular click also failed: {e2}")
                    return None
            
            # Wait for download to start/complete
            print("Waiting for download to complete...")
            
            # Check for download progress or completion
            initial_files = set(os.listdir(self.download_dir))
            
            # Wait and check for new files periodically
            for i in range(60):  # Check for 60 seconds
                time.sleep(1)
                current_files = set(os.listdir(self.download_dir))
                
                # Look for TradeWeb files specifically (they may exist from before)
                tradeweb_files = [f for f in current_files if f.startswith('Tradeweb_FTSE_ClosePrices') and f.endswith('.csv')]
                
                if tradeweb_files:
                    # Get the most recent TradeWeb file
                    latest_file = max([os.path.join(self.download_dir, f) for f in tradeweb_files], 
                                    key=os.path.getctime)
                    
                    # Check if it was created recently (within last 2 minutes)
                    file_age = time.time() - os.path.getctime(latest_file)
                    if file_age < 120:  # Less than 2 minutes old
                        print(f"Found recent TradeWeb download: {latest_file}")
                        print(f"File age: {file_age:.1f} seconds")
                        
                        # Check if file has actual content
                        if os.path.getsize(latest_file) > 500:  # More than 500 bytes
                            print(f"File size: {os.path.getsize(latest_file)} bytes - looks good!")
                            time.sleep(2)  # Final wait to ensure download is complete
                            
                            # Rename file with download datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = os.path.basename(latest_file)
                            name, ext = os.path.splitext(filename)
                            new_filename = f"Tradeweb_FTSE_ClosePrices_{timestamp}{ext}"
                            new_filepath = os.path.join(self.download_dir, new_filename)
                            
                            try:
                                os.rename(latest_file, new_filepath)
                                print(f"Renamed file to: {new_filename}")
                                return new_filepath
                            except Exception as rename_e:
                                print(f"Could not rename file: {rename_e}")
                                return latest_file
                        else:
                            print(f"File too small ({os.path.getsize(latest_file)} bytes), continuing to wait...")
                
                # Also check for new files since script started
                new_files = current_files - initial_files
                if new_files:
                    # Filter for data files
                    data_files = [f for f in new_files if f.endswith(('.xml', '.csv', '.xlsx', '.xls')) and not f.startswith('.')]
                    if data_files:
                        latest_file = max([os.path.join(self.download_dir, f) for f in data_files], 
                                        key=os.path.getctime)
                        print(f"Download completed: {latest_file}")
                        
                        # Wait a bit more to ensure download is complete
                        time.sleep(3)
                        
                        # Check if file has actual content
                        if os.path.getsize(latest_file) > 500:  # More than 500 bytes
                            # Rename file with download datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = os.path.basename(latest_file)
                            name, ext = os.path.splitext(filename)
                            new_filename = f"Tradeweb_FTSE_ClosePrices_{timestamp}{ext}"
                            new_filepath = os.path.join(self.download_dir, new_filename)
                            
                            try:
                                os.rename(latest_file, new_filepath)
                                print(f"Renamed file to: {new_filename}")
                                return new_filepath
                            except Exception as rename_e:
                                print(f"Could not rename file: {rename_e}")
                                return latest_file
                        else:
                            print(f"Downloaded file seems too small ({os.path.getsize(latest_file)} bytes), continuing to wait...")
                
                # Show progress
                if i % 10 == 0:
                    print(f"  Waiting... ({i+1}s)")
            
            # Check one final time for any downloaded files
            final_files = set(os.listdir(self.download_dir))
            new_files = final_files - initial_files
            data_files = [f for f in new_files if f.endswith(('.xml', '.csv', '.xlsx', '.xls')) and not f.startswith('.')]
            
            if data_files:
                latest_file = max([os.path.join(self.download_dir, f) for f in data_files], 
                                key=os.path.getctime)
                print(f"Download found after waiting: {latest_file}")
                
                # Rename file with download datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.basename(latest_file)
                name, ext = os.path.splitext(filename)
                new_filename = f"Tradeweb_FTSE_ClosePrices_{timestamp}{ext}"
                new_filepath = os.path.join(self.download_dir, new_filename)
                
                try:
                    os.rename(latest_file, new_filepath)
                    print(f"Renamed file to: {new_filename}")
                    return new_filepath
                except Exception as rename_e:
                    print(f"Could not rename file: {rename_e}")
                    return latest_file
            else:
                print("No downloaded file found after export")
                
                # Check if there was a page redirect or popup
                print(f"Current URL after export: {driver.current_url}")
                
                # Sometimes the file download happens through a redirect
                # Check for any new tabs or windows
                if len(driver.window_handles) > 1:
                    print("New window/tab detected - switching...")
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(3)
                    
                    # Check for files again
                    final_files = set(os.listdir(self.download_dir))
                    new_files = final_files - initial_files
                    data_files = [f for f in new_files if f.endswith(('.xml', '.csv', '.xlsx', '.xls'))]
                    
                    if data_files:
                        latest_file = max([os.path.join(self.download_dir, f) for f in data_files], 
                                        key=os.path.getctime)
                        print(f"Download found in new window: {latest_file}")
                        return latest_file
                
                return None
                
        except Exception as e:
            print(f"Error downloading file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def alternative_table_scrape(self, driver):
        """Alternative method: scrape table data directly if download fails"""
        try:
            print("Attempting to scrape table data directly...")
            
            # Find the main data table
            tables = driver.find_elements(By.XPATH, "//table")
            if not tables:
                print("No tables found on page")
                return None
            
            print(f"Found {len(tables)} table(s)")
            
            # Extract table data using pandas
            html = driver.page_source
            try:
                pandas_tables = pd.read_html(html)
                
                if pandas_tables:
                    # Use the largest table (likely the data table)
                    df = max(pandas_tables, key=len)
                    print(f"Found table with {len(df)} rows and {len(df.columns)} columns")
                    
                    # Save as XML (primary format) and CSV (backup)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Save as XML
                    xml_filename = f"Tradeweb_FTSE_ClosePrices_{timestamp}.xml"
                    xml_filepath = os.path.join(self.download_dir, xml_filename)
                    
                    # Convert DataFrame to XML
                    xml_data = df.to_xml(index=False)
                    with open(xml_filepath, 'w', encoding='utf-8') as f:
                        f.write(xml_data)
                    print(f"Data scraped and saved as XML: {xml_filepath}")
                    
                    # Also save as CSV backup
                    csv_filename = f"Tradeweb_FTSE_ClosePrices_{timestamp}.csv"
                    csv_filepath = os.path.join(self.download_dir, csv_filename)
                    df.to_csv(csv_filepath, index=False)
                    print(f"Data also saved as CSV backup: {csv_filepath}")
                    
                    return xml_filepath  # Return XML as primary format
                else:
                    print("No tables could be parsed from HTML")
                    return None
                    
            except Exception as e:
                print(f"Error parsing tables with pandas: {e}")
                
                # Fallback: manual table extraction
                return self.manual_table_extraction(driver, tables[0])
            
        except Exception as e:
            print(f"Error scraping table data: {e}")
            return None
    
    def manual_table_extraction(self, driver, table):
        """Manual table extraction when pandas fails"""
        try:
            print("Attempting manual table extraction...")
            
            # Extract headers
            headers = []
            try:
                header_rows = table.find_elements(By.XPATH, ".//thead//tr | .//tr[1]")
                if header_rows:
                    header_cells = header_rows[0].find_elements(By.XPATH, ".//th | .//td")
                    headers = [cell.text.strip() for cell in header_cells]
                    print(f"Found headers: {headers}")
            except:
                print("Could not extract headers")
            
            # Extract data rows
            data_rows = []
            try:
                rows = table.find_elements(By.XPATH, ".//tbody//tr | .//tr[position()>1]")
                print(f"Found {len(rows)} data rows")
                
                for row in rows:
                    cells = row.find_elements(By.XPATH, ".//td | .//th")
                    row_data = [cell.text.strip() for cell in cells]
                    if any(row_data):  # Skip empty rows
                        data_rows.append(row_data)
                        
            except Exception as e:
                print(f"Error extracting data rows: {e}")
            
            if data_rows:
                # Create DataFrame
                df = pd.DataFrame(data_rows)
                if headers and len(headers) == len(df.columns):
                    df.columns = headers
                
                # Save files
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Save as XML
                xml_filename = f"Tradeweb_FTSE_ClosePrices_manual_{timestamp}.xml"
                xml_filepath = os.path.join(self.download_dir, xml_filename)
                xml_data = df.to_xml(index=False)
                with open(xml_filepath, 'w', encoding='utf-8') as f:
                    f.write(xml_data)
                
                # Save as CSV
                csv_filename = f"Tradeweb_FTSE_ClosePrices_manual_{timestamp}.csv"
                csv_filepath = os.path.join(self.download_dir, csv_filename)
                df.to_csv(csv_filepath, index=False)
                
                print(f"Manual extraction completed: {xml_filepath}")
                return xml_filepath
            else:
                print("No data rows extracted")
                return None
                
        except Exception as e:
            print(f"Manual table extraction failed: {e}")
            return None
    
    def run(self):
        """Main execution method"""
        if not self.username or not self.password:
            self.logger.error("Username and password required")
            self.logger.error("Set TRADEWEB_USERNAME and TRADEWEB_PASSWORD environment variables")
            return None
        
        self.logger.info("Starting gilts price download process")
        driver = self.setup_driver()
        
        try:
            # Login
            if not self.login(driver):
                self.logger.error("Login failed - cannot proceed")
                return None
            
            self.logger.info("LOGIN SUCCESSFUL - Proceeding to download")
            
            # Download XML/CSV
            downloaded_file = self.download_gilt_csv(driver)
            
            # If download failed, try table scraping
            if not downloaded_file:
                self.logger.warning("Direct download failed, attempting table scraping...")
                downloaded_file = self.alternative_table_scrape(driver)
            
            if downloaded_file:
                self.logger.info(f"Successfully downloaded file: {downloaded_file}")
            else:
                self.logger.error("All download methods failed")
            
            return downloaded_file
            
        except Exception as e:
            self.logger.error(f"Error in main execution: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
        finally:
            self.logger.info("Closing browser...")
            driver.quit()
    

# Usage example
if __name__ == "__main__":
    # Use environment variables
    downloader = TradewegGiltDownloader()
    
    # Run the complete process
    result = downloader.run()
    
    if result:
        print(f"Successfully downloaded: {result}")
        
        # Load and display first few rows
        try:
            if result.endswith('.csv'):
                df = pd.read_csv(result)
                print(f"\nDownloaded CSV has {len(df)} rows and {len(df.columns)} columns")
                print("\nColumn names:", df.columns.tolist())
                print("\nFirst 5 rows of downloaded data:")
                print(df.head())
            elif result.endswith('.xml'):
                print(f"\nDownloaded XML file: {os.path.basename(result)}")
                # Read file size
                file_size = os.path.getsize(result)
                print(f"File size: {file_size} bytes")
        except Exception as e:
            print(f"Error reading downloaded file: {e}")
    else:
        print("Download failed")
