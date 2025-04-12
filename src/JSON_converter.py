import json

def convert_json_to_html(json_data):
    """
    Convert JSON form data to HTML.
    
    Args:
        json_data (dict): JSON representation of form data
        
    Returns:
        str: HTML representation of the form
    """
    # Verify json_data is a dictionary
    if not isinstance(json_data, dict):
        try:
            json_data = json.loads(json_data)
        except:
            return "<html><body><h1>Invalid form data</h1></body></html>"
    
    # Basic HTML structure
    html_lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "    <title>Completed Medical Form</title>",
        "    <style>",
        "        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }",
        "        .form-section { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; }",
        "        .form-field { margin-bottom: 10px; }",
        "        .field-label { font-weight: bold; display: block; }",
        "        .field-value { padding: 5px; background-color: #f9f9f9; border-radius: 3px; }",
        "    </style>",
        "</head>",
        "<body>",
        "    <h1>Completed Medical Form</h1>"
    ]
    
    # Process each section
    sections = {}
    
    # Group fields by section
    for field_path, field_value in json_data.items():
        if isinstance(field_value, dict):
            value = field_value.get('value', '')
            parts = field_path.split('/')
            
            if len(parts) > 1:
                section = parts[0]
                field_name = parts[-1]
                
                if section not in sections:
                    sections[section] = []
                
                label = field_value.get('label', field_name)
                sections[section].append((field_name, label, value))
            else:
                # Handle global fields
                if 'global' not in sections:
                    sections['global'] = []
                label = field_value.get('label', field_path)
                sections['global'].append((field_path, label, value))
        else:
            # Simple string value
            if 'global' not in sections:
                sections['global'] = []
            sections['global'].append((field_path, field_path, field_value))
    
    # Generate HTML for each section
    for section_name, fields in sections.items():
        if not fields:
            continue
            
        section_title = section_name.replace('_', ' ').title()
        html_lines.append(f'    <div class="form-section">')
        html_lines.append(f'        <h2>{section_title}</h2>')
        
        for field_name, label, value in fields:
            html_lines.append(f'        <div class="form-field">')
            html_lines.append(f'            <div class="field-label">{label}</div>')
            html_lines.append(f'            <div class="field-value">{value}</div>')
            html_lines.append(f'        </div>')
        
        html_lines.append(f'    </div>')
    
    # Close HTML tags
    html_lines.extend([
        "</body>",
        "</html>"
    ])
    
    return "\n".join(html_lines)
