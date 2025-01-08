import time
import subprocess
import requests
import asyncio
import base64
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
import io
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from shared_state_manager import shared_state


valid_numbers_list = []

def launch_browser(port, user_data_dir=None):
    """
    Launch Chrome with remote debugging on a specified port and user profile directory.
    """
    # try:
    chrome_command = [
    '/home/azureuser/chrome-linux64/chrome',
    f'--remote-debugging-port={port}',
    '--headless',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    "--disable-setuid-sandbox",
    "--disable-extensions",
    "--start-maximized",
    ]
    if user_data_dir:
        chrome_command += f" --user-data-dir={user_data_dir}"
    process = subprocess.Popen(chrome_command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    print(f"Launched Chrome with PID: {process.pid}")
    time.sleep(5)  # Give Chrome time to start
    print(process.stderr.read())
    return process
    #     start_time = time.time()
    #     while time.time() - start_time < 30:  # Maximum wait of 30 seconds
    #         try:
    #             response = requests.get(f'http://127.0.0.1:{port}/json')
    #             if response.status_code == 200:
    #                 print(f"Browser on port {port} is ready.")
    #                 break
    #         except requests.exceptions.ConnectionError:
    #             pass
    #         time.sleep(0.5)
    # except Exception as e:
    #     print(f"Failed to launch Chrome: {e}")

def setup_driver(port,profile_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument(f"--remote-debugging-port={port}")
            # options.binary_location = "/usr/bin/google-chrome-stable"
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument('--window-size=1920,1080')    
            # Additional stability options
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-infobars")
            options.add_argument("--start-maximized")
            
            # Memory management
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-zygote")  # Helps with memory issues
            options.add_argument("--single-process")  # More stable in headless mode
            driver_path = r"/usr/local/bin/chromedriver"
            # driver_path = r"C:\chromedriver-win64\chromedriver.exe"
            service = Service(driver_path)
            return webdriver.Chrome(service=service, options=options)


            # chrome_options = ChromeOptions()
            # chrome_options.add_argument("--disable-gpu")
            # chrome_options.add_argument("--no-sandbox")
            # # chrome_options.binary_location = ""
            # chrome_options.add_argument("--headless")
            # chrome_options.add_argument('--window-size=1920,1080')    
            # chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            # driver = webdriver.Chrome(options=chrome_options)
            # print(f"Connected to Chrome on port {port}")
            # return driver
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    raise Exception("Failed to connect to Chrome after multiple attempts")
    

def wait_for_whatsapp_load(driver):
    """
    Wait until WhatsApp Web is fully loaded and ready for use, then extract the QR code.
    """
    try:
        # Wait for the QR code canvas element to be present, which indicates the page is ready
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'canvas[aria-label="Scan this QR code to link a device!"]'))
        )
        print("WhatsApp Web is loaded and ready for scanning.")
        
        # Now, extract the QR code as base64 if the QR code canvas is visible
        try:
            qr_image_base64 = driver.execute_script("""
                var canvas = document.querySelector("canvas");
                return canvas.toDataURL('image/png').substring(22);  // Strip out 'data:image/png;base64,' from base64 string
            """)
            
            # Decode the base64 image
            image_data = base64.b64decode(qr_image_base64)  # Decode the base64 string into raw image data
            image = Image.open(io.BytesIO(image_data))  # Open the image from the byte stream

            # Convert the image to a numpy array
            img_np = np.array(image)

            # Use pyzbar to decode the QR code
            decoded_objects = decode(img_np)

            if decoded_objects:
                for obj in decoded_objects:
                    extracted_text = obj.data.decode('utf-8')
                    print(f"QR Code Detected: {extracted_text}")
                    shared_state.set_qr_detected(extracted_text)
                    monitor_login(driver)
                    print("shared_state.qr_detected_event.is_set()",shared_state.qr_detected_event.is_set())
                    # shared_state.qr_detected_event.set()
                    return {"message": "QR Code Detected", "qr_text": extracted_text}
            else:
                print("No QR code found.")
                return {"message": "No QR code found.", "qr_text": None}
        except Exception as e:
            print(f"Error extracting QR code: {e}")
            return {"message": "Error extracting QR code", "qr_text": None}

    except Exception as e:
        print(f"Error waiting for WhatsApp to load")


def monitor_login(driver):
    """Function to monitor for login status synchronously."""
    print("Monitoring login status...")

    time.sleep(5)  # Wait for 5 seconds before starting to check

    try:
        start_time = time.time()
        while True:
            try:
                # Check for a specific element that confirms login
                driver.find_element(By.CLASS_NAME, "x15bjb6t")  # Chat screen element
                print("Login successful!")
                return {"login_status": "Login successful"}
            except Exception:
                # Wait for a brief period before re-checking
                time.sleep(1)

                # Timeout after 120 seconds to avoid infinite waiting
                if time.time() - start_time > 120:
                    print("Login not detected within timeout.")
                    return {"login_status": "Login not detected"}
    except Exception as e:
        print(f"Error while monitoring login: {e}")


def check_whatsapp_number(driver, phone_number):
    global valid_numbers_list
    phone_number = str(phone_number).strip()
    # Check if the phone number ends with '.0' and remove it if it does
    if phone_number.endswith('.0'):
        phone_number = phone_number[:-2]

    # Check if the phone number has at least 10 digits (after removing the country code)
    if len(phone_number) < 10:
        print(f"Number {phone_number} is ignored (less than 10 digits).")
        return "INVALID"," " 
    if not phone_number.startswith('+91'):
        phone_number = '+91' + phone_number.strip()

    try:
        # Wait for the search box to become visible and enter the phone number
        search_box = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
        )
        # Clear the search box if needed
        try:
            clear_button = driver.find_element(By.XPATH, "//span[@data-icon='x-alt']")
            clear_button.click()
        except Exception:
            pass

        search_box.send_keys(phone_number)
        time.sleep(2)  # Wait for the search to complete

        # Check for "No results found" message
        no_results_element = WebDriverWait(driver, 1.5).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(text(), 'No results found for')]"))
        )
        if no_results_element:
            print(f"Number {phone_number} is INVALID.")
            return "INVALID","  "
    except Exception as e:
        print(f"Number {phone_number} is VALID.")
        try:
        # Try to retrieve the title of the contact
            title_element = WebDriverWait(driver, 1.5).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@class='_ak8j']//span[@dir='auto' and @title]"))
            )
            title = title_element.get_attribute("title")
            valid_numbers_list.append((phone_number, title,"VALID"))  # Add valid number to list
            return "VALID", title
        except Exception as e:
            print(f"Error retrieving title for {phone_number}")
            return "VALID", "Unknown"

def click_new_chat(driver):
    """
    Click the 'New Chat' button in WhatsApp Web.
    """
    try:
        driver.save_screenshot("screenshot.png")
        new_chat_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'span[data-icon="new-chat-outline"]'))
        )
        new_chat_button.click()
        print("Clicked on 'New Chat' button.")
        driver.save_screenshot("screenshot1.png")
        return True
    except Exception as e:
        print("Failed to click 'New Chat' button.")
        return False
    
def process_phone_numbers(numbers_df,driver, output_csv):
    try:
        print("Processing phone numbers...")
        # Apply the function to each row in the dataframe
        results = numbers_df['Phone Number'].apply(
            lambda number: pd.Series(check_whatsapp_number(driver, number))
        )
        print("Results",results)

         # Add the results to the DataFrame
        numbers_df[['WhatsAppStatus', 'Title']] = results
        print("Updated DataFrame with WhatsApp Status:", numbers_df)
        
        # Sort valid phone numbers (WhatsAppStatus == "Valid") to the top
        numbers_df.sort_values(by='WhatsAppStatus', ascending=False, inplace=True)
        print("NUMBER_DF",numbers_df)
        
        
        # Save the updated DataFrame to CSV
        numbers_df.to_csv(output_csv, index=False)
        print(f"Results saved to {output_csv}")
    except Exception as e:
        print(f"Error processing numbers in browser: {e}")