# llm_handler.py

import os
import json
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

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
            raise ImportError("Install 'langchain-ollama': pip install langchain-ollama")
        
        from langchain_ollama import ChatOllama
        
        try:
            # Ensure base_url has no trailing slash to avoid 404 errors
            base_url = "http://localhost:11434"
            
            return ChatOllama(
                model=self.model_name or "llama3",
                temperature=0.3,
                format="json",
                base_url=base_url
            )
        except Exception as e:
            if "404" in str(e):
                raise ValueError(f"Model '{self.model_name or 'llama3'}' not found. " 
                                f"Please run 'ollama pull {self.model_name or 'llama3'}' to download the model.")
            raise

    def _initialize_huggingface(self):
        """Initialize Hugging Face LLM with corrected implementation."""
        hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not hf_token:
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
            
        raise ImportError("Install 'langchain-huggingface' or 'langchain_community'")

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

    def process_form(self, form_data, user_query=None):
        """Process form with enhanced type checking."""
        # Handle the case where form_data is just a prompt string
        if isinstance(form_data, dict) and "prompt" in form_data and len(form_data) == 1:
            # This is a direct prompt request, not form processing
            try:
                return self._process_direct_prompt(form_data["prompt"], user_query)
            except Exception as e:
                print(f"Error processing prompt: {str(e)}")
                return {"reasoning": "Could not process prompt"}
                
        # Normal form processing logic
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
            # Fix the chain order - PromptTemplate first, then LLM
            chain = (
                prompt_template 
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
            print(f"Processing Error: {str(e)}")
            return self._get_empty_form(form_data)

    def _process_direct_prompt(self, prompt, context=None):
        """Process a direct prompt without form structure."""
        try:
            # Add context if provided
            if context:
                prompt = f"{context}\n\n{prompt}"
                
            # Format correctly for Ollama
            if self.model_type == "ollama":
                messages = [HumanMessage(content=prompt)]
                response = self.llm.invoke(messages)
            else:
                response = self.llm.invoke(prompt)
                
            # Handle different response formats
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
                
            # Try to parse as JSON if it looks like JSON
            if response_text.strip().startswith('{') and response_text.strip().endswith('}'):
                try:
                    return json.loads(response_text)
                except:
                    pass
                    
            # Return as reasoning if not JSON
            return {"reasoning": response_text}
        except Exception as e:
            print(f"Direct prompt processing error: {str(e)}")
            return {"reasoning": "Could not process prompt due to an error"}

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
        print("Attempting to recover from invalid response format...")
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

    def _call_llm(self, prompt):
        """Helper method to call LLM with consistent error handling"""
        try:
            # Format correctly for Ollama
            if self.model_type == "ollama":
                messages = [HumanMessage(content=prompt)]
                response = self.llm.invoke(messages)
            else:
                response = self.llm.invoke(prompt)
                
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except Exception as e:
            print(f"LLM Call Error: {str(e)}")
            raise
            
    def validate_input(self, field_info, user_input):
        """
        Use the LLM to validate a user input based on field information.
        """
        prompt = f"""
        You are a medical form validation assistant.
        Field information:
        Name: {field_info.get('name', '')}
        Type: {field_info.get('type', 'text')}
        Label: {field_info.get('label', '')}
        User input: {user_input}
        Is this input valid for this field? Consider:
        1. Data type correctness
        2. Format appropriateness
        3. Medical accuracy and reasonableness
        Return a JSON object with:
        {{"valid": true/false, "message": "explanation"}}
        """
        
        try:
            response = self._call_llm(prompt)
            try:
                result = json.loads(response.strip())
                return {
                    "valid": result.get("valid", False),
                    "message": result.get("message", "Invalid input")
                }
            except json.JSONDecodeError:
                # Fallback parsing
                valid = "valid: true" in response.lower() or "\"valid\": true" in response.lower()
                message = response.split("message:")[1].strip() if "message:" in response else "Invalid input"
                return {"valid": valid, "message": message}
        except Exception as e:
            print(f"Validation Error: {str(e)}")
            return {"valid": False, "message": f"Validation error: {str(e)}"}

    def suggest_validation_rules(self, field_info):
        """
        Use the LLM to suggest validation rules for a field.
        """
        prompt = f"""
        You are a medical form validation expert.
        Field information:
        Name: {field_info.get('name', '')}
        Type: {field_info.get('type', 'text')}
        Label: {field_info.get('label', '')}
        Suggest appropriate validation rules for this field, considering:
        1. Data type requirements
        2. Format constraints
        3. Minimum/maximum values
        4. Required status
        5. Medical context
        Return a JSON object with validation rules:
        {{
            "required": true/false,
            "pattern": "regex_pattern",
            "min": minimum_value,
            "max": maximum_value,
            "hint": "user-friendly hint"
        }}
        """
        
        try:
            response = self._call_llm(prompt)
            try:
                return json.loads(response.strip())
            except json.JSONDecodeError:
                # Fallback for invalid JSON
                return {
                    "required": "required: true" in response.lower(),
                    "hint": response.split("hint:")[1].strip() if "hint:" in response else ""
                }
        except Exception as e:
            print(f"Rule Suggestion Error: {str(e)}")
            return {}
