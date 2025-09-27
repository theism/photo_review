#!/usr/bin/env python3
"""
GUI viewer for API test results
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext
import json
import requests
from pathlib import Path
import threading

class APIResultsViewer:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("API Test Results Viewer")
        self.root.geometry("900x700")
        
        # Create main frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="CommCare API Test Results", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", pady=5)
        
        # Test buttons
        self.test_parsing_btn = ctk.CTkButton(buttons_frame, text="Test File Parsing", command=self.test_parsing)
        self.test_parsing_btn.pack(side="left", padx=5)
        
        self.test_env_btn = ctk.CTkButton(buttons_frame, text="Test .env File", command=self.test_env)
        self.test_env_btn.pack(side="left", padx=5)
        
        self.test_api_btn = ctk.CTkButton(buttons_frame, text="Test API Call", command=self.test_api)
        self.test_api_btn.pack(side="left", padx=5)
        
        self.test_download_btn = ctk.CTkButton(buttons_frame, text="Test Photo Download", command=self.test_photo_download)
        self.test_download_btn.pack(side="left", padx=5)
        
        self.show_photos_btn = ctk.CTkButton(buttons_frame, text="Show Downloaded Photos", command=self.show_downloaded_photos)
        self.show_photos_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(buttons_frame, text="Clear Results", command=self.clear_results)
        self.clear_btn.pack(side="left", padx=5)
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(main_frame, height=30, width=120, font=("Consolas", 10))
        self.results_text.pack(fill="both", expand=True, pady=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(main_frame, text="Ready to test API functionality", text_color="gray")
        self.status_label.pack(pady=5)
        
    def log(self, message, color="black"):
        """Add message to results text area"""
        self.results_text.insert(tk.END, f"{message}\n")
        if color == "green":
            self.results_text.tag_add("green", f"end-2l", "end-1l")
            self.results_text.tag_config("green", foreground="green")
        elif color == "red":
            self.results_text.tag_add("red", f"end-2l", "end-1l")
            self.results_text.tag_config("red", foreground="red")
        elif color == "blue":
            self.results_text.tag_add("blue", f"end-2l", "end-1l")
            self.results_text.tag_config("blue", foreground="blue")
        self.results_text.see(tk.END)
        self.root.update()
    
    def clear_results(self):
        """Clear the results text area"""
        self.results_text.delete(1.0, tk.END)
        self.status_label.configure(text="Results cleared", text_color="gray")
    
    def test_parsing(self):
        """Test parsing the API inputs file"""
        self.log("=== Testing API Input File Parsing ===", "blue")
        
        api_file = Path("api_inputs.txt")
        if not api_file.exists():
            self.log("❌ api_inputs.txt file not found", "red")
            return None
        
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self.log(f"Raw file content:\n{content}\n")
                
                # Remove comments (lines starting with #)
                lines = content.split('\n')
                filtered_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        filtered_lines.append(line)
                
                # Join non-comment lines and parse as JSON
                json_content = '\n'.join(filtered_lines)
                self.log(f"Filtered JSON content:\n{json_content}\n")
                
                # Parse JSON content
                data = json.loads(json_content)
                self.log(f"Parsed JSON data: {data}\n")
                
                # Extract domain and form_xmlns from JSON
                domain_form_pairs = {}
                for domain, form_xmlns in data.items():
                    # Clean domain name (remove quotes and extra characters)
                    domain = domain.strip().strip('"')
                    # Clean form_xmlns (remove quotes and extra characters)
                    form_xmlns = form_xmlns.strip().strip('"')
                    
                    domain_form_pairs[domain] = form_xmlns
                    self.log(f"✅ Domain: '{domain}' -> Form xmlns: '{form_xmlns}'", "green")
                
                return domain_form_pairs
                
        except Exception as e:
            self.log(f"❌ Error parsing API inputs file: {e}", "red")
            return None
    
    def test_env(self):
        """Test finding and reading the .env file"""
        self.log("\n=== Testing .env File ===", "blue")
        
        coverage_path = Path("C:/Users/Mathew Theis/Documents/Coverage/.env")
        if not coverage_path.exists():
            self.log(f"❌ .env file not found at: {coverage_path}", "red")
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
                self.log(f"✅ Found credentials: Username={api_username[:3]}..., Key={api_key[:8]}...", "green")
                return api_username, api_key
            else:
                self.log("❌ Could not find COMMCARE_USERNAME or COMMCARE_API_KEY in .env file", "red")
                return None, None
                
        except Exception as e:
            self.log(f"❌ Error reading .env file: {e}", "red")
            return None, None
    
    def test_api(self):
        """Test making an actual API call"""
        self.log("\n=== Testing API Call ===", "blue")
        
        # First test parsing
        domain_form_pairs = self.test_parsing()
        if not domain_form_pairs:
            self.log("❌ Cannot proceed without valid domain/form pairs", "red")
            return
        
        # Test .env file
        username, api_key = self.test_env()
        if not username or not api_key:
            self.log("❌ Cannot proceed without API credentials", "red")
            return
        
        # Test API call
        domain, form_xmlns = next(iter(domain_form_pairs.items()))
        self.log(f"Testing with domain: '{domain}', form_xmlns: '{form_xmlns}'")
        
        try:
            # CommCare List Forms API
            url = f"https://www.commcarehq.org/a/{domain}/api/v0.5/form/"
            self.log(f"API URL: {url}")
            
            params = {
                'xmlns': form_xmlns,
                'limit': 10  # Small limit for testing
            }
            self.log(f"API Parameters: {params}")
            
            self.log("Making API request...")
            response = requests.get(url, auth=(username, api_key), params=params, timeout=30)
            self.log(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ API call successful!", "green")
                self.log(f"Response keys: {list(data.keys())}")
                
                if 'objects' in data:
                    forms = data['objects']
                    self.log(f"Found {len(forms)} forms")
                    
                    if forms:
                        self.log("Sample form data:")
                        sample_form = forms[0]
                        for key, value in sample_form.items():
                            if isinstance(value, str) and len(value) > 50:
                                self.log(f"  {key}: {value[:50]}...")
                            else:
                                self.log(f"  {key}: {value}")
                        
                        # Look for forms with photo attachments
                        self.log(f"\nLooking for forms with photo attachments...")
                        photo_forms = []
                        for form in forms:
                            attachments = form.get('attachments', {})
                            for filename, attachment_info in attachments.items():
                                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                                    photo_forms.append(form)
                                    self.log(f"✅ Found form with photo: {filename}", "green")
                                    break
                        
                        if photo_forms:
                            self.log(f"Found {len(photo_forms)} forms with photo attachments", "green")
                        else:
                            self.log("No forms with photo attachments found")
                            
                        # Check form types
                        form_types = set()
                        for form in forms:
                            form_types.add(form.get('type', 'unknown'))
                        self.log(f"Form types found: {form_types}")
                        
                    else:
                        self.log("No forms found for this domain/form combination")
                else:
                    self.log("No 'objects' key in response")
                    self.log(f"Response data: {data}")
            else:
                self.log(f"❌ API call failed with status {response.status_code}", "red")
                self.log(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            self.log("❌ API request timed out", "red")
        except requests.exceptions.RequestException as e:
            self.log(f"❌ API request failed: {e}", "red")
        except Exception as e:
            self.log(f"❌ Unexpected error: {e}", "red")
    
    def test_photo_download(self):
        """Test the photo download functionality"""
        self.log("=== Testing Photo Download ===", "blue")
        
        try:
            # Import the test functions
            import subprocess
            import sys
            
            # Run the test_api.py script
            result = subprocess.run([sys.executable, "test_api.py"], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.log("✅ Photo download test completed successfully", "green")
                self.log("Test output:", "blue")
                self.log(result.stdout)
            else:
                self.log("❌ Photo download test failed", "red")
                self.log("Error output:", "red")
                self.log(result.stderr)
                
        except subprocess.TimeoutExpired:
            self.log("❌ Test timed out after 60 seconds", "red")
        except Exception as e:
            self.log(f"❌ Error running photo download test: {e}", "red")
    
    def show_downloaded_photos(self):
        """Show information about downloaded photos"""
        self.log("=== Downloaded Photos Information ===", "blue")
        
        try:
            # Check for downloaded_photos directory
            base_dir = Path("downloaded_photos")
            if not base_dir.exists():
                self.log("❌ No downloaded_photos directory found", "red")
                self.log("Run 'Test Photo Download' first", "yellow")
                return
            
            # Find all test directories (test_YYYYMMDD_HHMMSS)
            test_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("test_")]
            if not test_dirs:
                self.log("❌ No test download directories found", "red")
                self.log("Run 'Test Photo Download' first", "yellow")
                return
            
            # Get the most recent test directory
            latest_test_dir = max(test_dirs, key=lambda x: x.name)
            self.log(f"📁 Checking latest test directory: {latest_test_dir.name}", "blue")
            
            # List all files in the directory
            photo_files = list(latest_test_dir.glob("*"))
            if not photo_files:
                self.log("❌ No photos found in latest test directory", "red")
                return
            
            self.log(f"✅ Found {len(photo_files)} downloaded photos:", "green")
            
            for i, photo_file in enumerate(photo_files, 1):
                file_size = photo_file.stat().st_size
                self.log(f"  {i}. {photo_file.name} ({file_size:,} bytes)", "white")
                
                # Try to extract metadata from filename
                filename = photo_file.name
                
                # Remove file extension
                name_without_ext = filename.replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('.gif', '').replace('.bmp', '')
                
                # Check if it's the expected format: test_photo-{question_name}-{user_id}-form_{form_uuid}
                if name_without_ext.startswith('test_photo-') and 'form_' in name_without_ext:
                    # Expected format: test_photo-{question_name}-{user_id}-form_{form_uuid}
                    # Find the position of 'form_' and extract everything after it
                    form_start = name_without_ext.find('form_')
                    if form_start != -1:
                        # Extract form_id (everything after 'form_')
                        form_id = name_without_ext[form_start + 5:]  # +5 to skip 'form_'
                        
                        # Extract question_name and user_id by splitting the part before 'form_'
                        before_form = name_without_ext[:form_start].rstrip('-')
                        parts = before_form.split('-')
                        
                        # The question name should be the second part (index 1)
                        question_name = parts[1] if len(parts) > 1 else "unknown"
                        
                        # The user_id should be the third part (index 2)
                        user_id = parts[2] if len(parts) > 2 else "unknown"
                        
                        self.log(f"     Question: {question_name}", "gray")
                        self.log(f"     User ID: {user_id}", "gray")
                        self.log(f"     Form ID: {form_id}", "gray")
                    else:
                        self.log(f"     Could not find 'form_' in filename", "gray")
                
                # Check if it's the api_photo format: api_photo-{question_name}-{user_id}-form_{form_uuid}
                elif name_without_ext.startswith('api_photo-') and 'form_' in name_without_ext:
                    # API format: api_photo-{question_name}-{user_id}-form_{form_uuid}
                    # Find the position of 'form_' and extract everything after it
                    form_start = name_without_ext.find('form_')
                    if form_start != -1:
                        # Extract form_id (everything after 'form_')
                        form_id = name_without_ext[form_start + 5:]  # +5 to skip 'form_'
                        
                        # Extract question_name and user_id by splitting the part before 'form_'
                        before_form = name_without_ext[:form_start].rstrip('-')
                        parts = before_form.split('-')
                        
                        # The question name should be the second part (index 1)
                        question_name = parts[1] if len(parts) > 1 else "unknown"
                        
                        # The user_id should be the third part (index 2)
                        user_id = parts[2] if len(parts) > 2 else "unknown"
                        
                        self.log(f"     Question: {question_name}", "gray")
                        self.log(f"     User ID: {user_id}", "gray")
                        self.log(f"     Form ID: {form_id}", "gray")
                    else:
                        self.log(f"     Could not find 'form_' in filename", "gray")
                
                # Handle simple timestamp format (like 1749818959721.jpg)
                elif name_without_ext.isdigit():
                    self.log(f"     Filename appears to be timestamp: {name_without_ext}", "gray")
                    self.log(f"     Note: This suggests the filename creation may not be working as expected", "yellow")
                    self.log(f"     Expected format: test_photo-{{question}}-{{user_id}}-form_{{form_uuid}}.jpg", "yellow")
                
                else:
                    self.log(f"     Unknown filename format: {filename}", "gray")
                    self.log(f"     Raw filename: {filename}", "gray")
                
                self.log("")  # Empty line for readability
            
            # Show directory path
            self.log(f"Photos saved to: {latest_test_dir.absolute()}", "blue")
            
            # Show all available test directories
            if len(test_dirs) > 1:
                self.log(f"\n📁 Available test directories ({len(test_dirs)} total):", "blue")
                for test_dir in sorted(test_dirs, key=lambda x: x.name, reverse=True):
                    photo_count = len(list(test_dir.glob("*")))
                    self.log(f"  - {test_dir.name} ({photo_count} photos)", "gray")
            
        except Exception as e:
            self.log(f"❌ Error reading downloaded photos: {e}", "red")
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    viewer = APIResultsViewer()
    viewer.run()
