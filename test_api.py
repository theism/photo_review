#!/usr/bin/env python3
"""
Test script to verify CommCare API functionality
"""

import json
import requests
from pathlib import Path

def test_api_parsing():
    """Test parsing the API inputs file"""
    print("=== Testing API Input File Parsing ===")
    
    # Read the api_inputs.txt file
    api_file = Path("api_inputs.txt")
    if not api_file.exists():
        print("[ERROR] api_inputs.txt file not found")
        return False
    
    try:
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            print(f"Raw file content:\n{content}\n")
            
            # Remove comments (lines starting with #)
            lines = content.split('\n')
            filtered_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    filtered_lines.append(line)
            
            # Join non-comment lines and parse as JSON
            json_content = '\n'.join(filtered_lines)
            print(f"Filtered JSON content:\n{json_content}\n")
            
            # Parse JSON content
            data = json.loads(json_content)
            print(f"Parsed JSON data: {data}\n")
            
            # Extract domain and app_id from JSON
            domain_form_pairs = {}
            for domain, app_id in data.items():
                # Clean domain name (remove quotes and extra characters)
                domain = domain.strip().strip('"')
                # Clean app_id (remove quotes and extra characters)
                app_id = app_id.strip().strip('"')
                
                domain_form_pairs[domain] = app_id
                print(f"[OK] Domain: '{domain}' -> Form app_id: '{app_id}'")
            
            return domain_form_pairs
            
    except Exception as e:
        print(f"[ERROR] Error parsing API inputs file: {e}")
        return False

def test_env_file():
    """Test finding and reading the .env file"""
    print("\n=== Testing .env File ===")
    
    coverage_path = Path("C:/Users/Mathew Theis/Documents/Coverage/.env")
    if not coverage_path.exists():
        print(f"[FAIL] .env file not found at: {coverage_path}")
        return None, None
    
    try:
        api_username = None
        api_key = None
        with open(coverage_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('COMMCARE_USERNAME='):
                    api_username = line.split('=', 1)[1].strip()
                elif line.startswith('COMMCARE_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
        
        if api_username and api_key:
            print(f"[OK] Found credentials: Username={api_username[:3]}..., Key={api_key[:8]}...")
            return api_username, api_key
        else:
            print("[ERROR] Could not find COMMCARE_USERNAME or COMMCARE_API_KEY in .env file")
            return None, None
            
    except Exception as e:
        print(f"[ERROR] Error reading .env file: {e}")
        return None, None

def test_api_call(domain_form_pairs, username, api_key):
    """Test making an actual API call and downloading photos"""
    print("\n=== Testing API Call ===")
    
    if not domain_form_pairs:
        print("[ERROR] No domain/form pairs to test")
        return False
    
    # Test with the first domain/form pair
    domain, app_id = next(iter(domain_form_pairs.items()))
    print(f"Testing with domain: '{domain}', app_id: '{app_id}'")
    
    try:
        # CommCare List Forms API
        url = f"https://www.commcarehq.org/a/{domain}/api/v0.5/form/"
        print(f"API URL: {url}")
        
        params = {
            'app_id': app_id,  # Use the specific form app_id
            'limit': 10  # Small limit for testing
        }
        print(f"API Parameters: {params}")
        
        print("Making API request...")
        response = requests.get(url, auth=(username, api_key), params=params, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] API call successful!")
            print(f"Response keys: {list(data.keys())}")
            
            if 'objects' in data:
                forms = data['objects']
                print(f"Found {len(forms)} forms")
                
                if forms:
                    print("Sample form data:")
                    sample_form = forms[0]
                    for key, value in sample_form.items():
                        if isinstance(value, str) and len(value) > 50:
                            print(f"  {key}: {value[:50]}...")
                        else:
                            print(f"  {key}: {value}")
                    
                    # Look for forms with photo attachments
                    print(f"\nLooking for forms with photo attachments...")
                    photo_forms = []
                    for form in forms:
                        attachments = form.get('attachments', {})
                        for filename, attachment_info in attachments.items():
                            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                                photo_forms.append(form)
                                print(f"[OK] Found form with photo: {filename}")
                                break
                    
                    if photo_forms:
                        print(f"Found {len(photo_forms)} forms with photo attachments")
                        
                        # Test downloading photos
                        print(f"\n=== Testing Photo Download ===")
                        downloaded_photos = test_photo_download(photo_forms, username, api_key)
                        if downloaded_photos:
                            print(f"[OK] Successfully downloaded {len(downloaded_photos)} photos")
                            return downloaded_photos
                        else:
                            print("[FAIL] No photos were downloaded")
                    else:
                        print("No forms with photo attachments found")
                        
                    # Check form types
                    form_types = set()
                    for form in forms:
                        form_types.add(form.get('type', 'unknown'))
                    print(f"Form types found: {form_types}")
                    
                else:
                    print("No forms found for this domain/form combination")
            else:
                print("No 'objects' key in response")
                print(f"Response data: {data}")
        else:
            print(f"[ERROR] API call failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("[ERROR] API request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API request failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False
    
    return True

def test_photo_download(forms_data, username, api_key):
    """Test downloading photos from forms data"""
    print("\n=== Testing Photo Download ===")
    
    downloaded_photos = []
    # Create timestamped subdirectory
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_dir = Path("downloaded_photos") / f"test_{timestamp}"
    download_dir.mkdir(parents=True, exist_ok=True)
    
    photo_count = 0
    form_limit = 5  # Limit to 5 forms for testing
    
    # Process all forms (limit was already applied per domain in API call)
    forms_to_process = forms_data
    print(f"Processing {len(forms_to_process)} forms (limit {form_limit} per domain)")
    
    for form in forms_to_process:
            
        # Get form metadata
        # User ID is in the form.meta section
        form_data = form.get('form', {})
        meta = form_data.get('meta', {})
        user_id = meta.get('userID', 'unknown')
        form_id = form.get('id', 'unknown')
        domain = form.get('domain', 'unknown')
        
        print(f"Processing form {form_id} from user {user_id}")
        
        # Get attachments from the form data
        attachments = form.get('attachments', {})
        print(f"  Found {len(attachments)} attachments")
        
        for attachment_name, attachment_info in attachments.items():
            # Check if it's a photo file
            if attachment_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                print(f"  Processing photo: {attachment_name}")
                try:
                    # Get the download URL from attachment info
                    download_url = attachment_info.get('download_url')
                    if not download_url:
                        # Try alternative URL structure
                        download_url = attachment_info.get('url')
                    
                    if download_url:
                        print(f"    Download URL: {download_url}")
                        
                        # Download the photo
                        photo_response = requests.get(download_url, auth=(username, api_key))
                        photo_response.raise_for_status()
                        
                        # Extract question name from attachment name or form data
                        question_name = extract_question_name(attachment_name, form)
                        
                        # Create filename in CommCare format with proper extension
                        # Determine file extension from original attachment name
                        file_ext = '.jpg'  # Default to .jpg
                        if attachment_name.lower().endswith('.jpeg'):
                            file_ext = '.jpeg'
                        elif attachment_name.lower().endswith('.png'):
                            file_ext = '.png'
                        elif attachment_name.lower().endswith('.gif'):
                            file_ext = '.gif'
                        elif attachment_name.lower().endswith('.bmp'):
                            file_ext = '.bmp'
                        
                        filename = f"test_photo-{question_name}-{user_id}-form_{form_id}{file_ext}"
                        file_path = download_dir / filename
                        
                        print(f"    DEBUG: Creating filename: {filename}")
                        print(f"    DEBUG: Question name: {question_name}")
                        print(f"    DEBUG: User ID: {user_id}")
                        print(f"    DEBUG: Form UUID: {form_id}")
                        print(f"    DEBUG: File extension: {file_ext}")
                        
                        with open(file_path, 'wb') as f:
                            f.write(photo_response.content)
                        
                        downloaded_photos.append(str(file_path))
                        photo_count += 1
                        print(f"    [OK] Downloaded: {filename}")
                        
                    else:
                        print(f"    [ERROR] No download URL found for {attachment_name}")
                        
                except Exception as e:
                    print(f"    [ERROR] Error downloading {attachment_name}: {e}")
                    continue
    
    return downloaded_photos

def extract_question_name(attachment_name, form):
    """Extract question name from form data by finding the key that has this attachment as its value"""
    # Look for question path in form data that matches this attachment
    form_data = form.get('form', {})
    if form_data:
        # Recursively search through nested dictionaries
        def find_question_in_data(data, path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    if isinstance(value, str) and value == attachment_name:
                        # Found the key that corresponds to this attachment
                        print(f"    DEBUG: Found question key '{key}' for attachment '{attachment_name}' at path '{current_path}'")
                        return key
                    elif isinstance(value, str) and attachment_name in value:
                        # Partial match - the value contains the attachment name
                        print(f"    DEBUG: Found partial match - key '{key}' contains attachment '{attachment_name}' at path '{current_path}'")
                        return key
                    elif isinstance(value, dict):
                        # Recursively search nested dictionaries
                        result = find_question_in_data(value, current_path)
                        if result:
                            return result
            return None
        
        # Search through the form data
        question_name = find_question_in_data(form_data)
        if question_name:
            return question_name
    
    # Fallback: use a generic name based on attachment
    fallback_name = attachment_name.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
    print(f"    DEBUG: Using fallback question name: {fallback_name}")
    return fallback_name

def main():
    """Main test function"""
    print("CommCare API Test Script")
    print("=" * 50)
    
    # Test 1: Parse API inputs file
    domain_form_pairs = test_api_parsing()
    if not domain_form_pairs:
        print("\n[ERROR] Cannot proceed without valid domain/form pairs")
        return
    
    # Test 2: Find and read .env file
    username, api_key = test_env_file()
    if not username or not api_key:
        print("\n[ERROR] Cannot proceed without API credentials")
        return
    
    # Test 3: Make actual API call and download photos
    result = test_api_call(domain_form_pairs, username, api_key)
    
    if result:
        if isinstance(result, list) and len(result) > 0:
            print(f"\n[OK] All tests passed! Downloaded {len(result)} photos.")
            print(f"Photos saved to: test_downloaded_photos/")
            print("Downloaded files:")
            for photo_path in result:
                print(f"  - {photo_path}")
        else:
            print("\n[OK] API test passed, but no photos were downloaded.")
    else:
        print("\n[ERROR] API test failed. Check credentials and network connection.")

if __name__ == "__main__":
    main()
