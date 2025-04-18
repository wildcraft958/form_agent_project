import json
import logging

logger = logging.getLogger("RadReportNavigator.db")

# Load the JSON file with template data
def load_templates_data(file_path="src/database/templates.json"):
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
