import requests
import logging
from datetime import datetime

logger = logging.getLogger("RadReportNavigator.api")

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

# Format date for API request
def format_date_for_api(date_str):
    return date_str.replace(" ", "%20") if date_str else None

# Build API request URL for template details
def build_template_details_url(template_id, version=None):
    base_url = f"{TEMPLATES_ENDPOINT}/{template_id}/details"
    return f"{base_url}?version={version}" if version else base_url

# Fetch API data with error handling
def fetch_api_data(endpoint, params=None):
    try:
        response = requests.get(endpoint, params=params)
        return handle_api_response(response)
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None

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
