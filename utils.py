import pandas as pd
import datetime
import os
import shutil
import asyncio
from shared_state_manager import shared_state

# Prepare output filenames for the processed parts
def prepare_output_files(parts):
    output_csv_files = []
    for i, part in enumerate(parts):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file_name = f"output_{i+1}_{timestamp}.csv"
        output_file_path = os.path.join("output", output_file_name)
        output_csv_files.append(output_file_path)
    return output_csv_files

# Function to prepare ports and user data directories for each thread
def prepare_ports_and_user_data(total_numbers):
    if total_numbers <= 10:
        num_ports = 1
    elif total_numbers <= 20:
        num_ports = 2
    elif total_numbers <= 30:
        num_ports = 3
    else:
        num_ports = 4
    ports = [9222 + i for i in range(num_ports)]
    user_data_dirs = [f"chrome_profile_{i + 1}" for i in range(num_ports)]
    return ports, user_data_dirs


def merge_output_files(output_csv_files, merged_file_name):
    try:
        # Combine all output files into a single DataFrame
        combined_df = pd.concat((pd.read_csv(file) for file in output_csv_files), ignore_index=True)
        
        # Retrieve the cached data (which contains the additional columns)
        cached_data = shared_state.get_cached_data()

        if cached_data is not None:
            # Merge based on the 'Phone Number' column (you may need to adjust this column name)
            combined_df = pd.merge(combined_df, cached_data, how='left', on='Phone Number')

        combined_df['WhatsAppStatus'] = combined_df['WhatsAppStatus'].fillna('Invalid')  # Handle missing status

        # Save the combined DataFrame to a new file
        combined_df.to_csv(merged_file_name, index=False)
        print(f"Combined file created at {merged_file_name}")
        
        merged_df = pd.read_csv(merged_file_name)

        # Sort by 'WhatsAppStatus' in descending order
        merged_df.sort_values(by='WhatsAppStatus', ascending=False, inplace=True)
        print(f"Sorted DataFrame by WhatsAppStatus in descending order.")

        # Create the 'validated' folder if it doesn't exist
        validated_folder = "validated"
        if not os.path.exists(validated_folder):
            os.makedirs(validated_folder)

         # Create the 'success' folder if it doesn't exist
        success_folder = "success"
        if not os.path.exists(success_folder):
            os.makedirs(success_folder)
        
        # Check for existing files with the same name in the 'validated' folder
        validated_file_path = os.path.join(validated_folder, os.path.basename(merged_file_name))
        if os.path.exists(validated_file_path):
            # If a file with the same name exists, combine the existing file with the new one
            print(f"File with the same name found in validated folder: {validated_file_path}")
            existing_df = pd.read_csv(validated_file_path)
            combined_df = pd.concat([existing_df, combined_df], ignore_index=True)
            
            # Remove duplicates if necessary (optional)
            combined_df.drop_duplicates(inplace=True)

            # Sort the combined DataFrame by 'WhatsAppStatus' in descending order
            combined_df.sort_values(by='WhatsAppStatus', ascending=False, inplace=True)
            print(f"Sorted combined DataFrame by WhatsAppStatus in descending order.")

            # Save the updated combined file back to the validated folder
            combined_df.to_csv(validated_file_path, index=False)
            print(f"Combined with existing file and saved at {validated_file_path}")
        else:
            # Move the merged file to the 'validated' folder
            shutil.move(merged_file_name, validated_file_path)
            print(f"Moved merged file to {validated_file_path}")

         # Move processed files from validated folder to success folder
        shutil.copy(validated_file_path, os.path.join(success_folder, os.path.basename(merged_file_name)))
        print(f"Moved processed file to 'success' folder: {os.path.join(success_folder, os.path.basename(merged_file_name))}")

        
        # Delete individual output files
        for file in output_csv_files:
            os.remove(file)
            print(f"Deleted temporary file: {file}")
        
        return validated_file_path
    except Exception as e:
        print(f"Error merging output files: {e}")
        raise


# def merge_output_files(output_csv_files, merged_file_name):
#     try:
#         # Combine all output files into a single DataFrame
#         combined_df = pd.concat((pd.read_csv(file) for file in output_csv_files), ignore_index=True)
        
#         # Retrieve the cached data (which contains the additional columns)
#         cached_data = shared_state.get_cached_data()

#         if cached_data is not None:
#             # Merge based on the 'Phone Number' column (you may need to adjust this column name)
#             combined_df = pd.merge(combined_df, cached_data, how='left', on='Phone Number')

#         combined_df['WhatsAppStatus'] = combined_df['WhatsAppStatus'].fillna('Invalid')  # Handle missing status

#         # Save the combined DataFrame to a new file
#         combined_df.to_csv(merged_file_name, index=False)
#         print(f"Combined file created at {merged_file_name}")
        
#         # Create the 'validated' folder if it doesn't exist
#         validated_folder = "validated"
#         if not os.path.exists(validated_folder):
#             os.makedirs(validated_folder)
        

#         # Move the merged file to the 'validated' folder
#         validated_file_path = os.path.join(validated_folder, os.path.basename(merged_file_name))
#         shutil.move(merged_file_name, validated_file_path)
#         print(f"Moved merged file to {validated_file_path}")
        
#         # Delete individual output files
#         for file in output_csv_files:
#             os.remove(file)
#             print(f"Deleted temporary file: {file}")
        
#         return validated_file_path
#     except Exception as e:
#         print(f"Error merging output files: {e}")
#         raise

from browser_operations import launch_browser, setup_driver, wait_for_whatsapp_load, click_new_chat, process_phone_numbers

def run_in_browser_with_numbers(csv_file, output_csv, port, user_data_dir,merged_file_name):

    driver = None
    try:
        launch_browser(port, user_data_dir)
        print("Browser launched successfully.")
        driver = setup_driver(port, user_data_dir)
        print("Driver connected successfully.")
        driver.get("https://web.whatsapp.com")
        print("Navigated to WhatsApp Web.")
        
        try:
            qr_result = wait_for_whatsapp_load(driver)
            if qr_result and qr_result.get("message") == "QR Code Detected":
                qr_code_text = qr_result.get("qr_text", "No QR code text found")
                shared_state.set_qr_detected(qr_code_text)  # Store the QR code text in shared state
                print("QR code detected in another thread. Exiting...")
                print("shared_state.qr_detected_event.is_set()", shared_state.qr_detected_event.is_set())
                return qr_result, driver  # Return the qr_result to notify that QR is detected
            else:
                print("QR code not detected or no result returned.")
        except Exception as e:
            print("Error while waiting for WhatsApp to load:", str(e))

        print("shared_state",shared_state.qr_detected_event.is_set())
        output_csv_files = []
        # Process phone numbers only if QR code is not detected
        if not shared_state.qr_detected_event.is_set():
            print("checking for new chat")
            numbers_df = pd.read_csv(csv_file)
            print("numbers_df",numbers_df)
            while not click_new_chat(driver):
                print("Waiting for 'New Chat' button...")

            process_phone_numbers(numbers_df,driver, output_csv)
            output_csv_files.append(output_csv)  # Track output files
            

            if shared_state.qr_detected_event.is_set():
                print("QR detected in another thread. Exiting...")
                return
         # Merge all the output CSV files after processing
        final_output_file = merge_output_files([output_csv], merged_file_name)
        print(f"Final merged output file: {final_output_file}")

        return final_output_file
       
    except Exception as e:
        print(f"Error in browser operation: {e}")