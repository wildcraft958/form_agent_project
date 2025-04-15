import re
import html
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from bs4 import BeautifulSoup
import json

class TemplateParser:
    """
    Parse RadReport templates into a structured form schema compatible with form processor.
    Handles various template formats including HTML and XML.
    """
    
    def __init__(self):
        """Initialize the template parser."""
        pass
    
    def parse_template(self, template_data):
        """
        Parse template data into a structured form schema.
        
        Args:
            template_data (dict): Template data from RadReport API
            
        Returns:
            dict: Structured form schema
        """
        # First check if we have template data
        if not template_data or "error" in template_data:
            return {"error": template_data.get("error", "Invalid template data")}
        
        # Extract metadata
        form_schema = {
            "_metadata": {
                "title": template_data.get("title", "Medical Report"),
                "description": template_data.get("description", ""),
                "template_id": template_data.get("id"),
                "version": template_data.get("version"),
                "organization": template_data.get("organization", {}).get("name", ""),
                "specialty": template_data.get("specialty", {}).get("name", "")
            }
        }
        
        # Get template content
        content = template_data.get("content", "")
        if not content:
            return {**form_schema, "error": "No template content found"}
        
        # Determine content type and parse accordingly
        content_type = self._determine_content_type(content)
        
        if content_type == "html":
            fields = self._parse_html_template(content)
        elif content_type == "xml":
            fields = self._parse_xml_template(content)
        else:
            fields = self._parse_text_template(content)
        
        # Add parsed fields to schema
        form_schema.update(fields)
        
        return form_schema
    
    def _determine_content_type(self, content):
        """
        Determine the content type of the template.
        
        Args:
            content (str): Template content
            
        Returns:
            str: Content type ("html", "xml", or "text")
        """
        content = content.strip()
        
        # Check for HTML
        if content.startswith("<!DOCTYPE") or content.startswith("<html") or "<body" in content:
            return "html"
        
        # Check for XML
        if content.startswith("<?xml") or content.startswith("<template") or content.startswith("<report"):
            return "xml"
        
        # Default to text
        return "text"
    
    def _parse_html_template(self, content):
        """
        Parse HTML template content.
        
        Args:
            content (str): HTML template content
            
        Returns:
            dict: Parsed form fields
        """
        fields = {}
        
        try:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find form elements
            inputs = soup.find_all(['input', 'select', 'textarea'])
            
            for i, input_elem in enumerate(inputs):
                # Extract field attributes
                field_type = input_elem.get('type', input_elem.name)
                field_name = input_elem.get('name') or input_elem.get('id')
                
                # Generate field name if not present
                if not field_name:
                    field_name = f"field_{i+1}"
                
                # Clean field name
                field_name = field_name.lower().replace(' ', '_').replace('-', '_')
                
                # Find associated label
                label_text = self._find_label_for_element(soup, input_elem)
                
                # Create field definition
                fields[field_name] = {
                    "type": field_type,
                    "label": label_text or field_name.replace('_', ' ').title(),
                    "value": input_elem.get('value', ''),
                    "required": input_elem.has_attr('required'),
                    "placeholder": input_elem.get('placeholder', '')
                }
                
                # Additional field-specific processing
                if field_type == 'select':
                    options = []
                    for option in input_elem.find_all('option'):
                        options.append({
                            'value': option.get('value', option.text),
                            'text': option.text
                        })
                    fields[field_name]['options'] = options
                
            # Look for div elements with field-like structure
            div_fields = self._extract_fields_from_divs(soup)
            fields.update(div_fields)
            
            # Look for bracketed fields in text
            text_fields = self._extract_bracketed_fields(soup.get_text())
            fields.update(text_fields)
            
        except Exception as e:
            print(f"HTML parsing error: {e}")
            # Fallback to text parsing if HTML parsing fails
            fields.update(self._parse_text_template(content))
        
        return fields
    
    def _parse_xml_template(self, content):
        """
        Parse XML template content.
        
        Args:
            content (str): XML template content
            
        Returns:
            dict: Parsed form fields
        """
        fields = {}
        
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Extract fields based on common XML structures
            # This is a simplified example - would need to be adapted to actual XML schema
            
            # Process form-field elements
            for i, field_elem in enumerate(root.findall(".//field")):
                field_name = field_elem.get('name') or field_elem.get('id')
                
                # Generate field name if not present
                if not field_name:
                    field_name = f"field_{i+1}"
                
                # Clean field name
                field_name = field_name.lower().replace(' ', '_').replace('-', '_')
                
                # Create field definition
                fields[field_name] = {
                    "type": field_elem.get('type', 'text'),
                    "label": field_elem.get('label', field_name.replace('_', ' ').title()),
                    "value": field_elem.get('default', ''),
                    "required": field_elem.get('required') == 'true',
                    "description": field_elem.findtext('description', '')
                }
                
                # Add options if present
                options_elem = field_elem.find('options')
                if options_elem is not None:
                    options = []
                    for option in options_elem.findall('option'):
                        options.append({
                            'value': option.get('value', option.text),
                            'text': option.text
                        })
                    fields[field_name]['options'] = options
            
            # If no fields found, try extracting from text content
            if not fields:
                all_text = self._extract_text_from_xml(root)
                text_fields = self._extract_bracketed_fields(all_text)
                fields.update(text_fields)
                
        except Exception as e:
            print(f"XML parsing error: {e}")
            # Fallback to text parsing if XML parsing fails
            fields.update(self._parse_text_template(content))
            
        return fields
    
    def _parse_text_template(self, content):
        """
        Parse plain text template content, looking for fields in brackets.
        
        Args:
            content (str): Text template content
            
        Returns:
            dict: Parsed form fields
        """
        return self._extract_bracketed_fields(content)
    
    def _extract_bracketed_fields(self, text):
        """
        Extract fields enclosed in brackets from text.
        
        Args:
            text (str): Text content
            
        Returns:
            dict: Extracted fields
        """
        fields = {}
        
        # Common patterns in medical templates
        patterns = [
            r'\[(.*?)\]',              # [Field Name]
            r'\{\{(.*?)\}\}',          # {{Field Name}}
            r'__(.*?)__',              # __Field Name__
            r'<%(.*?)%>',              # <%Field Name%>
            r'#(.*?)#'                 # #Field Name#
        ]
        
        field_names = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up field name
                field_label = match.strip()
                if not field_label or field_label.lower() in ['blank', 'empty']:
                    continue
                    
                field_name = field_label.lower().replace(' ', '_').replace('-', '_')
                
                # Prevent duplicates
                if field_name in field_names:
                    continue
                    
                field_names.add(field_name)
                
                # Determine field type based on content
                field_type = self._guess_field_type(field_label)
                
                # Add to fields
                fields[field_name] = {
                    "type": field_type,
                    "label": field_label,
                    "value": "",
                    "required": True,
                    "description": f"Enter {field_label.lower()}"
                }
                
                # Add options for select fields
                if field_type == "select":
                    fields[field_name]["options"] = self._extract_options_for_field(field_label)
        
        return fields
    
    def _guess_field_type(self, field_label):
        """
        Guess field type based on field label.
        
        Args:
            field_label (str): Field label
            
        Returns:
            str: Guessed field type
        """
        label_lower = field_label.lower()
        
        # Date fields
        if any(date_term in label_lower for date_term in ['date', 'dob', 'birth', 'admission']):
            return "date"
            
        # Number fields
        if any(num_term in label_lower for num_term in ['age', 'number', 'count', 'value', 'score', 'quantity']):
            return "number"
            
        # Email fields
        if 'email' in label_lower:
            return "email"
            
        # Text area fields
        if any(text_term in label_lower for text_term in ['description', 'findings', 'comments', 'impression', 'notes']):
            return "textarea"
            
        # Select fields
        if any(select_term in label_lower for select_term in ['type', 'status', 'laterality', 'gender', 'sex']):
            return "select"
            
        # Default to text
        return "text"
    
    def _extract_options_for_field(self, field_label):
        """
        Extract options for select fields based on common medical terminology.
        
        Args:
            field_label (str): Field label
            
        Returns:
            list: List of options
        """
        label_lower = field_label.lower()
        
        # Gender options
        if any(term in label_lower for term in ['gender', 'sex']):
            return [
                {"value": "male", "text": "Male"},
                {"value": "female", "text": "Female"},
                {"value": "other", "text": "Other"}
            ]
            
        # Yes/No options
        if any(term in label_lower for term in ['present', 'absent', 'positive', 'negative']):
            return [
                {"value": "yes", "text": "Yes"},
                {"value": "no", "text": "No"}
            ]
            
        # Laterality options
        if any(term in label_lower for term in ['laterality', 'side']):
            return [
                {"value": "right", "text": "Right"},
                {"value": "left", "text": "Left"},
                {"value": "bilateral", "text": "Bilateral"}
            ]
            
        # Default options (for testing)
        return [
            {"value": "option1", "text": "Option 1"},
            {"value": "option2", "text": "Option 2"},
            {"value": "option3", "text": "Option 3"}
        ]
    
    def _find_label_for_element(self, soup, element):
        """
        Find label text for a form element.
        
        Args:
            soup: BeautifulSoup object
            element: Form element
            
        Returns:
            str: Label text or empty string
        """
        # Check for id attribute
        elem_id = element.get('id')
        if elem_id:
            # Find label with matching 'for' attribute
            label = soup.find('label', attrs={'for': elem_id})
            if label:
                return label.get_text().strip()
        
        # Check for parent label
        parent = element.parent
        if parent and parent.name == 'label':
            # Extract label text, excluding the input element's text
            label_text = parent.get_text().strip()
            return label_text
        
        # Check for preceding sibling that might be a label
        prev_sibling = element.find_previous_sibling()
        if prev_sibling and prev_sibling.name == 'label':
            return prev_sibling.get_text().strip()
            
        return ""
    
    def _extract_fields_from_divs(self, soup):
        """
        Extract fields from div elements with field-like structure.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            dict: Extracted fields
        """
        fields = {}
        
        # Look for div elements with field-like classes or IDs
        field_divs = soup.find_all('div', attrs={'class': lambda c: c and any(term in c.lower() for term in ['field', 'form-group', 'input'])})
        
        for i, div in enumerate(field_divs):
            # Look for label inside div
            label_elem = div.find('label')
            if not label_elem:
                continue
                
            label_text = label_elem.get_text().strip()
            if not label_text:
                continue
                
            # Generate field name
            field_name = f"div_field_{i+1}"
            
            # Try to get better field name from data attributes
            for attr in div.attrs:
                if 'field' in attr.lower() or 'name' in attr.lower():
                    field_name = div[attr]
                    break
            
            # Clean field name
            field_name = field_name.lower().replace(' ', '_').replace('-', '_')
            
            # Determine field type
            field_type = "text"  # Default
            
            # Look for contained input elements to determine type
            input_elem = div.find(['input', 'select', 'textarea'])
            if input_elem:
                field_type = input_elem.get('type', input_elem.name)
            
            # Create field definition
            fields[field_name] = {
                "type": field_type,
                "label": label_text,
                "value": "",
                "required": False,
                "description": f"Enter {label_text.lower()}"
            }
        
        return fields
    
    def _extract_text_from_xml(self, root):
        """
        Extract all text content from XML.
        
        Args:
            root: XML root element
            
        Returns:
            str: Combined text content
        """
        all_text = ""
        
        for elem in root.iter():
            if elem.text:
                all_text += elem.text + " "
            if elem.tail:
                all_text += elem.tail + " "
                
        return all_text