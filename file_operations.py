import pandas as pd
from typing import List
import os

UPLOADS_DIR = "uploads"  # Directory where the files will be saved
OUTPUT_DIR = "output"  # Directory where the processed files will be saved
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Ensure the output directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)  # Ensure the uploads directory exists

def find_phone_number_columns(dataframe: pd.DataFrame) -> List[str]:
    """
    Identify columns likely to contain phone numbers based on column names.
    """
    phone_keywords = ["phone", "contact", "mobile", "number"]
    phone_columns = [
        col for col in dataframe.columns 
        if any(keyword in col.lower() for keyword in phone_keywords)
    ]
    return phone_columns

def split_numbers(data: pd.DataFrame, column: str) -> List[List[str]]:
    total_numbers = len(data)
    
    if total_numbers <= 10:
        # Single chunk for 10 or fewer numbers
        return [data[column].tolist()]
    elif total_numbers <= 20:
        # Split into 2 chunks for 20 or fewer numbers
        chunk_size = 10
        return [data[column].iloc[i:i + chunk_size].tolist() for i in range(0, total_numbers, chunk_size)]
    elif total_numbers <= 30:
        # Split into 3 chunks for 30 or fewer numbers
        chunk_size = 10
        return [data[column].iloc[i:i + chunk_size].tolist() for i in range(0, total_numbers, chunk_size)]
    else:
        # Split into 4 parts for more than 30 numbers
        chunk_size = total_numbers // 4
        chunks = [data[column].iloc[i:i + chunk_size].tolist() for i in range(0, total_numbers, chunk_size)]

        # Handle any remaining numbers
        if total_numbers % 4 != 0:
            # Add remaining rows to the last chunk
            chunks[-1].extend(data[column].iloc[4 * chunk_size:].tolist())

        # Ensure exactly 4 parts are returned (pad with empty lists if necessary)
        while len(chunks) < 4:
            chunks.append([])

        return chunks
    # try:
    #     # Calculate the chunk size for 4 parts
    #     chunk_size = len(df) // 4  
    #     print("chunk size",chunk_size)
        
    #     # Create chunks
    #     chunks = [df[column].iloc[i:i + chunk_size].tolist() for i in range(0, len(df), chunk_size)]
        
    #     # Handle the last chunk if the division isn't perfectly even
    #     if len(df) % 4 != 0:
    #         # Add remaining rows to the last chunk
    #         chunks[-1].extend(df[column].iloc[4 * chunk_size:].tolist())
        
    #     # Ensure exactly 4 parts are returned (pad with empty lists if necessary)
    #     while len(chunks) < 4:
    #         chunks.append([])
        
    #     return chunks
    # except Exception as e:
    #     print(f"Error splitting phone numbers: {e}")
    #     return [None] * 4  # Return a list of None if there's an error

def save_chunks_to_files(phone_data: List[List[str]], base_filename: str) -> List[str]:
    """
    Save the phone data chunks to separate CSV files and return their full paths.
    """
    file_paths = []
    for idx, chunk in enumerate(phone_data):
        if chunk:
            # Create a DataFrame from the chunk
            chunk_df = pd.DataFrame(chunk, columns=["Phone Number"])
            
            # Generate a file path in the UPLOADS_DIR
            filename = f"{base_filename}_chunk_{idx + 1}.csv"
            file_path = os.path.join(UPLOADS_DIR, filename)  # Full path for the file
            chunk_df.to_csv(file_path, index=False)  # Save the chunk to CSV
            file_paths.append(file_path)  # Append the full path to the list
            
    return file_paths
