class FormProcessor:
    def __init__(self, llm_interface):
        """Initialize the Form Processor."""
        self.llm_interface = llm_interface
        self.form_data = None
        self.chat_history = []
    
    def load_form(self, form_json):
        """Load a form from JSON data."""
        self.form_data = form_json
    
    def process_form(self):
        if not self.form_data:
            print("Warning: No form data found. Creating sample data for testing.")
            # Create sample form data to prevent the error
            self.form_data = {
                "patient_name": {
                    "type": "text",
                    "value": "",
                    "placeholder": "Enter patient name",
                    "required": True
                },
                "diagnosis": {
                    "type": "textarea",
                    "value": "",
                    "placeholder": "Enter diagnosis",
                    "required": False
                }
            }
        
        completed_form = dict(self.form_data)
        
        # Create system prompt describing the form
        system_prompt = self._create_system_prompt()
        
        # Process each field iteratively with user interaction
        for field_name, field_data in self.form_data.items():
            while True:
                field_prompt = self._create_field_prompt(field_name, field_data)
                
                # Ask the user for input
                print(f"Bot: {field_prompt}")
                user_input = input("User: ")
                
                # Validate the user input
                if field_data['type'] == 'select':
                    valid_options = [opt.get('text', opt.get('value', '')) for opt in field_data.get('options', [])]
                    if user_input not in valid_options:
                        print(f"Bot: Invalid input. Please choose one of the following options: {', '.join(valid_options)}")
                        continue
                
                # Update the form with the user input
                completed_form[field_name]['value'] = user_input
                
                # Add to chat history
                self.chat_history.append({
                    'user': user_input,
                    'assistant': field_prompt
                })
                
                break
        
        return completed_form
    
    def _create_system_prompt(self):
        """Create a system prompt describing the form."""
        form_description = "You are an AI assistant helping to fill out a medical prescription form. "
        form_description += "The form has the following fields:\n"
        
        for field_name, field_data in self.form_data.items():
            field_type = field_data.get('type', 'text')
            required = "Required" if field_data.get('required', False) else "Optional"
            
            if field_type == 'select':
                options = [opt.get('text', opt.get('value', '')) for opt in field_data.get('options', [])]
                options_str = ", ".join(options)
                form_description += f"- {field_name}: {field_type.capitalize()} field ({required}). Options: {options_str}\n"
            else:
                form_description += f"- {field_name}: {field_type.capitalize()} field ({required})\n"
        
        form_description += "\nProvide accurate medical information for each field. Be specific and professional."
        
        return form_description
    
    def _create_field_prompt(self, field_name, field_data):
        """Create a prompt for a specific field."""
        field_type = field_data.get('type', 'text')
        placeholder = field_data.get('placeholder', '')
        
        prompt = f"Please provide a value for the {field_name} field."
        
        if placeholder:
            prompt += f" The placeholder suggests: '{placeholder}'."
        
        if field_type == 'textarea':
            prompt += " Please provide a detailed response."
        elif field_type == 'select':
            options = [opt.get('text', opt.get('value', '')) for opt in field_data.get('options', [])]
            options_str = ", ".join(options)
            prompt += f" Choose one of the following options: {options_str}."
        
        return prompt
