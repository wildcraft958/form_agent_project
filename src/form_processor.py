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
        
        # Process each field
        for field_name, field_data in self.form_data.items():
            field_prompt = self._create_field_prompt(field_name, field_data)
            
            # Get response from LLM
            response = self.llm_interface.generate_response(
                prompt=field_prompt,
                system_prompt=system_prompt,
                chat_history=self.chat_history
            )
            
            # Update the form with the response
            if field_data['type'] == 'select':
                # For select fields, ensure response matches an option
                valid_options = [opt.get('text', opt.get('value', '')) for opt in field_data.get('options', [])]
                if response not in valid_options:
                    # Find closest match
                    for option in valid_options:
                        if option.lower() in response.lower():
                            response = option
                            break
                    else:
                        # If no match found, use first option
                        response = valid_options[0] if valid_options else ""
            
            completed_form[field_name]['value'] = response
            
            # Add to chat history
            self.chat_history.append({
                'user': field_prompt,
                'assistant': response
            })
        
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
