import json
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel

console = Console()

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

def convert_html_to_json(html_content):
    """Convert HTML form content to JSON format."""
    try:
        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract form fields
        form_data = {}
        
        # Look for input elements
        input_tags = soup.find_all('input')
        for input_tag in input_tags:
            name = input_tag.get('name') or input_tag.get('id', f'unnamed_input_{len(form_data)}')
            input_type = input_tag.get('type', 'text')
            value = input_tag.get('value', '')
            placeholder = input_tag.get('placeholder', '')
            
            # Skip hidden inputs and submit buttons
            if input_type in ['hidden', 'submit', 'button']:
                continue
                
            # Add to form data
            form_data[name] = {
                'type': input_type,
                'value': value,
                'placeholder': placeholder,
                'required': input_tag.get('required') is not None
            }
        
        # Look for textarea elements
        textarea_tags = soup.find_all('textarea')
        for textarea_tag in textarea_tags:
            name = textarea_tag.get('name') or textarea_tag.get('id', f'unnamed_textarea_{len(form_data)}')
            value = textarea_tag.text.strip()
            placeholder = textarea_tag.get('placeholder', '')
            
            # Add to form data
            form_data[name] = {
                'type': 'textarea',
                'value': value,
                'placeholder': placeholder,
                'required': textarea_tag.get('required') is not None
            }
        
        # Look for select elements
        select_tags = soup.find_all('select')
        for select_tag in select_tags:
            name = select_tag.get('name') or select_tag.get('id', f'unnamed_select_{len(form_data)}')
            
            # Get options
            options = []
            for option_tag in select_tag.find_all('option'):
                option_value = option_tag.get('value', option_tag.text)
                option_text = option_tag.text.strip()
                selected = option_tag.get('selected') is not None
                options.append({
                    'value': option_value,
                    'text': option_text,
                    'selected': selected
                })
                
            # Add to form data
            form_data[name] = {
                'type': 'select',
                'options': options,
                'value': '',
                'required': select_tag.get('required') is not None
            }
        
        # Add labels
        label_tags = soup.find_all('label')
        for label_tag in label_tags:
            for_attr = label_tag.get('for')
            if for_attr and for_attr in form_data:
                form_data[for_attr]['label'] = label_tag.text.strip()
        
        # If no fields were found, try to extract structured content
        if not form_data:
            # Extract sections and fields from structured report
            sections = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'p'])
            for section in sections:
                # Skip empty sections
                if not section.text.strip():
                    continue
                
                # Create field name from section text
                field_name = section.text.strip().lower().replace(' ', '_')[:30]
                
                # Avoid duplicate keys
                counter = 1
                original_field_name = field_name
                while field_name in form_data:
                    field_name = f"{original_field_name}_{counter}"
                    counter += 1
                
                # Add to form data
                form_data[field_name] = {
                    'type': 'textarea',
                    'value': '',
                    'label': section.text.strip(),
                    'placeholder': f"Enter {section.text.strip()}",
                    'required': False
                }
        
        return form_data
        
    except Exception as e:
        console.print(Panel(f"[red]Error converting HTML to JSON: {e}[/red]", title="Conversion Error", border_style="red"))
        return None
