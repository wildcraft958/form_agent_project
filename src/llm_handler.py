import os
import json
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

    def generate_examples(self, field_name, field_type, form_context=None):
        """
        Generate example values for a given field using the LLM.
        """
        prompt = (
            f"You are helping to fill out a medical form.\n"
            f"Field: {field_name} (type: {field_type})\n"
        )
        if form_context:
            prompt += f"Form context: {form_context}\n"
        prompt += (
            "Give 3 realistic example values for this field, separated by commas. "
            "Be concise and use appropriate medical terminology."
        )

        try:
            # Use your LLM to generate examples
            response = self.llm.invoke(prompt)
            # Try to extract examples from the response
            if isinstance(response, str):
                # Split by commas and strip whitespace
                examples = [ex.strip() for ex in response.split(",") if ex.strip()]
                return examples
            return []
        except Exception as e:
            console.print(Panel(f"[red]Error generating examples for {field_name}: {e}[/red]", title="LLM Example Error", border_style="red"))
            return []
