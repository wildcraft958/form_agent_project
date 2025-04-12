import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
from bs4 import BeautifulSoup

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
                    "ml": 100,   # 100ml
                    "g": 5,
                    "mcg": 10000  # 10mg
                }
            },
            "duration": {"min": 1, "max": 365}
        }
    
    def load_form(self, schema: Dict):
        """Alias for load_schema method for backward compatibility."""
        return self.load_schema(schema)
        
    def load_schema(self, schema: Dict):
        """Load MRRT-compliant form schema"""
        self.form_schema = schema
        self._initialize_form_data(schema)
    
    def process_form(self):
        """Process form with nested sections and conditional fields"""
        if not self.form_schema:
            raise ValueError("No form schema loaded")
        self._process_sections(self.form_schema.get('sections', []))
        self._process_global_fields(self.form_schema.get('fields', []))
        return self.form_data
    
    def _process_global_fields(self, fields: List):
        """Process fields defined at the global level"""
        if fields:
            print("\n=== Global Fields ===")
            self._process_fields(fields, "global")
    
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
        
        # Use LLM to enrich field with validation rules if needed
        field = self._enrich_field_with_llm_validation(field)
        
        while attempts < self.max_attempts:
            # Create prompt with field context and LLM reasoning
            prompt, reasoning = self._create_field_prompt_with_reasoning(field)
            
            # Display reasoning if available
            if reasoning:
                print(f"Bot reasoning: {reasoning}")
                
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
    
    def _enrich_field_with_llm_validation(self, field: Dict) -> Dict:
        """Use LLM to determine validation criteria for the field if needed."""
        # Skip if field already has validation rules
        if 'validation' in field and field['validation']:
            return field
        
        # Create enriched field with LLM's help
        field_copy = field.copy()
        
        # Prepare prompt for LLM
        prompt = f"""
        I need validation rules for a medical form field.
        
        Field name: {field['name']}
        Field label: {field.get('label', field['name'])}
        Field type: {field.get('type', 'text')}
        
        Please analyze this medical field and provide appropriate validation rules, including:
        1. Data type (text, number, date, etc.)
        2. Format pattern (regex if applicable)
        3. Minimum and maximum values (if applicable)
        4. Whether this field should be required
        5. Any medical context or constraints that should be considered
        
        Format your response as a JSON object with validation rules.
        """
        
        try:
            # Query LLM for validation rules
            validation_response = self.llm_interface.process_form(
                {"prompt": prompt},
                "Generate validation rules for this medical form field."
            )
            
            # Add validation rules to the field if they exist
            if isinstance(validation_response, dict) and 'validation' in validation_response:
                field_copy['validation'] = validation_response['validation']
                
                # Add helpful hints for users if provided
                if 'hint' in validation_response:
                    field_copy['hint'] = validation_response['hint']
        
        except Exception as e:
            print(f"Error enriching field with LLM validation: {str(e)}")
        
        return field_copy
    
    def _create_field_prompt_with_reasoning(self, field: Dict) -> tuple:
        """Generate intelligent medical field prompts with LLM reasoning"""
        # Basic prompt with field information
        prompt = f"{field.get('label', 'Please provide information')}"
        reasoning = ""
        
        # For select fields, format options
        if field.get('type') == 'select':
            options = "\n".join([f"{i+1}. {opt['label']}" for i, opt in enumerate(field.get('options', []))])
            prompt += f"\nOptions:\n{options}"
        
        # Include format information if available
        if field.get('validation', {}).get('pattern'):
            prompt += f"\nFormat: {field['validation']['pattern']}"
        
        # Include medical coding information if available
        if field.get('coding'):
            codes = ", ".join([f"{sys}: {info['code']}" for sys, info in field['coding'].items()])
            prompt += f"\nMedical Codes: {codes}"
            
        # Include hints from LLM validation
        if field.get('hint'):
            prompt += f"\nHint: {field['hint']}"
            
        # Use LLM to generate field-specific reasoning and context
        try:
            reasoning_prompt = f"""
            You are a medical assistant helping a user fill out a form.
            
            Field: {field.get('label', field['name'])}
            Type: {field.get('type', 'text')}
            
            Provide brief reasoning about what information is needed for this field and why it's important.
            Include any medical context or considerations that might help the user provide the correct information.
            Keep your response focused and under 100 words.
            """
            
            reasoning_response = self.llm_interface.process_form(
                {"prompt": reasoning_prompt},
                "Generate context for this field."
            )
            
            if isinstance(reasoning_response, dict) and 'reasoning' in reasoning_response:
                reasoning = reasoning_response['reasoning']
            elif isinstance(reasoning_response, str):
                reasoning = reasoning_response
                
        except Exception as e:
            print(f"Error generating field reasoning: {str(e)}")
            
        return prompt, reasoning
    
    def _validate_field(self, field: Dict, value: str) -> Dict:
        """Perform context-aware medical validation"""
        # Check if field is required but empty
        if field.get('required') and not value:
            return {"valid": False, "message": "This field is required"}
        
        # If empty value provided for non-required field
        if not value:
            return {"valid": True, "value": ""}
            
        # Select appropriate validator based on field type
        validator = {
            'date': self._validate_date,
            'number': self._validate_number,
            'select': self._validate_select,
            'coded': self._validate_coded,
            'dosage': self._validate_dosage,
            'email': self._validate_email,
            'phone': self._validate_phone
        }.get(field.get('type'), self._validate_text)
        
        # Apply selected validator
        result = validator(field, value)
        
        # If standard validation passes but field has llm_validation flag, 
        # use LLM to validate complex medical content
        if result["valid"] and field.get('llm_validation', False):
            llm_result = self._validate_with_llm(field, value)
            if not llm_result["valid"]:
                return llm_result
                
        return result
    
    def _validate_with_llm(self, field: Dict, value: str) -> Dict:
        """Use LLM to perform complex medical content validation"""
        prompt = f"""
        Validate this input for the medical field '{field.get('label', field['name'])}':
        
        Input: {value}
        Field type: {field.get('type', 'text')}
        
        Is this input medically valid, reasonable, and appropriate for this field?
        Consider:
        1. Medical accuracy and plausibility
        2. Formatting and syntax correctness
        3. Potential contraindications or errors
        
        Return a JSON object with:
        {{
            "valid": true/false,
            "message": "explanation if invalid"
        }}
        """
        
        try:
            validation_response = self.llm_interface.process_form(
                {"prompt": prompt},
                "Validate this medical field input."
            )
            
            if isinstance(validation_response, dict) and 'valid' in validation_response:
                return validation_response
                
            return {"valid": True, "value": value}
            
        except Exception as e:
            print(f"Error in LLM validation: {str(e)}")
            return {"valid": True, "value": value}
    
    def _validate_email(self, field: Dict, value: str) -> Dict:
        """Validate email format"""
        email_pattern = r'^[\w.-]+@[\w.-]+\.\w+$'
        if not re.match(email_pattern, value):
            return {"valid": False, "message": "Please enter a valid email address"}
        return {"valid": True, "value": value}
    
    def _validate_phone(self, field: Dict, value: str) -> Dict:
        """Validate phone number format"""
        # Remove common phone number formatting characters
        cleaned = re.sub(r'[\s()-]', '', value)
        # Check if result is a valid phone number (at least 10 digits)
        if not re.match(r'^\+?\d{10,15}$', cleaned):
            return {"valid": False, "message": "Please enter a valid phone number"}
        return {"valid": True, "value": value}
    
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
        
        if 'validation' in field and 'pattern' in field['validation'] and not re.match(field['validation']['pattern'], value):
            return {"valid": False, "message": field['validation'].get('message', "Invalid format")}
        
        return {"valid": True, "value": value}
    
    def _appears_nonsensical(self, value: str) -> bool:
        """Detect placeholder/nonsense medical inputs"""
        patterns = [
            r'\bidk\b', r'\bna\b', r'\bn/a\b', r'\bxxx\b', r'\btest\b',
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
        # Process global fields
        for field in schema.get('fields', []):
            self.form_data[f"global/{field['name']}"] = None
            
        # Process sections
        for section in schema.get('sections', []):
            self._init_section(section)
    
    def _init_section(self, section: Dict, parent_path: str = ""):
        """Recursively initialize section data"""
        path = f"{parent_path}/{section['id']}" if parent_path else section['id']
        
        for field in section.get('fields', []):
            self.form_data[f"{path}/{field['name']}"] = None
            
        for subsection in section.get('sections', []):
            self._init_section(subsection, path)
