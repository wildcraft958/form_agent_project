# main.py (modified)
import os
import json
import re
from dotenv import load_dotenv
from src.html_converter import convert_html_to_json
from src.JSON_converter import convert_json_to_html
from src.llm_handler import LLMHandler
from src.chat_history import ChatHistoryManager
from src.form_processor import FormProcessor
from src.radreport_api import RadReportAPI
from src.template_navigator import TemplateNavigator
from src.radreport_converter import RadReportConverter

# Load environment variables
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

def enhance_form_schema(form_json):
    """Enhance the form schema with additional metadata for better interaction."""
    enhanced_form = dict(form_json)
    
    # Add field descriptions and validation metadata
    field_metadata = {
        "patient_name": {
            "description": "Enter the patient's full legal name as it appears on their medical records.",
            "validation": r"^[A-Za-z\s\-'.]+$",
            "validation_message": "Name should contain only letters, spaces, hyphens, and apostrophes."
        },
        "patient_dob": {
            "description": "Enter the patient's date of birth in MM/DD/YYYY format.",
            "type": "date"
        },
        "patient_id": {
            "description": "Enter the patient's unique medical ID number or insurance identifier."
        },
        "diagnosis": {
            "description": "Enter the patient's diagnosis or reason for prescription.",
            "type": "textarea"
        },
        "medication": {
            "description": "Enter the prescribed medication name (generic or brand name)."
        },
        "dosage": {
            "description": "Enter the prescribed dosage amount (e.g., 500mg, 10ml).",
            "validation": r"^\d+(\.\d+)?\s*[a-zA-Z]+$",
            "validation_message": "Dosage should include a number followed by a unit (e.g., 10mg, 5ml)."
        },
        "frequency": {
            "description": "How often should the patient take this medication?",
            "type": "select"
        },
        "duration": {
            "description": "For how many days should the medication be taken?",
            "type": "number",
            "validation": r"^\d+$",
            "validation_message": "Duration should be a positive whole number of days."
        },
        "special_instructions": {
            "description": "Enter any special instructions for taking this medication (e.g., with food, before bedtime).",
            "type": "textarea",
            "required": False
        }
    }
    
    # Update form fields with enhanced metadata
    for field_name, metadata in field_metadata.items():
        if field_name in enhanced_form:
            enhanced_form[field_name].update(metadata)
    
    return enhanced_form

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
    """Main execution flow with enhanced error handling and user experience."""
    paths = get_project_paths()
    
    try:
        # File paths
        json_output_path = os.path.join(paths["samples"], "form_structure.json")
        filled_form_path = os.path.join(paths["samples"], "filled_form.json")
        
        # Step 1: Display welcome message
        print("\n=== Medical Form Assistant ===")
        print("This bot will help you complete a medical form.")
        print("I'll guide you through each field with explanations.")
        print("Let's get started!\n")
        
        # Step 2: Initialize API and navigator
        rad_report_api = RadReportAPI()
        template_navigator = TemplateNavigator(rad_report_api)
        template_converter = RadReportConverter()
        
        # Step 3: Ask user for form source choice
        print("\n=== Select Form Source ===")
        print("1. Use a RadReport template")
        print("2. Use a local HTML form")
        
        source_choice = input("Enter your choice (1 or 2): ")
        
        form_json = None
        
        if source_choice == "1":
            # Step 3a: Navigate RadReport templates
            print("\n=== Navigating RadReport Templates ===")
            template_data = template_navigator.navigate_templates()
            
            # Convert template to form JSON
            print("\n=== Converting Template to Form ===")
            form_json = template_converter.convert_template_to_form(template_data)
            
            # Save the template form JSON
            save_json_to_file(form_json, json_output_path)
        else:
            # Step 3b: Use local HTML form
            print("\n=== Using Local HTML Form ===")
            sample_form_path = os.path.join(paths["samples"], "medical_form.html")
            
            # Read HTML form
            print("\n=== Reading HTML Form ===")
            html_content = read_html_file(sample_form_path)
            if not html_content:
                return
            
            # Convert HTML to JSON
            print("\n=== Converting HTML to JSON ===")
            form_json = convert_html_to_json(html_content)
            if not form_json:
                print("Conversion failed: Empty JSON output")
                return
            
            # Enhance form with metadata
            form_json = enhance_form_schema(form_json)
            save_json_to_file(form_json, json_output_path)
        
        # Step 4: Initialize components
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
        
        # Step 5: Initialize the form processor
        form_processor = FormProcessor(llm_handler)
        form_processor.load_form(form_json)
        
        # Step 6: Process form with iterative user interaction
        print("\n=== Processing Form with Interactive Communication ===")
        filled_form = form_processor.process_form()
        
        # Step 7: Summarize collected information
        print("\n=== Form Completion Summary ===")
        print("Thank you for completing the medical form. Here's a summary of the information provided:")
        
        for field_name, field_data in filled_form.items():
            if not field_name.startswith('_') and not field_data.get('hidden', False):
                display_name = " ".join(word.capitalize() for word in field_name.split('_'))
                value = field_data.get('value', 'Not provided')
                print(f"- {display_name}: {value}")
        
        # Step 8: Save results
        print("\n=== Saving Results ===")
        save_json_to_file(filled_form, filled_form_path)
        
        # Step 9: Convert JSON to HTML
        print("\n=== Converting JSON to HTML ===")
        html_output_path = os.path.join(paths["samples"], "filled_form.html")
        html_content = convert_json_to_html(filled_form)
        
        if not html_content:
            print("Conversion failed: Empty HTML output")
            return
        
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\nOperation completed successfully!")
        print(f"Filled form saved to: {filled_form_path}")
        print(f"HTML version saved to: {html_output_path}")
    
    except Exception as e:
        print(f"\n!!! Critical Error: {str(e)}")
        
        if isinstance(e, ImportError):
            print("Please check your package installations")
        elif "API token" in str(e):
            print("Verify your .env file contains correct API credentials")

if __name__ == "__main__":
    main()
