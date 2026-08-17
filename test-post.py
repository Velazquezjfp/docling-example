import base64
import os
import requests
import json

def get_base64_from_file(file_path):
    """Reads a file and returns its base64 encoded string."""
    try:
        with open(file_path, "rb") as pdf_file:
            # Read the file bytes and encode to base64
            encoded_bytes = base64.b64encode(pdf_file.read())
            # Decode the bytes to a utf-8 string so it can be serialized in JSON
            return encoded_bytes.decode('utf-8')
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return None

def main():
    # --- Configuration ---
    API_URL = "https://api.yourdomain.com/endpoint" # Replace with your actual endpoint
    API_KEY = "your_api_key_here"                   # Replace with your actual API key
    
    # File configuration
    filename = "document.pdf"                       # Replace with your actual PDF filename
    # Assumes the script is run from the directory containing the "docs" folder
    file_path = os.path.join("docs", filename)
    
    # --- 1. Process the File ---
    base64_string = get_base64_from_file(file_path)
    
    if not base64_string:
        print("Exiting because file could not be read.")
        return

    # --- 2. Construct the Payload ---
    # This structure is highly general so you can easily modify the options and target objects
    payload = {
        "options": {
            "use_ocr": True,
            "language_code": "en",
            "extraction_mode": "detailed"
        },
        "sources": [
            {
                "base_64": base64_string,
                "filename": filename,
                "kind": "file"
            }
        ],
        "target": {
            "destination_type": "database",
            "bucket_id": "12345"
        }
    }

    # --- 3. Set up Headers ---
    headers = {
        "X-Api-Key": API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # --- 4. Execute the POST Request ---
    print(f"Sending POST request to {API_URL}...")
    
    try:
        # Note: requests.post automatically converts the 'json' argument dictionary into a JSON string
        response = requests.post(API_URL, headers=headers, json=payload)
        
        # Output the results
        print(f"Response Status Code: {response.status_code}")
        
        # Try to parse the response as JSON
        try:
            print("Response JSON:")
            # Use json.dumps to pretty-print the response
            print(json.dumps(response.json(), indent=2))
        except ValueError:
            # If the response isn't JSON, print the raw text
            print("Response Text:")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")

if __name__ == "__main__":
    main()
