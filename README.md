# Photo Review Utility

A Python utility for reviewing and categorizing photo attachments on CommCareHQ forms to determine if they indicate real or fraudulent visits. The utility supports both local directory analysis and API-based photo downloading from CommCareHQ.  Code developed with Cursor AI tool.

## Features

- **Dual Data Sources**: Analyze photos from local directories or download directly from CommCareHQ API
- **Photo Filtering**: Multi-select filtering by question type with photo counts
- **Custom Review Categories**: Define custom buckets for photo classification (e.g., "Real", "Fake", "Verified", etc.)
- **Known Bad Photo Integration**: Optionally include known fraudulent photos in the review set
- **Randomized Review Process**: Photos from the selected data source are randomized (if local, from the full local set, if api, from what is downloaded)
- **CSV Export**: Export review results with metadata including reviewer name and date

## Installation

### Prerequisites

- Python 3.8 or higher
- Windows, macOS, or Linux

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/theism/photo_review
   cd photo_review
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python photo_utility
   ```

## Usage

### Starting the Application

```bash
python photo_utility
```

#### Command Line Options

- **`--debug`**: Enable debug mode with verbose output
- **`--help`**: Show help message and exit

Examples:
```bash
# Run with debug output
python photo_utility --debug

# Show help
python photo_utility --help
```

### Data Source Options

#### Option 1: Local Directory
1. Ensure you have already downloaded photos from CommCareHQ, following [Multimedia Export](https://dimagi.atlassian.net/wiki/spaces/commcarepublic/pages/2143956271/Form+Data+Export#Multimedia-Exports) instructions
2. In the application, select "Local Directory" radio button
2. Browse to a directory containing your downloaded CommCareHQ photos
3. Click "Check Photo Data" to validate photo naming format
4. Configure review settings and start review

#### Option 2: CommCareHQ API
1. Select "CommCareHQ API" radio button
2. Configure API settings:
   - **Domain/App Pairs File**: JSON file with domain and app mappings
   - **Date Range**: Optional start and end dates (MM/DD/YY format)
   - **Number of Forms**: Limit forms to download (20-1000)
3. Click "Check Photo Data" to download photos from API
4. Configure review settings and start review
5. Note that photos downloaded are saved in ..\photo_review\downloaded_photos and can be referenced via the Local Directory method in future sessions.

### API Configuration

#### Domain/App Pairs File Format
Create a JSON file with domain and form mappings:
```json
{
  "domain1": "app_id_1",
  "domain2": "app_id_2"
}
```

#### API Credentials
Create a `.env` file.  If you have already done this for the Coverage tool or followed these [instructions](https://dimagi.atlassian.net/wiki/spaces/connect/pages/3159162916/Connect+Analysis+Tools#Create-.env-file), then this step is complete.  Otherwise, create a .env file with :
```
COMMCARE_USERNAME=your_username
COMMCARE_API_KEY=your_api_key
```

### Review Process

1. **Configure Review Settings**:
   - **Reviewer Name**: Your name (saved for future sessions)
   - **Photo Filter**: Select which types of photos to review
   - **Percent to Display**: Percentage of photos to review (with live count)
   - **Review Categories**: Define custom buckets for classification
   - **Known Bad Photos**: Optionally include known fraudulent photos

2. **Start Review**:
   - Click "Start Review" to begin the randomized review process
   - Photos are displayed 3 per row with no labels
   - Click category buttons to classify each set of photos
   - Use "Next" to continue or "Back to Config" to modify settings

3. **Export Results**:
   - Review results are automatically saved to CSV
   - Includes form metadata, reviewer name, and review date
   - Known bad photos are marked with `is_known_bad` column

## File Structure

```
photo_review/
├── src/photo_utility/          # Main application code
│   ├── gui.py                  # GUI application
│   ├── scanner.py              # Photo scanning logic
│   ├── filenames.py            # Filename parsing
│   └── __main__.py             # Application entry point
├── requirements.txt            # Python dependencies
├── photo_utility               # Application launcher
├── test_api.py                 # API testing utility
├── view_api_results.py         # API results viewer
├── app_settings.txt            # Application settings (auto-generated)
└── downloaded_photos/          # Downloaded photos (auto-generated)
```

## Photo Naming Formats

The utility supports CommCareHQ photo naming conventions:

### Standard Format
```
[json_block]-[question_id]-[user_id]-form_[form_id].jpg
```

### Extended Format (with prefix)
```
[prefix]-[json_block]-[question_id]-[user_id]-form_[form_id].jpg
```

## API Testing

### Test API Connection
```bash
python test_api.py
```

### View API Results
```bash
python view_api_results.py
```

## Configuration Files

### app_settings.txt
Automatically created to persist:
- Reviewer name
- Last used directory
- API file path
- Review categories

### api_inputs.txt
Example format for API domain/form pairs:
```json
{
  "connect-experiments": "86bab9977e9afe5a61dbd30e0e500da7"
}
```

## Troubleshooting

### Common Issues

1. **"No module named 'customtkinter'"**:
   - Run `pip install -r requirements.txt`

2. **"No forms found"**:
   - Check API credentials in `.env` file
   - Verify domain/app pairs in input file
   - Check date range settings
   - Use the view_api_results test utility

3. **Photos not displaying**:
   - Ensure photos have proper file extensions
   - Check photo naming format matches CommCareHQ conventions

4. **API connection issues**:
   - Verify credentials in \.env file
   - Check network connectivity
   - Verify domain names and form IDs
   - Use the view_api_results test utility

### Debug Mode

Run with debug output to see detailed logging information:
```bash
python photo_utility --debug
```

Debug mode provides:
- Detailed API request/response information
- File processing steps
- Error tracebacks
- Photo download progress
- Form parsing details

Check terminal output for detailed error messages and API responses.

## Dependencies

- **customtkinter**: Modern GUI framework
- **pillow**: Image processing
- **requests**: HTTP requests for API calls
- **tkcalendar**: Date picker widgets
- **python-dateutil**: Date parsing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

See LICENSE file for details.