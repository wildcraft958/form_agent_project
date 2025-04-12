import json

def convert_json_to_html(json_data):
    """
    Convert JSON form data to HTML.
    
    Args:
        json_data (dict): JSON representation of form data
    
    Returns:
        str: HTML representation of the form
    """
    # Basic HTML structure
    html_lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "  <title>Filled Form</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 20px; }",
        "    .form-group { margin-bottom: 15px; }",
        "    label { display: block; margin-bottom: 5px; font-weight: bold; }",
        "    .value { padding: 8px; border: 1px solid #ddd; border-radius: 4px; background-color: #f9f9f9; }",
        "    .section { margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px; }",
        "    .section-title { font-size: 1.2em; color: #333; margin-bottom: 15px; }",
        "    .subsection { margin-left: 20px; margin-bottom: 15px; }",
        "    .form-container { max-width: 800px; margin: 0 auto; }",
        "    h1 { color: #2c3e50; }",
        "    .metadata { color: #7f8c8d; font-size: 0.9em; margin-bottom: 20px; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>Form Submission</h1>",
        "  <div class='form-container'>"
    ]
    
    # Process form data
    if isinstance(json_data, dict):
        # Extract form title if available
        if 'title' in json_data:
            html_lines[18] = f"  <h1>{json_data['title']}</h1>"
            
        # Add metadata if available
        if any(k in json_data for k in ['author', 'version', 'date', 'specialty']):
            metadata = []
            if 'author' in json_data:
                metadata.append(f"Author: {json_data['author']}")
            if 'version' in json_data:
                metadata.append(f"Version: {json_data['version']}")
            if 'date' in json_data:
                metadata.append(f"Date: {json_data['date']}")
            if 'specialty' in json_data:
                metadata.append(f"Specialty: {json_data['specialty']}")
                
            if metadata:
                html_lines.append("  <div class='metadata'>" + " | ".join(metadata) + "</div>")
        
        # Process flat structure (simple key-value pairs)
        simple_fields = {k: v for k, v in json_data.items() 
                        if not k.startswith('_') and k not in ['title', 'sections', 'fields', 
                                                              'author', 'version', 'date', 'specialty']}
        
        if simple_fields:
            html_lines.extend(_render_flat_fields(simple_fields))
            
        # Process hierarchical structure
        if 'fields' in json_data:
            html_lines.append("  <div class='section'>")
            html_lines.append("    <div class='section-title'>General Information</div>")
            html_lines.extend(_render_fields(json_data.get('fields', [])))
            html_lines.append("  </div>")
            
        if 'sections' in json_data:
            html_lines.extend(_render_sections(json_data.get('sections', [])))
    else:
        html_lines.append("  <p>Invalid form data</p>")
    
    # Close HTML tags
    html_lines.extend([
        "  </div>",
        "</body>",
        "</html>"
    ])
    
    return "\n".join(html_lines)

def _render_flat_fields(fields_dict):
    """Render fields from a flat dictionary structure."""
    html_lines = []
    
    for field_name, field_data in fields_dict.items():
        # Skip internal fields
        if field_name.startswith('_'):
            continue
            
        if isinstance(field_data, dict) and not field_data.get('hidden', False):
            label = field_data.get('label', field_name)
            value = field_data.get('value', '')
            html_lines.extend([
                f"    <div class='form-group'>",
                f"      <label>{label}</label>",
                f"      <div class='value'>{value}</div>",
                f"    </div>"
            ])
        elif not isinstance(field_data, dict) and field_data is not None:
            # For simple key-value pairs
            html_lines.extend([
                f"    <div class='form-group'>",
                f"      <label>{field_name}</label>",
                f"      <div class='value'>{field_data}</div>",
                f"    </div>"
            ])
            
    return html_lines

def _render_fields(fields_list):
    """Render fields from a list of field objects."""
    html_lines = []
    
    for field in fields_list:
        if not isinstance(field, dict) or field.get('hidden', False):
            continue
            
        name = field.get('name', '')
        label = field.get('label', name)
        value = field.get('value', '')
        
        # Special handling for different field types
        if field.get('type') == 'select' and field.get('options'):
            # For select fields, display the label of the selected option
            selected_option = next((opt for opt in field.get('options', []) 
                                   if opt.get('value') == value), None)
            if selected_option:
                display_value = f"{value} ({selected_option.get('label', '')})"
            else:
                display_value = value
        else:
            display_value = value
            
        html_lines.extend([
            f"    <div class='form-group'>",
            f"      <label>{label}</label>",
            f"      <div class='value'>{display_value}</div>",
            f"    </div>"
        ])
            
    return html_lines

def _render_sections(sections_list, level=0):
    """Recursively render sections and their fields."""
    html_lines = []
    indent = "  " * (level + 2)
    
    for section in sections_list:
        if not isinstance(section, dict):
            continue
            
        title = section.get('title', '')
        section_id = section.get('id', '')
        
        # Start section
        html_lines.extend([
            f"{indent}<div class='section' id='{section_id}'>",
            f"{indent}  <div class='section-title'>{title}</div>"
        ])
        
        # Add fields
        fields = section.get('fields', [])
        if fields:
            field_lines = _render_fields(fields)
            # Add indentation
            field_lines = [f"{indent}  {line[4:]}" for line in field_lines]
            html_lines.extend(field_lines)
        
        # Add subsections
        subsections = section.get('sections', [])
        if subsections:
            html_lines.extend([f"{indent}  <div class='subsection'>"])
            html_lines.extend(_render_sections(subsections, level + 1))
            html_lines.extend([f"{indent}  </div>"])
        
        # Close section
        html_lines.append(f"{indent}</div>")
        
    return html_lines
