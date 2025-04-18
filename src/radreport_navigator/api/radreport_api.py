import requests
import json
import logging
import os
import sys
from datetime import datetime
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RadReportNavigator")

# Constants
API_BASE_URL = "https://api3.rsna.org/radreport/v1"
TEMPLATES_ENDPOINT = f"{API_BASE_URL}/templates"
SUBSPECIALTY_ENDPOINT = f"{API_BASE_URL}/subspecialty"
ORGANIZATION_ENDPOINT = f"{API_BASE_URL}/organization"
LANGUAGE_ENDPOINT = f"{API_BASE_URL}/language"

def handle_api_response(response):
    """Handle API response and extract DATA payload"""
    if response.status_code == 200:
        data = response.json()
        return data.get("DATA", [])
    logger.error(f"API request failed with status code: {response.status_code}")
    return None

# Load the JSON file with template data
def load_templates_data(file_path="src/database/templates.json"):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get("DATA", [])
    except Exception as e:
        logger.error(f"Error loading templates: {e}")
        return []

# Save API response to file in samples folder
def save_response_to_file(response_data, template_id):
    samples_dir = os.path.join(os.getcwd(), "samples")
    os.makedirs(samples_dir, exist_ok=True)
    filename = f"template_{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = os.path.join(samples_dir, filename)
    try:
        with open(output_path, 'w') as file:
            json.dump(response_data, file, indent=4)
        logger.info(f"Response saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving response: {e}")

# Format date for API request
def format_date_for_api(date_str):
    return date_str.replace(" ", "%20") if date_str else None

# Build API request URL for template details
def build_template_details_url(template_id, version=None):
    base_url = f"{TEMPLATES_ENDPOINT}/{template_id}/details"
    return f"{base_url}?version={version}" if version else base_url

# Extract numeric ID from user input
def extract_template_id(user_input):
    match = re.search(r'(\d+)', user_input)
    return match.group(1) if match else None

# Fetch template details by ID
def fetch_template_details(template_id, version=None):
    try:
        url = build_template_details_url(template_id, version)
        logger.info(f"Fetching template details from: {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        
        if version and response.status_code != 200:
            logger.warning("Failed with version parameter, trying without version...")
            return fetch_template_details(template_id)
        
        logger.error(f"API request failed with status code: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error fetching template details: {e}")
        return None

# Fetch API data with error handling
def fetch_api_data(endpoint, params=None):
    try:
        response = requests.get(endpoint, params=params)
        return handle_api_response(response)
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None

# Fetch subspecialties
def fetch_subspecialties():
    logger.info("Fetching subspecialties")
    return fetch_api_data(SUBSPECIALTY_ENDPOINT)

# Fetch organizations
def fetch_organizations():
    logger.info("Fetching organizations")
    return fetch_api_data(ORGANIZATION_ENDPOINT)

# Fetch languages
def fetch_languages():
    logger.info("Fetching languages")
    return fetch_api_data(LANGUAGE_ENDPOINT)

# Find template in JSON data by ID
def find_template_by_id(templates_data, template_id):
    return next(
        (t for t in templates_data if str(t.get("template_id")) == str(template_id)),
        None
    )

# Display sample template IDs from JSON data
def display_sample_templates(templates_data, count=5):
    if not templates_data:
        logger.warning("No template data available to display samples")
        return
    
    print("\nSample templates from your data:")
    for i, template in enumerate(templates_data[:count], 1):
        print(f"{i}. ID: {template.get('template_id', 'N/A')} - {template.get('title', 'No title')}")

# Parameter-based navigation menu
def parameter_navigation_menu():
    menu_options = {
        "1": ("Search by specialty", handle_specialty_search),
        "2": ("Search by organization", handle_organization_search),
        "3": ("Search by language", handle_language_search),
        "4": ("Search by keyword", handle_keyword_search),
        "5": ("Go back to main menu", lambda: None)
    }
    
    while True:
        print("\n--- Parameter-based Navigation ---")
        for key, (text, _) in menu_options.items():
            print(f"{key}. {text}")
        
        choice = input("\nEnter your choice (1-5): ")
        handler = menu_options.get(choice, (None, None))[1]
        
        if handler:
            handler()
            if choice == '5':
                return
        else:
            print("Invalid choice. Please try again.")

def handle_specialty_search():
    subspecialties = fetch_subspecialties()
    if not subspecialties:
        return
    
    print("\nAvailable specialties:")
    for i, specialty in enumerate(subspecialties, 1):
        print(f"{i}. {specialty.get('name', 'N/A')} ({specialty.get('code', 'N/A')})")
    
    selected_specs = input("\nEnter specialty codes separated by commas (e.g., CH,CT): ")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"specialty": selected_specs})
    display_search_results(results)

def handle_organization_search():
    organizations = fetch_organizations()
    if not organizations:
        return
    
    print("\nAvailable organizations:")
    for i, org in enumerate(organizations, 1):
        print(f"{i}. {org.get('name', 'N/A')} ({org.get('code', 'N/A')})")
    
    selected_orgs = input("\nEnter organization codes separated by commas (e.g., rsna,acr): ")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"organization": selected_orgs})
    display_search_results(results)

def handle_language_search():
    languages = fetch_languages()
    if not languages:
        return
    
    print("\nAvailable languages:")
    for i, lang in enumerate(languages, 1):
        print(f"{i}. {lang.get('lang', 'N/A')} ({lang.get('code', 'N/A')})")
    
    selected_langs = input("\nEnter language codes separated by commas (e.g., en,fr): ")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"language": selected_langs})
    display_search_results(results)

def handle_keyword_search():
    keyword = input("\nEnter search keyword: ")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"search": keyword})
    display_search_results(results)

# Display search results with pagination
def display_search_results(results):
    if not results:
        print("No results found.")
        return
    
    page_size = 10
    total_pages = (len(results) + page_size - 1) // page_size
    current_page = 1
    
    while True:
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(results))
        
        print(f"\nPage {current_page} of {total_pages}:")
        for i, template in enumerate(results[start_idx:end_idx], start_idx + 1):
            print(f"{i}. ID: {template.get('template_id')} - {template.get('title')}")
        
        if total_pages > 1:
            print("\nN: Next page | P: Previous page | S: Select template | B: Back")
            nav = input("Enter navigation choice: ").upper()
            
            if nav == 'N' and current_page < total_pages:
                current_page += 1
            elif nav == 'P' and current_page > 1:
                current_page -= 1
            elif nav == 'S':
                select_template(results)
                return
            elif nav == 'B':
                return
        else:
            select_template(results)
            return

def select_template(templates):
    try:
        selection = int(input("\nEnter template number (0 to cancel): "))
        if 1 <= selection <= len(templates):
            template = templates[selection - 1]
            process_template_selection(template)
    except ValueError:
        print("Invalid selection.")

def process_template_selection(template):
    template_id = template.get("template_id")
    version_date = template.get("created")
    formatted_date = format_date_for_api(version_date)
    
    details = fetch_template_details(template_id, formatted_date)
    if details:
        result = {
            "currentVersion": {
                "created": version_date,
                "template_version": template.get("template_version")
            },
            "details": details
        }
        save_response_to_file(result, template_id)

# Main function
def main():
    logger.info("Starting RadReport Navigator CLI")
    templates_data = load_templates_data()
    
    if not templates_data:
        logger.error("Failed to load templates data. Exiting.")
        return
    
    while True:
        print("\n=== RadReport Navigator ===")
        print("1. Navigate templates by parameters")
        print("2. Search template by ID")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ")
        
        if choice == "1":
            parameter_navigation_menu()
        elif choice == "2":
            handle_direct_id_search(templates_data)
        elif choice == "3":
            logger.info("Exiting. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

def handle_direct_id_search(templates_data):
    display_sample_templates(templates_data)
    user_input = input("\nEnter template ID (e.g., RPT144): ")
    template_id = extract_template_id(user_input)
    
    if not template_id:
        print("Invalid template ID format.")
        return
    
    template = find_template_by_id(templates_data, template_id)
    if template:
        process_template_selection(template)
    else:
        logger.warning(f"Template {template_id} not found")

if __name__ == "__main__":
    main()
