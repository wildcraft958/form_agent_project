import json
import logging

logger = logging.getLogger("RadReportNavigator.db")

import os

# Get absolute path relative to current file
base_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(base_dir, "database", "templates.json")

# Load the JSON file with template data
def load_templates_data(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get("DATA", [])
    except Exception as e:
        logger.error(f"Error loading templates: {e}")
        return []

# Find template in JSON data by ID
def find_template_by_id(templates_data, template_id):
    return next(
        (t for t in templates_data if str(t.get("template_id")) == str(template_id)),
        None
    )
