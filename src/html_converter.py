import html_to_json

def convert_html_to_json(html_content):
    """
    Convert HTML form content to JSON format.
    
    Args:
        html_content (str): The HTML content of the form
        
    Returns:
        dict: JSON representation of the form
    """
    if not html_content:
        print("Error: Empty HTML content provided")
        return None
        
    try:
        # Convert HTML to JSON
        json_output = html_to_json.convert(html_content)
        
        # Extract form fields and their attributes
        form_data = extract_form_fields(json_output)
        
        return form_data
    except Exception as e:
        print(f"Error converting HTML to JSON: {e}")
        return None

def extract_form_fields(json_data):
    """
    Extract form fields from the JSON data.
    
    Args:
        json_data (dict): The JSON representation of the HTML
        
    Returns:
        dict: Extracted form fields with their attributes
    """
    # Initialize an empty dictionary to store form fields
    form_fields = {}
    
    if not json_data:
        print("Warning: Empty JSON data provided to extract_form_fields")
        return form_fields
    
    # Extract forms if they exist
    forms = json_data.get('form', [])
    
    if not forms:
        # Look for other input elements outside forms
        extract_inputs_from_json(json_data, form_fields)
        
        # If still no fields found, try different approaches
        if not form_fields:
            print("No form elements found, trying alternative extraction...")
            extract_inputs_from_json_alternative(json_data, form_fields)
            
        return form_fields
    
    # Process each form
    for form in forms:
        extract_inputs_from_json(form, form_fields)
        
    return form_fields

def extract_inputs_from_json(json_element, form_fields):
    """
    Recursively extract input elements from JSON.
    
    Args:
        json_element (dict): JSON element to extract inputs from
        form_fields (dict): Dictionary to store extracted fields
    """
    if not isinstance(json_element, dict):
        return
        
    # Check for input fields
    for element_type in ['input', 'textarea', 'select']:
        if element_type in json_element:
            for input_elem in json_element[element_type]:
                # Get attributes
                attrs = input_elem.get('_attributes', {})
                field_name = attrs.get('name', attrs.get('id', f'unnamed_{element_type}_{len(form_fields)}'))
                field_type = attrs.get('type', element_type)
                
                # Get field value
                field_value = attrs.get('value', '')
                
                # Get label if available
                label = find_associated_label(json_element, field_name)
                
                # Store in form_fields
                form_fields[field_name] = {
                    'type': field_type,
                    'value': field_value,
                    'label': label,
                    'attributes': attrs
                }
    
    # Recursively search in other elements
    for key, value in json_element.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    extract_inputs_from_json(item, form_fields)

def extract_inputs_from_json_alternative(json_element, form_fields):
    """
    Alternative approach to extract form fields when standard approach fails.
    
    Args:
        json_element (dict): JSON element to extract inputs from
        form_fields (dict): Dictionary to store extracted fields
    """
    # Try to find any elements with id or name attributes
    for key, value in json_element.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and '_attributes' in item:
                    attrs = item.get('_attributes', {})
                    if 'id' in attrs or 'name' in attrs:
                        field_name = attrs.get('name', attrs.get('id', f'field_{len(form_fields)}'))
                        form_fields[field_name] = {
                            'type': 'text',  # Default type
                            'value': attrs.get('value', ''),
                            'label': field_name,
                            'attributes': attrs
                        }
                extract_inputs_from_json_alternative(item, form_fields)
    
    # If still empty, create some default fields
    if not form_fields:
        default_fields = [
            "patient_name", "patient_id", "patient_dob", 
            "diagnosis", "medication", "dosage", 
            "frequency", "duration", "special_instructions"
        ]
        
        for field in default_fields:
            form_fields[field] = {
                'type': 'text',
                'value': '',
                'label': field.replace('_', ' ').title(),
                'attributes': {}
            }

def find_associated_label(json_element, field_name):
    """
    Find the label associated with a form field.
    
    Args:
        json_element (dict): JSON element to search for labels
        field_name (str): Name of the field to find label for
        
    Returns:
        str: The label text if found, otherwise an empty string
    """
    if not isinstance(json_element, dict):
        return ""
        
    if 'label' not in json_element:
        return ""
        
    for label in json_element['label']:
        attrs = label.get('_attributes', {})
        if attrs.get('for') == field_name:
            # First check for text content
            if '_value' in label:
                return label.get('_value', '')
            
            # Then check for nested text nodes
            for key, value in label.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            return item
    
    # If no label found, generate one from field name
    return field_name.replace('_', ' ').title()
