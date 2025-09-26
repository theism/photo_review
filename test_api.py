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
            
            # Extract domain and form_xmlns from JSON
            domain_form_pairs = {}
            for domain, form_xmlns in data.items():
                # Clean domain name (remove quotes and extra characters)
                domain = domain.strip().strip('"')
                # Clean form_xmlns (remove quotes and extra characters)
                form_xmlns = form_xmlns.strip().strip('"')
                
                domain_form_pairs[domain] = form_xmlns
                print(f"[OK] Domain: '{domain}' -> Form xmlns: '{form_xmlns}'")
            
            return domain_form_pairs
            
    except Exception as e:
        print(f"[ERROR] Error parsing API inputs file: {e}")
        return False

def test_env_file():
    """Test finding and reading the .env file"""
    print("\n=== Testing .env File ===")
    
    coverage_path = Path("C:/Users/Mathew Theis/Documents/Coverage/.env")
    if not coverage_path.exists():
        print(f"❌ .env file not found at: {coverage_path}")
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
    domain, form_xmlns = next(iter(domain_form_pairs.items()))
    print(f"Testing with domain: '{domain}', form_xmlns: '{form_xmlns}'")
    
    try:
        # CommCare List Forms API
        url = f"https://www.commcarehq.org/a/{domain}/api/v0.5/form/"
        print(f"API URL: {url}")
        
        params = {
            'xmlns': form_xmlns,  # Use the specific form xmlns
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
                            print(f"✅ Successfully downloaded {len(downloaded_photos)} photos")
                            return downloaded_photos
                        else:
                            print("❌ No photos were downloaded")
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
    download_dir = Path("test_downloaded_photos")
    download_dir.mkdir(exist_ok=True)
    
    photo_count = 0
    limit = 5  # Limit to 5 photos for testing
    
    for form in forms_data:
        if photo_count >= limit:
            break
            
        # Get form metadata
        user_id = form.get('user_id', 'unknown')
        form_uuid = form.get('id', 'unknown')
        domain = form.get('domain', 'unknown')
        
        print(f"Processing form {form_uuid} from user {user_id}")
        
        # Get attachments from the form data
        attachments = form.get('attachments', {})
        print(f"  Found {len(attachments)} attachments")
        
        for attachment_name, attachment_info in attachments.items():
            if photo_count >= limit:
                break
                
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
                        
                        # Create filename in CommCare format
                        filename = f"test_photo-{question_name}-{user_id}-form_{form_uuid}"
                        file_path = download_dir / filename
                        
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
    """Extract question name from attachment name or form data"""
    # Look for question path in form data that matches this attachment
    form_data = form.get('form', {})
    if form_data:
        # Look through form data for photo-related questions
        for key, value in form_data.items():
            if isinstance(value, str) and attachment_name in value:
                # Extract question name from the key or value
                if 'photograph' in key.lower() or 'photo' in key.lower():
                    return key
                elif 'photograph' in value.lower() or 'photo' in value.lower():
                    # Try to extract question name from the value
                    parts = value.split('/')
                    for part in parts:
                        if 'photograph' in part.lower() or 'photo' in part.lower():
                            return part
    
    # Fallback: use a generic name based on attachment
    return attachment_name.replace('.jpg', '').replace('.jpeg', '').replace('.png', '')

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
