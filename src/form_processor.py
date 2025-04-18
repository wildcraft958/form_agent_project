import re
import json
from rich.console import Console
from rich.panel import Panel

console = Console()

class FormProcessor:
    def __init__(self, llm_interface, form_context=None):
        """Initialize the Form Processor with improved validation and context."""
        self.llm_interface = llm_interface
        self.form_data = None
        self.chat_history = []
        self.max_attempts = 3
        self.form_context = form_context
        self.needs_review = []
        
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
            console.print(Panel("[yellow]Warning: No form data found. Creating sample data for testing.[/yellow]", border_style="yellow"))
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
            console.print(Panel(f"{self.form_context}", title="Form Context", border_style="cyan"))
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
            
            # Generate field prompt with examples and guidance
            field_prompt, last_exchanges = self._create_interactive_field_prompt(field_name, field_data)
            
            while attempts < self.max_attempts and not valid:
                # Display prompt to user (only on first attempt or if prompt changes)
                if attempts == 0:
                    console.print(Panel(field_prompt, title="Bot", border_style="blue"))
                
                # Get user input
                user_input = console.input("[bold magenta]User:[/bold magenta] ")
                
                # Check if user wants to skip optional field
                is_required = field_data.get('required', False)
                if not is_required and self._is_skip_request(user_input):
                    completed_form[field_name]['value'] = "Not specified"
                    console.print(Panel(f"I've marked {self._format_field_name(field_name)} as 'Not specified'. Moving on.", border_style="cyan"))
                    self.chat_history.append({
                        'user': user_input,
                        'assistant': f"I've marked {self._format_field_name(field_name)} as 'Not specified'. Moving on.",
                        'field': field_name,
                        'value': "Not specified"
                    })
                    valid = True
                    break
                
                # Save raw input in case validation fails
                raw_input = user_input
                
                # Validate with improved context awareness
                is_valid, validation_message, processed_value = self._validate_input_with_context(
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
                    console.print(Panel(f"I've recorded '{processed_value}' for {self._format_field_name(field_name)}. Thank you.", border_style="green"))
                    valid = True
                else:
                    # Increment attempt counter
                    attempts += 1
                    
                    # Show validation error with guidance for correction
                    guidance = self._generate_guidance(field_name, field_data, user_input, attempts)
                    console.print(Panel(f"{validation_message} {guidance}", border_style="red"))
                    
                    # Add failed attempt to chat history
                    self.chat_history.append({
                        'user': user_input,
                        'assistant': f"{validation_message} {guidance}",
                        'valid': False,
                        'field': field_name,
                        'error': validation_message
                    })
            
            # If max attempts reached, accept the input but flag for review
            if not valid:
                console.print(Panel("I'll accept your input and mark this for later review. Let's continue with the form.", border_style="yellow"))
                completed_form[field_name]['value'] = raw_input
                completed_form[field_name]['needs_review'] = True
                completed_form[field_name]['review_reason'] = "Maximum validation attempts reached"
                self.needs_review.append(field_name)
                
                # Add to chat history
                self.chat_history.append({
                    'user': raw_input,
                    'assistant': "I'll accept your input and mark this for later review.",
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
    
    def _is_skip_request(self, user_input):
        """Check if user is trying to skip the field."""
        skip_patterns = [
            r'^(none|n\/a|na|not applicable|skip|empty|nil|null|not specified|unknown)$',
            r'^$'  # Empty input
        ]
        return any(re.match(pattern, user_input.lower().strip()) for pattern in skip_patterns)
    
    def _create_interactive_field_prompt(self, field_name, field_data):
        """Create a detailed prompt with examples for a specific field."""
        # Get the last few exchanges for context
        last_exchanges = self._get_last_exchanges()
        
        # Determine if the field is required
        is_required = field_data.get('required', False)
        required_text = "(Required)" if is_required else "(Optional)"
        
        field_type = field_data.get('type', 'text')
        display_name = field_data.get('label', self._format_field_name(field_name))
        description = field_data.get('description', '')
        
        # Build base prompt
        prompt = f"Please provide a value for {display_name}. {description} {required_text}\n"
        
        # Add examples based on field type and name
        examples = self._get_field_examples(field_name, field_type)
        if examples:
            prompt += f"Examples: {examples}\n"
            
        # Add skip instructions for optional fields
        if not is_required:
            prompt += "If not applicable, you can type 'none' or leave it empty to skip this field."
        
        # Add options for select fields
        if (field_type == 'select'):
            options = field_data.get('options', [])
            if options:
                prompt += "\nPlease select one of the following options (enter the number or option name):"
                for i, option in enumerate(options):
                    option_text = option.get('text', option.get('value', ''))
                    prompt += f"\n{i+1}. {option_text}"
        
        # Return the prompt and context
        return prompt, last_exchanges
    
    def _get_field_examples(self, field_name, field_type):
        """Provide contextually appropriate examples, using form context and LLM if available."""
        # Try to generate examples using LLM if available
        if self.form_context and hasattr(self.llm_interface, "generate_examples"):
            try:
                llm_examples = self.llm_interface.generate_examples(
                    field_name=field_name,
                    field_type=field_type,
                    form_context=self.form_context
                )
                if llm_examples:
                    # If LLM returns a string, split by commas
                    if isinstance(llm_examples, str):
                        examples = [e.strip() for e in llm_examples.split(",") if e.strip()]
                        if examples:
                            return ", ".join(examples)
                    # If LLM returns a list, join as string
                    elif isinstance(llm_examples, list):
                        return ", ".join(str(e) for e in llm_examples)
                    # Otherwise, fallback
                    return str(llm_examples)
            except Exception as e:
                console.print(Panel(f"[yellow]LLM failed to generate examples for '{field_name}': {e}[/yellow]", title="LLM Example Warning", border_style="yellow"))
                # Fallback to default value if LLM fails
                
        return "Appropriate text for this field"
    
    def _format_field_name(self, field_name):
        """Format field name for display (convert snake_case to Title Case)."""
        return " ".join(word.capitalize() for word in field_name.split('_'))
    
    def _validate_input_with_context(self, field_name, field_data, user_input, last_exchanges):
        """Validate user input with improved context awareness."""
        field_type = field_data.get('type', 'text')
        is_required = field_data.get('required', False)
        display_name = field_data.get('label', self._format_field_name(field_name))
        
        # Handle empty input for required fields
        if is_required and not user_input.strip():
            return False, f"This field is required. Please provide a value for {display_name}.", None
        
        # For select fields, use dedicated validation
        if field_type == 'select':
            return self._validate_select_input(field_data, user_input)
        
        # Apply context-aware validation
        # For medical abbreviations and short terms, be more lenient
        field_name_lower = field_name.lower()
        
        # Common medical abbreviations and short terms dictionary
        medical_abbreviations = {
            'mri': 'Magnetic Resonance Imaging',
            'ct': 'Computed Tomography',
            'us': 'Ultrasound',
            'xr': 'X-Ray',
            'cxr': 'Chest X-Ray',
            'pet': 'Positron Emission Tomography',
            'np': 'No Pain',
            'nad': 'No Acute Distress',
            'wdwn': 'Well-Developed, Well-Nourished'
        }
        
        # Check if input is a known medical abbreviation
        if user_input.strip().lower() in medical_abbreviations:
            expanded = medical_abbreviations[user_input.strip().lower()]
            return True, None, f"{user_input.upper()} ({expanded})"
        
        # Prepare validation prompt for LLM with improved context
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
            "validation_rules": self._get_flexible_validation_rules(field_name, field_type),
            "is_medical_form": True
        }
        
        # Call LLM for validation with improved context awareness
        try:
            validation_result = self.llm_interface.validate_input(validation_prompt)
            
            # Parse validation result
            if isinstance(validation_result, dict):
                is_valid = validation_result.get('is_valid', False)
                message = validation_result.get('message', '')
                processed_value = validation_result.get('processed_value', user_input)
                
                # For short clinical inputs that passed LLM validation, accept them
                if is_valid and len(user_input.strip()) >= 2:
                    return True, message, processed_value
                
                # For failed validations, provide specific feedback
                if not is_valid:
                    return False, message, None
            
            # Fallback to flexible validation for medical terms
            return self._flexible_medical_validation(field_name, field_data, user_input)
            
        except Exception as e:
            print(f"Error during LLM validation: {str(e)}")
            # Fallback to flexible validation
            return self._flexible_medical_validation(field_name, field_data, user_input)
    
    def _get_flexible_validation_rules(self, field_name, field_type):
        """Get more flexible validation rules based on field name and type."""
        rules = {}
        
        # Common validation rules by field type
        type_rules = {
            "date": {
                "format": "MM/DD/YYYY",
                "min_year": 1900,
                "max_year": 2100,
                "allow_formats": ["MM/DD/YYYY", "MM-DD-YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]
            },
            "number": {
                "min": None,  # No minimum value
                "allow_decimals": True
            },
            "email": {
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            }
        }
        
        # Add type-specific rules
        if field_type in type_rules:
            rules.update(type_rules[field_type])
        
        # Field-specific rules based on field name - more flexible than before
        field_name_lower = field_name.lower()
        
        if "name" in field_name_lower:
            rules["min_length"] = 1  # More flexible
            rules["max_length"] = 100
            rules["pattern"] = r"^[A-Za-z\s\-'.]+$"
            rules["description"] = "Name should contain only letters, spaces, hyphens, and apostrophes."
        elif "diagnosis" in field_name_lower or "impression" in field_name_lower:
            rules["min_length"] = 2  # More flexible - allow short diagnoses
            rules["description"] = "Medical diagnosis should be specific."
        elif "procedure" in field_name_lower:
            rules["min_length"] = 2  # Allow abbreviations like "MRI"
            rules["allow_abbreviations"] = True
            rules["description"] = "Procedure name, can include common medical abbreviations."
        elif "clinical" in field_name_lower and "information" in field_name_lower:
            rules["min_length"] = 3  # More flexible
            rules["description"] = "Clinical information about patient symptoms or context."
        
        return rules
    
    def _flexible_medical_validation(self, field_name, field_data, user_input):
        """Perform more flexible validation for medical terms."""
        field_type = field_data.get('type', 'text')
        display_name = field_data.get('label', self._format_field_name(field_name))
        input_text = user_input.strip()
        
        # Validation specific to medical field types
        field_name_lower = field_name.lower()
        
        # Accept common medical abbreviations and terms regardless of length
        common_medical_terms = [
            'mri', 'ct', 'pet', 'us', 'xr', 'ekg', 'ecg', 'cbc', 'wbc', 'rbc', 
            'bp', 'hr', 'sob', 'cp', 'mi', 'cva', 'tia', 'uti', 'bph', 'gerd', 
            'dm', 'htn', 'chf', 'copd', 'ra', 'sle', 'oa', 'fx', 'nad'
        ]
        
        # Check if input is an accepted medical term
        if input_text.lower() in common_medical_terms:
            return True, None, input_text.upper()
        
        # Validate based on field type with more flexibility
        if field_type == 'date':
            # More flexible date validation
            date_patterns = [
                r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}',  # MM/DD/YYYY or DD/MM/YYYY
                r'\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}',    # YYYY/MM/DD
                r'\d{1,2}[/\-\.]\d{4}'                   # MM/YYYY
            ]
            if any(re.match(pattern, input_text) for pattern in date_patterns):
                return True, None, input_text
            return False, f"Please enter a valid date format for {display_name}.", None
            
        elif field_type == 'number':
            # More flexible number validation
            if re.match(r'^-?\d*\.?\d+$', input_text):
                return True, None, input_text
            return False, f"Please enter a valid number for {display_name}.", None
            
        elif field_type == 'email':
            # Basic email validation
            if '@' in input_text and '.' in input_text.split('@')[1]:
                return True, None, input_text
            return False, f"Please enter a valid email address for {display_name}.", None
        
        # For text fields, be much more flexible
        if field_type in ['text', 'textarea']:
            # Accept any input that's not completely nonsensical
            if not self._is_completely_random(input_text):
                return True, None, input_text
            
            return False, f"Your input appears to be random characters. Please provide meaningful information for {display_name}.", None
        
        # Default to accepting the input
        return True, None, input_text
    
    def _is_completely_random(self, user_input):
        """Check if input appears to be completely random characters (less strict than before)."""
        # Only reject inputs that appear to be keyboard mashing
        random_patterns = [
            r'^[asdfjkl;]+$',             # Home row mashing
            r'^[qwerty]+$',               # Top row mashing
            r'^[zxcvbnm]+$',              # Bottom row mashing
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{10,}$'  # Very complex random string
        ]
        
        # Consider input random only if it matches a random pattern AND is longer than 8 chars
        return any(re.match(pattern, user_input.lower()) for pattern in random_patterns) and len(user_input) > 8
    
    def _validate_select_input(self, field_data, user_input):
        """Validate input for select-type fields with improved matching."""
        options = field_data.get('options', [])
        option_values = [opt.get('value', '') for opt in options]
        option_texts = [opt.get('text', opt.get('value', '')) for opt in options]
        
        # Check if input is empty (allow for optional fields)
        if not user_input.strip():
            return True, None, ""
        
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
                # Check for partial matches with fuzzy matching
                matches = []
                user_input_lower = user_input.lower()
                
                for i, text in enumerate(option_texts):
                    # Check if user input is a substring of the option
                    if user_input_lower in text.lower():
                        matches.append((i, text))
                    # Check if option is a substring of the user input
                    elif text.lower() in user_input_lower:
                        matches.append((i, text))
                    # Check for similarity (first character match)
                    elif text.lower().startswith(user_input_lower[0]):
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
                    # No matches - but be lenient and accept if there aren't too many options
                    if len(options) <= 3:
                        # For few options, show all options again
                        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(option_texts)])
                        return False, f"Invalid selection. Please choose one of these options:\n{options_str}", None
                    else:
                        # For many options, just accept and flag for review
                        return True, None, user_input + " (needs verification)"
    
    def _generate_guidance(self, field_name, field_data, user_input, attempt):
        """Generate helpful guidance based on failed attempt count."""
        field_type = field_data.get('type', 'text')
        display_name = field_data.get('label', self._format_field_name(field_name))
        
        if attempt == 1:
            # First attempt - provide gentle guidance
            examples = self._get_field_examples(field_name, field_type)
            return f"For example: {examples}"
        elif attempt == 2:
            # Second attempt - provide more specific guidance
            if field_type == 'date':
                return "You can enter a date like MM/DD/YYYY (e.g., 04/18/2025)."
            elif field_type == 'number':
                return "Please enter a numeric value (e.g., 42 or 7.5)."
            elif field_type == 'email':
                return "Please enter a valid email address (e.g., name@example.com)."
            elif field_type == 'select':
                return "You can enter the number or the exact text of one of the options."
            else:
                return f"For {display_name}, you can enter any relevant information. If there is none, you can type 'none'."
        else:
            # Last attempt - offer an escape option
            is_required = field_data.get('required', False)
            if is_required:
                return "This is a required field. Please provide any relevant information to continue."
            else:
                return "This field is optional. You can type 'none' or leave it empty to skip."
