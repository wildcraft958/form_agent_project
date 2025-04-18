# src/JSON_converter.py
import json

def convert_json_to_html(json_data):
    """Convert JSON form data to HTML."""
    try:
        # Start building the HTML document
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "    <title>Filled Radiology Report Form</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        .form-container { max-width: 800px; margin: 0 auto; }",
            "        .form-field { margin-bottom: 15px; }",
            "        .field-label { font-weight: bold; margin-bottom: 5px; }",
            "        .field-value { padding: 5px; border: 1px solid #ddd; }",
            "        textarea.field-value { width: 100%; min-height: 100px; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <div class='form-container'>",
            "        <h1>Completed Radiology Report</h1>"
        ]
        
        # Add form fields
        for field_name, field_data in json_data.items():
            # Skip hidden fields
            if isinstance(field_data, dict) and field_data.get('hidden', False):
                continue
                
            # Format field name for display
            display_name = field_data.get('label', " ".join(word.capitalize() for word in field_name.split('_')))
            
            # Get field value
            if isinstance(field_data, dict):
                value = field_data.get('value', '')
                field_type = field_data.get('type', 'text')
            else:
                value = str(field_data)
                field_type = 'text'
                
            # Add field to HTML
            html_lines.append(f"        <div class='form-field'>")
            html_lines.append(f"            <div class='field-label'>{display_name}</div>")
            
            # Format value based on field type
            if field_type == 'textarea':
                html_lines.append(f"            <textarea class='field-value' readonly>{value}</textarea>")
            else:
                html_lines.append(f"            <div class='field-value'>{value}</div>")
                
            html_lines.append(f"        </div>")
        
        # Close HTML document
        html_lines.extend([
            "    </div>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_lines)
        
    except Exception as e:
        print(f"Error converting JSON to HTML: {e}")
        return None
