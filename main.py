import os
import json
from dotenv import load_dotenv
from src.html_converter import convert_html_to_json
from src.JSON_converter import convert_json_to_html
from src.llm_handler import LLMHandler
from src.chat_history import ChatHistoryManager

# Load environment variables first
load_dotenv()

def read_html_file(file_path):
    """Read HTML file content with improved error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"Unexpected error reading file: {str(e)}")
        return None

def save_json_to_file(json_data, file_path):
    """Save JSON data to file with directory creation."""
    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        print(f"Successfully saved JSON to {file_path}")
    except Exception as e:
        print(f"Error saving JSON file: {str(e)}")

def get_project_paths():
    """Get standardized project paths."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    samples_dir = os.path.join(base_dir, "form_agent_project", "samples")
    return {
        "base": base_dir,
        "samples": samples_dir,
        "history": os.path.join(base_dir, "chat_history.json")
    }

def main():
    """Main execution flow with enhanced error handling."""
    paths = get_project_paths()
    
    try:
        # File paths
        sample_form_path = os.path.join(paths["samples"], "medical_form.html")
        json_output_path = os.path.join(paths["samples"], "form_structure.json")
        filled_form_path = os.path.join(paths["samples"], "filled_form.json")

        # Step 1: Read HTML form
        print("\n=== Reading HTML Form ===")
        html_content = read_html_file(sample_form_path)
        if not html_content:
            return

        # Step 2: Convert HTML to JSON
        print("\n=== Converting HTML to JSON ===")
        form_json = convert_html_to_json(html_content)
        if not form_json:
            print("Conversion failed: Empty JSON output")
            return
            
        save_json_to_file(form_json, json_output_path)

        # Step 3: Initialize components
        print("\n=== Initializing Components ===")
        history_manager = ChatHistoryManager(history_file=paths["history"])
        
        model_type = os.getenv("MODEL_TYPE", "ollama").lower()
        if model_type not in ["ollama", "huggingface"]:
            raise ValueError(f"Invalid MODEL_TYPE: {model_type}. Choose 'ollama' or 'huggingface'")

        llm_handler = LLMHandler(
            model_type=model_type,
            history_manager=history_manager,
            model_name=os.getenv("MODEL_NAME")  # Get specific model from env
        )

        # Step 4: Process form with LLM
        print(f"\n=== Processing Form with {model_type.upper()} ===")
        user_query = os.getenv("USER_QUERY", "Please fill out this medical form with appropriate information")

        filled_form = llm_handler.process_form(form_json, user_query=user_query)
        
        # Access values safely
        for field, info in filled_form.items():
            if isinstance(info, dict):
                value = info.get("value", "")
            else:
                value = ""  # Handle simple format case
            print(f"{field}: {value}")
        
        if not any(field.get('value') for field in filled_form.values()):
            print("\033[91mWarning: Form fields not populated properly\033[0m")
            # Implement additional error handling

        if not filled_form:
            raise RuntimeError("Form processing failed: Empty response from LLM")

        # Step 5: Save results
        print("\n=== Saving Results ===")
        save_json_to_file(filled_form, filled_form_path)
        
        print("\nOperation completed successfully!")
        print(f"Filled form saved to: {filled_form_path}")
        
        #Step 6: Convert JSON to HTML
        print("\n=== Converting JSON to HTML ===")
        html_output_path = os.path.join(paths["samples"], "filled_form.html")
        # Convert JSON to HTML
        html_content = convert_json_to_html(filled_form)
        if not html_content:
            print("Conversion failed: Empty HTML output")
            return
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Successfully saved HTML to {html_output_path}")
        

    except Exception as e:
        print(f"\n!!! Critical Error: {str(e)}")
        if isinstance(e, ImportError):
            print("Please check your package installations")
        elif "API token" in str(e):
            print("Verify your .env file contains correct API credentials")

if __name__ == "__main__":
    main()
