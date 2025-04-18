# src/form_processor.py
import re

class FormProcessor:
    def __init__(self, llm_interface):
        """Initialize the Form Processor with improved validation."""
        self.llm_interface = llm_interface
        self.form_data = None
        self.chat_history = []
        self.max_attempts = 3  # Maximum validation attempts before proceeding

    def load_form(self, form_json):
        """Load a form from JSON data."""
        self.form_data = form_json

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
                # Additional sample fields would be defined here
            }

        completed_form = dict(self.form_data)

        # Create system prompt describing the form
        system_prompt = self._create_system_prompt()

        # Process each field iteratively with enhanced user interaction
        for field_name, field_data in self.form_data.items():
            # Skip processing if field is hidden or system-managed
            if field_data.get('hidden', False):
                continue

            attempts = 0
            while attempts < self.max_attempts:
                # Generate descriptive field prompt
                field_prompt = self._create_radiology_field_prompt(field_name, field_data)

                # Display prompt to user
                print(f"Bot: {field_prompt}")

                # Get user input
                user_input = input("User: ")

                # Validate the user input
                is_valid, validation_message, processed_value = self._validate_radiology_input(field_name, field_data, user_input)

                if is_valid:
                    # Update the form with validated input
                    completed_form[field_name]['value'] = processed_value

                    # Add to chat history
                    self.chat_history.append({
                        'user': user_input,
                        'assistant': field_prompt,
                        'valid': True
                    })

                    # Confirm the input with the user
                    self._confirm_input(field_name, processed_value)
                    break
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
                        'error': validation_message
                    })

                # If max attempts reached, use a default value or proceed
                if attempts >= self.max_attempts:
                    print(f"Bot: I'll mark this question for review later. Let's continue with the form.")
                    completed_form[field_name]['value'] = "[NEEDS REVIEW]"
                    break

        return completed_form

    def _validate_input(self, field_name, field_data, user_input):
        """Validate user input based on field type and requirements."""
        field_type = field_data.get('type', 'text')

        # Handle empty input for required fields
        if field_data.get('required', False) and not user_input.strip():
            return False, "This field is required. Please provide a valid response.", None

        # Specific validation based on field type
        if field_type == 'select':
            return self._validate_select_input(field_data, user_input)
        elif field_type == 'date':
            return self._validate_date_input(user_input)
        elif field_type == 'number':
            return self._validate_number_input(user_input)
        elif field_type == 'email':
            return self._validate_email_input(user_input)
        elif field_type == 'textarea':
            # Textarea should have a minimum length to ensure meaningful content
            if len(user_input.strip()) < 5:
                return False, f"Please provide more detailed information for {field_name}.", None
            return True, None, user_input.strip()
        else:
            # Default text validation - avoid nonsensical inputs
            if self._appears_nonsensical(user_input):
                return False, f"The input '{user_input}' doesn't seem appropriate for {field_name}. Please provide a valid response.", None
            return True, None, user_input.strip()

    def _validate_radiology_input(self, field_name, field_data, user_input):
        """Additional validation specific to radiology fields."""
        # Check for common radiology-specific fields
        lower_field = field_name.lower()
        
        if 'impression' in lower_field or 'diagnosis' in lower_field:
            # Ensure the impression is sufficiently detailed
            if len(user_input.strip()) < 10:
                return False, "Please provide a more detailed clinical impression or diagnosis.", None
            return True, None, user_input.strip()
            
        elif 'finding' in lower_field or 'observation' in lower_field:
            # Ensure the findings are sufficiently detailed
            if len(user_input.strip()) < 10:
                return False, "Please provide more detailed findings or observations.", None
            return True, None, user_input.strip()
            
        elif 'measurement' in lower_field or 'size' in lower_field:
            # Validate that measurements include units
            if not re.search(r'\d+\.?\d*\s*(?:mm|cm|in)', user_input):
                return False, "Please include units (mm, cm) with measurements.", None
            return True, None, user_input.strip()
            
        # Default to standard validation
        return self._validate_input(field_name, field_data, user_input)

    def _validate_select_input(self, field_data, user_input):
        """Validate input for select-type fields with improved number selection."""
        options = field_data.get('options', [])
        option_values = [opt.get('value', '') for opt in options]
        option_texts = [opt.get('text', opt.get('value', '')) for opt in options]

        # Check if user entered a numeric selection
        try:
            # If user entered a number, convert to index (1-based)
            selection_index = int(user_input) - 1
            if 0 <= selection_index < len(options):
                return True, None, option_values[selection_index]
            else:
                return False, f"Please enter a number between 1 and {len(options)}.", None
        except ValueError:
            # If not a number, check if direct match with option text or value
            if user_input in option_values:
                return True, None, user_input
            elif user_input in option_texts:
                index = option_texts.index(user_input)
                return True, None, option_values[index]
            else:
                options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(option_texts)])
                return False, f"Invalid selection. Please choose one of the following options by entering the number:\n{options_str}", None

    def _validate_date_input(self, user_input):
        """Validate and process date input."""
        try:
            # Use datetime parsing to validate date
            from datetime import datetime
            
            # Try multiple date formats
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    date_obj = datetime.strptime(user_input, fmt)
                    return True, None, date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
                    
            # If no format matched
            return False, "Please enter a valid date in format MM/DD/YYYY or YYYY-MM-DD.", None
        except Exception:
            return False, "Invalid date format. Please enter a date in format MM/DD/YYYY.", None

    def _validate_number_input(self, user_input):
        """Validate and process numerical input."""
        try:
            # Strip any units or extra text
            num_str = re.search(r'\d+\.?\d*', user_input)
            if num_str:
                num_value = float(num_str.group())
                # Check if it's actually an integer
                if num_value.is_integer():
                    return True, None, int(num_value)
                return True, None, num_value
            return False, "Please enter a valid number.", None
        except Exception:
            return False, "Invalid number format. Please enter a numeric value.", None

    def _validate_email_input(self, user_input):
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, user_input):
            return True, None, user_input.lower()
        return False, "Please enter a valid email address.", None

    def _appears_nonsensical(self, user_input):
        """Check if input appears to be nonsensical or placeholder text."""
        nonsensical_patterns = [
            r'i don\'?t care',
            r'whatever',
            r'asdf',
            r'test',
            r'xxx',
            r'idk',
            r'na',
            r'n/?a',
            r'none',
            r'no',
            r'maybe'
        ]
        
        # If input is very short, check if it matches common nonsensical patterns
        if len(user_input) < 3 or any(re.search(pattern, user_input.lower()) for pattern in nonsensical_patterns):
            return True
        return False

    def _create_descriptive_field_prompt(self, field_name, field_data):
        """Create a detailed, informative prompt for a specific field."""
        field_type = field_data.get('type', 'text')
        placeholder = field_data.get('placeholder', '')
        description = field_data.get('description', '')
        
        # Format field name for display (convert snake_case to Title Case)
        display_name = field_data.get('label', " ".join(word.capitalize() for word in field_name.split('_')))
        
        # Build a detailed prompt
        prompt = f"Please provide a value for {display_name}."
        
        if description:
            prompt += f"\n{description}"
            
        if placeholder:
            prompt += f"\nFor example: '{placeholder}'"
            
        if field_type == 'select':
            options = field_data.get('options', [])
            if options:
                prompt += "\nPlease select one of the following options (enter the number):"
                for i, option in enumerate(options):
                    option_text = option.get('text', option.get('value', ''))
                    prompt += f"\n{i+1}. {option_text}"
        elif field_type == 'date':
            prompt += "\nPlease enter in format MM/DD/YYYY."
        elif field_type == 'textarea':
            prompt += "\nPlease provide a detailed response."
            
        if field_data.get('required', False):
            prompt += "\n(Required)"
        else:
            prompt += "\n(Optional)"
            
        return prompt

    def _create_radiology_field_prompt(self, field_name, field_data):
        """Create a radiology-specific field prompt."""
        # Format field name for display
        display_name = field_data.get('label', " ".join(word.capitalize() for word in field_name.split('_')))
        lower_field = field_name.lower()
        
        # Radiology-specific prompts
        if 'impression' in lower_field or 'diagnosis' in lower_field:
            return (f"Please provide your impression for this study ({display_name}). "
                    f"This should include your overall assessment and diagnosis.")
                    
        elif 'finding' in lower_field or 'observation' in lower_field:
            return (f"Please describe the findings for {display_name}. "
                    f"Include all relevant observations and measurements.")
                    
        elif 'comparison' in lower_field:
            return (f"If there are previous studies for comparison, "
                    f"please describe any changes since the prior examination ({display_name}).")
                    
        elif 'technique' in lower_field:
            return (f"Please describe the {display_name} used for this study.")
        
        elif 'clinical' in lower_field and 'history' in lower_field:
            return (f"Please provide the relevant clinical history for this patient.")
        
        elif 'recommendation' in lower_field:
            return (f"Please provide any follow-up recommendations based on this study.")
                    
        # Default to standard prompt
        return self._create_descriptive_field_prompt(field_name, field_data)

    def _confirm_input(self, field_name, value):
        """Confirm the captured input with the user."""
        display_name = " ".join(word.capitalize() for word in field_name.split('_'))
        print(f"Bot: I've recorded '{value}' for {display_name}. Thank you.")

    def _create_system_prompt(self):
        """Create a system prompt describing the form."""
        form_description = "You are filling out a radiology report form. "
        form_description += "The form has the following fields:\n"
        
        for field_name, field_data in self.form_data.items():
            if isinstance(field_data, dict):
                field_type = field_data.get('type', 'text')
                required = "Required" if field_data.get('required', False) else "Optional"
                
                if field_type == 'select':
                    options = [opt.get('text', opt.get('value', '')) for opt in field_data.get('options', [])]
                    options_str = ", ".join(options)
                    form_description += f"- {field_name}: {field_type.capitalize()} field ({required}). Options: {options_str}\n"
                else:
                    form_description += f"- {field_name}: {field_type.capitalize()} field ({required})\n"
        
        form_description += "\nPlease provide accurate medical information for the radiology report."
        
        return form_description
