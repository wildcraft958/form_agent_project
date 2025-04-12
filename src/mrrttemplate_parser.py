# New file: mrrttemplate_parser.py
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
        soup = BeautifulSoup(html_content, 'html.parser')
        self._extract_metadata(soup)
        self._parse_sections(soup.find('body') or soup)
        return self.schema

    def _extract_metadata(self, soup):
        """Extract template metadata from Dublin Core"""
        meta = soup.find('meta', {'name': 'DCTERMS'})
        if meta and meta.get('content'):
            try:
                self.schema.update(json.loads(meta['content']))
            except json.JSONDecodeError:
                pass

    def _parse_sections(self, element):
        """Recursively parse template sections and fields"""
        for child in element.children:
            if isinstance(child, str):
                continue
                
            if child.name == 'section':
                section = self._create_section(child)
                self.schema['sections'].append(section)
            elif child.name in ['input', 'select', 'textarea']:
                field = self._create_field(child)
                self.schema['fields'].append(field)
            else:
                self._parse_sections(child)

    def _create_section(self, element):
        """Create nested section structure with MRRT attributes"""
        section = {
            "id": element.get('id', ''),
            "title": element.get('data-title', ''),
            "fields": [],
            "sections": [],
            "conditional": self._parse_conditionals(element)
        }
        
        # Process child elements
        for child in element.children:
            if isinstance(child, str):
                continue
                
            if child.name == 'field':
                section['fields'].append(self._create_field(child))
            elif child.name == 'section':
                section['sections'].append(self._create_section(child))
        
        return section

    def _create_field(self, element):
        """Extract field properties from MRRT attributes"""
        field = {
            "name": element.get('id') or element.get('name', ''),
            "type": element.get('data-field-type', 'text'),
            "label": element.get('data-field-label', ''),
            "required": element.get('data-required', 'false').lower() == 'true',
            "options": self._parse_options(element),
            "validation": {
                "pattern": element.get('data-validation-pattern'),
                "min": element.get('data-validation-min'),
                "max": element.get('data-validation-max')
            },
            "coding": self._parse_coding(element)
        }
        
        # Handle value lists for checkboxes/radio
        if 'data-values' in element.attrs:
            field['values'] = json.loads(element['data-values'])
            
        return field

    def _parse_options(self, element):
        """Parse dropdown/select options with value triggers"""
        return [{
            "value": opt.get('value'),
            "label": opt.get('data-label'),
            "trigger": opt.get('data-trigger-field')
        } for opt in element.find_all('option')]

    def _parse_conditionals(self, element):
        """Parse conditional display rules"""
        return {
            "depends_on": element.get('data-depends-on'),
            "values": json.loads(element.get('data-visible-values', '[]'))
        }

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

    def _create_field(self, element):
        """Extract field properties from MRRT attributes with enhanced validation"""
        field = {
            "name": element.get('id') or element.get('name', ''),
            "type": element.get('data-field-type', 'text'),
            "label": element.get('data-field-label', ''),
            "required": element.get('data-required', 'false').lower() == 'true',
            "options": self._parse_options(element),
            "validation": self.extract_field_validation(element),
            "coding": self._parse_coding(element)
        }

        # Add LLM validation flag for complex medical fields
        if field["type"] in ['diagnosis', 'medication', 'procedure', 'finding']:
            field["llm_validation"] = True

        # Handle value lists for checkboxes/radio
        if 'data-values' in element.attrs:
            try:
                field['values'] = json.loads(element['data-values'])
            except json.JSONDecodeError:
                field['values'] = element['data-values'].split(',')

        return field
