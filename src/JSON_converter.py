# src/JSON_converter.py

import json

def convert_json_to_html(json_data):
    """Convert JSON form data to HTML with highlighting for review fields."""
    try:
        # Start building the HTML document
        html_lines = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "    <title>Completed Medical Form</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }",
            "        h1 { color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }",
            "        h2 { color: #3498db; margin-top: 30px; }",
            "        .field { margin-bottom: 20px; }",
            "        .field-label { font-weight: bold; color: #555; }",
            "        .field-value { margin-top: 5px; }",
            "        .needs-review { background-color: #ffe6e6; padding: 10px; border-left: 3px solid #ff0000; }",
            "        .review-reason { color: #dc3545; font-style: italic; }",
            "        .review-summary { background-color: #f2f2f2; padding: 15px; margin-top: 30px; border-radius: 5px; }",
            "    </style>",
            "</head>",
            "<body>",
            "    <h1>Completed Medical Form</h1>"
        ]
        
        # List to collect fields that need review
        review_fields = []
        
        # Add each field from the JSON data
        for field_name, field_data in json_data.items():
            # Skip hidden fields and system fields (starting with '_')
            if isinstance(field_data, dict) and (field_data.get('hidden', False) or field_name.startswith('_')):
                continue
                
            # Get field values
            label = field_data.get('label', " ".join(word.capitalize() for word in field_name.split('_')))
            value = field_data.get('value', '')
            
            # Check if field needs review
            needs_review = field_data.get('needs_review', False)
            review_class = "needs-review" if needs_review else ""
            review_reason = field_data.get('review_reason', '')
            
            if needs_review:
                review_fields.append((label, review_reason))
            
            # Add the field to the HTML
            html_lines.extend([
                f"    <div class='field {review_class}'>",
                f"        <div class='field-label'>{label}:</div>",
                f"        <div class='field-value'>{value}</div>"
            ])
            
            # Add review reason if needed
            if needs_review:
                html_lines.append(f"        <div class='review-reason'>{review_reason}</div>")
                
            html_lines.append("    </div>")
        
        # Add a summary of fields needing review if any
        if review_fields:
            html_lines.extend([
                "    <div class='review-summary'>",
                "        <h2>Fields Needing Review</h2>",
                "        <ul>"
            ])
            
            for label, reason in review_fields:
                html_lines.append(f"            <li><strong>{label}</strong>: {reason}</li>")
                
            html_lines.extend([
                "        </ul>",
                "    </div>"
            ])
        
        # Close the HTML document
        html_lines.extend([
            "</body>",
            "</html>"
        ])
        
        return '\n'.join(html_lines)
    
    except Exception as e:
        print(f"Error converting JSON to HTML: {e}")
        return None
