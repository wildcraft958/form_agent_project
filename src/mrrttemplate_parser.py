# mrrttemplate_parser.py

import json
from bs4 import BeautifulSoup

class MRRTParser:
    """Parse MRRT HTML templates into structured form schema"""
    
    def __init__(self):
        self.schema = {
            "title": "",
            "sections": [],
            "fields": []
        }
        
    def parse_html(self, html_content):
        """Convert MRRT HTML template to structured JSON schema"""
        if not html_content or not isinstance(html_content, str):
            print("Error: Invalid HTML content provided")
            return self.schema
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            self._extract_metadata(soup)
            self._parse_sections(soup.find('body') or soup)
            
            # If no sections or fields were found, create default structure
            if not self.schema['sections'] and not self.schema['fields']:
                self._create_default_structure()
                
            return self.schema
        except Exception as e:
            print(f"Error parsing MRRT template: {e}")
            self._create_default_structure()
            return self.schema
            
    def _create_default_structure(self):
        """Create a default form structure when parsing fails"""
        self.schema["title"] = "Medical Report Template"
        
        # Add patient information section
        patient_section = {
            "id": "patient_info",
            "title": "Patient Information",
            "fields": [
                self._create_field("patient_name", "Patient Name", "text", True),
                self._create_field("patient_id", "Patient ID", "text", True),
                self._create_field("patient_dob", "Date of Birth", "date", True),
                self._create_field("patient_gender", "Gender", "select", True, 
                                   options=[{"value": "M", "label": "Male"}, 
                                            {"value": "F", "label": "Female"}, 
                                            {"value": "O", "label": "Other"}])
            ],
            "sections": []
        }
        
        # Add clinical information section
        clinical_section = {
            "id": "clinical_info",
            "title": "Clinical Information",
            "fields": [
                self._create_field("diagnosis", "Diagnosis", "textarea", True),
                self._create_field("symptoms", "Symptoms", "textarea", False),
                self._create_field("medical_history", "Medical History", "textarea", False)
            ],
            "sections": []
        }
        
        # Add medication section
        medication_section = {
            "id": "medication",
            "title": "Medication",
            "fields": [
                self._create_field("medication_name", "Medication Name", "text", True),
                self._create_field("dosage", "Dosage", "text", True),
                self._create_field("frequency", "Frequency", "select", True,
                                  options=[{"value": "daily", "label": "Once Daily"}, 
                                           {"value": "bid", "label": "Twice Daily"}, 
                                           {"value": "tid", "label": "Three Times Daily"}, 
                                           {"value": "qid", "label": "Four Times Daily"},
                                           {"value": "prn", "label": "As Needed"}]),
                self._create_field("duration", "Duration (days)", "number", True),
                self._create_field("special_instructions", "Special Instructions", "textarea", False)
            ],
            "sections": []
        }
        
        self.schema["sections"] = [patient_section, clinical_section, medication_section]
        
    def _create_field(self, name, label, field_type, required, options=None):
        """Helper to create field definitions"""
        field = {
            "name": name,
            "label": label,
            "type": field_type,
            "required": required
        }
        
        if options:
            field["options"] = options
            
        return field

    def _extract_metadata(self, soup):
        """Extract template metadata from Dublin Core"""
        try:
            # Try to get title
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                self.schema["title"] = title_tag.string.strip()
                
            # Look for Dublin Core metadata
            meta = soup.find('meta', {'name': 'DCTERMS'})
            if meta and meta.get('content'):
                try:
                    self.schema.update(json.loads(meta['content']))
                except json.JSONDecodeError:
                    pass
                    
            # Alternative title sources
            if not self.schema["title"]:
                h1 = soup.find('h1')
                if h1 and h1.string:
                    self.schema["title"] = h1.string.strip()
                    
        except Exception as e:
            print(f"Error extracting metadata: {e}")

    def _parse_sections(self, element):
        """Recursively parse template sections and fields"""
        if not element:
            return
            
        try:
            for child in element.children:
                if not child or isinstance(child, str) and not child.strip():
                    continue
                    
                if isinstance(child, str):
                    continue
                    
                if child.name == 'section':
                    section = self._create_section(child)
                    self.schema['sections'].append(section)
                elif child.name in ['input', 'select', 'textarea']:
                    field = self._create_field_from_element(child)
                    self.schema['fields'].append(field)
                elif child.name:  # Only process if it's a tag
                    self._parse_sections(child)
        except Exception as e:
            print(f"Error parsing sections: {e}")

    def _create_section(self, element):
        """Create nested section structure with MRRT attributes"""
        try:
            section = {
                "id": element.get('id', f"section_{len(self.schema['sections'])}"),
                "title": element.get('data-title', element.get('title', element.get('id', 'Section'))),
                "fields": [],
                "sections": [],
                "conditional": self._parse_conditionals(element)
            }
            
            # Process child elements
            for child in element.children:
                if isinstance(child, str) and not child.strip():
                    continue
                    
                if isinstance(child, str):
                    continue
                    
                if child.name == 'field' or child.name in ['input', 'select', 'textarea']:
                    section['fields'].append(self._create_field_from_element(child))
                elif child.name == 'section':
                    section['sections'].append(self._create_section(child))
                elif child.name and child.name not in ['script', 'style']:
                    # Look for fields in other elements
                    fields = child.find_all(['input', 'select', 'textarea'])
                    for field in fields:
                        section['fields'].append(self._create_field_from_element(field))
            
            return section
        except Exception as e:
            print(f"Error creating section: {e}")
            return {
                "id": f"section_{len(self.schema['sections'])}",
                "title": "Section",
                "fields": [],
                "sections": []
            }

    def _create_field_from_element(self, element):
        """Extract field properties from MRRT attributes"""
        try:
            # Get basic field info
            element_id = element.get('id') or element.get('name', '')
            field_name = element_id if element_id else f"field_{len(self.schema['fields'])}"
            
            # Find label - check for label tag or attribute
            label = ''
            if element.parent and element.parent.name == 'label':
                label = element.parent.get_text().strip()
            else:
                # Look for a label that references this field
                prev_sibling = element.find_previous_sibling('label')
                if prev_sibling and prev_sibling.get('for') == element_id:
                    label = prev_sibling.get_text().strip()
            
            # If still no label, use name or placeholder
            if not label:
                label = element.get('data-field-label', element.get('placeholder', field_name))
                
            # Format label if it's just a field name
            if label == field_name:
                label = field_name.replace('_', ' ').title()
                
            field = {
                "name": field_name,
                "type": element.get('data-field-type', element.get('type', 'text')),
                "label": label,
                "required": element.get('data-required', element.get('required', 'false')).lower() == 'true',
                "options": self._parse_options(element),
                "validation": self.extract_field_validation(element),
                "coding": self._parse_coding(element)
            }
            
            # Handle value lists for checkboxes/radio
            if 'data-values' in element.attrs:
                try:
                    field['values'] = json.loads(element['data-values'])
                except json.JSONDecodeError:
                    field['values'] = element['data-values'].split(',')
                    
            # Add LLM validation flag for complex medical fields
            if field["type"] in ['diagnosis', 'medication', 'procedure', 'finding']:
                field["llm_validation"] = True
                
            return field
        except Exception as e:
            print(f"Error creating field: {e}")
            return {
                "name": f"field_{len(self.schema['fields'])}",
                "type": "text",
                "label": "Field",
                "required": False
            }

    def _parse_options(self, element):
        """Parse dropdown/select options with value triggers"""
        try:
            options = []
            
            # Check for option elements
            option_elements = element.find_all('option')
            if option_elements:
                for opt in option_elements:
                    options.append({
                        "value": opt.get('value', opt.get_text().strip()),
                        "label": opt.get('data-label', opt.get_text().strip()),
                        "trigger": opt.get('data-trigger-field')
                    })
            
            # Check for data-options attribute
            elif element.get('data-options'):
                try:
                    options_data = json.loads(element['data-options'])
                    if isinstance(options_data, list):
                        options = options_data
                except json.JSONDecodeError:
                    # Try comma-separated format
                    for item in element['data-options'].split(','):
                        item = item.strip()
                        options.append({"value": item, "label": item})
                        
            # Add some default options if none found for select types
            elif element.name == 'select' and not options:
                if element.get('type') == 'gender' or 'gender' in element.get('id', '').lower() or 'gender' in element.get('name', '').lower():
                    options = [
                        {"value": "M", "label": "Male"},
                        {"value": "F", "label": "Female"},
                        {"value": "O", "label": "Other"}
                    ]
                elif element.get('type') == 'yesno' or 'yesno' in element.get('id', '').lower():
                    options = [
                        {"value": "Y", "label": "Yes"},
                        {"value": "N", "label": "No"}
                    ]
                    
            return options
        except Exception as e:
            print(f"Error parsing options: {e}")
            return []

    def _parse_conditionals(self, element):
        """Parse conditional display rules"""
        try:
            depends_on = element.get('data-depends-on')
            if depends_on:
                values = []
                if element.get('data-visible-values'):
                    try:
                        values = json.loads(element.get('data-visible-values', '[]'))
                    except json.JSONDecodeError:
                        values = [v.strip() for v in element.get('data-visible-values', '').split(',') if v.strip()]
                
                return {
                    "depends_on": depends_on,
                    "values": values
                }
            return None
        except Exception as e:
            print(f"Error parsing conditionals: {e}")
            return None

    def _parse_coding(self, element):
        """Parse medical coding systems (RadLex, SNOMED, LOINC) with enhanced error handling"""
        coding = {}
        try:
            # Direct coding information in attributes
            for attribute in element.attrs:
                if attribute.startswith('data-code-'):
                    system = attribute.replace('data-code-', '').upper()
                    code = element[attribute]
                    display = element.get(f'data-display-{system.lower()}', code)
                    coding[system] = {
                        "code": code,
                        "display": display
                    }
            
            # Find nested code elements
            for code in element.find_all('code'):
                system = code.get('scheme')
                if system:
                    system = system.upper()
                    coding[system] = {
                        "code": code.get('value', ''),
                        "display": code.get('meaning', code.get('value', ''))
                    }
                    
        except Exception as e:
            print(f"Error parsing coding information: {e}")
            
        return coding

    def extract_field_validation(self, element):
        """Extract validation rules from MRRT attributes with enhanced error handling"""
        validation = {}
        try:
            # Extract basic validation attributes
            if 'data-required' in element.attrs:
                validation['required'] = element['data-required'].lower() == 'true'
                
            if 'required' in element.attrs:
                validation['required'] = element.has_attr('required')
                
            if 'data-min' in element.attrs or 'data-minimum' in element.attrs:
                min_value = element.get('data-min', element.get('data-minimum'))
                try:
                    validation['min'] = float(min_value)
                except (ValueError, TypeError):
                    pass
                    
            if 'data-max' in element.attrs or 'data-maximum' in element.attrs:
                max_value = element.get('data-max', element.get('data-maximum'))
                try:
                    validation['max'] = float(max_value)
                except (ValueError, TypeError):
                    pass
                    
            if 'data-pattern' in element.attrs or 'data-format' in element.attrs:
                validation['pattern'] = element.get('data-pattern', element.get('data-format'))
                
            if 'data-error-message' in element.attrs or 'data-validation-message' in element.attrs:
                validation['message'] = element.get('data-error-message',
                                                   element.get('data-validation-message'))
            
            # Add field-specific validation based on type
            field_type = element.get('data-field-type', element.get('type', '')).lower()
            
            if field_type == 'date' and 'pattern' not in validation:
                validation['pattern'] = r'^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$'
                validation['message'] = 'Use format: YYYY-MM-DD or MM/DD/YYYY'
                
            elif field_type == 'email' and 'pattern' not in validation:
                validation['pattern'] = r'^[\w.-]+@[\w.-]+\.\w+$'
                validation['message'] = 'Enter a valid email address'
                
            elif field_type == 'phone' and 'pattern' not in validation:
                validation['pattern'] = r'^\+?[\d\s()-]{10,15}$'
                validation['message'] = 'Enter a valid phone number'
                
            elif field_type == 'numeric' or field_type == 'number':
                if 'min' not in validation:
                    validation['min'] = 0
            
            # Advanced medical validation flags
            validation['llm_validation'] = field_type in [
                'diagnosis', 'medication', 'procedure', 'finding',
                'impression', 'clinicalhistory', 'assessment'
            ]
            
        except Exception as e:
            print(f"Error extracting validation rules: {e}")
            
        return validation
