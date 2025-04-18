import os
import json
import re
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

console = Console()
load_dotenv()

def is_package_available(package_name):
    """Check if a Python package is available."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

class LLMHandler:
    def __init__(self, model_type="huggingface", history_manager=None, model_name=None):
        self.model_type = model_type.lower()
        self.history_manager = history_manager
        self.model_name = model_name
        self.llm = self._initialize_llm()
        
        # Initialize domain-specific examples dictionary
        self.domain_examples = self._initialize_domain_examples()
    
    def _initialize_llm(self):
        """Initialize the appropriate LLM with error handling."""
        if self.model_type == "ollama":
            return self._initialize_ollama()
        elif self.model_type == "huggingface":
            return self._initialize_huggingface()
        raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def _initialize_ollama(self):
        """Initialize Ollama LLM with proper configuration."""
        if not is_package_available("langchain_ollama"):
            console.print(Panel("[red]Install 'langchain-ollama': pip install langchain-ollama[/red]", title="Import Error", border_style="red"))
            raise ImportError("Install 'langchain-ollama': pip install langchain-ollama")
        
        from langchain_ollama import ChatOllama
        
        return ChatOllama(
            model=self.model_name or "llama3",
            temperature=0.3,
            format="json"
        )
    
    def _initialize_huggingface(self):
        """Initialize Hugging Face LLM with corrected implementation."""
        hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not hf_token:
            console.print(Panel("[red]HUGGINGFACEHUB_API_TOKEN required in .env[/red]", title="Token Error", border_style="red"))
            raise ValueError("HUGGINGFACEHUB_API_TOKEN required in .env")
        
        if is_package_available("langchain_huggingface"):
            from langchain_huggingface import HuggingFaceEndpoint
            
            return HuggingFaceEndpoint(
                repo_id=self.model_name or "ruslanmv/Medical-Llama3-8B",
                task="text-generation",
                max_new_tokens=512,
                temperature=0.3,
                huggingfacehub_api_token=hf_token
            )
        
        if is_package_available("langchain_community.llms"):
            from langchain_community.llms import HuggingFaceHub
            
            return HuggingFaceHub(
                repo_id=self.model_name or "ruslanmv/Medical-Llama3-8B",
                huggingfacehub_api_token=hf_token,
                model_kwargs={"temperature": 0.3, "max_length": 512}
            )
        
        console.print(Panel("[red]Install 'langchain-huggingface' or 'langchain_community'[/red]", title="Import Error", border_style="red"))
        raise ImportError("Install 'langchain-huggingface' or 'langchain_community'")
    
    def validate_input(self, validation_prompt):
        """
        Validate user input using LLM reasoning with improved medical context.
        
        Args:
            validation_prompt: Dict containing validation requirements and user input
            
        Returns:
            Dict with validation result: {is_valid: bool, message: str, processed_value: str}
        """
        # Add medical context to the validation prompt
        validation_prompt["domain"] = "medical"
        validation_prompt["be_lenient"] = True
        
        # Convert the validation prompt to a string for the LLM
        validation_str = json.dumps(validation_prompt, indent=2)
        
        prompt_template = PromptTemplate(
            template="""You are a medical form validation assistant.

                Please analyze the following user input for a medical form field and determine if it is valid.
                Be lenient with medical terminology and abbreviations - they are often short but valid.

                Consider the context:
                1. This is a MEDICAL form, so standard medical abbreviations are acceptable
                2. Short answers can be valid for medical fields (e.g., "MRI" is valid for procedure)
                3. Prioritize accepting input unless it's clearly nonsensical

                Validation Request:
                {validation_str}

                Return your analysis as JSON with the following structure:
                {{
                    "is_valid": true/false,
                    "message": "Explanation message or validation error",
                    "processed_value": "The processed value (if valid) or null (if invalid)"
                }}

                JSON Response:""",
                        input_variables=["validation_str"]
                    )
        
        try:
            chain = (
                {"validation_str": lambda x: x}
                | prompt_template
                | self.llm
                | StrOutputParser()
            )
            
            response = chain.invoke(validation_str)
            
            # Parse the JSON response
            try:
                json_response = json.loads(response.strip())
                return json_response
            except json.JSONDecodeError:
                # Handle non-JSON responses
                if "is_valid" in response.lower():
                    # Try to extract key elements from non-JSON response
                    is_valid = "true" in response.lower() and "false" not in response.lower()
                    return {
                        "is_valid": is_valid,
                        "message": "Response parsing error, but input appears " + ("valid" if is_valid else "invalid"),
                        "processed_value": validation_prompt["user_input"] if is_valid else None
                    }
                else:
                    # Default to accepting the input to avoid frustration
                    return {
                        "is_valid": True,
                        "message": "Unable to validate clearly, accepting input.",
                        "processed_value": validation_prompt["user_input"]
                    }
        except Exception as e:
            console.print(Panel(f"[red]Error during validation: {e}[/red]", title="Validation Error", border_style="red"))
            # Return default response in case of errors - be lenient
            return {
                "is_valid": True,
                "message": "Validation service encountered an error. Accepting input.",
                "processed_value": validation_prompt["user_input"]
            }

    
    def process_form(self, form_data, user_query=None):
        """Process form with enhanced type checking."""
        system_prompt = self.create_system_prompt(form_data)
        user_query = user_query or "Fill this medical form accurately."
        
        # Generate safe form description
        form_description = []
        for field, info in form_data.items():
            field_type = "text"
            if isinstance(info, dict):
                field_type = info.get("type", "text")
            form_description.append(f"{field}: {field_type}")
            
        prompt_template = PromptTemplate(
            template="""{system_prompt}

Current Form Structure:
{form_description}

User Request: {user_query}

Output JSON:""",
            input_variables=["system_prompt", "form_description", "user_query"]
        )
        
        try:
            chain = (
                RunnablePassthrough.assign(
                    system_prompt=lambda x: x["system_prompt"],
                    form_description=lambda x: "\n".join(x["form_description"]),
                    user_query=lambda x: x["user_query"]
                )
                | prompt_template
                | self.llm
                | StrOutputParser()
            )
            
            response = chain.invoke({
                "system_prompt": system_prompt,
                "form_description": form_description,
                "user_query": user_query
            })
            
            return self._safe_parse_response(form_data, response)
            
        except Exception as e:
            console.print(Panel(f"[red]Processing Error: {str(e)}[/red]", title="Processing Error", border_style="red"))
            return self._get_empty_form(form_data)
    
    def create_system_prompt(self, form_data):
        """Generate structured system prompt with type safety."""
        prompt = [
            "You are a medical AI assistant filling out a JSON form. Rules:",
            "1. Use exact field names from the form",
            "2. Provide valid medical values",
            "3. Output format: {\"field_name\": \"value\"}",
            "\nForm fields:"
        ]
        
        for field, info in form_data.items():
            # Handle both dict and string field definitions
            if isinstance(info, dict):
                label = info.get("label", field)
                field_type = info.get("type", "text")
                options = info.get("options")
            else:
                label = str(info)
                field_type = "text"
                options = None
                
            desc = f"- {label} (Field: {field}, Type: {field_type})"
            if options:
                desc += f", Options: {', '.join(map(str, options))}"
            prompt.append(desc)
        
        return "\n".join(prompt)
    
    def _safe_parse_response(self, original_form, response):
        """Safely parse response while preserving original structure."""
        try:
            parsed = json.loads(response.strip())
            return self._update_form_structure(original_form, parsed)
        except json.JSONDecodeError:
            return self._handle_invalid_response(original_form, response)
    
    def _update_form_structure(self, original_form, parsed_data):
        """Update original form structure with parsed values."""
        updated_form = original_form.copy()
        
        for field, info in updated_form.items():
            # Handle both dict and string field definitions
            if isinstance(info, dict):
                info["value"] = parsed_data.get(field, "")
            else:
                updated_form[field] = {
                    "value": parsed_data.get(field, ""),
                    "original": info
                }
        
        return updated_form
    
    def _handle_invalid_response(self, original_form, response):
        """Fallback parsing for invalid responses."""
        console.print(Panel("[yellow]Attempting to recover from invalid response format...[/yellow]", title="Recovery", border_style="yellow"))
        pairs = {}
        
        for line in response.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                pairs[key.strip()] = val.strip()
                
        return self._update_form_structure(original_form, pairs)
    
    def _get_empty_form(self, original_form):
        """Return original form structure with empty values."""
        empty_form = original_form.copy()
        
        for field, info in empty_form.items():
            if isinstance(info, dict):
                info["value"] = ""
            else:
                empty_form[field] = {"value": "", "original": info}
                
        return empty_form

    def _initialize_domain_examples(self):
        """Initialize dictionary of domain-specific examples."""
        return {
            # Patient information fields
            "patient_name": ["John Smith", "Maria Rodriguez", "Aisha Patel"],
            "date_of_birth": ["05/12/1985", "10/23/1972", "01/30/1995"],
            "mrn": ["MRN12345", "456789", "PT-987654"],
            "patient_id": ["PT-12345", "ID98765", "MRN-54321"],
            
            # Vital signs
            "temperature": ["98.6 F", "37.0 C", "99.1 F"],
            "blood_pressure": ["120/80 mmHg", "135/85 mmHg", "110/70 mmHg"],
            "heart_rate": ["72 bpm", "85 bpm", "64 bpm"],
            "respiratory_rate": ["16/min", "18/min", "14/min"],
            
            # Common medical fields
            "diagnosis": ["Acute Myocardial Infarction", "Type 2 Diabetes Mellitus", 
                          "Community-acquired Pneumonia"],
            "symptoms": ["Chest pain radiating to left arm", "Persistent dry cough for 2 weeks", 
                         "Fatigue and shortness of breath"],
            "allergies": ["Penicillin", "No known allergies", "Sulfa drugs, Shellfish"],
            "medications": ["Lisinopril 10mg daily", "Metformin 500mg BID, Atorvastatin 20mg daily", 
                            "None"],
            
            # Radiology specific
            "impression": ["No acute intracranial abnormality", 
                          "Bibasilar atelectasis without evidence of pneumonia", 
                          "Mild degenerative changes of the lumbar spine"],
            "findings": ["Normal heart size. No focal consolidation.", 
                        "There is a 2.5 cm hypodense lesion in the right lobe of the liver", 
                        "Unremarkable study without evidence of fracture or dislocation"],
            "technique": ["CT head without contrast", "Portable AP chest radiograph", 
                         "MRI of the right knee without contrast"],
            
            # Procedure related
            "procedure": ["Colonoscopy", "Cardiac Catheterization", "Total Hip Arthroplasty"],
            "indication": ["Screening for colorectal cancer", "Evaluation of chest pain", 
                          "Progressive joint pain unresponsive to conservative treatment"],
            
            # Dates and times
            "date": ["04/18/2025", "05/22/2025", "03/15/2025"],
            "time": ["14:30", "08:45", "16:15"],
            
            # General
            "comments": ["Patient tolerated procedure well", "Follow-up in 2 weeks", 
                        "Contact patient's cardiologist for further recommendations"],
            
            # Pathology specific
            "specimen": ["Left breast core biopsy", "Right colon, partial resection", 
                        "Liver, right lobe, needle biopsy"],
            "gross_description": ["The specimen consists of three cores of tan-white soft tissue", 
                                 "A segment of colon measuring 15 cm in length with attached mesentery", 
                                 "Multiple fragments of tan-brown tissue"],
            "microscopic_description": ["Sections show infiltrating ductal carcinoma", 
                                       "Sections reveal colonic mucosa with adenomatous change", 
                                       "Liver parenchyma with macrovesicular steatosis"],
            
            # Laboratory
            "lab_result": ["Hemoglobin: 13.5 g/dL", "Glucose: 95 mg/dL", "TSH: 2.1 uIU/mL"],
            "lab_value": ["120 mg/dL", "6.7%", "3.5 mmol/L"],
            "reference_range": ["3.5-5.0 mmol/L", "70-99 mg/dL", "12.0-15.5 g/dL"]
        }

    def generate_examples(self, field_name, field_type, form_context=None, form_structure=None):
        """
        Generate contextually appropriate example values for a given field using the LLM.
        
        Args:
            field_name (str): Name of the field
            field_type (str): Type of the field (text, number, date, etc.)
            form_context (str, optional): Context about the form
            form_structure (dict, optional): Structure of the form with other fields
            
        Returns:
            list: List of example values
        """
        # Extract field details for better context
        field_display = self._format_field_name(field_name)
        
        # Determine the domain from context or default to medical
        domain = "medical"
        if form_context:
            if "radiology" in form_context.lower():
                domain = "radiology"
            elif "cardiology" in form_context.lower():
                domain = "cardiology"
            elif "pathology" in form_context.lower():
                domain = "pathology"
            elif "laboratory" in form_context.lower() or "lab" in form_context.lower():
                domain = "laboratory"
        
        # Build a more structured prompt
        prompt = f"""You are a {domain} professional helping to generate realistic example values for a form field.

Field Name: {field_name}
Display Name: {field_display}
Field Type: {field_type}
"""
        
        # Add form context if available
        if form_context:
            prompt += f"\nForm Context:\n{form_context}\n"
        
        # Add form structure context if available
        if form_structure:
            related_fields = []
            # Find related fields (fields that might be related to the current one)
            for f_name, f_info in form_structure.items():
                if f_name != field_name and not f_name.startswith('_'):
                    # Check if field names share common terms
                    if isinstance(f_name, str) and isinstance(field_name, str):
                        common_terms = set(field_name.lower().split('_')).intersection(
                            set(f_name.lower().split('_'))
                        )
                        if common_terms:
                            f_label = f_info.get('label', self._format_field_name(f_name)) if isinstance(f_info, dict) else f_name
                            related_fields.append(f"{f_label} ({f_name})")
            
            if related_fields:
                prompt += "\nRelated Fields:\n- " + "\n- ".join(related_fields) + "\n"
        
        # Add field-specific context based on common patterns
        field_name_lower = field_name.lower()
        
        # Add examples from our dictionary if we have them
        field_examples = []
        
        # Try exact match first
        if field_name_lower in self.domain_examples:
            field_examples = self.domain_examples[field_name_lower]
        else:
            # Try to find partial matches
            for key in self.domain_examples.keys():
                if key in field_name_lower or any(term in field_name_lower for term in key.split('_')):
                    field_examples = self.domain_examples[key]
                    break
        
        # If we found matching examples, add them to the prompt
        if field_examples:
            prompt += f"\nHere are some example values for similar fields:\n"
            for example in field_examples:
                prompt += f"- {example}\n"
        
        # Add specific instructions based on field type
        type_instructions = {
            "date": "Provide 3 realistic dates in MM/DD/YYYY format, relevant to this context.",
            "number": "Provide 3 realistic numeric values (with appropriate units if applicable).",
            "email": "Provide 3 realistic email addresses relevant to this context.",
            "phone": "Provide 3 realistic phone numbers in the format (XXX) XXX-XXXX.",
            "textarea": "Provide 3 brief but realistic text entries, each 1-2 sentences long.",
            "select": "Provide 3 options that might appear in a dropdown for this field.",
            "radio": "Provide 3 options that might be selected for this field.",
            "checkbox": "Provide 3 options that might be checked for this field."
        }
        
        # Add type-specific instructions or default to text
        prompt += f"\n{type_instructions.get(field_type, 'Provide 3 realistic example values for this field.')}"
        
        # Final guidance
        prompt += """

Important guidelines:
1. Provide EXACTLY 3 different examples
2. Separate examples with commas
3. Keep each example concise and realistic
4. Use appropriate terminology for the domain
5. Format appropriately for the field type
6. DO NOT number your examples or add extra explanations
7. DO NOT prefix examples with "Example 1:", etc.

Your 3 examples (comma separated):"""
        
        try:
            # Invoke the LLM with the enhanced prompt
            response = self.llm.invoke(prompt)
            
            # Process and validate the response
            if isinstance(response, str):
                # Clean up the response - remove any prefixes like "Example 1:" etc.
                cleaned_response = re.sub(r'Example \d+:\s*', '', response)
                cleaned_response = re.sub(r'^\d+\.\s*', '', cleaned_response, flags=re.MULTILINE)
                
                # Split by commas and clean whitespace
                examples = [ex.strip() for ex in cleaned_response.split(",") if ex.strip()]
                
                # Basic validation to ensure we have reasonable examples
                validated_examples = []
                for ex in examples:
                    # Validate length - reject extremely short or long examples
                    if 2 <= len(ex) <= 100:
                        validated_examples.append(ex)
                
                # If we have examples, return them
                if validated_examples:
                    # Limit to 3 examples
                    return validated_examples[:3]
            
            # If we get here, we either have no response or no valid examples
            # Fallback to field-specific examples if we have them
            if field_examples:
                return field_examples[:3]
                
            # Otherwise use general fallbacks based on field type
            fallbacks = {
                "date": ["04/18/2025", "05/22/2025", "03/15/2025"],
                "number": ["42", "7.5", "100"],
                "email": ["example@hospital.org", "doctor@clinic.com", "patient@email.com"],
                "phone": ["(555) 123-4567", "(555) 987-6543", "(555) 555-5555"],
                "textarea": ["Normal findings", "Patient responded well to treatment", 
                            "No significant abnormalities"],
                "text": ["Sample text", "Example entry", "Test value"]
            }
            
            return fallbacks.get(field_type, ["Example 1", "Example 2", "Example 3"])
            
        except Exception as e:
            console.print(Panel(f"[red]Error generating examples for {field_name}: {e}[/red]", 
                               title="LLM Example Error", border_style="red"))
            
            # Return field-specific fallbacks if available
            if field_examples:
                return field_examples[:3]
                
            # Otherwise fallback to very generic examples
            return ["Example value", "Sample entry", "Test data"]
            
    def _format_field_name(self, field_name):
            """Format field name for display (convert snake_case to Title Case)."""
            return " ".join(word.capitalize() for word in field_name.split('_'))

   