# src/radreport_converter.py
from typing import Dict, Any
import html
import re
from bs4 import BeautifulSoup

class RadReportConverter:
    """
    Class to convert RadReport templates to the format expected by the form processor.
    """
    
    def __init__(self):
        """Initialize the RadReportConverter class."""
        pass
    
    def convert_template_to_form(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert RadReport template to the form format expected by the form processor.
        
        Args:
            template_data: Template data from RadReport API
            
        Returns:
            Dict containing form data in the expected format
        """
        # Extract template content from API response
        template_html = template_data.get('template', '')
        
        # Parse HTML content
        soup = BeautifulSoup(template_html, 'html.parser')
        
        # Initialize form data
        form_data = {}
        
        # Extract form fields
        sections = soup.find_all(['section', 'div'], {'class': 'section'})
        
        for section in sections:
            section_title = section.find(['h1', 'h2', 'h3', 'h4', 'div', 'span'], {'class': 'title'})
            section_name = section_title.get_text(strip=True) if section_title else 'Unnamed Section'
            
            # Find all input elements in this section
            inputs = section.find_all(['input', 'select', 'textarea'])
            
            for input_elem in inputs:
                field_id = input_elem.get('id', '')
                field_name = self._sanitize_field_name(field_id)
                field_type = input_elem.get('type', input_elem.name)
                
                # Skip hidden fields
                if field_type == 'hidden':
                    continue
                
                # Find label for this input
                label = None
                label_elem = section.find('label', {'for': field_id})
                if label_elem:
                    label = label_elem.get_text(strip=True)
                
                # Determine field type and options
                if input_elem.name == 'select':
                    options = []
                    for option in input_elem.find_all('option'):
                        option_value = option.get('value', option.get_text(strip=True))
                        option_text = option.get_text(strip=True)
                        options.append({'value': option_value, 'text': option_text})
                    
                    form_data[field_name] = {
                        'type': 'select',
                        'value': '',
                        'label': label or field_name,
                        'options': options,
                        'section': section_name,
                        'description': f"{section_name}: {label or field_name}" if label else field_name,
                        'required': input_elem.get('required') is not None
                    }
                elif field_type == 'checkbox' or field_type == 'radio':
                    # Group checkboxes/radios with the same name
                    if field_name in form_data:
                        if 'options' not in form_data[field_name]:
                            form_data[field_name]['options'] = []
                        
                        form_data[field_name]['options'].append({
                            'value': input_elem.get('value', 'on'),
                            'text': label or input_elem.get('value', 'on')
                        })
                    else:
                        form_data[field_name] = {
                            'type': field_type,
                            'value': '',
                            'label': label or field_name,
                            'options': [{
                                'value': input_elem.get('value', 'on'),
                                'text': label or input_elem.get('value', 'on')
                            }],
                            'section': section_name,
                            'description': f"{section_name}: {label or field_name}" if label else field_name,
                            'required': input_elem.get('required') is not None
                        }
                else:
                    placeholder = input_elem.get('placeholder', '')
                    
                    form_data[field_name] = {
                        'type': field_type if field_type != 'text' else input_elem.name,
                        'value': '',
                        'label': label or field_name,
                        'placeholder': placeholder,
                        'section': section_name,
                        'description': f"{section_name}: {label or field_name}" if label else field_name,
                        'required': input_elem.get('required') is not None
                    }
        
        # Add form metadata
        form_data['_metadata'] = {
            'title': template_data.get('title', 'RadReport Template'),
            'description': template_data.get('description', ''),
            'author': template_data.get('author', ''),
            'id': template_data.get('id', ''),
            'created': template_data.get('created', ''),
            'updated': template_data.get('updated', '')
        }
        
        return form_data
    
    def _sanitize_field_name(self, field_id: str) -> str:
        """
        Sanitize field ID to create a valid field name.
        
        Args:
            field_id: Field ID from the template
            
        Returns:
            Sanitized field name
        """
        # Remove non-alphanumeric characters except underscores
        field_name = re.sub(r'[^a-zA-Z0-9_]', '_', field_id)
        
        # Ensure the field name starts with a letter
        if field_name and not field_name[0].isalpha():
            field_name = 'field_' + field_name
            
        return field_name
