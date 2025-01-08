
# from fastapi import FastAPI, File, UploadFile, HTTPException, Body, BackgroundTasks
# from fastapi.responses import JSONResponse
# import io
# from concurrent.futures import ThreadPoolExecutor,as_completed
# import os
# import pandas as pd
# from file_operations import split_numbers, save_chunks_to_files, find_phone_number_columns
# from utils import prepare_output_files, prepare_ports_and_user_data, run_in_browser_with_numbers
# import threading
# import time
# from shared_state_manager import shared_state

# app = FastAPI()


# # Directory for storing uploaded files
# UPLOAD_DIR = "uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)

# @app.post("/upload-file/")
# async def upload_file(
#     file: UploadFile = File(None),
#     phone_numbers: list[str] = Body(default=None),
#     background_tasks: BackgroundTasks = BackgroundTasks()
# ):

#     # Validate input
#     if not file and not phone_numbers:
#         raise HTTPException(status_code=400, detail="Either a file or a list of phone numbers must be provided")

#     try:
#         # Clear only the cache at the start of new request
#         shared_state.clear_cache_only()
#         shared_state.clear_data_cache()

#         all_file_paths = []
#         # Process file upload
#         if file:
#             # Validate file type
#             if file.content_type not in ["text/csv", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
#                 raise HTTPException(status_code=400, detail="File must be a CSV or XLSX")
            
#             # Read file content
#             content = await file.read()
#             original_file_name = file.filename.split('.')[0]
#             temp_file_path = f"/tmp/{file.filename}"
#             with open(temp_file_path, "wb") as f:
#                 f.write(content)
#             data = pd.read_csv(io.BytesIO(content)) if file.content_type == "text/csv" else pd.read_excel(io.BytesIO(content))

#             # Cache the full data
#             shared_state.cache_data(data)

#             # Identify phone number columns
#             phone_columns = find_phone_number_columns(data)
#             if not phone_columns:
#                 return JSONResponse(content={"message": "No phone number column found."}, status_code=400)

#             # Process phone numbers from file
#             phone_data = {col: split_numbers(data, col) for col in phone_columns}
#             all_file_paths = []
#             for col, chunks in phone_data.items():
#                 file_paths = save_chunks_to_files(chunks, col)
#                 all_file_paths.extend(file_paths)
        
#         else:
#             # Process provided phone numbers list
#             chunks = split_numbers(pd.DataFrame({'phone': phone_numbers}), 'phone')
#             all_file_paths = save_chunks_to_files(chunks, 'phone')
#             original_file_name = "phone_numbers" 

#         # Prepare execution environment
#         total_numbers = sum(len(pd.read_csv(file)) for file in all_file_paths)
#         ports, user_data_dirs = prepare_ports_and_user_data(total_numbers)
#         output_csv_files = prepare_output_files(all_file_paths)

#         # Execute browser operations in parallel
#         with ThreadPoolExecutor() as executor:
#             futures = [
#                 executor.submit(run_in_browser_with_numbers, input_file, output_file, port, user_data_dir,f"{original_file_name}_NurenAi_Validator.csv")
#                 for input_file, output_file, port, user_data_dir in zip(all_file_paths, output_csv_files, ports, user_data_dirs)
#             ]
            
#             driver = None
#             # Wait for threads and check for QR codes
#             for future in as_completed(futures):
#                 try:

#                     merged_output_file = future.result()
#                 except Exception as e:
#                     print(f"Error in thread: {str(e)}")
#                     continue

#         # Final check for QR codes
#         if shared_state.qr_detected_event.is_set():
#             qr_codes = shared_state.get_all_qr_codes()
#             if qr_codes:
#                 return JSONResponse(
#                     content={"message": f"QR Code detected Login again"},#: {', '.join(qr_codes)}
#                     status_code=200
#                 )
#          # Clean up temporary files
#         for file in all_file_paths + output_csv_files:
#             if os.path.exists(file):
#                 os.remove(file)
#                 print(f"Deleted temporary file: {file}")

#         # Return merged file
#         if merged_output_file and os.path.exists(merged_output_file):
#             return JSONResponse(
#                 content={"message": "Files processed successfully", "merged_file": merged_output_file}
#             )
#         else:
#             raise HTTPException(status_code=500, detail="Error generating merged file")
#     except Exception as e:
#         print(f"Error in upload_file: {str(e)}")  # Log the error
#         raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
import shutil
import os
import io
import csv
from pydantic import BaseModel
from typing import List,Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks,Body
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from file_operations import split_numbers, save_chunks_to_files, find_phone_number_columns
from utils import prepare_output_files, prepare_ports_and_user_data, run_in_browser_with_numbers
from shared_state_manager import shared_state

app = FastAPI()

class PhoneNumbersRequest(BaseModel):
    phone_numbers: List[str]

# Directory for storing uploaded files
UPLOAD_DIR = "uploads"
SUCCESSFUL_DIR = "successful"  # Directory for successful processed files
VALIDATED_DIR = "validated"
SUCCESS_DIR = "success"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SUCCESSFUL_DIR, exist_ok=True)

def save_phone_numbers_to_csv(phone_numbers, upload_dir):
    """Create a temporary CSV file to store phone numbers."""
    file_name = "phone_numbers.csv"
    file_path = os.path.join(upload_dir, file_name)
    with open(file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Phone Number"])  # Add a header row
        for number in phone_numbers:
            writer.writerow([number])
    return file_path

# Function to process the file in the background
def process_file_in_background(file_path, original_file_name):
    try:
        # Process the file based on the provided path
        with open(file_path, "rb") as file:
            content = file.read()

        # Your existing processing logic here
        shared_state.clear_cache_only()
        shared_state.clear_data_cache()

        all_file_paths = []
        data = pd.read_csv(io.BytesIO(content)) if file_path.endswith(".csv") else pd.read_excel(io.BytesIO(content))

        # Cache the full data
        shared_state.cache_data(data)

        # Identify phone number columns
        phone_columns = find_phone_number_columns(data)
        if not phone_columns:
            raise HTTPException(status_code=400, detail="No phone number column found.")

        # Process phone numbers from file
        phone_data = {col: split_numbers(data, col) for col in phone_columns}
        all_file_paths = []
        for col, chunks in phone_data.items():
            file_paths = save_chunks_to_files(chunks, col)
            all_file_paths.extend(file_paths)

        # Prepare execution environment
        total_numbers = sum(len(pd.read_csv(file)) for file in all_file_paths)
        ports, user_data_dirs = prepare_ports_and_user_data(total_numbers)
        output_csv_files = prepare_output_files(all_file_paths)

        # Execute browser operations in parallel
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(run_in_browser_with_numbers, input_file, output_file, port, user_data_dir, f"{original_file_name}_NurenAi_Validator.csv")
                for input_file, output_file, port, user_data_dir in zip(all_file_paths, output_csv_files, ports, user_data_dirs)
            ]
            
            driver = None
            # Wait for threads and check for QR codes
            for future in as_completed(futures):
                try:
                    merged_output_file = future.result()
                except Exception as e:
                    print(f"Error in thread: {str(e)}")
                    continue

        # Final check for QR codes
        if shared_state.qr_detected_event.is_set():
            qr_codes = shared_state.get_all_qr_codes()
            if qr_codes:
                print(f"QR Code detected, please log in again: {', '.join(qr_codes)}")

        # Clean up temporary files
        for file in all_file_paths + output_csv_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted temporary file: {file}")

        # Store merged output file path to be used in GET request later
        if merged_output_file and os.path.exists(merged_output_file):
            return merged_output_file
        else:
            raise HTTPException(status_code=500, detail="Error generating merged file")

    except Exception as e:
        print(f"Error in processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in processing file: {str(e)}")


@app.post("/upload-file/")
async def upload_file(    
    file: UploadFile = File(None),
    phone_numbers: Optional[PhoneNumbersRequest] = Body(default=None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):

    # Validate input
    if not file and not phone_numbers:
        raise HTTPException(status_code=400, detail="Either a file or a list of phone numbers must be provided")

    try:
        # # Save the uploaded file temporarily
        # temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
        # with open(temp_file_path, "wb") as temp_file:
        #     temp_file.write(await file.read())
        # filename =file.filename.split('.')[0]
        # Save the uploaded file temporarily if provided
        if file:
            temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(await file.read())
            filename = file.filename.split('.')[0]
        elif phone_numbers:
            # Save phone numbers to a CSV file
            temp_file_path = save_phone_numbers_to_csv(phone_numbers, UPLOAD_DIR)
            filename = "phone_numbers"
        # Trigger the background task to process the file
        background_tasks.add_task(process_file_in_background, temp_file_path, file.filename.split('.')[0])

        # Immediately return a response to the user
        return JSONResponse(
            content={"message": f"{filename} uploaded successfully."},
            status_code=200
        )
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")  # Log the error
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/download-merged-file/")
async def download_merged_file():
    # Check if there are any files in the "validated" folder
    validated_files = os.listdir(SUCCESS_DIR)
    
    if not validated_files:
        raise HTTPException(status_code=404, detail="In Processing........")

    # Get the first file from the validated folder (you can change this logic if needed)
    file_to_send = validated_files[0]
    merged_file_path = os.path.join(SUCCESS_DIR, file_to_send)

    # Move the file to the "successful" folder
    successful_path = os.path.join(SUCCESSFUL_DIR, file_to_send)
    shutil.move(merged_file_path, successful_path)
    print(f"Moved merged file to successful folder: {successful_path}")

    # Return the file as a response
    return FileResponse(successful_path)

    

# # This function will keep Chrome open after the response is returned
# def keep_chrome_open(driver):
#     """Function to keep Chrome open indefinitely after processing."""
#     print("Chrome instance will remain open. Close manually if needed.")
#     while True:
#         try:
#             input("Press Ctrl+C to exit and close the browser...")
#         except KeyboardInterrupt:
#             print("Closing Chrome instance...")
#             if driver:
#                 driver.quit()
#             break