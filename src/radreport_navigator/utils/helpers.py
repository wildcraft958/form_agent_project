import re
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("RadReportNavigator.utils")

# Extract numeric ID from user input
def extract_template_id(user_input):
    match = re.search(r'(\d+)', user_input)
    return match.group(1) if match else None

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
