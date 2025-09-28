# Photo Review Utility

A Python utility for reviewing and categorizing photos from CommCareHQ forms to determine if they indicate real or fraudulent visits. The utility supports both local directory analysis and API-based photo downloading from CommCareHQ.

## Features

- **Dual Data Sources**: Analyze photos from local directories or download directly from CommCareHQ API
- **Photo Filtering**: Multi-select filtering by question type with photo counts
- **Custom Review Categories**: Define custom buckets for photo classification (e.g., "Real", "Fake", "Verified", etc.)
- **Known Bad Photo Integration**: Optionally include known fraudulent photos in the review set
- **Randomized Review Process**: Photos are randomized for unbiased review
- **CSV Export**: Export review results with metadata including reviewer name and date
- **Modern GUI**: Built with CustomTkinter for a clean, modern interface

## Installation

### Prerequisites

- Python 3.8 or higher
- Windows, macOS, or Linux

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd photo_review
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python photo_utility
   ```

## Usage

### Starting the Application

```bash
python photo_utility
```

### Data Source Options

#### Option 1: Local Directory
1. Select "Local Directory" radio button
2. Browse to a directory containing CommCareHQ photos
3. Click "Check Photo Data" to validate photo naming format
4. Configure review settings and start review

#### Option 2: CommCareHQ API
1. Select "CommCare API" radio button
2. Configure API settings:
   - **Domain/Form Pairs File**: JSON file with domain and form mappings
   - **Date Range**: Optional start and end dates (MM/DD/YY format)
   - **Number of Forms**: Limit forms to download (20-1000)
3. Click "Check Photo Data" to download photos from API
4. Configure review settings and start review

### API Configuration

#### Domain/Form Pairs File Format
Create a JSON file with domain and form mappings:
```json
{
  "domain1": "form_xmlns_1",
  "domain2": "form_xmlns_2"
}
```

#### API Credentials
Create a `.env` file in a "Coverage" directory with:
```
COMMCARE_USERNAME=your_username
COMMCARE_API_KEY=your_api_key
```

### Review Process

1. **Configure Review Settings**:
   - **Reviewer Name**: Your name (saved for future sessions)
   - **Photo Filter**: Select which question types to review
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
├── requirements.txt             # Python dependencies
├── photo_utility               # Application launcher
├── test_api.py                 # API testing utility
├── view_api_results.py         # API results viewer
├── api_inputs.txt              # Example API input file
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
  "connect-experiments": "DFB8B67C-8307-4206-9FE0-2F0AA2ECB8EF"
}
```

## Troubleshooting

### Common Issues

1. **"No module named 'customtkinter'"**:
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`

2. **"No forms found"**:
   - Check API credentials in `.env` file
   - Verify domain/form pairs in input file
   - Check date range settings

3. **Photos not displaying**:
   - Ensure photos have proper file extensions
   - Check photo naming format matches CommCareHQ conventions

4. **API connection issues**:
   - Verify credentials in Coverage/.env file
   - Check network connectivity
   - Verify domain names and form IDs

### Debug Mode

Run with debug output:
```bash
python photo_utility
```
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

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review terminal output for error messages
3. Create an issue with detailed description and error logs
