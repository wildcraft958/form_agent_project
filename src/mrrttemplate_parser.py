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
        """Parse medical coding systems (RadLex, SNOMED, LOINC)"""
        coding = {}
        for code in element.find_all('code'):
            system = code.get('scheme')
            if system in ['RadLex', 'SNOMEDCT', 'LOINC']:
                coding[system] = {
                    "code": code.get('value'),
                    "display": code.get('meaning')
                }
        return coding
