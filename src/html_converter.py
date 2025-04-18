from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel

console = Console()

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
