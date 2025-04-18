# src/form_processor.py

import re
import json

class FormProcessor:
    def __init__(self, llm_interface, form_context=None):
        """Initialize the Form Processor with improved validation and context."""
        self.llm_interface = llm_interface
        self.form_data = None
        self.chat_history = []
        self.max_attempts = 3  # Maximum validation attempts before proceeding
        self.form_context = form_context  # Add form context
        self.needs_review = []  # List of fields that need human review
    
    def load_form(self, form_json):
        """Load a form from JSON data."""
        self.form_data = form_json
    
    def _get_last_exchanges(self, num_exchanges=2):
        """Get the last N exchanges for context."""
        if not self.chat_history or len(self.chat_history) == 0:
            return []
        return self.chat_history[-min(num_exchanges, len(self.chat_history)):]
    
    def process_form(self):
        """Process the form with interactive validation and user-friendly prompts."""
        if not self.form_data:
            print("Warning: No form data found. Creating sample data for testing.")
            self.form_data = {
                "patient_name": {
                    "type": "text",
                    "value": "",
                    "placeholder": "Enter patient name",
                    "required": True,
                    "description": "Full name as it appears on medical records"
                }
            }
            
        # Initialize form with form context if available
        completed_form = dict(self.form_data)
        
        # Start conversation with form context if available
        if self.form_context:
            print(f"Bot: {self.form_context}\n")
            
            # Add to chat history
            self.chat_history.append({
                'user': '',
                'assistant': self.form_context,
                'is_context': True
            })
        
        # Process each field iteratively with enhanced user interaction
        for field_name, field_data in self.form_data.items():
            # Skip processing if field is hidden or system-managed
            if field_data.get('hidden', False) or field_name.startswith('_'):
                continue
                
            attempts = 0
            valid = False
            
            while attempts < self.max_attempts and not valid:
                # Generate field prompt with reasoning from chat history
                field_prompt, last_exchanges = self._create_interactive_field_prompt(field_name, field_data)
                
                # Display prompt to user
                print(f"Bot: {field_prompt}")
                
                # Get user input
                user_input = input("User: ")
                
                # Save raw input in case validation fails
                raw_input = user_input
                
                # Validate with LLM reasoning
                is_valid, validation_message, processed_value = self._validate_input_with_llm(
                    field_name, field_data, user_input, last_exchanges
                )
                
                if is_valid:
                    # Update the form with validated input
                    completed_form[field_name]['value'] = processed_value
                    
                    # Add to chat history
                    self.chat_history.append({
                        'user': user_input,
                        'assistant': field_prompt,
                        'valid': True,
                        'field': field_name,
                        'value': processed_value
                    })
                    
                    # Confirm the input with the user
                    self._confirm_input(field_name, processed_value)
                    valid = True
                else:
                    # Increment attempt counter
                    attempts += 1
                    
                    # Show validation error
                    print(f"Bot: {validation_message}")
                    
                    # Add failed attempt to chat history
                    self.chat_history.append({
                        'user': user_input,
                        'assistant': field_prompt,
                        'valid': False,
                        'field': field_name,
                        'error': validation_message
                    })
            
            # If max attempts reached, flag for human review
            if not valid:
                print(f"Bot: I'll mark this question for review later. Let's continue with the form.")
                completed_form[field_name]['value'] = raw_input
                completed_form[field_name]['needs_review'] = True
                completed_form[field_name]['review_reason'] = "Maximum validation attempts reached"
                self.needs_review.append(field_name)
                
                # Add to chat history
                self.chat_history.append({
                    'user': raw_input,
                    'assistant': "This field needs human review.",
                    'valid': False,
                    'field': field_name,
                    'flagged': True
                })
        
        # Add review status to the completed form
        if self.needs_review:
            completed_form['_review_status'] = {
                'fields_needing_review': self.needs_review,
                'hidden': True
            }
        
        return completed_form
    
    def _create_interactive_field_prompt(self, field_name, field_data):
        """Create a detailed, informative prompt for a specific field with reasoning."""
        # Get the last few exchanges for context
        last_exchanges = self._get_last_exchanges()
        
        # Determine if the field is required
        is_required = field_data.get('required', False)
        required_text = "(Required)" if is_required else "(Optional)"
        
        field_type = field_data.get('type', 'text')
        display_name = field_data.get('label', self._format_field_name(field_name))
        description = field_data.get('description', '')
        
        # Build prompt based on field type
        if 'impression' in field_name.lower() or 'diagnosis' in field_name.lower():
            prompt = f"Please provide your impression for this study ({display_name}). "\
                    f"This should include your overall assessment and diagnosis. {required_text}"
                    
        elif 'finding' in field_name.lower() or 'observation' in field_name.lower():
            prompt = f"Please describe the findings for {display_name}. "\
                    f"Include all relevant observations and measurements. {required_text}"
                    
        elif 'comparison' in field_name.lower():
            prompt = f"If there are previous studies for comparison, "\
                    f"please describe any changes since the prior examination ({display_name}). {required_text}"
                    
        elif 'technique' in field_name.lower():
            prompt = f"Please describe the {display_name} used for this study. {required_text}"
                    
        elif 'clinical' in field_name.lower():
            prompt = f"Please provide a value for {display_name}. "\
                    f"{description} {required_text}"
        else:
            # Default prompt construction
            prompt = f"Please provide a value for {display_name}. "\
                    f"{description} {required_text}"
        
        # Add options for select fields
        if field_type == 'select':
            options = field_data.get('options', [])
            if options:
                prompt += "\nPlease select one of the following options (enter the number):"
                for i, option in enumerate(options):
                    option_text = option.get('text', option.get('value', ''))
                    prompt += f"\n{i+1}. {option_text}"
        
        # Return the prompt and context
        return prompt, last_exchanges
    
    def _format_field_name(self, field_name):
        """Format field name for display (convert snake_case to Title Case)."""
        return " ".join(word.capitalize() for word in field_name.split('_'))
    
    def _validate_input_with_llm(self, field_name, field_data, user_input, last_exchanges):
        """Validate user input using LLM reasoning based on field type and requirements."""
        field_type = field_data.get('type', 'text')
        is_required = field_data.get('required', False)
        display_name = field_data.get('label', self._format_field_name(field_name))
        
        # Handle empty input for required fields
        if is_required and not user_input.strip():
            return False, f"This field is required. Please provide a valid value for {display_name}.", None
        
        # For select fields, use dedicated validation
        if field_type == 'select':
            return self._validate_select_input(field_data, user_input)
        
        # Prepare validation prompt for LLM
        validation_prompt = {
            "field_name": field_name,
            "field_type": field_type,
            "display_name": display_name,
            "is_required": is_required,
            "user_input": user_input,
            "field_description": field_data.get('description', ''),
            "previous_exchanges": [
                {"role": ex.get('user', ''), "content": ex.get('assistant', '')} 
                for ex in last_exchanges
            ],
            "validation_rules": self._get_validation_rules(field_name, field_type)
        }
        
        # Call LLM for validation
        try:
            validation_result = self.llm_interface.validate_input(validation_prompt)
            
            # Parse validation result
            if isinstance(validation_result, dict):
                is_valid = validation_result.get('is_valid', False)
                message = validation_result.get('message', '')
                processed_value = validation_result.get('processed_value', user_input)
                
                return is_valid, message, processed_value
            else:
                # Fallback to basic validation if LLM validation fails
                return self._basic_validation(field_name, field_data, user_input)
        
        except Exception as e:
            print(f"Error during LLM validation: {str(e)}")
            # Fallback to basic validation
            return self._basic_validation(field_name, field_data, user_input)
    
    def _get_validation_rules(self, field_name, field_type):
        """Get validation rules based on field name and type."""
        rules = {}
        
        # Common validation rules by field type
        type_rules = {
            "date": {
                "format": "MM/DD/YYYY",
                "min_year": 1900,
                "max_year": 2100
            },
            "number": {
                "min": 0,
                "allow_decimals": True
            },
            "email": {
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            }
        }
        
        # Add type-specific rules
        if field_type in type_rules:
            rules.update(type_rules[field_type])
        
        # Field-specific rules based on field name
        if "name" in field_name.lower():
            rules["min_length"] = 2
            rules["max_length"] = 100
            rules["pattern"] = r"^[A-Za-z\s\-'.]+$"
            rules["description"] = "Name should contain only letters, spaces, hyphens, and apostrophes."
        
        elif "diagnosis" in field_name.lower() or "impression" in field_name.lower():
            rules["min_length"] = 10
            rules["description"] = "Medical diagnosis should be detailed and specific."
            
        elif "clinical" in field_name.lower() and "information" in field_name.lower():
            rules["min_length"] = 5
            rules["description"] = "Clinical information should describe the patient's symptoms or clinical context."
            
        return rules
    
    def _basic_validation(self, field_name, field_data, user_input):
        """Perform basic validation as fallback."""
        field_type = field_data.get('type', 'text')
        is_required = field_data.get('required', False)
        display_name = field_data.get('label', self._format_field_name(field_name))
        
        # Required field validation
        if is_required and not user_input.strip():
            return False, f"This field is required. Please provide a value for {display_name}.", None
            
        # Validate based on field type
        if field_type == 'date':
            # Basic date validation
            if not re.match(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', user_input):
                return False, f"Please enter a valid date in MM/DD/YYYY format.", None
        
        elif field_type == 'number':
            # Basic number validation
            if not re.match(r'^-?\d+(\.\d+)?$', user_input):
                return False, f"Please enter a valid number.", None
        
        elif field_type == 'email':
            # Basic email validation
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', user_input):
                return False, f"Please enter a valid email address.", None
                
        # Length validation for text/textarea
        if field_type in ['text', 'textarea']:
            # Check for extremely short inputs
            if len(user_input.strip()) < 2:
                return False, f"Please provide more detailed information for {display_name}.", None
                
            # Check for nonsensical inputs
            if self._appears_nonsensical(user_input):
                return False, f"Your input doesn't seem appropriate for {display_name}. Please provide a meaningful response.", None
        
        return True, None, user_input.strip()
    
    def _validate_select_input(self, field_data, user_input):
        """Validate input for select-type fields with improved option presentation."""
        options = field_data.get('options', [])
        option_values = [opt.get('value', '') for opt in options]
        option_texts = [opt.get('text', opt.get('value', '')) for opt in options]
        
        # Check if user entered a numeric selection
        try:
            # If user entered a number, convert to index (1-based)
            selection_index = int(user_input) - 1
            if 0 <= selection_index < len(options):
                # Return the value if available, otherwise the text
                value = option_values[selection_index] if option_values[selection_index] else option_texts[selection_index]
                return True, None, value
            else:
                return False, f"Please enter a number between 1 and {len(options)}.", None
        except ValueError:
            # If not a number, check if direct match with option text or value
            if user_input in option_values:
                return True, None, user_input
            elif user_input in option_texts:
                index = option_texts.index(user_input)
                return True, None, option_values[index] if option_values[index] else user_input
            else:
                # Check for partial matches
                matches = []
                for i, text in enumerate(option_texts):
                    if user_input.lower() in text.lower():
                        matches.append((i, text))
                
                if len(matches) == 1:
                    # One clear match
                    index = matches[0][0]
                    return True, None, option_values[index] if option_values[index] else option_texts[index]
                elif len(matches) > 1:
                    # Multiple matches, ask for clarification
                    match_options = "\n".join([f"{i+1}. {text}" for i, text in enumerate([m[1] for m in matches])])
                    return False, f"Multiple matches found. Please select one of the following:\n{match_options}", None
                else:
                    # No matches
                    options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(option_texts)])
                    return False, f"Invalid selection. Please choose one of the following options by entering the number:\n{options_str}", None
    
    def _appears_nonsensical(self, user_input):
        """Check if input appears to be nonsensical or placeholder text."""
        nonsensical_patterns = [
            r'^[a-z]{1,3}$',  # Very short inputs like "a", "ab", "abc"
            r'asdf|qwerty|zxcv',  # Keyboard patterns
            r'^test|testing|dummy$',  # Test inputs
            r'^[x]+$',  # Repeating x's
            r'^(whatever|idk|idc|no|na|n/a|none)$'  # Common placeholder responses
        ]
        
        # If input is very short and appears nonsensical
        return any(re.search(pattern, user_input.lower()) for pattern in nonsensical_patterns)
    
    def _confirm_input(self, field_name, value):
        """Confirm the captured input with the user."""
        display_name = self._format_field_name(field_name)
        print(f"Bot: I've recorded '{value}' for {display_name}. Thank you.")
