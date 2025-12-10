import time
import pandas as pd
import gspread
import os
import json
from io import StringIO 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options # New Import

# --- CONFIGURATION ---
SHEET_NAME = "Customer_Data"
# Note: JSON file will be created by GitHub Action temporarily
JSON_FILE = "credentials.json"     

LOGIN_URL = "https://cpms.plugtrail.in/login"
DATA_PAGE_URL = "https://cpms.plugtrail.in/users"

# Get sensitive data from GitHub Secrets (Environment Variables)
USER_EMAIL = os.environ.get("LOGIN_EMAIL")
USER_PASSWORD = os.environ.get("LOGIN_PASSWORD")

def automate_data_transfer():
    print("Step 1: Connecting to Google Sheets...")
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Check if credentials file exists (created by GitHub Action)
        if not os.path.exists(JSON_FILE):
            print("Error: credentials.json not found!")
            return

        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        print("Success! Google Sheet Connected.")
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    print("Step 2: Opening the Dashboard (Headless Mode)...")
    
    # --- HEADLESS SETUP (Server lo Screen undadu kabatti idi mandatory) ---
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Browser kanipinchadu
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    driver.get(LOGIN_URL)
    time.sleep(5) 

    # --- LOGIN LOGIC ---
    print("Entering the Login Details...")
    try:
        if not USER_EMAIL or not USER_PASSWORD:
            raise ValueError("Email or Password not found in Environment Variables")

        driver.find_element(By.XPATH, "(//input)[1]").send_keys(USER_EMAIL) 
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(USER_PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except Exception as e:
        print(f"Login Error: {e}")
        driver.quit()
        return
    
    time.sleep(5) 

    # --- DATA PAGE LOOP ---
    print("Directing to Data Page...")
    driver.get(DATA_PAGE_URL) 
    time.sleep(3)

    all_customers = [] 
    page_number = 1

    while True:
        print(f"Scraping Page {page_number}...")
        try:
            dfs = pd.read_html(StringIO(driver.page_source))
            if len(dfs) > 0:
                df = dfs[0]
                all_customers.append(df) 
                print(f"In Page {page_number} ,{len(df)} rows were found.")
            else:
                print("No data in the Page.")
                break
        except Exception as e:
            print(f"Error reading table: {e}")
            break

        # --- NEXT BUTTON LOGIC ---
        try:
            next_btn = driver.find_element(By.XPATH, "//button[@aria-label='Go to next page']")
            
            if "Mui-disabled" in next_btn.get_attribute("class") or not next_btn.is_enabled():
                print("Reached the last Page! Loop stopping.")
                break
            
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(5) 
            page_number += 1
            
        except:
            print("This is the last page. Stopping loop.")
            break

    # --- FINAL UPLOAD ---
    if len(all_customers) > 0:
        print("Step 4: Writing all the Data into the GoogleSheet...")
        final_df = pd.concat(all_customers, ignore_index=True)
        final_df = final_df.fillna("")
        
        sheet.clear()
        try:
            sheet.update(values=[final_df.columns.values.tolist()] + final_df.values.tolist(), range_name='A1')
        except:
             sheet.update([final_df.columns.values.tolist()] + final_df.values.tolist())

        print(f"Success! Total {len(final_df)} rows are uploaded.")
    else:
        print("Sorry, No Data Found.")

    driver.quit()

if __name__ == "__main__":
    automate_data_transfer()