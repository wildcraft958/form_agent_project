import html_to_json

def convert_html_to_json(html_content):
    """
    Convert HTML form content to JSON format.
    
    Args:
        html_content (str): The HTML content of the form
        
    Returns:
        dict: JSON representation of the form
    """
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
    
    # Extract forms if they exist
    forms = json_data.get('form', [])
    if not forms:
        # Look for other input elements outside forms
        extract_inputs_from_json(json_data, form_fields)
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
    # Check for input fields
    for element_type in ['input', 'textarea', 'select']:
        if element_type in json_element:
            for input_elem in json_element[element_type]:
                # Get attributes
                attrs = input_elem.get('_attributes', {})
                field_name = attrs.get('name', attrs.get('id', f'unnamed_{element_type}'))
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

def find_associated_label(json_element, field_name):
    """
    Find the label associated with a form field.
    
    Args:
        json_element (dict): JSON element to search for labels
        field_name (str): Name of the field to find label for
        
    Returns:
        str: The label text if found, otherwise an empty string
    """
    if 'label' not in json_element:
        return ""
    
    for label in json_element['label']:
        attrs = label.get('_attributes', {})
        if attrs.get('for') == field_name:
            return label.get('_value', '')
    
    return ""
