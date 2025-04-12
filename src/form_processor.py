import re
from datetime import datetime
from typing import Dict, Any, Optional, List

class EnhancedFormProcessor:
    """Process complex medical forms with nested sections and conditional logic"""
    
    def __init__(self, llm_interface):
        self.llm_interface = llm_interface
        self.form_schema = None
        self.form_data = {}
        self.context = {}
        self.max_attempts = 3
        self.medical_ranges = {
            "dosage": {
                "max_values": {
                    "mg": 5000,  # 5g max
                    "ml": 100,    # 100ml
                    "g": 5,
                    "mcg": 10000  # 10mg
                }
            },
            "duration": {"min": 1, "max": 365}
        }

    def load_schema(self, schema: Dict):
        """Load MRRT-compliant form schema"""
        self.form_schema = schema
        self._initialize_form_data(schema)

    def process_form(self):
        """Process form with nested sections and conditional fields"""
        if not self.form_schema:
            raise ValueError("No form schema loaded")
            
        self._process_sections(self.form_schema.get('sections', []))
        return self.form_data

    def _process_sections(self, sections: List, parent_path: str = ""):
        """Recursively process form sections"""
        for section in sections:
            if self._should_skip_section(section):
                continue
                
            section_path = f"{parent_path}/{section['id']}" if parent_path else section['id']
            print(f"\n=== {section.get('title', 'Section')} ===")
            self._process_fields(section.get('fields', []), section_path)
            self._process_sections(section.get('sections', []), section_path)

    def _process_fields(self, fields: List, section_path: str):
        """Process individual fields with contextual validation"""
        for field in fields:
            if self._should_skip_field(field):
                continue
            
            field_path = f"{section_path}/{field['name']}"
            self._handle_field(field, field_path)

    def _should_skip_section(self, section: Dict) -> bool:
        """Check section-level conditions"""
        if 'conditional' in section:
            dep_field = self.form_data.get(section['conditional']['depends_on'])
            return dep_field not in section['conditional']['values']
        return False

    def _should_skip_field(self, field: Dict) -> bool:
        """Check field-level conditions"""
        if 'conditional' in field:
            dep_field = self.form_data.get(field['conditional']['depends_on'])
            return dep_field not in field['conditional']['values']
        return False

    def _handle_field(self, field: Dict, field_path: str):
        """Handle field input with medical validation"""
        attempts = 0
        while attempts < self.max_attempts:
            prompt = self._create_field_prompt(field)
            print(f"Bot: {prompt}")
            
            user_input = input("User: ").strip()
            validation_result = self._validate_field(field, user_input)
            
            if validation_result["valid"]:
                self._store_valid_input(field, field_path, validation_result["value"])
                return
                
            print(f"Bot: {validation_result['message']}")
            attempts += 1

        print(f"Bot: Marking {field['name']} for review")
        self.form_data[field_path] = "[NEEDS REVIEW]"

    def _create_field_prompt(self, field: Dict) -> str:
        """Generate intelligent medical field prompts"""
        prompt = f"{field.get('label', 'Please provide information')}"
        
        if field.get('type') == 'select':
            options = "\n".join([f"{i+1}. {opt['label']}" for i, opt in enumerate(field.get('options', []))])
            prompt += f"\nOptions:\n{options}"
            
        if field.get('validation', {}).get('pattern'):
            prompt += f"\nFormat: {field['validation']['pattern']}"
            
        if field.get('coding'):
            codes = ", ".join([f"{sys}: {info['code']}" for sys, info in field['coding'].items()])
            prompt += f"\nMedical Codes: {codes}"
            
        return prompt

    def _validate_field(self, field: Dict, value: str) -> Dict:
        """Perform context-aware medical validation"""
        if field.get('required') and not value:
            return {"valid": False, "message": "This field is required"}
            
        validator = {
            'date': self._validate_date,
            'number': self._validate_number,
            'select': self._validate_select,
            'coded': self._validate_coded,
            'dosage': self._validate_dosage
        }.get(field.get('type'), self._validate_text)
        
        return validator(field, value)

    def _validate_dosage(self, field: Dict, value: str) -> Dict:
        """Validate medical dosage with unit-specific ranges"""
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$', value)
        if not match:
            return {"valid": False, "message": "Invalid dosage format. Use format: 500mg, 10ml"}
            
        amount, unit = match.groups()
        unit = unit.lower()
        max_values = self.medical_ranges['dosage']['max_values']
        
        if unit in max_values:
            try:
                num = float(amount)
                if num > max_values[unit]:
                    return {"valid": False, "message": f"Dosage exceeds maximum {max_values[unit]}{unit}"}
            except ValueError:
                return {"valid": False, "message": "Invalid numerical value"}
                
        return {"valid": True, "value": value}

    def _validate_date(self, field: Dict, value: str) -> Dict:
        """Validate date formats with medical context"""
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                datetime.strptime(value, fmt)
                return {"valid": True, "value": value}
            except ValueError:
                continue
        return {"valid": False, "message": f"Invalid date format. Use {field.get('validation', {}).get('pattern', 'MM/DD/YYYY')}"}

    def _validate_coded(self, field: Dict, value: str) -> Dict:
        """Validate against medical coding systems"""
        valid_codes = []
        for system, code_info in field.get('coding', {}).items():
            if value.lower() in [code_info['code'].lower(), code_info['display'].lower()]:
                valid_codes.append(f"{system}: {code_info['code']}")
                
        return {"valid": bool(valid_codes), "value": valid_codes[0]} if valid_codes else \
               {"valid": False, "message": f"Invalid code. Valid options: {', '.join(field['coding'].keys())}"}

    def _validate_select(self, field: Dict, value: str) -> Dict:
        """Validate select inputs with option triggers"""
        options = field.get('options', [])
        try:
            index = int(value) - 1
            if 0 <= index < len(options):
                selected = options[index]
                if 'trigger' in selected:
                    self.context[selected['trigger']] = selected['value']
                return {"valid": True, "value": selected['value']}
        except ValueError:
            pass
            
        for opt in options:
            if value == opt['value'] or value == opt.get('label'):
                if 'trigger' in opt:
                    self.context[opt['trigger']] = opt['value']
                return {"valid": True, "value": opt['value']}
                
        return {"valid": False, "message": f"Invalid selection. Choose from: {', '.join([opt['label'] for opt in options])}"}

    def _validate_number(self, field: Dict, value: str) -> Dict:
        """Validate numerical ranges for medical values"""
        try:
            num = float(value)
            min_val = field.get('validation', {}).get('min', float('-inf'))
            max_val = field.get('validation', {}).get('max', float('inf'))
            
            if num < min_val or num > max_val:
                return {"valid": False, "message": f"Value must be between {min_val} and {max_val}"}
                
            return {"valid": True, "value": num}
        except ValueError:
            return {"valid": False, "message": "Invalid numerical value"}

    def _validate_text(self, field: Dict, value: str) -> Dict:
        """Validate text inputs with medical context"""
        if self._appears_nonsensical(value):
            return {"valid": False, "message": "Input appears invalid. Please provide meaningful response"}
            
        if 'validation' in field and not re.match(field['validation'].get('pattern', ''), value):
            return {"valid": False, "message": field['validation'].get('message', "Invalid format")}
            
        return {"valid": True, "value": value}

    def _appears_nonsensical(self, value: str) -> bool:
        """Detect placeholder/nonsense medical inputs"""
        patterns = [
            r'idk', r'na', r'n/a', r'xxx', r'test',
            r'\d{10,}',  # Excessive numbers
            r'[^\w\s]{3,}'  # Too many special chars
        ]
        return any(re.search(p, value.lower()) for p in patterns)

    def _store_valid_input(self, field: Dict, path: str, value: Any):
        """Store validated input with context tracking"""
        self.form_data[path] = value
        self.context[field['name']] = value
        print(f"Bot: Saved {value} for {field.get('label', field['name'])}")

    def _initialize_form_data(self, schema: Dict):
        """Initialize form structure with default values"""
        self.form_data = {}
        for section in schema.get('sections', []):
            self._init_section(section)

    def _init_section(self, section: Dict, parent_path: str = ""):
        """Recursively initialize section data"""
        path = f"{parent_path}/{section['id']}" if parent_path else section['id']
        for field in section.get('fields', []):
            self.form_data[f"{path}/{field['name']}"] = None
        for subsection in section.get('sections', []):
            self._init_section(subsection, path)
